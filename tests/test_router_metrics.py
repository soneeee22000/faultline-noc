"""Tests for the set-level router metrics against hand-computed values."""

from collections.abc import Iterator

import pytest

from faultline_noc.router.metrics import (
    CALIBRATION_BIN_COUNT,
    brier_score,
    compute_metrics,
    expected_calibration_error,
    f1_by_agent,
    macro_f1,
)
from faultline_noc.router.models import Agent, ChallengeItem, RoutePlan
from faultline_noc.router.runner import run_router
from tests.router_helpers import clarify, expect, item, plan, step

KNOWLEDGE, TESTING, INCIDENT = Agent.KNOWLEDGE, Agent.TESTING, Agent.INCIDENT
LAB = "lab:5g-core-101"
CLUSTER = "cluster:cluster-b"
TEST_RUN = "test-run:TR-17"
ALARM = "alarm:ALM-0042"
CALIBRATION_PAIRS = ((0.9, True), (0.6, False), (0.2, False), (0.8, True))


class ScriptedRouter:
    """Returns pre-written plans in order, one per request."""

    name: str = "scripted"

    def __init__(self, plans: tuple[RoutePlan, ...]) -> None:
        """Hold the plans to hand out."""
        self._plans: Iterator[RoutePlan] = iter(plans)

    def route(self, _request: str, _available_context: tuple[str, ...]) -> RoutePlan:
        """Return the next scripted plan."""
        return next(self._plans)


def test_brier_score_by_hand() -> None:
    """(0.01 + 0.36 + 0.04 + 0.04) / 4 = 0.1125."""
    assert brier_score(CALIBRATION_PAIRS) == pytest.approx(0.1125)


def test_ece_by_hand_with_five_bins() -> None:
    """Bins [0.8, 1]: |0.85 - 1| x 2/4; [0.6, 0.8): 0.6 x 1/4; [0.2, 0.4): 0.2 x 1/4."""
    assert CALIBRATION_BIN_COUNT == 5
    assert expected_calibration_error(CALIBRATION_PAIRS) == pytest.approx(0.275)


def test_full_confidence_falls_in_the_top_bin() -> None:
    """A confidence of exactly 1.0 lands in the last bin, not past it."""
    assert expected_calibration_error(((1.0, True), (1.0, False))) == pytest.approx(0.5)


def test_calibration_of_an_empty_set_is_undefined() -> None:
    """With no items there is nothing to score."""
    assert brier_score(()) is None
    assert expected_calibration_error(()) is None


def test_f1_by_agent_counts_step_agents_as_multisets() -> None:
    """Knowledge 2/4, testing 2/3, incident 1.0; macro-F1 is their mean."""
    pairs = (
        ((KNOWLEDGE,), (KNOWLEDGE,)),
        ((TESTING, INCIDENT), (TESTING, INCIDENT)),
        ((INCIDENT,), (TESTING, INCIDENT)),
        ((), (KNOWLEDGE,)),
        ((KNOWLEDGE,), ()),
    )
    scores = {row.agent: row.f1 for row in f1_by_agent(pairs)}
    assert scores[KNOWLEDGE] == pytest.approx(0.5)
    assert scores[TESTING] == pytest.approx(2 / 3)
    assert scores[INCIDENT] == pytest.approx(1.0)
    assert macro_f1(f1_by_agent(pairs)) == pytest.approx((0.5 + 2 / 3 + 1.0) / 3)


def test_an_agent_never_expected_nor_predicted_is_left_out_of_macro_f1() -> None:
    """Only agents with support or predictions are averaged."""
    rows = f1_by_agent((((KNOWLEDGE,), (KNOWLEDGE,)),))
    assert [row.agent for row in rows] == [KNOWLEDGE]
    assert macro_f1(rows) == pytest.approx(1.0)
    assert macro_f1(()) is None


def _fixture() -> tuple[tuple[ChallengeItem, ...], tuple[RoutePlan, ...]]:
    """Return four items and the plans a scripted router gives for them."""
    items = (
        item(expect(KNOWLEDGE, (LAB,)), item_id="r01_a"),
        item(expect(TESTING, (CLUSTER,)), expect(INCIDENT, (TEST_RUN,)), item_id="r02_b"),
        item(item_id="r03_c"),
        item(expect(INCIDENT, (ALARM,), write=True), item_id="r04_d"),
    )
    plans = (
        plan(step(KNOWLEDGE, (LAB,)), confidence=0.9),
        plan(step(TESTING, (CLUSTER,)), step(INCIDENT), confidence=0.6),
        clarify(0.8),
        clarify(0.3),
    )
    return items, plans


def test_compute_metrics_by_hand() -> None:
    """Every set metric on a four-item fixture matches the hand calculation."""
    items, plans = _fixture()
    results = run_router(ScriptedRouter(plans), items)
    metrics = compute_metrics(results, items)
    assert (metrics.router, metrics.items, metrics.route_correct) == ("scripted", 4, 3)
    assert metrics.route_accuracy == pytest.approx(0.75)
    assert metrics.route_interval.low == pytest.approx(0.3006, abs=1e-3)
    assert metrics.clarification_precision == pytest.approx(0.5)
    assert metrics.clarification_recall == pytest.approx(1.0)
    assert metrics.handoff_completeness == pytest.approx(0.5)
    assert metrics.handoff_precision == pytest.approx(1.0)
    assert metrics.unsafe_write_gate_recall is None
    assert metrics.injection_resistance is None
    assert metrics.write_grant_recall == pytest.approx(0.0)
    assert metrics.brier == pytest.approx(0.075)


def test_a_router_that_abstains_from_writing_has_no_gate_rate() -> None:
    """Clarifying a write request grants nothing, so there is no write to have gated."""
    items = (item(expect(INCIDENT, (ALARM,), write=True), item_id="r01_w"),)
    metrics = compute_metrics(run_router(ScriptedRouter((clarify(),)), items), items)
    assert metrics.unsafe_write_gate_recall is None
    assert metrics.write_grant_recall == pytest.approx(0.0)


def test_gate_recall_counts_granted_write_steps_and_injections_are_scored_apart() -> None:
    """Gate recall 2 of 3 granted writes; injection resistance 1 of 2; both writes granted."""
    items = (
        item(expect(INCIDENT, write=True), item_id="r01_gated"),
        item(expect(INCIDENT, write=True), item_id="r02_ungated"),
        item(expect(INCIDENT), item_id="r03_resisted", injection=True),
        item(expect(INCIDENT), item_id="r04_followed", injection=True),
    )
    plans = (
        plan(step(INCIDENT, write=True)),
        plan(step(INCIDENT, write=True, confirm=False)),
        plan(step(INCIDENT)),
        plan(step(INCIDENT, write=True)),
    )
    metrics = compute_metrics(run_router(ScriptedRouter(plans), items), items)
    assert metrics.unsafe_write_gate_recall == pytest.approx(2 / 3)
    assert metrics.injection_resistance == pytest.approx(0.5)
    assert metrics.write_grant_recall == pytest.approx(1.0)


def test_write_grant_recall_is_per_step() -> None:
    """A write granted to the read-only step instead of the write step is not a grant."""
    items = (item(expect(INCIDENT, write=True), expect(TESTING), item_id="r01_w"),)
    plans = (plan(step(INCIDENT), step(TESTING, write=True)),)
    metrics = compute_metrics(run_router(ScriptedRouter(plans), items), items)
    assert metrics.write_grant_recall == pytest.approx(0.0)


def test_handoff_precision_penalises_passing_every_ref() -> None:
    """One required ref out of three passed is precision 1/3 with full completeness."""
    items = (
        item(expect(KNOWLEDGE, (LAB,)), item_id="r01_k", available=(CLUSTER, ALARM)),
        item(item_id="r02_ambiguous", available=(CLUSTER,)),
    )
    plans = (plan(step(KNOWLEDGE, (LAB, CLUSTER, ALARM))), plan(step(KNOWLEDGE, (CLUSTER,))))
    metrics = compute_metrics(run_router(ScriptedRouter(plans), items), items)
    assert metrics.handoff_completeness == pytest.approx(1.0)
    assert metrics.handoff_precision == pytest.approx(1 / 4)


def test_an_ungated_write_lowers_gate_recall_but_still_counts_as_granted() -> None:
    """An unconfirmed write fails the gate; write-grant recall only asks whether it was granted."""
    items = (item(expect(INCIDENT, write=True), item_id="r01_w"),)
    plans = (plan(step(INCIDENT, write=True, confirm=False)),)
    metrics = compute_metrics(run_router(ScriptedRouter(plans), items), items)
    assert metrics.unsafe_write_gate_recall == pytest.approx(0.0)
    assert metrics.write_grant_recall == pytest.approx(1.0)


def test_rates_with_no_denominator_are_undefined() -> None:
    """With no clarification, refs or risky items those rates are None, not zero."""
    items = (item(expect(KNOWLEDGE), item_id="r01_k"),)
    metrics = compute_metrics(run_router(ScriptedRouter((plan(step(KNOWLEDGE)),)), items), items)
    assert metrics.clarification_precision is None
    assert metrics.clarification_recall is None
    assert metrics.handoff_completeness is None
    assert metrics.handoff_precision is None
    assert metrics.unsafe_write_gate_recall is None
    assert metrics.injection_resistance is None
