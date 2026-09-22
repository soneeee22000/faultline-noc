"""Markdown rendering of the router metrics, the detection matrix and the harness check."""

from collections.abc import Iterable, Sequence

from faultline_noc.router.detectors import DetectorName
from faultline_noc.router.metrics import (
    CALIBRATION_BIN_COUNT,
    MatrixCell,
    RouterMetrics,
    detection_matrix,
)
from faultline_noc.router.models import Agent, ChallengeItem, RoutePlan, RouteStep
from faultline_noc.router.runner import ItemResult

NOT_APPLICABLE = "n/a"
CLARIFY_LABEL = "clarify"
ROUTE_JOINER = " > "
GATED_WRITE_MARKER = "+write"
UNGATED_WRITE_MARKER = "+UNGATED"
METRIC_HEADER = (
    "Router",
    "Route acc",
    "95% CI",
    "Macro-F1",
    "Clarify P",
    "Clarify R",
    "Handoff R",
    "Handoff P",
    "Gate recall",
    "Inj resist",
    "Write grant",
    "Brier",
    "ECE",
)


def _table(header: Sequence[str], rows: Iterable[Sequence[str]]) -> str:
    """Return a markdown table."""
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _rate(value: float | None) -> str:
    """Return a rate to three decimals, or n/a when it has no denominator."""
    return NOT_APPLICABLE if value is None else f"{value:.3f}"


def _write_marker(step: RouteStep) -> str:
    """Return the suffix that marks a gated or an ungated write step."""
    if not step.grants_write:
        return ""
    return GATED_WRITE_MARKER if step.requires_confirmation else UNGATED_WRITE_MARKER


def route_label(plan: RoutePlan) -> str:
    """Return a plan as 'clarify' or its ordered agents, marking gated and ungated writes."""
    if plan.requires_clarification:
        return CLARIFY_LABEL
    return ROUTE_JOINER.join(f"{step.agent}{_write_marker(step)}" for step in plan.steps)


def expected_label(item: ChallengeItem) -> str:
    """Return the expected outcome in the same form as route_label."""
    if item.expected.requires_clarification:
        return CLARIFY_LABEL
    return ROUTE_JOINER.join(
        f"{step.agent}{GATED_WRITE_MARKER if step.network_write else ''}"
        for step in item.expected.steps
    )


def _metrics_row(metrics: RouterMetrics) -> tuple[str, ...]:
    """Return one router's row of the metrics table."""
    interval = metrics.route_interval
    return (
        metrics.router,
        f"{metrics.route_accuracy:.3f} ({metrics.route_correct}/{metrics.items})",
        f"[{interval.low:.3f}, {interval.high:.3f}]",
        _rate(metrics.macro_f1),
        _rate(metrics.clarification_precision),
        _rate(metrics.clarification_recall),
        _rate(metrics.handoff_completeness),
        _rate(metrics.handoff_precision),
        _rate(metrics.unsafe_write_gate_recall),
        _rate(metrics.injection_resistance),
        _rate(metrics.write_grant_recall),
        _rate(metrics.brier),
        _rate(metrics.ece),
    )


def _f1_table(metrics: Sequence[RouterMetrics]) -> str:
    """Return F1 per specialist for every router."""
    rows = []
    for entry in metrics:
        scores = {row.agent: row.f1 for row in entry.f1_by_agent}
        rows.append((entry.router, *(_rate(scores.get(agent)) for agent in Agent)))
    return _table(("Router", *(str(agent) for agent in Agent)), rows)


def _matrix_table(cells: Sequence[MatrixCell], routers: Sequence[str]) -> str:
    """Return the router x detector matrix as tripped / applicable."""
    lookup = {(cell.router, cell.detector): cell for cell in cells}
    rows = []
    for router in routers:
        row = [router]
        for detector in DetectorName:
            cell = lookup.get((router, detector))
            row.append(NOT_APPLICABLE if cell is None else f"{cell.tripped}/{cell.applicable}")
        rows.append(tuple(row))
    return _table(("Router", *(str(detector) for detector in DetectorName)), rows)


def _baseline_table(
    results: Sequence[ItemResult], items: Sequence[ChallengeItem], baseline: str
) -> str:
    """Return every item where the baseline trips a detector, with its plan and the expected one."""
    by_id = {item.id: item for item in items}
    rows = [
        (
            result.item_id,
            expected_label(by_id[result.item_id]),
            route_label(result.plan),
            ", ".join(result.tripped()),
        )
        for result in results
        if result.router == baseline and result.tripped()
    ]
    if not rows:
        return f"{baseline} trips no detector on this set."
    return _table(("Item", "Expected", baseline, "Tripped"), rows)


def _harness_section(failures: Sequence[str], baseline: str) -> str:
    """Return the harness-check verdict."""
    if not failures:
        return (
            "PASS: every mutant ran and tripped its own detector on an item where "
            f"{baseline} does not, no mutant tripped anything undeclared, {baseline} "
            "gated every write it granted (unsafe-write gate recall 1.000), and a followed "
            "injection tripped unsafe_write on every injection item."
        )
    return "FAIL:\n" + "\n".join(f"- {failure}" for failure in failures)


def render_report(
    results: Sequence[ItemResult],
    items: Sequence[ChallengeItem],
    metrics: Sequence[RouterMetrics],
    failures: Sequence[str],
    baseline: str,
) -> str:
    """Return the full markdown report for a router run."""
    routers = tuple(entry.router for entry in metrics)
    sections = (
        "# Faultline router eval report",
        f"{len(items)} challenge items x {len(routers)} routers = {len(results)} plans. "
        "Keyword rules and mutants only; no LLM is called. The challenge set is authored by "
        f"the project author, so the {baseline} numbers are not a quality claim.",
        "## Route metrics",
        _table(METRIC_HEADER, (_metrics_row(entry) for entry in metrics)),
        f"Calibration: Brier and ECE ({CALIBRATION_BIN_COUNT} equal-width bins) over "
        f"{len(items)} items; at this size ECE is a rough signal. Handoff R is completeness "
        "(required refs delivered), Handoff P is precision (delivered over refs passed on). "
        "Gate recall is over granted write steps, so a router that grants none shows n/a.",
        "## F1 by specialist (step agents, order ignored)",
        _f1_table(metrics),
        "## Detection matrix (items tripped / items where the detector applies)",
        _matrix_table(detection_matrix(results), routers),
        f"## Items where {baseline} trips a detector",
        _baseline_table(results, items, baseline),
        "## Harness check",
        _harness_section(failures, baseline),
    )
    return "\n\n".join(sections)
