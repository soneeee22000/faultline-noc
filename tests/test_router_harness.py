"""Tests for the router harness check: mutants are caught, a disabled detector fails the check."""

from dataclasses import replace

import pytest

from faultline_noc.router.baseline import KeywordBaseline
from faultline_noc.router.challenge import load_challenge, smoke_subset
from faultline_noc.router.detectors import DETECTORS, DetectorName
from faultline_noc.router.harness import (
    BASELINE_NAME,
    INJECTION_PROBE,
    NOT_EXERCISED,
    ROUTER_MUTANT_TARGETS,
    MutantTarget,
    default_routers,
    harness_failures,
)
from faultline_noc.router.models import Agent, ChallengeItem, RoutePlan, Tag
from faultline_noc.router.mutants import (
    AlwaysIncident,
    DropsContext,
    NeverClarify,
    UngatedWrite,
)
from faultline_noc.router.runner import ItemResult, run_router, run_routers
from tests.router_helpers import plan, step

UNGATED_STUB = "stub_ungated_incident"


def _never(_plan: RoutePlan, _item: ChallengeItem) -> bool:
    """Stand-in detector check that never trips."""
    return False


def _ungated_only(candidate: RoutePlan, _item: ChallengeItem) -> bool:
    """unsafe_write with its unrequested-write half removed: only a missing gate trips."""
    return any(step.grants_write and not step.requires_confirmation for step in candidate.steps)


class UngatedIncidentStub:
    """Answers every request with one ungated incident write step."""

    name: str = UNGATED_STUB

    def route(self, _request: str, _available_context: tuple[str, ...]) -> RoutePlan:
        """Return a single ungated write to the incident agent."""
        return plan(step(Agent.INCIDENT, write=True, confirm=False))


@pytest.fixture(scope="module")
def challenge() -> tuple[ChallengeItem, ...]:
    """Return the committed challenge set."""
    return load_challenge()


@pytest.fixture(scope="module")
def results(challenge: tuple[ChallengeItem, ...]) -> tuple[ItemResult, ...]:
    """Return the baseline and every mutant over the full set."""
    return run_routers(default_routers(), challenge)


def test_harness_passes_on_the_full_set(
    results: tuple[ItemResult, ...], challenge: tuple[ChallengeItem, ...]
) -> None:
    """Each mutant is caught by its own detector and the baseline gates every write."""
    assert harness_failures(results, challenge) == ()


def test_harness_passes_on_the_smoke_subset(challenge: tuple[ChallengeItem, ...]) -> None:
    """The smoke subset alone exercises every mutant."""
    subset = smoke_subset(challenge)
    assert harness_failures(run_routers(default_routers(), subset), subset) == ()


def test_each_detector_is_the_target_of_exactly_one_mutant() -> None:
    """Four mutants, one per detector."""
    targeted = [target.detector for target in ROUTER_MUTANT_TARGETS.values()]
    assert sorted(targeted) == sorted(DetectorName)
    assert set(ROUTER_MUTANT_TARGETS) == {
        AlwaysIncident.name,
        DropsContext.name,
        UngatedWrite.name,
        NeverClarify.name,
    }


@pytest.mark.parametrize("disabled", [detector.name for detector in DETECTORS])
def test_harness_fails_when_a_detector_is_disabled(
    disabled: DetectorName, challenge: tuple[ChallengeItem, ...]
) -> None:
    """Switching off any detector makes the check fail, and every failure names that detector."""
    detectors = tuple(
        replace(detector, check=_never) if detector.name == disabled else detector
        for detector in DETECTORS
    )
    results = run_routers(default_routers(), challenge, detectors)
    failures = harness_failures(results, challenge, detectors=detectors)
    assert failures
    assert all(str(disabled) in failure for failure in failures)


def test_default_routers_are_the_baseline_and_the_four_mutants() -> None:
    """What the CLI runs is exactly the baseline plus every mutant with a declared target."""
    names = [router.name for router in default_routers()]
    assert len(names) == len(set(names))
    assert set(names) == {BASELINE_NAME} | set(ROUTER_MUTANT_TARGETS)


def test_baseline_only_results_fail_the_check(challenge: tuple[ChallengeItem, ...]) -> None:
    """A run with no mutant results cannot pass: each missing mutant is reported."""
    failures = harness_failures(run_router(KeywordBaseline(), challenge), challenge)
    assert set(failures) == {f"{name}: {NOT_EXERCISED}" for name in ROUTER_MUTANT_TARGETS}


def test_a_missing_mutant_is_reported(challenge: tuple[ChallengeItem, ...]) -> None:
    """Dropping one mutant from the run fails the check for that mutant alone."""
    routers = tuple(r for r in default_routers() if r.name != NeverClarify.name)
    failures = harness_failures(run_routers(routers, challenge), challenge)
    assert failures == (f"{NeverClarify.name}: {NOT_EXERCISED}",)


def test_the_injection_probe_catches_a_detector_blind_to_unrequested_writes(
    challenge: tuple[ChallengeItem, ...],
) -> None:
    """With only the gate half of unsafe_write, every injection item fails the probe."""
    detectors = tuple(
        replace(detector, check=_ungated_only)
        if detector.name == DetectorName.UNSAFE_WRITE
        else detector
        for detector in DETECTORS
    )
    results = run_routers(default_routers(), challenge, detectors)
    failures = harness_failures(results, challenge, detectors=detectors)
    injected = [item for item in challenge if Tag.INJECTION in item.tags]
    assert len(failures) == len(injected)
    assert all(failure.startswith(INJECTION_PROBE) for failure in failures)
    assert all(str(DetectorName.UNSAFE_WRITE) in failure for failure in failures)


def test_a_set_without_injection_items_fails_the_probe(
    challenge: tuple[ChallengeItem, ...],
) -> None:
    """With nothing to probe, the injection half of unsafe_write is reported as unexercised."""
    clean = tuple(item for item in challenge if Tag.INJECTION not in item.tags)
    failures = harness_failures(run_routers(default_routers(), clean), clean)
    assert len(failures) == 1
    assert failures[0].startswith(INJECTION_PROBE)


def test_a_mutant_without_raw_material_is_reported(challenge: tuple[ChallengeItem, ...]) -> None:
    """drops_context run without multi-step items can never show its defect."""
    subset = tuple(item for item in challenge if Tag.MULTI not in item.tags)
    failures = harness_failures(run_routers(default_routers(), subset), subset)
    assert len(failures) == 1
    assert str(DetectorName.MISSING_HANDOFF_CONTEXT) in failures[0]


def test_an_undeclared_side_effect_fails_the_check(
    challenge: tuple[ChallengeItem, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stub whose declared effects leave out unsafe_write is flagged for exactly that."""
    declared = MutantTarget(
        DetectorName.MISROUTE,
        frozenset({DetectorName.MISSING_HANDOFF_CONTEXT, DetectorName.MISSED_CLARIFICATION}),
    )
    monkeypatch.setitem(ROUTER_MUTANT_TARGETS, UNGATED_STUB, declared)
    results = run_routers((*default_routers(), UngatedIncidentStub()), challenge)
    failures = harness_failures(results, challenge)
    assert failures
    assert all(str(DetectorName.UNSAFE_WRITE) in failure for failure in failures)


def test_an_unsafe_baseline_fails_the_check(challenge: tuple[ChallengeItem, ...]) -> None:
    """A router named as the baseline that writes without confirmation fails on gate recall."""
    results = run_router(UngatedIncidentStub(), challenge)
    everything = harness_failures(results, challenge, baseline=UNGATED_STUB)
    failures = [failure for failure in everything if NOT_EXERCISED not in failure]
    assert any("gate recall" in failure for failure in failures)
    assert all(str(DetectorName.UNSAFE_WRITE) in failure for failure in failures)


def test_missing_baseline_results_fail_the_check(challenge: tuple[ChallengeItem, ...]) -> None:
    """Without baseline results there is nothing to compare mutants against."""
    failures = harness_failures(run_router(DropsContext(), challenge), challenge)
    assert failures == (f"{BASELINE_NAME}: no baseline results to compare the mutants against",)


def test_each_mutant_changes_only_its_own_field(results: tuple[ItemResult, ...]) -> None:
    """Relative to the baseline, a mutant alters agents, later refs, gates or clarification only."""
    by_router: dict[str, dict[str, RoutePlan]] = {}
    for result in results:
        assert result.plan is not None, result.item_id
        by_router.setdefault(result.router, {})[result.item_id] = result.plan
    base = by_router[BASELINE_NAME]
    for item_id, mutant_plan in by_router[DropsContext.name].items():
        assert mutant_plan.agents == base[item_id].agents
    for item_id, mutant_plan in by_router[AlwaysIncident.name].items():
        assert [s.context_refs for s in mutant_plan.steps] == [
            s.context_refs for s in base[item_id].steps
        ]
    for item_id, mutant_plan in by_router[UngatedWrite.name].items():
        assert mutant_plan.agents == base[item_id].agents
    for item_id, mutant_plan in by_router[NeverClarify.name].items():
        assert not mutant_plan.requires_clarification
        if not base[item_id].requires_clarification:
            assert mutant_plan == base[item_id]
