"""Runs agents over scenarios and seeds and records RCAs, correctness and detections."""

from collections.abc import Sequence

from faultline_noc.agents import DEFAULT_AGENTS, AgentSpec, build_agent
from faultline_noc.detectors import (
    DETECTORS,
    DetectionResult,
    Detector,
    RunEvidence,
    run_detectors,
    write_on_non_root,
)
from faultline_noc.evidence import EvidenceSession, TraceEvent
from faultline_noc.models import RCA, FrozenModel
from faultline_noc.scenario import Scenario
from faultline_noc.simulator import SimulationResult, simulate
from faultline_noc.topology import Topology


class RunResult(FrozenModel):
    """One agent on one scenario at one seed."""

    agent: str
    scenario_id: str
    seed: int
    rca: RCA
    correct: bool
    writes_on_root_only: bool
    detections: tuple[DetectionResult, ...]


class TracedRun(FrozenModel):
    """A run result together with the ordered session trace that produced it."""

    result: RunResult
    trace: tuple[TraceEvent, ...]


def run_traced(
    simulation: SimulationResult,
    topology: Topology,
    spec: AgentSpec,
    detectors: Sequence[Detector] = DETECTORS,
) -> TracedRun:
    """Run one agent like run_one, and also keep the session trace for inspection."""
    truth = simulation.truth
    agent = build_agent(spec, truth)
    session = EvidenceSession(simulation.telemetry, topology)
    rca = agent.propose(session)
    run = RunEvidence(rca=rca, trace=session.trace)
    result = RunResult(
        agent=agent.name,
        scenario_id=simulation.telemetry.scenario_id,
        seed=simulation.telemetry.seed,
        rca=rca,
        correct=(rca.root_cause_nf, rca.fault_class) == (truth.root_cause_nf, truth.fault_class),
        writes_on_root_only=not write_on_non_root(run, truth),
        detections=run_detectors(run, truth, detectors),
    )
    return TracedRun(result=result, trace=run.trace)


def run_one(
    simulation: SimulationResult,
    topology: Topology,
    spec: AgentSpec,
    detectors: Sequence[Detector] = DETECTORS,
) -> RunResult:
    """Let one agent propose through a fresh session on a simulation, then score and detect."""
    return run_traced(simulation, topology, spec, detectors).result


def run_matrix(
    scenarios: Sequence[Scenario],
    topology: Topology,
    seeds: Sequence[int],
    agents: Sequence[AgentSpec] = DEFAULT_AGENTS,
    detectors: Sequence[Detector] = DETECTORS,
) -> tuple[RunResult, ...]:
    """Run every agent on every scenario at every seed, ordered by agent, scenario, seed.

    Each scenario and seed is simulated once and the result is shared by every agent.
    """
    simulations = [simulate(scenario, topology, seed) for scenario in scenarios for seed in seeds]
    return tuple(
        run_one(simulation, topology, spec, detectors)
        for spec in agents
        for simulation in simulations
    )
