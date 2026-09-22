"""Router plans, challenge items and their expectations.

A router turns one user request into an ordered plan over three specialist agents. Asking the
user to clarify is an outcome of routing, never a fourth agent.
"""

from collections import Counter
from enum import StrEnum
from typing import Final, Literal, Protocol, Self

from pydantic import Field, model_validator

from faultline_noc.models import MAX_CONFIDENCE, MIN_CONFIDENCE, FrozenModel

ITEM_ID_PATTERN = r"^r\d{2}_[a-z0-9_]+$"
CHALLENGE_SCHEMA_VERSION: Final = 1
MULTI_STEP_MIN = 2


class Agent(StrEnum):
    """The specialist agents a router can hand a step to."""

    KNOWLEDGE = "knowledge"
    TESTING = "testing"
    INCIDENT = "incident"


class Capability(StrEnum):
    """What a step is allowed to do; network_write changes network or lab state."""

    READ = "read"
    NETWORK_WRITE = "network_write"


class Tag(StrEnum):
    """Challenge-item tags; single, multi, ambiguous and write follow from the expectation."""

    SINGLE = "single"
    MULTI = "multi"
    AMBIGUOUS = "ambiguous"
    WRITE = "write"
    INJECTION = "injection"


def check_clarification(
    requires_clarification: bool, step_count: int, question: str | None = None
) -> None:
    """Raise ValueError unless a clarification has no steps and a route has at least one."""
    if requires_clarification and step_count:
        raise ValueError("a clarification must not contain steps")
    if not requires_clarification and not step_count:
        raise ValueError("a route needs at least one step")
    if question is not None and not requires_clarification:
        raise ValueError("only a clarification carries a question")


class RouteStep(FrozenModel):
    """One step of a plan: the agent, what it should do, what it may see and do."""

    agent: Agent
    objective: str = Field(min_length=1)
    context_refs: tuple[str, ...]
    allowed_capabilities: tuple[Capability, ...] = Field(min_length=1)
    requires_confirmation: bool

    @model_validator(mode="after")
    def _distinct_capabilities(self) -> Self:
        """Reject a repeated capability."""
        if len(set(self.allowed_capabilities)) != len(self.allowed_capabilities):
            raise ValueError("allowed_capabilities must not repeat")
        return self

    @property
    def grants_write(self) -> bool:
        """Return True when the step may change network or lab state."""
        return Capability.NETWORK_WRITE in self.allowed_capabilities


class RoutePlan(FrozenModel):
    """A router's answer: ordered steps, or a clarification question, with a confidence."""

    steps: tuple[RouteStep, ...]
    requires_clarification: bool
    clarification_question: str | None
    confidence: float = Field(ge=MIN_CONFIDENCE, le=MAX_CONFIDENCE)

    @model_validator(mode="after")
    def _clarification_is_an_outcome(self) -> Self:
        """Require a question and no steps to clarify, and at least one step otherwise."""
        check_clarification(
            self.requires_clarification, len(self.steps), self.clarification_question
        )
        if self.requires_clarification and not (self.clarification_question or "").strip():
            raise ValueError("a clarification needs a question")
        return self

    @property
    def agents(self) -> tuple[Agent, ...]:
        """Return the step agents in order."""
        return tuple(step.agent for step in self.steps)


class ExpectedStep(FrozenModel):
    """What one step of the correct plan must have: its agent, its refs, whether it writes."""

    agent: Agent
    context_refs: tuple[str, ...] = ()
    network_write: bool = False


class Expectation(FrozenModel):
    """The correct plan for an item: an ordered route, or a clarification."""

    requires_clarification: bool
    steps: tuple[ExpectedStep, ...] = ()

    @model_validator(mode="after")
    def _clarification_is_an_outcome(self) -> Self:
        """Apply the same clarification rule as a plan."""
        check_clarification(self.requires_clarification, len(self.steps))
        return self

    @property
    def agents(self) -> tuple[Agent, ...]:
        """Return the expected agents in order."""
        return tuple(step.agent for step in self.steps)

    @property
    def requests_write(self) -> bool:
        """Return True when the user asked for a change to network or lab state."""
        return any(step.network_write for step in self.steps)


def structural_tags(expected: Expectation) -> frozenset[Tag]:
    """Return the tags implied by an expectation: its shape, and write if it asks for one."""
    if expected.requires_clarification:
        shape = Tag.AMBIGUOUS
    elif len(expected.steps) >= MULTI_STEP_MIN:
        shape = Tag.MULTI
    else:
        shape = Tag.SINGLE
    return frozenset({shape, Tag.WRITE}) if expected.requests_write else frozenset({shape})


class ChallengeItem(FrozenModel):
    """One authored request, the context a router may pass on, and the correct plan."""

    id: str = Field(pattern=ITEM_ID_PATTERN)
    request: str = Field(min_length=1)
    available_context: tuple[str, ...]
    expected: Expectation
    tags: tuple[Tag, ...] = Field(min_length=1)
    baseline_miss: str | None = None

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        """Check expected refs are available and the tags match the expectation."""
        available = frozenset(self.available_context)
        for step in self.expected.steps:
            missing = [ref for ref in step.context_refs if ref not in available]
            if missing:
                raise ValueError(f"{self.id}: {missing} not in available_context")
        if len(set(self.tags)) != len(self.tags):
            raise ValueError(f"{self.id}: tags must not repeat")
        if set(self.tags) - {Tag.INJECTION} != structural_tags(self.expected):
            raise ValueError(f"{self.id}: tags do not match the expected plan")
        return self


class ChallengeSet(FrozenModel):
    """The authored challenge set as stored in YAML."""

    schema_version: Literal[1] = CHALLENGE_SCHEMA_VERSION
    items: tuple[ChallengeItem, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_ids(self) -> Self:
        """Reject duplicate item ids."""
        duplicates = [key for key, count in Counter(i.id for i in self.items).items() if count > 1]
        if duplicates:
            raise ValueError(f"duplicate item ids: {duplicates}")
        return self


class Router(Protocol):
    """Turns a request and the refs it may pass on into a plan; it never sees the expectation."""

    name: str

    def route(self, request: str, available_context: tuple[str, ...]) -> RoutePlan:
        """Return the plan for one request."""
        ...
