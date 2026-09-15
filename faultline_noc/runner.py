"""Runs agents over scenarios and seeds and records RCAs, correctness and detections."""

from collections.abc import Sequence

from faultline_noc.agents import (
    AgentFactory,
    BlamesSymptom,
    CitesUnseenEvidence,
    OracleAgent,
    RuleBaseline,
    WritesBeforeGathering,
)
from faultline_noc.agents.protocol import Agent
from faultline_noc.detectors import DETECTORS, DetectionResult, Detector, RunEvidence, run_detectors
from faultline_noc.evidence import EvidenceSession
from faultline_noc.models import RCA, FrozenModel, GroundTruth
from faultline_noc.scenario import Scenario
from faultline_noc.simulator import simulate
from faultline_noc.topology import Topology


def rule_baseline_factory(_truth: GroundTruth) -> Agent:
    """Build a rule baseline; it never sees ground truth."""
    return RuleBaseline()


AGENT_FACTORIES: tuple[AgentFactory, ...] = (
    rule_baseline_factory,
    OracleAgent,
    CitesUnseenEvidence,
    WritesBeforeGathering,
    BlamesSymptom,
)


class RunResult(FrozenModel):
    """One agent on one scenario at one seed."""

    agent: str
    scenario_id: str
    seed: int
    rca: RCA
    correct: bool
    detections: tuple[DetectionResult, ...]


def run_one(
    scenario: Scenario,
    topology: Topology,
    seed: int,
    factory: AgentFactory,
    detectors: Sequence[Detector] = DETECTORS,
) -> RunResult:
    """Simulate, let the agent propose through a fresh session, then score and detect."""
    simulation = simulate(scenario, topology, seed)
    truth = simulation.truth
    agent = factory(truth)
    session = EvidenceSession(simulation.telemetry, topology)
    rca = agent.propose(session)
    correct = (rca.root_cause_nf, rca.fault_class) == (truth.root_cause_nf, truth.fault_class)
    return RunResult(
        agent=agent.name,
        scenario_id=scenario.id,
        seed=seed,
        rca=rca,
        correct=correct,
        detections=run_detectors(RunEvidence(rca=rca, trace=session.trace), truth, detectors),
    )


def run_matrix(
    scenarios: Sequence[Scenario],
    topology: Topology,
    seeds: Sequence[int],
    factories: Sequence[AgentFactory] = AGENT_FACTORIES,
    detectors: Sequence[Detector] = DETECTORS,
) -> tuple[RunResult, ...]:
    """Run every agent on every scenario at every seed, ordered by agent, scenario, seed."""
    return tuple(
        run_one(scenario, topology, seed, factory, detectors)
        for factory in factories
        for scenario in scenarios
        for seed in seeds
    )
