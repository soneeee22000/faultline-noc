"""Mutant routers: the keyword baseline with exactly one known defect each.

They exist to prove the detectors fire. Each wraps the baseline, so it can only show its defect
where the baseline produces the raw material for it. The harness check fails if the
challenge set gives a mutant no raw material.
"""

from faultline_noc.router.baseline import KeywordBaseline
from faultline_noc.router.models import Agent, Capability, RoutePlan, Router, RouteStep

GUESS_AGENT = Agent.KNOWLEDGE


def _with_steps(plan: RoutePlan, steps: tuple[RouteStep, ...]) -> RoutePlan:
    """Return a routed plan with new steps and the original confidence."""
    return RoutePlan(
        steps=steps,
        requires_clarification=False,
        clarification_question=None,
        confidence=plan.confidence,
    )


def _changed(step: RouteStep, **changes: object) -> RouteStep:
    """Return a validated copy of a step with some fields changed."""
    return RouteStep.model_validate({**step.model_dump(), **changes})


class _WrapsBaseline:
    """Holds the router whose plans the mutant corrupts."""

    def __init__(self, base: Router | None = None) -> None:
        """Wrap the given router, or a fresh keyword baseline."""
        self._base: Router = base if base is not None else KeywordBaseline()


class AlwaysIncident(_WrapsBaseline):
    """Sends every step to the incident agent; clarifications, refs and gates are unchanged."""

    name: str = "mutant_always_incident"

    def route(self, request: str, available_context: tuple[str, ...]) -> RoutePlan:
        """Return the baseline plan with every step relabelled to incident."""
        plan = self._base.route(request, available_context)
        if plan.requires_clarification:
            return plan
        steps = tuple(_changed(step, agent=Agent.INCIDENT) for step in plan.steps)
        return _with_steps(plan, steps)


class DropsContext(_WrapsBaseline):
    """Hands no context refs to any step after the first."""

    name: str = "mutant_drops_context"

    def route(self, request: str, available_context: tuple[str, ...]) -> RoutePlan:
        """Return the baseline plan with context_refs cleared on steps two onwards."""
        plan = self._base.route(request, available_context)
        if plan.requires_clarification:
            return plan
        later = tuple(_changed(step, context_refs=()) for step in plan.steps[1:])
        return _with_steps(plan, (plan.steps[0], *later))


class UngatedWrite(_WrapsBaseline):
    """Grants network_write steps without asking for confirmation."""

    name: str = "mutant_ungated_write"

    def route(self, request: str, available_context: tuple[str, ...]) -> RoutePlan:
        """Return the baseline plan with requires_confirmation cleared on every write step."""
        plan = self._base.route(request, available_context)
        if plan.requires_clarification:
            return plan
        steps = tuple(
            _changed(step, requires_confirmation=False) if step.grants_write else step
            for step in plan.steps
        )
        return _with_steps(plan, steps)


class NeverClarify(_WrapsBaseline):
    """Never asks the user; where the baseline would clarify it guesses a read-only step."""

    name: str = "mutant_never_clarify"

    def route(self, request: str, available_context: tuple[str, ...]) -> RoutePlan:
        """Return the baseline plan, or a read-only guess in place of a clarification."""
        plan = self._base.route(request, available_context)
        if not plan.requires_clarification:
            return plan
        guess = RouteStep(
            agent=GUESS_AGENT,
            objective=request,
            context_refs=available_context,
            allowed_capabilities=(Capability.READ,),
            requires_confirmation=False,
        )
        return _with_steps(plan, (guess,))


MUTANT_ROUTERS: tuple[type[_WrapsBaseline], ...] = (
    AlwaysIncident,
    DropsContext,
    UngatedWrite,
    NeverClarify,
)
