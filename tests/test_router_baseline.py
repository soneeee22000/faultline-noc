"""Tests for the keyword baseline router: gating, injection handling and documented misses."""

import pytest

from faultline_noc.router import baseline as baseline_module
from faultline_noc.router.baseline import NO_TARGET_QUESTION, KeywordBaseline
from faultline_noc.router.challenge import load_challenge
from faultline_noc.router.models import Agent, ChallengeItem, RoutePlan, Tag
from faultline_noc.router.runner import ItemResult, run_router


@pytest.fixture(scope="module")
def challenge() -> tuple[ChallengeItem, ...]:
    """Return the committed challenge set."""
    return load_challenge()


@pytest.fixture(scope="module")
def results(challenge: tuple[ChallengeItem, ...]) -> dict[str, ItemResult]:
    """Return the baseline's results keyed by item id."""
    return {result.item_id: result for result in run_router(KeywordBaseline(), challenge)}


def _plan(result: ItemResult) -> RoutePlan:
    """Return a baseline result's plan; the baseline always answers with a valid plan."""
    assert result.plan is not None, result.item_id
    return result.plan


def test_every_write_the_baseline_grants_needs_confirmation(
    results: dict[str, ItemResult],
) -> None:
    """No baseline step grants network_write without requires_confirmation."""
    steps = [step for result in results.values() for step in _plan(result).steps]
    assert any(step.grants_write for step in steps)
    assert all(step.requires_confirmation for step in steps if step.grants_write)


def test_no_injection_item_gets_a_write(
    challenge: tuple[ChallengeItem, ...], results: dict[str, ItemResult]
) -> None:
    """Instructions in quotes, pasted logs, reported speech or override phrases grant nothing."""
    injected = [item.id for item in challenge if Tag.INJECTION in item.tags]
    assert injected
    for item_id in injected:
        assert not any(step.grants_write for step in _plan(results[item_id]).steps), item_id


def test_the_injection_filters_are_what_keeps_those_items_safe(
    challenge: tuple[ChallengeItem, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    """With quote stripping and override detection switched off, every injection item writes."""
    monkeypatch.setattr("faultline_noc.router.lexicon.strip_quoted_material", lambda text: text)
    monkeypatch.setattr("faultline_noc.router.lexicon.is_injected", lambda _sentence: False)
    injected = [item for item in challenge if Tag.INJECTION in item.tags]
    for result in run_router(KeywordBaseline(), injected):
        assert any(step.grants_write for step in _plan(result).steps), result.item_id


def test_the_baseline_misses_exactly_the_documented_items(
    challenge: tuple[ChallengeItem, ...], results: dict[str, ItemResult]
) -> None:
    """Every route the baseline gets wrong carries a baseline_miss note, and no other item does."""
    documented = {item.id for item in challenge if item.baseline_miss}
    missed = {item_id for item_id, result in results.items() if not result.correct}
    assert missed == documented


def test_ordered_multi_intent_hands_the_test_run_on() -> None:
    """Testing then incident, with the test-run ref on the incident step."""
    plan = KeywordBaseline().route(
        "Run the attach test on cluster B, then tell me why latency spiked.",
        ("cluster:cluster-b", "test-run:TR-17"),
    )
    assert plan.agents == (Agent.TESTING, Agent.INCIDENT)
    assert "test-run:TR-17" in plan.steps[1].context_refs


def test_a_write_without_a_target_asks_which_one() -> None:
    """A bare write imperative is a clarification, not a guess."""
    plan = KeywordBaseline().route("Restart it.", ("nf:amf-1", "nf:smf-1"))
    assert plan.requires_clarification
    assert plan.clarification_question == NO_TARGET_QUESTION


def test_a_question_about_a_write_verb_is_not_a_write() -> None:
    """Asking why something scaled grants no write."""
    plan = KeywordBaseline().route("Why did upf-1 scale out last night?", ("nf:upf-1",))
    assert not any(step.grants_write for step in plan.steps)


def test_routing_is_deterministic(challenge: tuple[ChallengeItem, ...]) -> None:
    """Routing the set twice gives identical plans."""
    assert run_router(KeywordBaseline(), challenge) == run_router(KeywordBaseline(), challenge)


def test_refs_follow_the_agent_affinity() -> None:
    """A knowledge step gets lab and doc refs, not alarms."""
    refs = baseline_module.refs_for(Agent.KNOWLEDGE, ("lab:x", "alarm:ALM-1", "doc:y"))
    assert refs == ("lab:x", "doc:y")
