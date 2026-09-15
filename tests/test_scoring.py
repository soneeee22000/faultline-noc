"""Tests for Wilson intervals, the detection matrix and the harness discrimination check."""

from dataclasses import replace

import pytest

from faultline_noc.agents import (
    DEFAULT_AGENTS,
    BlamesSymptom,
    OracleAgent,
    TruthAwareAgent,
)
from faultline_noc.detectors import DETECTORS, DetectorName, RunEvidence
from faultline_noc.models import GroundTruth
from faultline_noc.runner import run_matrix
from faultline_noc.scenario import Scenario
from faultline_noc.scoring import (
    MUTANT_TARGETS,
    accuracy_by,
    actions_correct,
    detection_matrix,
    harness_failures,
    wilson_interval,
)
from faultline_noc.topology import Topology

SEEDS = (0, 1, 2)


def _never(_run: RunEvidence, _truth: GroundTruth) -> bool:
    """Stand-in detector check that never trips."""
    return False


def test_wilson_interval_with_no_trials_is_uninformative() -> None:
    """With zero trials the interval spans the whole range."""
    interval = wilson_interval(0, 0)
    assert (interval.low, interval.high) == (0.0, 1.0)


@pytest.mark.parametrize(
    ("successes", "trials", "low", "high"),
    [(5, 10, 0.2366, 0.7634), (10, 10, 0.7225, 1.0), (0, 10, 0.0, 0.2775)],
)
def test_wilson_interval_known_values(successes: int, trials: int, low: float, high: float) -> None:
    """Wilson 95% bounds match hand-computed values."""
    interval = wilson_interval(successes, trials)
    assert interval.low == pytest.approx(low, abs=1e-3)
    assert interval.high == pytest.approx(high, abs=1e-3)


def test_harness_passes_on_the_real_agents(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """Each mutant trips its own detector and the clean agents trip none."""
    results = run_matrix(tuple(scenarios.values()), topology, SEEDS)
    assert harness_failures(results) == ()


def test_every_detector_is_the_target_of_some_mutant() -> None:
    """No detector is left without a mutant that exercises it in the matrix."""
    targeted = {target.detector for target in MUTANT_TARGETS.values()}
    assert targeted == {detector.name for detector in DETECTORS}


@pytest.mark.parametrize("disabled", [detector.name for detector in DETECTORS])
def test_harness_fails_when_a_detector_is_disabled(
    disabled: DetectorName, scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """Switching off any detector makes the harness check fail, naming that detector."""
    detectors = tuple(
        replace(detector, check=_never) if detector.name == disabled else detector
        for detector in DETECTORS
    )
    results = run_matrix(tuple(scenarios.values()), topology, (0,), detectors=detectors)
    failures = harness_failures(results)
    assert failures
    assert all(str(disabled) in failure for failure in failures)


def test_harness_flags_a_mutant_that_was_never_exercised(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """Running the symptom mutant only on the no-fault scenario is reported as unexercised."""
    results = run_matrix(
        (scenarios["s06_no_fault"],), topology, (0,), agents=(TruthAwareAgent(BlamesSymptom),)
    )
    failures = harness_failures(results)
    assert len(failures) == 1
    assert "never applicable" in failures[0]


def test_harness_flags_a_side_effect_that_is_not_declared(
    scenarios: dict[str, Scenario], topology: Topology, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An undeclared co-trip fails the check even when the mutant's own detector trips."""
    results = run_matrix(
        (scenarios["s07_log_injection"],), topology, (0,), agents=(TruthAwareAgent(BlamesSymptom),)
    )
    target = MUTANT_TARGETS[BlamesSymptom.name]
    monkeypatch.setitem(
        MUTANT_TARGETS, BlamesSymptom.name, replace(target, may_also_trip=frozenset())
    )
    failures = harness_failures(results)
    assert failures
    assert all(str(DetectorName.CITATION_UNSUPPORTED) in failure for failure in failures)


def test_accuracy_rows_count_oracle_runs(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """The oracle's overall row is all correct with N equal to scenarios times seeds."""
    results = run_matrix(
        tuple(scenarios.values()), topology, SEEDS, agents=(TruthAwareAgent(OracleAgent),)
    )
    (row,) = accuracy_by(results, per_scenario=False)
    assert row.total == len(scenarios) * len(SEEDS)
    assert row.correct == row.total
    assert row.accuracy == 1.0
    per_scenario = accuracy_by(results, per_scenario=True)
    assert [item.scope for item in per_scenario] == sorted(scenarios)


def test_action_accuracy_separates_writes_on_the_wrong_node(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """The bystander mutant is top-1 correct yet never action-correct; the oracle is both."""
    results = run_matrix(tuple(scenarios.values()), topology, (0,))
    top1 = {row.agent: row.correct for row in accuracy_by(results, per_scenario=False)}
    actions = {
        row.agent: row.correct
        for row in accuracy_by(results, per_scenario=False, outcome=actions_correct)
    }
    assert top1["mutant_restarts_bystander"] == len(scenarios)
    assert actions["mutant_restarts_bystander"] == 0
    assert actions[OracleAgent.name] == len(scenarios)


def test_detection_matrix_covers_every_agent_and_detector(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """The matrix has one cell per agent and detector, and the oracle's cells are all zero."""
    results = run_matrix(tuple(scenarios.values()), topology, (0,))
    cells = detection_matrix(results)
    assert len(cells) == len(DEFAULT_AGENTS) * len(DETECTORS)
    oracle_cells = [cell for cell in cells if cell.agent == OracleAgent.name]
    assert all(cell.tripped == 0 for cell in oracle_cells)
