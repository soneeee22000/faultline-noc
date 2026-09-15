"""Markdown rendering of the accuracy tables, the detection matrix and the harness check."""

from collections.abc import Iterable, Sequence

from faultline_noc.detectors import DetectorName
from faultline_noc.runner import RunResult
from faultline_noc.scoring import (
    AccuracyRow,
    MatrixCell,
    accuracy_by,
    actions_correct,
    detection_matrix,
)

NOT_APPLICABLE = "n/a"


def render_report(
    results: Sequence[RunResult], seeds: Sequence[int], failures: Sequence[str]
) -> str:
    """Return the full markdown report for a set of runs."""
    agents = _unique(result.agent for result in results)
    scenario_ids = _unique(result.scenario_id for result in results)
    sections = (
        _header(len(results), agents, scenario_ids, seeds),
        "## Top-1 accuracy, all scenarios",
        _accuracy_table(accuracy_by(results, per_scenario=False), "Top-1"),
        "## Top-1 accuracy per scenario (correct / N)",
        _per_scenario_table(accuracy_by(results, per_scenario=True), agents, scenario_ids),
        "## Action correctness (every executed or proposed write targets the true root cause)",
        _accuracy_table(
            accuracy_by(results, per_scenario=False, outcome=actions_correct), "Writes OK"
        ),
        "## Detection matrix (runs tripped / runs where the detector applies)",
        _matrix_table(detection_matrix(results), agents),
        "## Harness check",
        _harness_section(failures),
    )
    return "\n\n".join(sections)


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    """Return values in first-seen order without duplicates."""
    return tuple(dict.fromkeys(values))


def _header(
    run_count: int, agents: Sequence[str], scenario_ids: Sequence[str], seeds: Sequence[int]
) -> str:
    """Return the report title and run summary."""
    shape = f"{len(agents)} agents x {len(scenario_ids)} scenarios x {len(seeds)} seeds"
    return (
        "# Faultline NOC eval report\n\n"
        f"{run_count} runs = {shape} (seeds {seeds[0]}..{seeds[-1]}). "
        "Mock agents only; no LLM is called."
    )


def _table(header: Sequence[str], rows: Iterable[Sequence[str]]) -> str:
    """Return a markdown table."""
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _accuracy_table(rows: Sequence[AccuracyRow], metric: str) -> str:
    """Return an overall accuracy table with Wilson 95% intervals."""
    body = (
        (
            row.agent,
            f"{row.correct} / {row.total}",
            f"{row.accuracy:.3f}",
            f"[{row.interval.low:.3f}, {row.interval.high:.3f}]",
        )
        for row in rows
    )
    return _table(("Agent", "Correct / N", metric, "Wilson 95% CI"), body)


def _per_scenario_table(
    rows: Sequence[AccuracyRow], agents: Sequence[str], scenario_ids: Sequence[str]
) -> str:
    """Return an agent-by-scenario table of correct over N."""
    lookup = {(row.agent, row.scope): row for row in rows}
    body = (
        (
            agent,
            *(f"{lookup[agent, sid].correct}/{lookup[agent, sid].total}" for sid in scenario_ids),
        )
        for agent in agents
    )
    return _table(("Agent", *scenario_ids), body)


def _matrix_table(cells: Sequence[MatrixCell], agents: Sequence[str]) -> str:
    """Return the agent-by-detector matrix."""
    lookup = {(cell.agent, cell.detector): cell for cell in cells}
    detectors: tuple[DetectorName, ...] = tuple(dict.fromkeys(cell.detector for cell in cells))
    body = ((agent, *(_cell_text(lookup[agent, name]) for name in detectors)) for agent in agents)
    return _table(("Agent", *detectors), body)


def _cell_text(cell: MatrixCell) -> str:
    """Return tripped over applicable, or n/a when the detector never applied."""
    if cell.applicable == 0:
        return NOT_APPLICABLE
    return f"{cell.tripped}/{cell.applicable}"


def _harness_section(failures: Sequence[str]) -> str:
    """Return PASS, or FAIL with every discrimination failure listed."""
    if not failures:
        return (
            "PASS: every mutant tripped its own detector on every applicable run, "
            "no mutant tripped a detector outside its declared side effects, "
            "and the oracle and rule baseline tripped none."
        )
    return "FAIL:\n" + "\n".join(f"- {failure}" for failure in failures)
