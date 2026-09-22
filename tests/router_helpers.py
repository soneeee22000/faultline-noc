"""Builders for router plans and challenge items shared by the router tests."""

from faultline_noc.router.models import (
    Agent,
    Capability,
    ChallengeItem,
    Expectation,
    ExpectedStep,
    RoutePlan,
    RouteStep,
    Tag,
    structural_tags,
)

TAG_ORDER = tuple(Tag)


def step(
    agent: Agent,
    refs: tuple[str, ...] = (),
    *,
    write: bool = False,
    confirm: bool | None = None,
) -> RouteStep:
    """Return a plan step; a write step is confirmed unless confirm says otherwise."""
    capabilities = (Capability.READ, Capability.NETWORK_WRITE) if write else (Capability.READ,)
    return RouteStep(
        agent=agent,
        objective=f"{agent} step",
        context_refs=refs,
        allowed_capabilities=capabilities,
        requires_confirmation=write if confirm is None else confirm,
    )


def plan(*steps: RouteStep, confidence: float = 0.8) -> RoutePlan:
    """Return a routed plan over the given steps."""
    return RoutePlan(
        steps=steps,
        requires_clarification=False,
        clarification_question=None,
        confidence=confidence,
    )


def clarify(confidence: float = 0.6) -> RoutePlan:
    """Return a plan that asks for clarification."""
    return RoutePlan(
        steps=(),
        requires_clarification=True,
        clarification_question="Which one?",
        confidence=confidence,
    )


def item(
    *expected_steps: ExpectedStep,
    item_id: str = "r01_fixture",
    injection: bool = False,
    available: tuple[str, ...] = (),
) -> ChallengeItem:
    """Return a challenge item; no steps means the correct outcome is a clarification."""
    expectation = Expectation(
        requires_clarification=not expected_steps, steps=tuple(expected_steps)
    )
    refs = {ref for expected in expected_steps for ref in expected.context_refs}
    tags = set(structural_tags(expectation)) | ({Tag.INJECTION} if injection else set())
    return ChallengeItem(
        id=item_id,
        request="fixture request",
        available_context=tuple(sorted(refs | set(available))),
        expected=expectation,
        tags=tuple(tag for tag in TAG_ORDER if tag in tags),
    )


def expect(agent: Agent, refs: tuple[str, ...] = (), *, write: bool = False) -> ExpectedStep:
    """Return an expected step."""
    return ExpectedStep(agent=agent, context_refs=refs, network_write=write)
