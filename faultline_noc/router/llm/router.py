"""A Claude-backed router that answers through a forced submit_route_plan tool call.

The router never sees an item's expectation. Its answer is either a valid RoutePlan or a
malformed answer with a reason; a malformed answer is scored as incorrect and is never replaced
by a fallback plan.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from faultline_noc.llm.agent import ModelProfile
from faultline_noc.llm.pricing import SpendTracker, usage_cost_usd
from faultline_noc.llm.transport import Request, Response, Transport, request_key
from faultline_noc.models import MAX_CONFIDENCE, MIN_CONFIDENCE, FrozenModel
from faultline_noc.router.detectors import DETECTORS, Detector, route_matches, run_detectors
from faultline_noc.router.llm.prompt import (
    MAX_OUTPUT_TOKENS,
    SUBMIT_ROUTE_PLAN,
    SYSTEM_PROMPT,
    TOOL_DEFINITION,
    user_message,
)
from faultline_noc.router.models import ChallengeItem, RoutePlan
from faultline_noc.router.runner import ItemResult, malformed_detections

ROUTER_PREFIX = "router_"
TransportFactory = Callable[[str, str], Transport]


class CallRecord(FrozenModel):
    """What one model call cost and how its answer parsed; the cassette key names the file."""

    router: str
    item_id: str
    model: str
    cassette_key: str
    stop_reason: str | None
    input_tokens: int
    output_tokens: int
    cost_usd: float
    parse_status: str


@dataclass(frozen=True)
class ParsedAnswer:
    """A valid plan, or the reason the answer is malformed and any confidence it stated."""

    plan: RoutePlan | None
    malformed: str | None
    stated_confidence: float | None


def build_request(profile: ModelProfile, item: ChallengeItem) -> Request:
    """Return a Messages API request that forces exactly one submit_route_plan call."""
    return {
        "model": profile.model,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "system": SYSTEM_PROMPT,
        "tools": [TOOL_DEFINITION],
        "tool_choice": {"type": "tool", "name": SUBMIT_ROUTE_PLAN},
        "messages": [
            {"role": "user", "content": user_message(item.request, item.available_context)}
        ],
    }


def _stated_confidence(tool_input: Mapping[str, Any]) -> float | None:
    """Return the confidence a malformed answer stated, when it is a number in range."""
    value = tool_input.get("confidence")
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value) if MIN_CONFIDENCE <= value <= MAX_CONFIDENCE else None


def _submitted_input(response: Response) -> Mapping[str, Any] | None:
    """Return the input of the first submit_route_plan call, or None when there is none."""
    for block in response.get("content") or []:
        if block.get("type") == "tool_use" and block.get("name") == SUBMIT_ROUTE_PLAN:
            tool_input = block.get("input")
            return tool_input if isinstance(tool_input, Mapping) else {}
    return None


def parse_answer(response: Response) -> ParsedAnswer:
    """Return the plan from a response, or why it is malformed; nothing is substituted."""
    tool_input = _submitted_input(response)
    if tool_input is None:
        return ParsedAnswer(None, f"no {SUBMIT_ROUTE_PLAN} call", None)
    try:
        return ParsedAnswer(RoutePlan.model_validate(dict(tool_input)), None, None)
    except ValidationError as error:
        reason = f"invalid plan: {error.errors()[0]['msg']}"
        return ParsedAnswer(None, reason, _stated_confidence(tool_input))


def score_answer(
    router: str,
    item: ChallengeItem,
    answer: ParsedAnswer,
    detectors: Sequence[Detector] = DETECTORS,
) -> ItemResult:
    """Score a parsed answer; a malformed one is incorrect and trips per malformed_detections."""
    if answer.plan is None:
        return ItemResult(
            router=router,
            item_id=item.id,
            plan=None,
            correct=False,
            detections=malformed_detections(item, detectors),
            malformed=answer.malformed,
            stated_confidence=answer.stated_confidence,
        )
    return ItemResult(
        router=router,
        item_id=item.id,
        plan=answer.plan,
        correct=route_matches(answer.plan, item),
        detections=run_detectors(answer.plan, item, detectors),
    )


def _call_record(
    router: str, item: ChallengeItem, request: Request, response: Response, answer: ParsedAnswer
) -> CallRecord:
    """Return the cost and parse record for one call."""
    usage = response.get("usage") or {}
    model = str(request["model"])
    return CallRecord(
        router=router,
        item_id=item.id,
        model=model,
        cassette_key=request_key(request),
        stop_reason=response.get("stop_reason"),
        input_tokens=int(usage.get("input_tokens") or 0),
        output_tokens=int(usage.get("output_tokens") or 0),
        cost_usd=usage_cost_usd(model, usage),
        parse_status="ok" if answer.plan is not None else "malformed",
    )


class LlmRouter:
    """Routes each item with one model call through a per-item transport."""

    def __init__(
        self, profile: ModelProfile, transports: TransportFactory, spend: SpendTracker
    ) -> None:
        """Bind a model profile, a per-item transport factory and the shared spend tracker."""
        self.profile = profile
        self.name = ROUTER_PREFIX + profile.label
        self._transports = transports
        self._spend = spend

    def route_item(self, item: ChallengeItem) -> tuple[ItemResult, CallRecord]:
        """Route one item: stop if the spend threshold is reached, call, parse and score."""
        self._spend.check()
        request = build_request(self.profile, item)
        response = self._transports(self.profile.model, item.id).create(request)
        self._spend.record(self.profile.model, response.get("usage") or {})
        answer = parse_answer(response)
        record = _call_record(self.name, item, request, response, answer)
        return score_answer(self.name, item, answer), record


def run_llm_router(
    router: LlmRouter, items: Sequence[ChallengeItem]
) -> tuple[tuple[ItemResult, ...], tuple[CallRecord, ...]]:
    """Route every item in order and return the scored results and their call records."""
    pairs = [router.route_item(item) for item in items]
    return tuple(result for result, _ in pairs), tuple(record for _, record in pairs)
