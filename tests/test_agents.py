"""Tests for the rule baseline, the oracle and the mutant agents."""

import pytest

from faultline_noc.agents import (
    UNDELIVERED_LOG_ID,
    BlamesSymptom,
    BlindAgent,
    CitesUnseenEvidence,
    CitesUnsupportedEvidence,
    FollowsInjection,
    OracleAgent,
    ProposesUncitedWrite,
    RestartsBystander,
    RuleBaseline,
    TakesInjectedActionUnread,
    TruthAwareAgent,
    WritesBeforeGathering,
)
from faultline_noc.detectors import RunEvidence
from faultline_noc.evidence import EventSource, EvidenceSession
from faultline_noc.models import FaultClass
from faultline_noc.runner import run_one
from faultline_noc.scenario import Scenario
from faultline_noc.simulator import SimulationResult, simulate
from faultline_noc.topology import Topology
from tests.conftest import FAULTED_SCENARIO_IDS, SCENARIO_IDS

SEEDS = (0, 1, 2)
BASELINE_SWEEP_SEEDS = range(200)
BASELINE = BlindAgent(RuleBaseline)
MIN_SHADOWING_ALARMS = 2


def _simulate(
    scenarios: dict[str, Scenario], topology: Topology, scenario_id: str, seed: int = 0
) -> tuple[SimulationResult, EvidenceSession]:
    """Simulate a scenario at a seed and open a fresh evidence session on it."""
    result = simulate(scenarios[scenario_id], topology, seed=seed)
    return result, EvidenceSession(result.telemetry, topology)


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("scenario_id", SCENARIO_IDS)
def test_oracle_matches_ground_truth(
    scenario_id: str, seed: int, scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """The oracle is top-1 correct on every scenario, which validates the scorer."""
    simulation = simulate(scenarios[scenario_id], topology, seed)
    assert run_one(simulation, topology, TruthAwareAgent(OracleAgent)).correct


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


@pytest.mark.parametrize("scenario_id", SCENARIO_IDS)
def test_rule_baseline_is_top1_correct_over_many_seeds(
    scenario_id: str, scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """Pins the baseline's real accuracy: correct on every one of 200 seeds per scenario."""
    wrong = [
        seed
        for seed in BASELINE_SWEEP_SEEDS
        if not run_one(simulate(scenarios[scenario_id], topology, seed), topology, BASELINE).correct
    ]
    assert wrong == []


def test_rule_baseline_finds_no_fault_in_the_control_over_many_seeds(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """On s06 the baseline answers insufficient_evidence with no actions at every seed."""
    offending = []
    for seed in BASELINE_SWEEP_SEEDS:
        _result, session = _simulate(scenarios, topology, "s06_no_fault", seed)
        rca = RuleBaseline().propose(session)
        if rca.fault_class != FaultClass.INSUFFICIENT_EVIDENCE or rca.actions:
            offending.append(seed)
    assert offending == []


def test_rule_baseline_never_takes_the_injected_action(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """On s07 the injected restart is neither proposed nor executed at any seed."""
    offending = []
    for seed in BASELINE_SWEEP_SEEDS:
        result, session = _simulate(scenarios, topology, "s07_log_injection", seed)
        rca = RuleBaseline().propose(session)
        run = RunEvidence(rca=rca, trace=session.trace)
        injected = result.truth.injected_action
        if injected in rca.actions or injected in run.executed_writes():
            offending.append(seed)
    assert offending == []


def test_router_ntp_noise_does_not_shadow_the_upf(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """Where rtr-1 has repeated NTP_OFFSET_HIGH alarms in s01, the baseline still blames upf-1."""
    shadow_seeds = []
    for seed in BASELINE_SWEEP_SEEDS:
        result, session = _simulate(scenarios, topology, "s01_upf_crashloop", seed)
        router_ntp = sum(
            1
            for alarm in result.telemetry.alarms
            if alarm.node == "rtr-1" and alarm.code == "NTP_OFFSET_HIGH"
        )
        if router_ntp >= MIN_SHADOWING_ALARMS:
            shadow_seeds.append(seed)
            assert RuleBaseline().propose(session).root_cause_nf == "upf-1", seed
    assert shadow_seeds


def test_cites_unseen_evidence_cites_a_real_log_id_it_never_read(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """The mutant reads alarms only and cites an existing log id that was never delivered."""
    result, session = _simulate(scenarios, topology, "s01_upf_crashloop")
    rca = CitesUnseenEvidence(result.truth).propose(session)
    log_ids = {log.evidence_id for log in result.telemetry.logs}
    assert UNDELIVERED_LOG_ID in rca.cited_evidence_ids
    assert UNDELIVERED_LOG_ID in log_ids
    assert UNDELIVERED_LOG_ID not in session.seen_evidence_ids()
    assert EventSource.LOGS not in {event.source for event in session.trace}


@pytest.mark.parametrize("scenario_id", SCENARIO_IDS)
def test_writes_before_gathering_issues_a_write_first(
    scenario_id: str, scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """The mutant's first non-topology event is a write."""
    result, session = _simulate(scenarios, topology, scenario_id)
    WritesBeforeGathering(result.truth).propose(session)
    events = [event for event in session.trace if event.source != EventSource.TOPOLOGY]
    assert events[0].is_write


@pytest.mark.parametrize("scenario_id", SCENARIO_IDS)
def test_proposes_uncited_write_proposes_a_restart_with_no_citations(
    scenario_id: str, scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """The mutant reads evidence, never executes, and proposes a restart citing nothing."""
    result, session = _simulate(scenarios, topology, scenario_id)
    rca = ProposesUncitedWrite(result.truth).propose(session)
    assert rca.cited_evidence_ids == ()
    assert any(action.is_write for action in rca.actions)
    assert not any(event.is_write for event in session.trace)


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


def test_follows_injection_keeps_the_root_and_proposes_the_injected_action(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """On s07 the mutant reads the injected line, names nrf-1 and proposes restarting amf-1."""
    result, session = _simulate(scenarios, topology, "s07_log_injection")
    rca = FollowsInjection(result.truth).propose(session)
    assert result.truth.injection_evidence_id in session.seen_evidence_ids()
    assert rca.root_cause_nf == "nrf-1"
    assert result.truth.injected_action in rca.actions
    assert not any(event.is_write for event in session.trace)


def test_takes_injected_action_unread_executes_without_reading_logs(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """On s07 the mutant never reads logs but still executes the injected restart."""
    result, session = _simulate(scenarios, topology, "s07_log_injection")
    rca = TakesInjectedActionUnread(result.truth).propose(session)
    run = RunEvidence(rca=rca, trace=session.trace)
    assert EventSource.LOGS not in {event.source for event in session.trace}
    assert result.truth.injected_action in run.executed_writes()
    assert rca.root_cause_nf == "nrf-1"


@pytest.mark.parametrize("scenario_id", SCENARIO_IDS)
def test_restarts_bystander_proposes_a_restart_off_the_root(
    scenario_id: str, scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """The mutant proposes restarting a node that is neither the root nor the injection target."""
    result, session = _simulate(scenarios, topology, scenario_id)
    rca = RestartsBystander(result.truth).propose(session)
    truth = result.truth
    injected_target = truth.injected_action.target if truth.injected_action else None
    targets = {action.target for action in rca.actions if action.is_write}
    assert targets - {truth.root_cause_nf, injected_target}
    assert rca.cited_evidence_ids


@pytest.mark.parametrize("scenario_id", FAULTED_SCENARIO_IDS)
def test_cites_unsupported_evidence_cites_no_causal_record(
    scenario_id: str, scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """The mutant names the true root but cites only delivered, non-causal records."""
    result, session = _simulate(scenarios, topology, scenario_id)
    rca = CitesUnsupportedEvidence(result.truth).propose(session)
    assert rca.root_cause_nf == result.truth.root_cause_nf
    assert rca.cited_evidence_ids
    assert set(rca.cited_evidence_ids) <= session.seen_evidence_ids()
    assert not set(rca.cited_evidence_ids) & set(result.truth.causal_evidence_ids)
