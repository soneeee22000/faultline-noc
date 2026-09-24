"""Tests for the LLM router: parsing, the malformed-answer boundary, metrics and replay."""

import json
from pathlib import Path
from typing import Any

import pytest

from faultline_noc.llm.agent import MODEL_PROFILES
from faultline_noc.llm.pricing import SpendTracker
from faultline_noc.llm.transport import CassetteMissingError, CassetteStore, ReplayTransport
from faultline_noc.router.detectors import DetectorName
from faultline_noc.router.llm.__main__ import main
from faultline_noc.router.llm.prompt import SUBMIT_ROUTE_PLAN, prompt_sha256
from faultline_noc.router.llm.router import (
    LlmRouter,
    build_request,
    parse_answer,
    score_answer,
)
from faultline_noc.router.metrics import compute_metrics
from faultline_noc.router.models import Agent, RoutePlan
from faultline_noc.router.runner import ItemResult
from tests.router_helpers import clarify, expect, item, plan, step

HAIKU = MODEL_PROFILES["claude-haiku-4-5"]
COMMITTED = Path(__file__).resolve().parent.parent / "site" / "src" / "data"


def _response(tool_input: object, name: str = SUBMIT_ROUTE_PLAN) -> dict[str, Any]:
    """Return a Messages API response carrying one tool call."""
    block = {"type": "tool_use", "id": "toolu_1", "name": name, "input": tool_input}
    usage = {"input_tokens": 100, "output_tokens": 20}
    return {"content": [block], "stop_reason": "tool_use", "usage": usage}


def _plan_input(route: RoutePlan) -> dict[str, Any]:
    """Return the tool input for a plan."""
    return dict(route.model_dump(mode="json"))


def test_a_valid_tool_call_parses_to_the_plan() -> None:
    """A well-formed submit_route_plan call yields exactly that plan."""
    expected = plan(step(Agent.KNOWLEDGE, ("doc:x",)))
    answer = parse_answer(_response(_plan_input(expected)))
    assert answer.plan == expected
    assert answer.malformed is None


def test_stringified_steps_are_malformed_and_keep_the_stated_confidence() -> None:
    """Steps serialised as a JSON string are not repaired; the stated confidence is kept."""
    tool_input = _plan_input(plan(step(Agent.KNOWLEDGE)))
    tool_input["steps"] = json.dumps(tool_input["steps"])
    answer = parse_answer(_response(tool_input))
    assert answer.plan is None
    assert answer.malformed is not None and answer.malformed.startswith("invalid plan")
    assert answer.stated_confidence == tool_input["confidence"]


def test_a_missing_tool_call_is_malformed() -> None:
    """A response without submit_route_plan is malformed and states no confidence."""
    answer = parse_answer(_response({}, name="something_else"))
    assert answer.malformed == f"no {SUBMIT_ROUTE_PLAN} call"
    assert answer.stated_confidence is None


def test_malformed_output_on_a_clarification_item_stays_incorrect() -> None:
    """A malformed answer where clarification is expected gets no credit anywhere."""
    ambiguous = item()
    answer = parse_answer(_response({"plan": {}, "confidence": 0.9}))
    result = score_answer("router_llm_test", ambiguous, answer)
    assert result.correct is False
    assert result.plan is None
    assert DetectorName.MISSED_CLARIFICATION in result.tripped()
    metrics = compute_metrics([result], [ambiguous])
    assert metrics.route_correct == 0
    assert metrics.clarification_recall == 0.0
    assert metrics.brier == pytest.approx(0.81)


def test_malformed_output_never_counts_as_resisting_an_injection() -> None:
    """An injection item answered with garbage is not credited as resisted."""
    injected = item(expect(Agent.INCIDENT, ("alarm:A",)), injection=True)
    result = score_answer("router_llm_test", injected, parse_answer(_response({})))
    metrics = compute_metrics([result], [injected])
    assert metrics.injection_resistance == 0.0
    assert DetectorName.UNSAFE_WRITE not in result.tripped()


def test_a_malformed_result_cannot_be_marked_correct() -> None:
    """The result boundary rejects a malformed answer marked correct, or one with a plan."""
    with pytest.raises(ValueError, match="cannot be correct"):
        ItemResult(
            router="r", item_id="r01_x", plan=None, correct=True, detections=(), malformed="x"
        )
    with pytest.raises(ValueError, match="not both"):
        ItemResult(
            router="r", item_id="r01_x", plan=clarify(), correct=True, detections=(), malformed="x"
        )


def test_the_request_forces_one_tool_and_never_shows_the_expectation() -> None:
    """The request forces submit_route_plan and carries only the request and its refs."""
    target = item(expect(Agent.TESTING, ("cluster:c",)))
    request = build_request(HAIKU, target)
    assert request["tool_choice"] == {"type": "tool", "name": SUBMIT_ROUTE_PLAN}
    assert "testing" not in request["messages"][0]["content"]


def test_replay_fails_closed_without_a_cassette(tmp_path: Path) -> None:
    """A request with no recorded response raises instead of calling the API."""
    router = LlmRouter(
        HAIKU, lambda _model, _item: ReplayTransport(CassetteStore(tmp_path)), SpendTracker(1.0)
    )
    with pytest.raises(CassetteMissingError):
        router.route_item(item(expect(Agent.KNOWLEDGE)))


def test_committed_llm_payload_replays_byte_for_byte(tmp_path: Path) -> None:
    """Replaying the committed cassettes reproduces router_llm_results.json exactly."""
    committed = COMMITTED / "router_llm_results.json"
    fresh = tmp_path / "router_llm_results.json"
    assert main(["--replay", "--all", "--json", str(fresh)]) == 0
    assert fresh.read_bytes() == committed.read_bytes()
    assert json.loads(committed.read_text(encoding="utf-8"))["meta"]["prompt_sha256"] == (
        prompt_sha256()
    )
