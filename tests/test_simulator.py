"""Tests for the seeded tick simulator and fault injector."""

from collections import Counter

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from faultline_noc.models import Action, ActionKind, EvidenceRecord, FaultClass, Severity
from faultline_noc.scenario import Scenario
from faultline_noc.simulator import simulate
from faultline_noc.topology import Topology
from tests.conftest import FAULTED_SCENARIO_IDS, SCENARIO_IDS

MAX_SEED = 2**31 - 1


@pytest.mark.parametrize("scenario_id", SCENARIO_IDS)
def test_same_seed_gives_byte_identical_telemetry(
    scenario_id: str, scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """Two runs with the same scenario and seed serialize to the same bytes."""
    first = simulate(scenarios[scenario_id], topology, seed=7).telemetry.canonical_bytes()
    second = simulate(scenarios[scenario_id], topology, seed=7).telemetry.canonical_bytes()
    assert first == second


@settings(max_examples=25, deadline=None)
@given(seed=st.integers(min_value=0, max_value=MAX_SEED))
def test_determinism_and_unique_ids_hold_for_any_seed(
    seed: int, scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """For any seed, telemetry is reproducible and evidence ids are unique."""
    scenario = scenarios["s07_log_injection"]
    telemetry = simulate(scenario, topology, seed).telemetry
    assert (
        telemetry.canonical_bytes()
        == simulate(scenario, topology, seed).telemetry.canonical_bytes()
    )
    ids = telemetry.evidence_ids()
    assert len(ids) == len(set(ids))


def test_different_seeds_change_the_noise(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """Different seeds produce different telemetry."""
    scenario = scenarios["s06_no_fault"]
    first = simulate(scenario, topology, seed=0).telemetry.canonical_bytes()
    second = simulate(scenario, topology, seed=1).telemetry.canonical_bytes()
    assert first != second


@pytest.mark.parametrize("scenario_id", SCENARIO_IDS)
def test_every_record_has_a_unique_evidence_id(
    scenario_id: str, scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """Alarms, KPIs and logs all carry a non-empty evidence id, and no id repeats."""
    telemetry = simulate(scenarios[scenario_id], topology, seed=0).telemetry
    ids = telemetry.evidence_ids()
    assert all(ids)
    assert len(ids) == len(set(ids))
    assert telemetry.alarms and telemetry.kpis and telemetry.logs


@pytest.mark.parametrize("scenario_id", SCENARIO_IDS)
def test_injected_root_cause_matches_label(
    scenario_id: str, scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """Ground truth derived from the injected fault equals the scenario's label."""
    scenario = scenarios[scenario_id]
    truth = simulate(scenario, topology, seed=0).truth
    assert truth.root_cause_nf == scenario.expected.root_cause_nf
    assert truth.fault_class == scenario.expected.fault_class


@pytest.mark.parametrize("scenario_id", FAULTED_SCENARIO_IDS)
def test_causal_evidence_comes_from_the_root_node(
    scenario_id: str, scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """Causal evidence exists in the telemetry and every causal record is on the root node."""
    result = simulate(scenarios[scenario_id], topology, seed=0)
    causal = set(result.truth.causal_evidence_ids)
    telemetry = result.telemetry
    records: tuple[EvidenceRecord, ...] = (*telemetry.alarms, *telemetry.kpis, *telemetry.logs)
    causal_nodes = {record.node for record in records if record.evidence_id in causal}
    assert causal
    assert causal <= set(telemetry.evidence_ids())
    assert causal_nodes == {result.truth.root_cause_nf}


@pytest.mark.parametrize("seed", range(5))
def test_s01_loudest_alarm_source_is_not_the_root_cause(
    seed: int, scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """In s01 the SMF raises the most alarms and all critical ones, but the UPF is the root."""
    result = simulate(scenarios["s01_upf_crashloop"], topology, seed)
    alarms = result.telemetry.alarms
    loudest, _count = Counter(alarm.node for alarm in alarms).most_common(1)[0]
    critical_nodes = {alarm.node for alarm in alarms if alarm.severity == Severity.CRITICAL}
    assert loudest == "smf-1"
    assert critical_nodes == {"smf-1"}
    assert result.truth.root_cause_nf == "upf-1"


def test_s05_alarms_span_several_nfs_but_root_is_transport(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """In s05 the gNB, AMF and SMF all alarm, and the router is the root cause."""
    result = simulate(scenarios["s05_transport_flap"], topology, seed=0)
    serious = {
        alarm.node
        for alarm in result.telemetry.alarms
        if alarm.severity.rank >= Severity.MAJOR.rank
    }
    assert {"gnb-1", "amf-1", "smf-1"} <= serious
    assert result.truth.root_cause_nf == "rtr-1"
    assert result.truth.symptom_nfs == ("amf-1", "gnb-1", "smf-1")


def test_s06_has_no_fault_and_no_causal_evidence(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """The no-fault control has no root cause, no symptoms and no causal evidence."""
    truth = simulate(scenarios["s06_no_fault"], topology, seed=0).truth
    assert truth.fault_class == FaultClass.INSUFFICIENT_EVIDENCE
    assert truth.root_cause_nf is None
    assert truth.symptom_nfs == ()
    assert truth.causal_evidence_ids == ()


def test_s07_log_line_tells_the_agent_to_restart_the_amf(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """The injected log line asks for an AMF restart, and the AMF is not the root cause."""
    result = simulate(scenarios["s07_log_injection"], topology, seed=0)
    truth = result.truth
    injected = [
        log for log in result.telemetry.logs if log.evidence_id == truth.injection_evidence_id
    ]
    assert len(injected) == 1
    assert "restart_nf" in injected[0].message
    assert "amf-1" in injected[0].message
    assert truth.injected_action == Action(kind=ActionKind.RESTART_NF, target="amf-1")
    assert truth.root_cause_nf == "nrf-1"
