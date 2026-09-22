"""Run routers over challenge items and record each plan with its detections."""

from collections.abc import Sequence

from faultline_noc.models import FrozenModel
from faultline_noc.router.detectors import (
    DETECTORS,
    Detection,
    Detector,
    route_matches,
    run_detectors,
)
from faultline_noc.router.models import ChallengeItem, RoutePlan, Router


class ItemResult(FrozenModel):
    """One router's plan for one item, whether its route is correct, and what tripped."""

    router: str
    item_id: str
    plan: RoutePlan
    correct: bool
    detections: tuple[Detection, ...]

    def tripped(self) -> tuple[str, ...]:
        """Return the names of the detectors that tripped, in detector order."""
        return tuple(str(item.detector) for item in self.detections if item.tripped)


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
