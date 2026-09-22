"""Tests for the router plan and challenge-item models and their validators."""

import pytest
from pydantic import ValidationError

from faultline_noc.router.models import (
    Agent,
    Capability,
    ChallengeItem,
    ChallengeSet,
    Expectation,
    ExpectedStep,
    RoutePlan,
    RouteStep,
    Tag,
)


def _step(agent: Agent = Agent.KNOWLEDGE, *, write: bool = False) -> RouteStep:
    """Return a route step, optionally granting network_write behind a confirmation."""
    capabilities = (Capability.READ, Capability.NETWORK_WRITE) if write else (Capability.READ,)
    return RouteStep(
        agent=agent,
        objective="explain the AMF",
        context_refs=("lab:5g-core-101",),
        allowed_capabilities=capabilities,
        requires_confirmation=write,
    )


def _item(**overrides: object) -> ChallengeItem:
    """Return a valid single-intent challenge item with fields overridden."""
    fields: dict[str, object] = {
        "id": "r01_explain_amf",
        "request": "Explain the AMF.",
        "available_context": ("lab:5g-core-101",),
        "expected": Expectation(
            requires_clarification=False,
            steps=(ExpectedStep(agent=Agent.KNOWLEDGE, context_refs=("lab:5g-core-101",)),),
        ),
        "tags": (Tag.SINGLE,),
    }
    fields.update(overrides)
    return ChallengeItem.model_validate(fields)


def test_a_routed_plan_lists_its_agents_in_order() -> None:
    """A plan's agents are its step agents, in step order."""
    plan = RoutePlan(
        steps=(_step(Agent.TESTING), _step(Agent.INCIDENT)),
        requires_clarification=False,
        clarification_question=None,
        confidence=0.7,
    )
    assert plan.agents == (Agent.TESTING, Agent.INCIDENT)


def test_a_clarification_needs_a_question_and_no_steps() -> None:
    """Clarification is an outcome with a question, never a step to a fourth agent."""
    plan = RoutePlan(
        steps=(), requires_clarification=True, clarification_question="Which NF?", confidence=0.6
    )
    assert plan.agents == ()
    with pytest.raises(ValidationError):
        RoutePlan(
            steps=(), requires_clarification=True, clarification_question=None, confidence=0.6
        )
    with pytest.raises(ValidationError):
        RoutePlan(
            steps=(_step(),),
            requires_clarification=True,
            clarification_question="Which NF?",
            confidence=0.6,
        )


def test_a_routed_plan_needs_a_step_and_no_question() -> None:
    """A plan that does not clarify has at least one step and no question."""
    with pytest.raises(ValidationError):
        RoutePlan(steps=(), requires_clarification=False, clarification_question=None, confidence=1)
    with pytest.raises(ValidationError):
        RoutePlan(
            steps=(_step(),),
            requires_clarification=False,
            clarification_question="Which NF?",
            confidence=0.5,
        )


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_confidence_is_bounded(confidence: float) -> None:
    """Confidence lies in [0, 1]."""
    with pytest.raises(ValidationError):
        RoutePlan(
            steps=(_step(),),
            requires_clarification=False,
            clarification_question=None,
            confidence=confidence,
        )


def test_a_step_reports_whether_it_grants_network_write() -> None:
    """Only a step whose capabilities include network_write grants it."""
    assert _step(write=True).grants_write
    assert not _step().grants_write


def test_a_step_needs_at_least_one_distinct_capability() -> None:
    """Capabilities are non-empty and not repeated."""
    with pytest.raises(ValidationError):
        RouteStep(
            agent=Agent.KNOWLEDGE,
            objective="x",
            context_refs=(),
            allowed_capabilities=(),
            requires_confirmation=False,
        )
    with pytest.raises(ValidationError):
        RouteStep(
            agent=Agent.KNOWLEDGE,
            objective="x",
            context_refs=(),
            allowed_capabilities=(Capability.READ, Capability.READ),
            requires_confirmation=False,
        )


def test_a_valid_item_loads() -> None:
    """The fixture item is valid and keeps its single tag."""
    assert _item().tags == (Tag.SINGLE,)


def test_an_item_may_only_require_refs_it_makes_available() -> None:
    """Every expected context ref must be in the item's available context."""
    with pytest.raises(ValidationError, match="not in available_context"):
        _item(available_context=())


@pytest.mark.parametrize(
    "tags",
    [(Tag.MULTI,), (Tag.AMBIGUOUS,), (Tag.SINGLE, Tag.WRITE), (), (Tag.SINGLE, Tag.SINGLE)],
)
def test_structural_tags_must_match_the_expectation(tags: tuple[Tag, ...]) -> None:
    """single, multi, ambiguous and write follow from the expected plan, and tags are unique."""
    with pytest.raises(ValidationError):
        _item(tags=tags)


def test_an_injection_item_may_also_expect_a_legitimate_write() -> None:
    """A user can ask for one write while pasted text injects another; the set can express it."""
    expected = Expectation(
        requires_clarification=False,
        steps=(ExpectedStep(agent=Agent.INCIDENT, network_write=True),),
    )
    injected = _item(expected=expected, tags=(Tag.SINGLE, Tag.WRITE, Tag.INJECTION))
    assert injected.expected.requests_write


@pytest.mark.parametrize("question", ["", "   ", "\n\t"])
def test_a_clarification_question_must_have_content(question: str) -> None:
    """An empty or whitespace-only question does not count as asking."""
    with pytest.raises(ValidationError):
        RoutePlan(
            steps=(), requires_clarification=True, clarification_question=question, confidence=0.6
        )


def test_an_expected_clarification_has_no_steps() -> None:
    """The expectation follows the same clarification rule as a plan."""
    with pytest.raises(ValidationError):
        Expectation(requires_clarification=True, steps=(ExpectedStep(agent=Agent.INCIDENT),))
    with pytest.raises(ValidationError):
        Expectation(requires_clarification=False, steps=())


def test_item_ids_follow_the_pattern() -> None:
    """Item ids look like r01_short_name."""
    with pytest.raises(ValidationError):
        _item(id="Item 1")


def test_a_challenge_set_rejects_duplicate_ids() -> None:
    """Two items with the same id are rejected."""
    with pytest.raises(ValidationError, match="duplicate"):
        ChallengeSet(items=(_item(), _item()))
