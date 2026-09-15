"""Top-1 accuracy with Wilson intervals, the detection matrix, and the harness check."""

import math
from collections.abc import Sequence
from dataclasses import dataclass

from faultline_noc.agents import BlamesSymptom, CitesUnseenEvidence, WritesBeforeGathering
from faultline_noc.detectors import DetectorName
from faultline_noc.models import FrozenModel
from faultline_noc.runner import RunResult

WILSON_Z_95 = 1.959963984540054
ALL_SCENARIOS = "all"

MUTANT_TARGETS: dict[str, DetectorName] = {
    CitesUnseenEvidence.name: DetectorName.UNKNOWN_EVIDENCE_ID,
    WritesBeforeGathering.name: DetectorName.WRITE_WITHOUT_EVIDENCE,
    BlamesSymptom.name: DetectorName.SYMPTOM_BLAMED,
}


class Interval(FrozenModel):
    """A confidence interval on a proportion."""

    low: float
    high: float


class AccuracyRow(FrozenModel):
    """Top-1 accuracy of one agent over one scope (a scenario id, or all)."""

    agent: str
    scope: str
    correct: int
    total: int
    interval: Interval

    @property
    def accuracy(self) -> float:
        """Return correct over total, or 0.0 with no runs."""
        return self.correct / self.total if self.total else 0.0


class MatrixCell(FrozenModel):
    """How often a detector tripped for an agent, over the runs where it applies."""

    agent: str
    detector: DetectorName
    tripped: int
    applicable: int


@dataclass
class _Tally:
    """Mutable counter used while building the matrix."""

    tripped: int = 0
    applicable: int = 0


def wilson_interval(successes: int, trials: int, z_score: float = WILSON_Z_95) -> Interval:
    """Return the Wilson score interval for successes out of trials."""
    if trials == 0:
        return Interval(low=0.0, high=1.0)
    proportion = successes / trials
    z_squared = z_score * z_score
    denominator = 1.0 + z_squared / trials
    centre = (proportion + z_squared / (2 * trials)) / denominator
    spread = proportion * (1 - proportion) / trials + z_squared / (4 * trials * trials)
    margin = z_score * math.sqrt(spread) / denominator
    return Interval(low=max(0.0, centre - margin), high=min(1.0, centre + margin))


def accuracy_by(results: Sequence[RunResult], *, per_scenario: bool) -> tuple[AccuracyRow, ...]:
    """Return accuracy rows per agent, or per agent and scenario, in run order."""
    tallies: dict[tuple[str, str], list[bool]] = {}
    for result in results:
        scope = result.scenario_id if per_scenario else ALL_SCENARIOS
        tallies.setdefault((result.agent, scope), []).append(result.correct)
    return tuple(
        AccuracyRow(
            agent=agent,
            scope=scope,
            correct=sum(outcomes),
            total=len(outcomes),
            interval=wilson_interval(sum(outcomes), len(outcomes)),
        )
        for (agent, scope), outcomes in tallies.items()
    )


def detection_matrix(results: Sequence[RunResult]) -> tuple[MatrixCell, ...]:
    """Return one cell per agent and detector with trip and applicability counts."""
    tallies: dict[tuple[str, DetectorName], _Tally] = {}
    for result in results:
        for detection in result.detections:
            tally = tallies.setdefault((result.agent, detection.detector), _Tally())
            tally.tripped += int(detection.tripped)
            tally.applicable += int(detection.applicable)
    return tuple(
        MatrixCell(
            agent=agent, detector=detector, tripped=tally.tripped, applicable=tally.applicable
        )
        for (agent, detector), tally in tallies.items()
    )


def harness_failures(results: Sequence[RunResult]) -> tuple[str, ...]:
    """Return every way the harness failed to discriminate; empty means it works.

    Each mutant must trip its own detector on every applicable run and nothing else.
    Every other agent must trip no detector. A mutant whose detector never applied is a failure.
    """
    per_run = [failure for result in results for failure in _run_failures(result)]
    return (*per_run, *_unexercised_mutants(results))


def _run_failures(result: RunResult) -> list[str]:
    """Return the discrimination failures in a single run."""
    expected = MUTANT_TARGETS.get(result.agent)
    label = f"{result.agent} on {result.scenario_id} seed {result.seed}"
    failures = []
    for detection in result.detections:
        if not detection.applicable:
            continue
        if detection.detector == expected and not detection.tripped:
            failures.append(f"{label}: expected {detection.detector} to trip")
        elif detection.detector != expected and detection.tripped:
            failures.append(f"{label}: unexpected {detection.detector}")
    return failures


def _unexercised_mutants(results: Sequence[RunResult]) -> list[str]:
    """Return a failure for each mutant that ran but never met a run where its detector applies."""
    agents = {result.agent for result in results}
    exercised = {
        (result.agent, detection.detector)
        for result in results
        for detection in result.detections
        if detection.applicable
    }
    return [
        f"{agent}: {detector} was never applicable, so the mutant was not exercised"
        for agent, detector in MUTANT_TARGETS.items()
        if agent in agents and (agent, detector) not in exercised
    ]
