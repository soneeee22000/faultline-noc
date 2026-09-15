"""Tests for the rule baseline, the oracle and the three mutant agents."""

import pytest

from faultline_noc.agents import (
    FABRICATED_EVIDENCE_ID,
    BlamesSymptom,
    CitesUnseenEvidence,
    OracleAgent,
    RuleBaseline,
    WritesBeforeGathering,
)
from faultline_noc.evidence import EventSource, EvidenceSession
from faultline_noc.models import FaultClass
from faultline_noc.runner import run_one
from faultline_noc.scenario import Scenario
from faultline_noc.simulator import SimulationResult, simulate
from faultline_noc.topology import Topology
from tests.conftest import SCENARIO_IDS

SEEDS = (0, 1, 2)


def _simulate(
    scenarios: dict[str, Scenario], topology: Topology, scenario_id: str
) -> tuple[SimulationResult, EvidenceSession]:
    """Simulate a scenario at seed 0 and open a fresh evidence session on it."""
    result = simulate(scenarios[scenario_id], topology, seed=0)
    return result, EvidenceSession(result.telemetry, topology)


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("scenario_id", SCENARIO_IDS)
def test_oracle_matches_ground_truth(
    scenario_id: str, seed: int, scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """The oracle is top-1 correct on every scenario, which validates the scorer."""
    assert run_one(scenarios[scenario_id], topology, seed, OracleAgent).correct


@pytest.mark.parametrize("scenario_id", SCENARIO_IDS)
def test_oracle_cites_only_delivered_evidence(
    scenario_id: str, scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """Every id the oracle cites was delivered to it in this session."""
    result, session = _simulate(scenarios, topology, scenario_id)
    rca = OracleAgent(result.truth).propose(session)
    assert set(rca.cited_evidence_ids) <= session.seen_evidence_ids()


@pytest.mark.parametrize("scenario_id", SCENARIO_IDS)
def test_rule_baseline_cites_only_delivered_evidence(
    scenario_id: str, scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """The rule baseline returns a valid RCA that cites only delivered evidence."""
    _result, session = _simulate(scenarios, topology, scenario_id)
    rca = RuleBaseline().propose(session)
    assert set(rca.cited_evidence_ids) <= session.seen_evidence_ids()
    assert (rca.root_cause_nf is None) == (rca.fault_class == FaultClass.INSUFFICIENT_EVIDENCE)


def test_rule_baseline_never_reads_logs(scenarios: dict[str, Scenario], topology: Topology) -> None:
    """The rule baseline works from topology and alarms only, so log text cannot steer it."""
    _result, session = _simulate(scenarios, topology, "s07_log_injection")
    RuleBaseline().propose(session)
    assert EventSource.LOGS not in {event.source for event in session.trace}


def test_cites_unseen_evidence_adds_a_fabricated_id(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """The mutant cites an id that was never delivered."""
    result, session = _simulate(scenarios, topology, "s01_upf_crashloop")
    rca = CitesUnseenEvidence(result.truth).propose(session)
    assert FABRICATED_EVIDENCE_ID in rca.cited_evidence_ids
    assert FABRICATED_EVIDENCE_ID not in session.seen_evidence_ids()


@pytest.mark.parametrize("scenario_id", SCENARIO_IDS)
def test_writes_before_gathering_issues_a_write_first(
    scenario_id: str, scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """The mutant's first non-topology event is a write."""
    result, session = _simulate(scenarios, topology, scenario_id)
    WritesBeforeGathering(result.truth).propose(session)
    events = [event for event in session.trace if event.source != EventSource.TOPOLOGY]
    assert events[0].is_write


def test_blames_symptom_names_the_loudest_symptom(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """In s01 the mutant blames the SMF, whose alarms are loudest."""
    result, session = _simulate(scenarios, topology, "s01_upf_crashloop")
    rca = BlamesSymptom(result.truth).propose(session)
    assert rca.root_cause_nf == "smf-1"
    assert rca.actions == ()


def test_blames_symptom_defers_to_oracle_without_symptoms(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """With no symptoms to blame, the mutant answers like the oracle."""
    result, session = _simulate(scenarios, topology, "s06_no_fault")
    rca = BlamesSymptom(result.truth).propose(session)
    assert rca.fault_class == FaultClass.INSUFFICIENT_EVIDENCE
