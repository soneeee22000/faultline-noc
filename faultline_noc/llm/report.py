"""Markdown summary of an LLM evaluation: accuracy, safe writes, key detectors and spend."""

from collections.abc import Sequence

from faultline_noc.llm.evaluate import LlmEvalPayload
from faultline_noc.scoring import AccuracyRow

NOT_APPLICABLE = "n/a"
KEY_DETECTORS: tuple[str, ...] = (
    "symptom_blamed",
    "injected_action_taken",
    "write_on_non_root",
    "unknown_evidence_id",
    "citation_unsupported",
)


def render_markdown(payload: LlmEvalPayload) -> str:
    """Return the evaluation report as markdown."""
    summary = (
        f"{payload.runs} runs: {len(payload.scenarios)} scenarios x {len(payload.seeds)} seeds, "
        f"the rule baseline plus {len(payload.models)} model(s)."
    )
    sections = (
        "# LLM evaluation",
        summary,
        "## Top-1 accuracy per scenario (correct / N)",
        _per_scenario(payload),
        "## Overall",
        _overall(payload),
        "## Key detectors (runs tripped / runs where the detector applies)",
        _detectors(payload),
        "## Spend, from recorded usage",
        _spend(payload),
    )
    return "\n\n".join(sections)


def _table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    """Return a markdown table."""
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _agents(rows: Sequence[AccuracyRow]) -> list[str]:
    """Return agent names in first-seen order."""
    return list(dict.fromkeys(row.agent for row in rows))


def _per_scenario(payload: LlmEvalPayload) -> str:
    """Return correct / N per agent and scenario."""
    cells = {
        (row.agent, row.scope): f"{row.correct}/{row.total}"
        for row in payload.accuracy_per_scenario
    }
    rows = [
        [agent, *(cells.get((agent, scenario), NOT_APPLICABLE) for scenario in payload.scenarios)]
        for agent in _agents(payload.accuracy_per_scenario)
    ]
    return _table(["Agent", *payload.scenarios], rows)


def _overall(payload: LlmEvalPayload) -> str:
    """Return overall top-1 accuracy with Wilson intervals, and write correctness."""
    writes = {row.agent: row for row in payload.action_correctness}
    rows = [
        [
            row.agent,
            f"{row.correct}/{row.total}",
            f"[{row.interval.low:.2f}, {row.interval.high:.2f}]",
            f"{writes[row.agent].correct}/{writes[row.agent].total}",
        ]
        for row in payload.accuracy_overall
    ]
    return _table(["Agent", "Top-1", "Wilson 95% CI", "Writes only on the true root"], rows)


def _detectors(payload: LlmEvalPayload) -> str:
    """Return tripped / applicable counts for the detectors that matter most for LLMs."""
    cells = {
        (cell.agent, cell.detector.value): f"{cell.tripped}/{cell.applicable}"
        for cell in payload.detection_matrix
    }
    rows = [
        [agent, *(cells.get((agent, detector), NOT_APPLICABLE) for detector in KEY_DETECTORS)]
        for agent in _agents(payload.accuracy_overall)
    ]
    return _table(["Agent", *KEY_DETECTORS], rows)


def _spend(payload: LlmEvalPayload) -> str:
    """Return spend and token counts per model."""
    if not payload.models:
        return "No model runs."
    rows = [
        [
            model,
            f"${payload.spend_usd.get(model, 0.0):.4f}",
            str(payload.tokens.get(model, {}).get("input", 0)),
            str(payload.tokens.get(model, {}).get("output", 0)),
        ]
        for model in payload.models
    ]
    return _table(["Model", "USD", "Input tokens", "Output tokens"], rows)
