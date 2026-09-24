"""Run the keyword baseline and each model router over the same items, with cassettes per item."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from faultline_noc.llm.agent import MODEL_PROFILES
from faultline_noc.llm.pricing import SpendTracker
from faultline_noc.llm.transport import (
    AnthropicTransport,
    CassetteStore,
    RecordingTransport,
    ReplayTransport,
    Transport,
)
from faultline_noc.paths import DEFAULT_CASSETTES_DIR
from faultline_noc.router.baseline import KeywordBaseline
from faultline_noc.router.llm.router import CallRecord, LlmRouter, TransportFactory, run_llm_router
from faultline_noc.router.metrics import RouterMetrics, compute_metrics
from faultline_noc.router.models import ChallengeItem
from faultline_noc.router.runner import ItemResult, run_router

CHALLENGE_CASSETTES = "router"
DEV_CASSETTES = "router-dev"


@dataclass(frozen=True)
class RunConfig:
    """Record or replay, which models, and whether the items are the development set."""

    record: bool
    models: tuple[str, ...]
    dev: bool
    cassettes_dir: Path = DEFAULT_CASSETTES_DIR


@dataclass(frozen=True)
class RunOutput:
    """Scored results for the baseline and the models, call records and every router's metrics."""

    baseline_results: tuple[ItemResult, ...]
    model_results: tuple[ItemResult, ...]
    records: tuple[CallRecord, ...]
    metrics: tuple[RouterMetrics, ...]


def transport_factory(config: RunConfig) -> TransportFactory:
    """Return a factory giving each (model, item) its own cassette directory."""
    root = config.cassettes_dir / (DEV_CASSETTES if config.dev else CHALLENGE_CASSETTES)
    live: list[Transport] = []

    def make(model: str, item_id: str) -> Transport:
        """Return the record or replay transport for one item."""
        store = CassetteStore(root / model / item_id)
        if not config.record:
            return ReplayTransport(store)
        if not live:
            live.append(AnthropicTransport())
        return RecordingTransport(live[0], store)

    return make


def run_all(config: RunConfig, items: Sequence[ChallengeItem], spend: SpendTracker) -> RunOutput:
    """Score the baseline, then each model in order, over the same items."""
    baseline_router = KeywordBaseline()
    baseline_results = run_router(baseline_router, items)
    factory = transport_factory(config)
    model_results: list[ItemResult] = []
    records: list[CallRecord] = []
    routers = [LlmRouter(MODEL_PROFILES[model], factory, spend) for model in config.models]
    for router in routers:
        results, calls = run_llm_router(router, items)
        model_results.extend(results)
        records.extend(calls)
    metrics = (
        compute_metrics(baseline_results, items),
        *(
            compute_metrics([r for r in model_results if r.router == router.name], items)
            for router in routers
        ),
    )
    return RunOutput(tuple(baseline_results), tuple(model_results), tuple(records), metrics)
