"""Tests for the hard scenarios: benign major noise, a silent root, and the baseline failing."""

from faultline_noc.agents import BlindAgent
from faultline_noc.agents.baseline import RuleBaseline
from faultline_noc.runner import run_one
from faultline_noc.scenario import Scenario, check_against_topology
from faultline_noc.simulator import simulate
from faultline_noc.topology import Topology
from tests.conftest import HARD_SCENARIO_IDS

HARD_SWEEP_SEEDS = range(50)
BASELINE = BlindAgent(RuleBaseline)
S08 = "s08_smf_crashloop_router_noise"
S09 = "s09_upf_crashloop_silent"


def _baseline_roots(scenario: Scenario, topology: Topology) -> set[str | None]:
    """Return every root cause the rule baseline names over the sweep seeds."""
    return {
        run_one(simulate(scenario, topology, seed), topology, BASELINE).rca.root_cause_nf
        for seed in HARD_SWEEP_SEEDS
    }


def test_hard_scenarios_load_and_fit_the_topology(
    hard_scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """Both hard scenarios load, match their file names and reference real nodes."""
    assert tuple(sorted(hard_scenarios)) == HARD_SCENARIO_IDS
    for scenario in hard_scenarios.values():
        check_against_topology(scenario, topology)


def test_extra_major_noise_lands_only_on_its_node(
    hard_scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """The benign router alarm is major, non-causal and raised on rtr-1 alone."""
    result = simulate(hard_scenarios[S08], topology, seed=0)
    extra = [a for a in result.telemetry.alarms if a.code == "SYSLOG_COLLECTOR_UNREACHABLE"]
    assert extra
    assert {alarm.node for alarm in extra} == {"rtr-1"}
    assert not {alarm.evidence_id for alarm in extra} & set(result.truth.causal_evidence_ids)


def test_silent_root_leaves_only_kpi_evidence(
    hard_scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """A silent crash-loop raises no restart alarm or log; its causal evidence is KPIs only."""
    result = simulate(hard_scenarios[S09], topology, seed=0)
    assert all(alarm.code != "NF_PROCESS_RESTART" for alarm in result.telemetry.alarms)
    assert result.truth.causal_evidence_ids
    assert all(evidence_id.startswith("kpi-") for evidence_id in result.truth.causal_evidence_ids)


def test_rule_baseline_blames_the_router_on_s08(
    hard_scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """The unknown benign router alarm makes the baseline blame rtr-1 at every seed."""
    assert _baseline_roots(hard_scenarios[S08], topology) == {"rtr-1"}


def test_rule_baseline_never_names_the_silent_upf_on_s09(
    hard_scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """With no root alarm, the baseline blames a symptom and never the UPF."""
    assert "upf-1" not in _baseline_roots(hard_scenarios[S09], topology)
