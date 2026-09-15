"""Tests for the YAML scenario schema and its checks against the topology."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from faultline_noc.models import FaultClass
from faultline_noc.paths import DEFAULT_SCENARIOS_DIR
from faultline_noc.scenario import (
    ExpectedLabel,
    FaultSpec,
    Scenario,
    check_against_topology,
    load_scenario,
)
from faultline_noc.topology import Topology
from tests.conftest import SCENARIO_IDS


def test_all_required_scenarios_load(scenarios: dict[str, Scenario]) -> None:
    """The four slice scenarios are present and valid."""
    assert tuple(sorted(scenarios)) == SCENARIO_IDS


def test_scenarios_reference_known_nodes(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """Every node a scenario names exists in the topology."""
    for scenario in scenarios.values():
        check_against_topology(scenario, topology)


def test_fault_start_outside_scenario_is_rejected(scenarios: dict[str, Scenario]) -> None:
    """A fault that starts after the last tick fails validation."""
    raw = scenarios["s01_upf_crashloop"].model_dump(mode="json")
    raw["fault"]["start_tick"] = raw["ticks"]
    with pytest.raises(ValidationError):
        Scenario.model_validate(raw)


def test_injection_outside_scenario_is_rejected(scenarios: dict[str, Scenario]) -> None:
    """A log injection after the last tick fails validation."""
    raw = scenarios["s07_log_injection"].model_dump(mode="json")
    raw["injection"]["tick"] = raw["ticks"] + 1
    with pytest.raises(ValidationError):
        Scenario.model_validate(raw)


def test_label_with_root_and_insufficient_evidence_is_rejected() -> None:
    """A label cannot name a root cause and also claim insufficient evidence."""
    with pytest.raises(ValidationError):
        ExpectedLabel.model_validate(
            {"root_cause_nf": "upf-1", "fault_class": "insufficient_evidence"}
        )


def test_label_with_fault_and_no_root_is_rejected() -> None:
    """A label with a fault class must name the root cause node."""
    with pytest.raises(ValidationError):
        ExpectedLabel.model_validate({"root_cause_nf": None, "fault_class": "nf_crashloop"})


def test_down_ticks_longer_than_period_is_rejected() -> None:
    """A fault cannot be down for longer than its cycle."""
    with pytest.raises(ValidationError):
        FaultSpec(
            kind=FaultClass.NF_CRASHLOOP, target="upf-1", start_tick=0, period=2, down_ticks=3
        )


def test_fault_cycle_is_down_then_up() -> None:
    """A crash-loop with period 4 and 2 down ticks alternates two down, two up."""
    spec = FaultSpec(
        kind=FaultClass.NF_CRASHLOOP, target="upf-1", start_tick=8, period=4, down_ticks=2
    )
    assert not spec.is_down(7)
    assert [spec.is_down(tick) for tick in range(8, 16)] == [True, True, False, False] * 2
    assert [tick for tick in range(30) if spec.is_cycle_start(tick)] == [8, 12, 16, 20, 24, 28]


def test_flap_on_an_nf_is_rejected_by_topology_check(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """A transport flap must target the router, not an NF."""
    scenario = scenarios["s01_upf_crashloop"]
    assert scenario.fault is not None
    flap = scenario.fault.model_copy(update={"kind": FaultClass.TRANSPORT_FLAP})
    with pytest.raises(ValueError, match="router"):
        check_against_topology(scenario.model_copy(update={"fault": flap}), topology)


def test_unknown_node_is_rejected_by_topology_check(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """A scenario naming a node that is not in the topology fails the check."""
    scenario = scenarios["s01_upf_crashloop"]
    assert scenario.fault is not None
    ghost = scenario.fault.model_copy(update={"target": "upf-9"})
    with pytest.raises(ValueError, match="upf-9"):
        check_against_topology(scenario.model_copy(update={"fault": ghost}), topology)


def test_scenario_id_must_match_file_name(tmp_path: Path) -> None:
    """A scenario file whose id differs from its file name is rejected."""
    source = DEFAULT_SCENARIOS_DIR / "s06_no_fault.yaml"
    renamed = tmp_path / "s99_renamed.yaml"
    renamed.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(ValueError, match="s99_renamed"):
        load_scenario(renamed)
