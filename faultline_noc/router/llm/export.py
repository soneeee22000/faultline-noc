"""JSON export of an LLM router run, kept apart from router_results.json.

The keyword baseline is scored in the same run and its metrics are included for comparison. Its
plans stay in router_results.json. Every model outcome carries its cassette key, cost and parse
status, and malformed answers are exported as such, with no plan.
"""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from pydantic import Field

from faultline_noc.models import FrozenModel
from faultline_noc.router.detectors import DetectorName
from faultline_noc.router.export import JSON_INDENT, round_floats
from faultline_noc.router.llm.router import CallRecord
from faultline_noc.router.metrics import (
    CALIBRATION_BIN_COUNT,
    MatrixCell,
    RouterMetrics,
    detection_matrix,
)
from faultline_noc.router.models import RoutePlan
from faultline_noc.router.runner import ItemResult

LLM_SCHEMA_VERSION: Final = 1


@dataclass(frozen=True)
class LlmRunLabels:
    """Where an LLM router run came from."""

    command: str
    challenge_set: str
    baseline: str
    prompt_sha256: str
    prompt_tuned_on: str
    dev_items: int


class LlmPayloadMeta(FrozenModel):
    """The command, the frozen prompt, the models and what the run cost."""

    command: str
    challenge_set: str
    items: int = Field(ge=1)
    baseline: str
    routers: tuple[str, ...]
    models: tuple[str, ...]
    prompt_sha256: str
    prompt_tuned_on: str
    dev_items: int = Field(ge=1)
    calibration_bins: int = Field(ge=1)
    cost_usd: float
    malformed: dict[str, int]


class LlmOutcome(FrozenModel):
    """One model's answer on one item: the plan, or why it was malformed, and its cost."""

    router: str
    item_id: str
    correct: bool
    tripped: tuple[DetectorName, ...]
    plan: RoutePlan | None
    malformed: str | None
    stated_confidence: float | None
    cassette_key: str
    stop_reason: str | None
    input_tokens: int
    output_tokens: int
    cost_usd: float


class LlmRouterPayload(FrozenModel):
    """Everything a page needs to show the model routers next to the baseline."""

    schema_version: Literal[1] = LLM_SCHEMA_VERSION
    meta: LlmPayloadMeta
    metrics: tuple[RouterMetrics, ...]
    detection_matrix: tuple[MatrixCell, ...]
    outcomes: tuple[LlmOutcome, ...]


def _outcome(result: ItemResult, record: CallRecord) -> LlmOutcome:
    """Return the exported form of one model result and its call record."""
    return LlmOutcome(
        router=result.router,
        item_id=result.item_id,
        correct=result.correct,
        tripped=tuple(DetectorName(name) for name in result.tripped()),
        plan=result.plan,
        malformed=result.malformed,
        stated_confidence=result.stated_confidence,
        cassette_key=record.cassette_key,
        stop_reason=record.stop_reason,
        input_tokens=record.input_tokens,
        output_tokens=record.output_tokens,
        cost_usd=record.cost_usd,
    )


def _meta(
    metrics: Sequence[RouterMetrics],
    model_results: Sequence[ItemResult],
    records: Sequence[CallRecord],
    labels: LlmRunLabels,
) -> LlmPayloadMeta:
    """Return the payload meta block."""
    malformed = Counter(result.router for result in model_results if result.malformed)
    routers = tuple(entry.router for entry in metrics)
    return LlmPayloadMeta(
        command=labels.command,
        challenge_set=labels.challenge_set,
        items=metrics[0].items,
        baseline=labels.baseline,
        routers=routers,
        models=tuple(dict.fromkeys(record.model for record in records)),
        prompt_sha256=labels.prompt_sha256,
        prompt_tuned_on=labels.prompt_tuned_on,
        dev_items=labels.dev_items,
        calibration_bins=CALIBRATION_BIN_COUNT,
        cost_usd=sum(record.cost_usd for record in records),
        malformed={router: malformed[router] for router in routers if router != labels.baseline},
    )


def build_llm_payload(
    baseline_results: Sequence[ItemResult],
    model_results: Sequence[ItemResult],
    records: Sequence[CallRecord],
    metrics: Sequence[RouterMetrics],
    labels: LlmRunLabels,
) -> LlmRouterPayload:
    """Return the LLM router payload, with floats rounded so replays give the same bytes."""
    if len(model_results) != len(records):
        raise ValueError("every model result needs its call record")
    payload = LlmRouterPayload(
        meta=_meta(metrics, model_results, records, labels),
        metrics=tuple(metrics),
        detection_matrix=detection_matrix([*baseline_results, *model_results]),
        outcomes=tuple(map(_outcome, model_results, records)),
    )
    return LlmRouterPayload.model_validate(round_floats(payload.model_dump(mode="json")))


def write_llm_payload(path: Path, payload: LlmRouterPayload) -> None:
    """Write the payload JSON with LF line endings, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = payload.model_dump_json(indent=JSON_INDENT) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
