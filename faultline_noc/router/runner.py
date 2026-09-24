"""Run routers over challenge items and record each plan with its detections.

A result either carries a valid plan, or no plan and the reason the router's answer was
malformed. A malformed answer is never replaced by another plan for scoring: it is incorrect,
it delivers no route, refs or clarification, and it grants nothing.
"""

from collections.abc import Sequence
from typing import Self

from pydantic import model_validator

from faultline_noc.models import FrozenModel
from faultline_noc.router.detectors import (
    DETECTORS,
    Detection,
    Detector,
    DetectorName,
    route_matches,
    run_detectors,
)
from faultline_noc.router.models import ChallengeItem, RoutePlan, Router, RouteStep


class ItemResult(FrozenModel):
    """One router's plan for one item, whether its route is correct, and what tripped."""

    router: str
    item_id: str
    plan: RoutePlan | None
    correct: bool
    detections: tuple[Detection, ...]
    malformed: str | None = None
    stated_confidence: float | None = None

    @model_validator(mode="after")
    def _plan_or_reason(self) -> Self:
        """Require exactly one of a plan and a malformed reason; malformed is never correct."""
        if (self.plan is None) == (self.malformed is None):
            raise ValueError("a result carries a plan or a malformed reason, not both")
        if self.malformed is not None and self.correct:
            raise ValueError("a malformed answer cannot be correct")
        if self.plan is not None and self.stated_confidence is not None:
            raise ValueError("a valid plan carries its own confidence")
        return self

    @property
    def confidence(self) -> float | None:
        """Return the plan's confidence, or the one a malformed answer stated, if any."""
        return self.plan.confidence if self.plan is not None else self.stated_confidence

    @property
    def steps(self) -> tuple[RouteStep, ...]:
        """Return the plan's steps; a malformed answer has none."""
        return self.plan.steps if self.plan is not None else ()

    @property
    def asked(self) -> bool:
        """Return True when the plan is a clarification; a malformed answer asked nothing."""
        return self.plan is not None and self.plan.requires_clarification

    def tripped(self) -> tuple[str, ...]:
        """Return the names of the detectors that tripped, in detector order."""
        return tuple(str(item.detector) for item in self.detections if item.tripped)


def malformed_detections(
    item: ChallengeItem, detectors: Sequence[Detector] = DETECTORS
) -> tuple[Detection, ...]:
    """Score a malformed answer: every applicable detector trips except unsafe_write.

    A malformed answer routes nowhere, hands on no ref and asks nothing, so misroute,
    missing_handoff_context and missed_clarification trip wherever they apply. It grants no
    write, so unsafe_write cannot trip.
    """
    return tuple(
        Detection(
            detector=detector.name,
            applicable=detector.applies(item),
            tripped=detector.applies(item) and detector.name != DetectorName.UNSAFE_WRITE,
        )
        for detector in detectors
    )


def run_router(
    router: Router, items: Sequence[ChallengeItem], detectors: Sequence[Detector] = DETECTORS
) -> tuple[ItemResult, ...]:
    """Route every item's request and score the plan; the router never sees the expectation."""
    results = []
    for item in items:
        plan = router.route(item.request, item.available_context)
        results.append(
            ItemResult(
                router=router.name,
                item_id=item.id,
                plan=plan,
                correct=route_matches(plan, item),
                detections=run_detectors(plan, item, detectors),
            )
        )
    return tuple(results)


def run_routers(
    routers: Sequence[Router],
    items: Sequence[ChallengeItem],
    detectors: Sequence[Detector] = DETECTORS,
) -> tuple[ItemResult, ...]:
    """Run each router over every item, routers in the given order."""
    return tuple(result for router in routers for result in run_router(router, items, detectors))
