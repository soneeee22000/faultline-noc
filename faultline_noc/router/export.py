"""JSON export of a router run: metrics, detection matrix, the items and every plan.

The payload carries no timestamps or absolute paths, so the same challenge set always gives the
same bytes. Floats are rounded so the committed file does not churn on the last digit.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, Self

from pydantic import Field, model_validator

from faultline_noc.models import FrozenModel
from faultline_noc.router.detectors import DetectorName
from faultline_noc.router.metrics import (
    CALIBRATION_BIN_COUNT,
    MatrixCell,
    RouterMetrics,
    detection_matrix,
)
from faultline_noc.router.models import ChallengeItem, RoutePlan
from faultline_noc.router.runner import ItemResult

SCHEMA_VERSION: Final = 1
RATE_DECIMALS = 6
JSON_INDENT = 2
CHALLENGE_SET_LABEL = "scenarios/router/challenge.yaml"


@dataclass(frozen=True)
class RunLabels:
    """Where a run came from: the reproducible command, the baseline and the challenge file."""

    command: str
    baseline: str
    challenge_set: str = CHALLENGE_SET_LABEL


class PayloadMeta(FrozenModel):
    """The command, the run shape and the harness verdict."""

    command: str
    challenge_set: str
    items: int = Field(ge=1)
    routers: tuple[str, ...]
    baseline: str
    detectors: tuple[DetectorName, ...]
    calibration_bins: int = Field(ge=1)
    harness_pass: bool
    failures: tuple[str, ...]

    @model_validator(mode="after")
    def _pass_mirrors_failures(self) -> Self:
        """Reject a verdict that disagrees with the failure list."""
        if self.harness_pass == bool(self.failures):
            raise ValueError("harness_pass must be true exactly when failures is empty")
        return self


class ItemOutcome(FrozenModel):
    """One router's plan for one item, whether the route is correct, and what tripped."""

    router: str
    item_id: str
    correct: bool
    tripped: tuple[DetectorName, ...]
    plan: RoutePlan


class RouterPayload(FrozenModel):
    """Everything a page needs to show one router run."""

    schema_version: Literal[1] = SCHEMA_VERSION
    meta: PayloadMeta
    metrics: tuple[RouterMetrics, ...]
    detection_matrix: tuple[MatrixCell, ...]
    items: tuple[ChallengeItem, ...]
    outcomes: tuple[ItemOutcome, ...]


def round_floats(value: object) -> object:
    """Return a JSON-shaped value with every float rounded to RATE_DECIMALS."""
    if isinstance(value, float):
        return round(value, RATE_DECIMALS)
    if isinstance(value, dict):
        return {key: round_floats(entry) for key, entry in value.items()}
    if isinstance(value, list):
        return [round_floats(entry) for entry in value]
    return value


def _outcome(result: ItemResult) -> ItemOutcome:
    """Return the exported form of one result; this payload has no slot for a malformed answer."""
    if result.plan is None:
        raise ValueError(
            f"{result.router} on {result.item_id}: malformed answers need the LLM payload"
        )
    return ItemOutcome(
        router=result.router,
        item_id=result.item_id,
        correct=result.correct,
        tripped=tuple(DetectorName(name) for name in result.tripped()),
        plan=result.plan,
    )


def build_payload(
    results: Sequence[ItemResult],
    items: Sequence[ChallengeItem],
    metrics: Sequence[RouterMetrics],
    failures: Sequence[str],
    labels: RunLabels,
) -> RouterPayload:
    """Return the export payload for a router run, with floats rounded."""
    meta = PayloadMeta(
        command=labels.command,
        challenge_set=labels.challenge_set,
        items=len(items),
        routers=tuple(entry.router for entry in metrics),
        baseline=labels.baseline,
        detectors=tuple(DetectorName),
        calibration_bins=CALIBRATION_BIN_COUNT,
        harness_pass=not failures,
        failures=tuple(failures),
    )
    payload = RouterPayload(
        meta=meta,
        metrics=tuple(metrics),
        detection_matrix=detection_matrix(results),
        items=tuple(items),
        outcomes=tuple(_outcome(result) for result in results),
    )
    return RouterPayload.model_validate(round_floats(payload.model_dump(mode="json")))


def payload_json(payload: RouterPayload) -> str:
    """Return the payload as indented JSON with a trailing newline."""
    return payload.model_dump_json(indent=JSON_INDENT) + "\n"


def write_payload(path: Path, payload: RouterPayload) -> None:
    """Write the payload JSON to a path with LF line endings, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload_json(payload), encoding="utf-8", newline="\n")
