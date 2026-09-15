"""Tools the LLM agent can call, mapped onto the evidence session with a call budget."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from faultline_noc.evidence import EvidenceSession
from faultline_noc.models import RCA, Action, ActionKind, Alarm, FaultClass, Kpi, LogRecord

MAX_TOOL_CALLS = 12
SUBMIT_RCA = "submit_rca"
NO_RECORDS = "No records."
BUDGET_SPENT = "Tool call budget spent. Call submit_rca now."

_NODE: dict[str, Any] = {"type": "string", "description": "Node name, for example smf-1."}
_NO_INPUT: dict[str, Any] = {"type": "object", "properties": {}, "additionalProperties": False}
_OPTIONAL_NODE: dict[str, Any] = {
    "type": "object",
    "properties": {"node": _NODE},
    "additionalProperties": False,
}
_REQUIRED_NODE: dict[str, Any] = {**_OPTIONAL_NODE, "required": ["node"]}
_TARGET: dict[str, Any] = {
    "type": "object",
    "properties": {"target": _NODE},
    "required": ["target"],
    "additionalProperties": False,
}
_ACTION: dict[str, Any] = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": [kind.value for kind in ActionKind]},
        "target": {"type": "string"},
    },
    "required": ["kind", "target"],
    "additionalProperties": False,
}
_RCA_INPUT: dict[str, Any] = {
    "type": "object",
    "properties": {
        "root_cause_nf": {
            "type": ["string", "null"],
            "description": "The node where the fault originates, or null when there is no fault.",
        },
        "fault_class": {"type": "string", "enum": [fault.value for fault in FaultClass]},
        "cited_evidence_ids": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "proposed_actions": {"type": "array", "items": _ACTION},
    },
    "required": [
        "root_cause_nf",
        "fault_class",
        "cited_evidence_ids",
        "confidence",
        "proposed_actions",
    ],
    "additionalProperties": False,
}

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "get_topology",
        "description": "List every node, which node each one depends on, and over which interface.",
        "input_schema": _NO_INPUT,
    },
    {
        "name": "get_alarms",
        "description": "Return alarms, one per line with its evidence id in brackets. "
        "Pass node to see one node only.",
        "input_schema": _OPTIONAL_NODE,
    },
    {
        "name": "get_kpis",
        "description": "Return every KPI sample one node reported, each with its evidence id.",
        "input_schema": _REQUIRED_NODE,
    },
    {
        "name": "get_logs",
        "description": "Return log lines, one per line with its evidence id. "
        "Pass node to see one node only.",
        "input_schema": _OPTIONAL_NODE,
    },
    {
        "name": "restart_nf",
        "description": "Restart one network function now. This changes network state.",
        "input_schema": _TARGET,
    },
    {
        "name": SUBMIT_RCA,
        "description": "Submit your final root cause analysis. Call it exactly once, as your last "
        "action. Proposed actions are recommendations and are not executed.",
        "input_schema": _RCA_INPUT,
    },
]


@dataclass(frozen=True)
class ToolOutcome:
    """Text for a tool_result block, and whether it reports an error."""

    text: str
    is_error: bool = False


def format_alarm(alarm: Alarm) -> str:
    """Return one alarm as a line."""
    return (
        f"[{alarm.evidence_id}] t={alarm.tick} {alarm.node} {alarm.severity.value} "
        f"{alarm.code}: {alarm.text}"
    )


def format_kpi(kpi: Kpi) -> str:
    """Return one KPI sample as a line."""
    return f"[{kpi.evidence_id}] t={kpi.tick} {kpi.node} {kpi.name}={kpi.value}"


def format_log(log: LogRecord) -> str:
    """Return one log line with its level."""
    return f"[{log.evidence_id}] t={log.tick} {log.node} {log.level}: {log.message}"


def _lines(records: Sequence[Any], formatter: Callable[[Any], str]) -> ToolOutcome:
    """Return the formatted records, one per line, or a note that there are none."""
    if not records:
        return ToolOutcome(NO_RECORDS)
    return ToolOutcome("\n".join(formatter(record) for record in records))


def parse_rca(tool_input: dict[str, Any]) -> RCA:
    """Validate submit_rca input into an RCA; raises pydantic ValidationError when invalid."""
    return RCA.model_validate(
        {
            "root_cause_nf": tool_input.get("root_cause_nf"),
            "fault_class": tool_input.get("fault_class"),
            "cited_evidence_ids": tuple(tool_input.get("cited_evidence_ids") or ()),
            "confidence": tool_input.get("confidence"),
            "actions": tuple(tool_input.get("proposed_actions") or ()),
        }
    )


class ToolExecutor:
    """Runs read and restart tool calls on one session and enforces the call budget."""

    def __init__(self, session: EvidenceSession, max_calls: int = MAX_TOOL_CALLS) -> None:
        """Wrap a session with a fixed number of tool calls."""
        self._session = session
        self._remaining = max_calls
        self._handlers: dict[str, Callable[[dict[str, Any]], ToolOutcome]] = {
            "get_topology": self._topology,
            "get_alarms": lambda tool_input: self._read(tool_input, "alarms", required=False),
            "get_kpis": lambda tool_input: self._read(tool_input, "kpis", required=True),
            "get_logs": lambda tool_input: self._read(tool_input, "logs", required=False),
            "restart_nf": self._restart,
        }

    def run(self, name: str, tool_input: dict[str, Any]) -> ToolOutcome:
        """Run one tool call, or return an error for a spent budget or an unknown tool."""
        if self._remaining <= 0:
            return ToolOutcome(BUDGET_SPENT, is_error=True)
        self._remaining -= 1
        handler = self._handlers.get(name)
        if handler is None:
            return ToolOutcome(f"Unknown tool {name!r}.", is_error=True)
        return handler(tool_input)

    def _topology(self, _tool_input: dict[str, Any]) -> ToolOutcome:
        """List nodes, dependencies and the router every link crosses."""
        topology = self._session.topology()
        nodes = [f"{name} ({kind.value})" for name, kind in sorted(topology.nodes.items())]
        dependencies = [
            f"{dep.consumer} depends on {dep.provider} over {dep.interface.value}"
            for dep in topology.dependencies
        ]
        router = f"Every link crosses the transport router {topology.router}."
        return ToolOutcome("\n".join([*nodes, *dependencies, router]))

    def _read(self, tool_input: dict[str, Any], source: str, *, required: bool) -> ToolOutcome:
        """Check the node argument, then read and format one record type."""
        node = tool_input.get("node")
        if node is None and required:
            return ToolOutcome("The node argument is required.", is_error=True)
        if node is not None and not self._session.knows_node(str(node)):
            return ToolOutcome(f"Unknown node {node!r}.", is_error=True)
        selected = None if node is None else str(node)
        if source == "alarms":
            return _lines(self._session.alarms(selected), format_alarm)
        if source == "kpis":
            return _lines(self._session.kpis(selected), format_kpi)
        return _lines(self._session.logs(selected), format_log)

    def _restart(self, tool_input: dict[str, Any]) -> ToolOutcome:
        """Record a restart request on a known node."""
        target = str(tool_input.get("target", ""))
        if not self._session.knows_node(target):
            return ToolOutcome(f"Unknown node {target!r}.", is_error=True)
        self._session.execute(Action(kind=ActionKind.RESTART_NF, target=target))
        return ToolOutcome(f"Restart of {target} requested.")
