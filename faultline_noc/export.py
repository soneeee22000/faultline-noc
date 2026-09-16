"""JSON export of a harness run for the project page: rates, matrix, scenarios and sample traces.

The payload carries no timestamps or paths, so the same seeds always give the same bytes.
"""

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Final, Literal, Self

from pydantic import Field, model_validator

from faultline_noc.agents import (
    DEFAULT_AGENTS,
    AgentSpec,
    FollowsInjection,
    RuleBaseline,
    build_agent,
)
from faultline_noc.detectors import DetectionResult, DetectorName
from faultline_noc.evidence import EventKind, EventSource, TraceEvent
from faultline_noc.models import RCA, Action, FaultClass, FrozenModel, GroundTruth
from faultline_noc.runner import RunResult, TracedRun, run_traced
from faultline_noc.scenario import FaultSpec, InjectionSpec, Scenario
from faultline_noc.scoring import (
    AccuracyRow,
    MatrixCell,
    accuracy_by,
    actions_correct,
    detection_matrix,
)
from faultline_noc.simulator import simulate
from faultline_noc.topology import Topology

SCHEMA_VERSION: Final = 1
RATE_DECIMALS = 6
MAX_IDS_PER_READ = 6
SAMPLE_SEED = 0
JSON_INDENT = 2
SAMPLE_RUNS: tuple[tuple[str, str], ...] = (
    ("s07_log_injection", RuleBaseline.name),
    ("s07_log_injection", FollowsInjection.name),
    ("s01_upf_crashloop", RuleBaseline.name),
)


class RateRow(FrozenModel):
    """A proportion for one agent over one scope, with its Wilson 95% interval."""

    agent: str
    scope: str
    correct: int = Field(ge=0)
    n: int = Field(ge=0)
    rate: float
    wilson_low: float
    wilson_high: float


class PayloadMeta(FrozenModel):
    """The command, the run shape and the harness verdict."""

    command: str
    seed_count: int = Field(ge=1)
    seed_first: int
    seed_last: int
    runs: int = Field(ge=0)
    agents: tuple[str, ...]
    scenarios: tuple[str, ...]
    detectors: tuple[DetectorName, ...]
    harness_pass: bool
    failures: tuple[str, ...]

    @model_validator(mode="after")
    def _pass_mirrors_failures(self) -> Self:
        """Reject a verdict that disagrees with the failure list."""
        if self.harness_pass == bool(self.failures):
            raise ValueError("harness_pass must be true exactly when failures is empty")
        return self


class ScenarioSummary(FrozenModel):
    """What a scenario injects, the trap it sets, and which NFs are root and symptoms."""

    id: str
    trap: str
    injected_fault: FaultSpec | None
    injection: InjectionSpec | None
    root_nf: str | None
    fault_class: FaultClass
    symptom_nfs: tuple[str, ...]


class TraceStep(FrozenModel):
    """One session call; delivered ids are truncated but their count is kept."""

    index: int = Field(ge=0)
    kind: EventKind
    source: EventSource
    delivered_count: int = Field(ge=0)
    shown_evidence_ids: tuple[str, ...]
    hidden_count: int = Field(ge=0)
    action: Action | None


class SampleTrace(FrozenModel):
    """One agent's run on one scenario: ordered reads, the RCA and the detections."""

    scenario_id: str
    agent: str
    seed: int
    injection_evidence_id: str | None
    steps: tuple[TraceStep, ...]
    rca: RCA
    correct: bool
    writes_on_root_only: bool
    detections: tuple[DetectionResult, ...]


class ResultsPayload(FrozenModel):
    """Everything the project page shows, from one real run of the harness."""

    schema_version: Literal[1] = SCHEMA_VERSION
    meta: PayloadMeta
    accuracy_overall: tuple[RateRow, ...]
    accuracy_per_scenario: tuple[RateRow, ...]
    action_correctness: tuple[RateRow, ...]
    detection_matrix: tuple[MatrixCell, ...]
    scenarios: tuple[ScenarioSummary, ...]
    sample_traces: tuple[SampleTrace, ...]


def build_payload(
    results: Sequence[RunResult],
    seeds: Sequence[int],
    failures: Sequence[str],
    scenarios: Sequence[Scenario],
    topology: Topology,
    *,
    command: str,
) -> ResultsPayload:
    """Return the export payload for a set of runs, reusing the scorer for every number."""
    return ResultsPayload(
        meta=_meta(results, seeds, failures, command),
        accuracy_overall=_rate_rows(accuracy_by(results, per_scenario=False)),
        accuracy_per_scenario=_rate_rows(accuracy_by(results, per_scenario=True)),
        action_correctness=_rate_rows(
            accuracy_by(results, per_scenario=False, outcome=actions_correct)
        ),
        detection_matrix=detection_matrix(results),
        scenarios=tuple(summarise_scenario(scenario, topology) for scenario in scenarios),
        sample_traces=_sample_traces(results, scenarios, topology),
    )


def payload_json(payload: ResultsPayload) -> str:
    """Return the payload as indented JSON with a trailing newline."""
    return payload.model_dump_json(indent=JSON_INDENT) + "\n"


def write_payload(path: Path, payload: ResultsPayload) -> None:
    """Write the payload JSON to a path with LF line endings, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload_json(payload), encoding="utf-8", newline="\n")


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    """Return values in first-seen order without duplicates."""
    return tuple(dict.fromkeys(values))


def _meta(
    results: Sequence[RunResult], seeds: Sequence[int], failures: Sequence[str], command: str
) -> PayloadMeta:
    """Return the run summary and harness verdict."""
    detectors = tuple(
        dict.fromkeys(item.detector for result in results for item in result.detections)
    )
    return PayloadMeta(
        command=command,
        seed_count=len(seeds),
        seed_first=seeds[0],
        seed_last=seeds[-1],
        runs=len(results),
        agents=_unique(result.agent for result in results),
        scenarios=_unique(result.scenario_id for result in results),
        detectors=detectors,
        harness_pass=not failures,
        failures=tuple(failures),
    )


def _rate_rows(rows: Sequence[AccuracyRow]) -> tuple[RateRow, ...]:
    """Convert scorer rows into rounded rate rows."""
    return tuple(
        RateRow(
            agent=row.agent,
            scope=row.scope,
            correct=row.correct,
            n=row.total,
            rate=round(row.accuracy, RATE_DECIMALS),
            wilson_low=round(row.interval.low, RATE_DECIMALS),
            wilson_high=round(row.interval.high, RATE_DECIMALS),
        )
        for row in rows
    )


def summarise_scenario(scenario: Scenario, topology: Topology) -> ScenarioSummary:
    """Summarise a scenario from its YAML and the ground truth of its sample seed."""
    truth = simulate(scenario, topology, SAMPLE_SEED).truth
    return ScenarioSummary(
        id=scenario.id,
        trap=scenario.title,
        injected_fault=scenario.fault,
        injection=scenario.injection,
        root_nf=truth.root_cause_nf,
        fault_class=truth.fault_class,
        symptom_nfs=truth.symptom_nfs,
    )


def _sample_traces(
    results: Sequence[RunResult], scenarios: Sequence[Scenario], topology: Topology
) -> tuple[SampleTrace, ...]:
    """Re-run the sample seed for each sample pair in this run and check it matches the score."""
    ran = {(result.scenario_id, result.agent, result.seed): result for result in results}
    by_id = {scenario.id: scenario for scenario in scenarios}
    traces = []
    for scenario_id, agent in SAMPLE_RUNS:
        scored = ran.get((scenario_id, agent, SAMPLE_SEED))
        if scored is None or scenario_id not in by_id:
            continue
        simulation = simulate(by_id[scenario_id], topology, SAMPLE_SEED)
        traced = run_traced(simulation, topology, _spec_named(agent, simulation.truth))
        if traced.result != scored:
            raise ValueError(f"re-run of {agent} on {scenario_id} differs from the scored run")
        traces.append(sample_trace(traced, simulation.truth.injection_evidence_id))
    return tuple(traces)


def _spec_named(agent: str, truth: GroundTruth) -> AgentSpec:
    """Return the default agent spec whose built agent has the given name."""
    for spec in DEFAULT_AGENTS:
        if build_agent(spec, truth).name == agent:
            return spec
    raise KeyError(f"no default agent named {agent!r}")


def sample_trace(traced: TracedRun, injection_evidence_id: str | None) -> SampleTrace:
    """Return a sample trace, keeping cited and injected ids visible in truncated reads."""
    result = traced.result
    highlighted = frozenset(result.rca.cited_evidence_ids) | {injection_evidence_id}
    return SampleTrace(
        scenario_id=result.scenario_id,
        agent=result.agent,
        seed=result.seed,
        injection_evidence_id=injection_evidence_id,
        steps=tuple(_step(index, event, highlighted) for index, event in enumerate(traced.trace)),
        rca=result.rca,
        correct=result.correct,
        writes_on_root_only=result.writes_on_root_only,
        detections=result.detections,
    )


def _step(index: int, event: TraceEvent, highlighted: frozenset[str | None]) -> TraceStep:
    """Return one trace step showing the first ids delivered plus any highlighted ones."""
    shown = tuple(
        evidence_id
        for position, evidence_id in enumerate(event.evidence_ids)
        if position < MAX_IDS_PER_READ or evidence_id in highlighted
    )
    return TraceStep(
        index=index,
        kind=event.kind,
        source=event.source,
        delivered_count=len(event.evidence_ids),
        shown_evidence_ids=shown,
        hidden_count=len(event.evidence_ids) - len(shown),
        action=event.action,
    )
