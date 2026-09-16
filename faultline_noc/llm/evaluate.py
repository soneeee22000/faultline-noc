"""Runs the rule baseline and LLM agents over scenarios and seeds, and builds the report payload."""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import Literal

from faultline_noc.agents import AgentSpec, BlindAgent
from faultline_noc.agents.baseline import RuleBaseline
from faultline_noc.export import (
    SampleTrace,
    ScenarioSummary,
    sample_trace,
    summarise_scenario,
)
from faultline_noc.llm.agent import MODEL_PROFILES, LlmAgent, TransportFactory
from faultline_noc.llm.pricing import SpendTracker
from faultline_noc.llm.transport import (
    AnthropicTransport,
    CassetteStore,
    RecordingTransport,
    ReplayTransport,
    Transport,
)
from faultline_noc.models import FrozenModel
from faultline_noc.runner import RunResult, TracedRun, run_traced
from faultline_noc.scenario import Scenario
from faultline_noc.scoring import (
    AccuracyRow,
    MatrixCell,
    accuracy_by,
    actions_correct,
    detection_matrix,
)
from faultline_noc.simulator import SimulationResult, simulate
from faultline_noc.topology import Topology

Mode = Literal["record", "replay"]
SPEND_DECIMALS = 4
LLM_SAMPLE_SEED = 0
TraceKey = tuple[str, str]
LLM_SAMPLE_RUNS: tuple[TraceKey, ...] = (
    ("s08_smf_crashloop_router_noise", "rule_baseline"),
    ("s08_smf_crashloop_router_noise", "llm_sonnet_5"),
)


@dataclass(frozen=True)
class EvalConfig:
    """What to run: mode, models, seeds, spend cap and where cassettes live."""

    mode: Mode
    models: tuple[str, ...]
    seeds: tuple[int, ...]
    budget_usd: float
    cassettes_dir: Path


@dataclass
class EvalOutcome:
    """What one evaluation produced: every scored run, and the traces kept for the report."""

    results: list[RunResult] = field(default_factory=list)
    traces: dict[TraceKey, SampleTrace] = field(default_factory=dict)


class LlmEvalPayload(FrozenModel):
    """Everything the LLM results report needs, with no timestamps so replays are byte-stable."""

    schema_version: Literal[1] = 1
    command: str
    models: tuple[str, ...]
    scenarios: tuple[str, ...]
    seeds: tuple[int, ...]
    runs: int
    spend_usd: dict[str, float]
    tokens: dict[str, dict[str, int]]
    accuracy_overall: tuple[AccuracyRow, ...]
    accuracy_per_scenario: tuple[AccuracyRow, ...]
    action_correctness: tuple[AccuracyRow, ...]
    detection_matrix: tuple[MatrixCell, ...]
    sample_scenarios: tuple[ScenarioSummary, ...] = ()
    sample_traces: tuple[SampleTrace, ...] = ()


def new_spend_tracker(config: EvalConfig) -> SpendTracker:
    """Return a tracker capped at the budget when recording, and uncapped when replaying."""
    return SpendTracker(budget_usd=config.budget_usd if config.mode == "record" else math.inf)


def transport_factory(config: EvalConfig, model: str) -> TransportFactory:
    """Return per-run transports that record live responses or replay recorded ones."""
    live = AnthropicTransport() if config.mode == "record" else None

    def make(scenario_id: str, seed: int) -> Transport:
        """Build the transport for one run's cassette directory."""
        store = CassetteStore(config.cassettes_dir / model / scenario_id / f"seed-{seed}")
        if live is None:
            return ReplayTransport(store)
        return RecordingTransport(live, store)

    return make


def agent_specs(config: EvalConfig, spend: SpendTracker) -> tuple[AgentSpec, ...]:
    """Return the rule baseline followed by one LLM agent per model."""
    llm_agents = tuple(
        BlindAgent(
            partial(LlmAgent, MODEL_PROFILES[model], transport_factory(config, model), spend)
        )
        for model in config.models
    )
    return (BlindAgent(RuleBaseline), *llm_agents)


def _keep_sample(
    traced: TracedRun,
    simulation: SimulationResult,
    seed: int,
    traces: dict[TraceKey, SampleTrace],
) -> None:
    """Keep this run's trace when the report shows it, so nothing has to be run twice."""
    result = traced.result
    if seed != LLM_SAMPLE_SEED or (result.scenario_id, result.agent) not in LLM_SAMPLE_RUNS:
        return
    traces[(result.scenario_id, result.agent)] = sample_trace(
        traced, simulation.truth.injection_evidence_id
    )


def run_evaluation(
    config: EvalConfig,
    scenarios: Sequence[Scenario],
    topology: Topology,
    outcome: EvalOutcome,
    spend: SpendTracker,
) -> None:
    """Append one result per agent, scenario and seed; completed results survive a spend stop."""
    specs = agent_specs(config, spend)
    for scenario in scenarios:
        for seed in config.seeds:
            simulation = simulate(scenario, topology, seed)
            for spec in specs:
                traced = run_traced(simulation, topology, spec)
                outcome.results.append(traced.result)
                _keep_sample(traced, simulation, seed, outcome.traces)


def _sample_scenarios(
    scenarios: Sequence[Scenario],
    topology: Topology,
    traces: Mapping[TraceKey, SampleTrace],
) -> tuple[ScenarioSummary, ...]:
    """Summarise every scenario a kept trace refers to, in the order the scenarios were run."""
    needed = {trace.scenario_id for trace in traces.values()}
    return tuple(
        summarise_scenario(scenario, topology) for scenario in scenarios if scenario.id in needed
    )


def build_payload(
    config: EvalConfig,
    scenarios: Sequence[Scenario],
    outcome: EvalOutcome,
    spend: SpendTracker,
    topology: Topology,
) -> LlmEvalPayload:
    """Summarise results into the report payload, rounding spend so replays match records."""
    results = outcome.results
    return LlmEvalPayload(
        command=f"python -m faultline_noc.llm --replay --seeds {len(config.seeds)}",
        models=config.models,
        scenarios=tuple(scenario.id for scenario in scenarios),
        seeds=config.seeds,
        runs=len(results),
        spend_usd={
            model: round(usd, SPEND_DECIMALS) for model, usd in sorted(spend.spent_usd.items())
        },
        tokens={
            model: dict(sorted(counts.items())) for model, counts in sorted(spend.tokens.items())
        },
        accuracy_overall=accuracy_by(results, per_scenario=False),
        accuracy_per_scenario=accuracy_by(results, per_scenario=True),
        action_correctness=accuracy_by(results, per_scenario=False, outcome=actions_correct),
        detection_matrix=detection_matrix(results),
        sample_scenarios=_sample_scenarios(scenarios, topology, outcome.traces),
        sample_traces=tuple(
            outcome.traces[key] for key in LLM_SAMPLE_RUNS if key in outcome.traces
        ),
    )
