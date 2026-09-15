"""Evidence session: the only surface an agent uses to read telemetry or request actions."""

from collections.abc import Sequence
from enum import StrEnum
from typing import TypeVar

from faultline_noc.models import Action, Alarm, FrozenModel, Kpi, LogRecord, Telemetry
from faultline_noc.topology import Topology


class EventKind(StrEnum):
    """Whether a trace event read something or requested an action."""

    READ = "read"
    ACTION = "action"


class EventSource(StrEnum):
    """What a trace event touched."""

    TOPOLOGY = "topology"
    ALARMS = "alarms"
    KPIS = "kpis"
    LOGS = "logs"
    ACTION = "action"


RecordT = TypeVar("RecordT", Alarm, Kpi, LogRecord)

EVIDENCE_SOURCES: frozenset[EventSource] = frozenset(
    {EventSource.ALARMS, EventSource.KPIS, EventSource.LOGS}
)


class TraceEvent(FrozenModel):
    """One call an agent made on its evidence session."""

    kind: EventKind
    source: EventSource
    evidence_ids: tuple[str, ...] = ()
    action: Action | None = None

    @property
    def gathers_evidence(self) -> bool:
        """Return True for reads of alarms, KPIs or logs; topology is not evidence."""
        return self.kind == EventKind.READ and self.source in EVIDENCE_SOURCES

    @property
    def is_write(self) -> bool:
        """Return True when the event requested a state-changing action."""
        return self.action is not None and self.action.is_write


class EvidenceSession:
    """Hands telemetry to one agent run and records every read and action, in order.

    Actions are recorded only; nothing is executed in this mock-only slice.
    """

    def __init__(self, telemetry: Telemetry, topology: Topology) -> None:
        """Open a session over one run's telemetry and the lab topology."""
        self._telemetry = telemetry
        self._topology = topology
        self._events: list[TraceEvent] = []

    @property
    def trace(self) -> tuple[TraceEvent, ...]:
        """Return the events recorded so far."""
        return tuple(self._events)

    def topology(self) -> Topology:
        """Return the topology and record the read."""
        self._record_read(EventSource.TOPOLOGY, ())
        return self._topology

    @property
    def run_label(self) -> tuple[str, int]:
        """Return the scenario id and seed of the run; neither carries ground truth."""
        return self._telemetry.scenario_id, self._telemetry.seed

    def knows_node(self, name: str) -> bool:
        """Return True when a node exists; this lookup is not recorded as a read."""
        return name in self._topology.nodes

    def alarms(self, node: str | None = None) -> tuple[Alarm, ...]:
        """Return all alarms, or one node's, and record the ids delivered."""
        records = _for_node(self._telemetry.alarms, node)
        self._record_read(EventSource.ALARMS, records)
        return records

    def kpis(self, node: str | None = None) -> tuple[Kpi, ...]:
        """Return all KPI samples, or one node's, and record the ids delivered."""
        records = _for_node(self._telemetry.kpis, node)
        self._record_read(EventSource.KPIS, records)
        return records

    def logs(self, node: str | None = None) -> tuple[LogRecord, ...]:
        """Return all log lines, or one node's, and record the ids delivered."""
        records = _for_node(self._telemetry.logs, node)
        self._record_read(EventSource.LOGS, records)
        return records

    def execute(self, action: Action) -> None:
        """Record a requested action."""
        self._events.append(
            TraceEvent(kind=EventKind.ACTION, source=EventSource.ACTION, action=action)
        )

    def seen_evidence_ids(self) -> frozenset[str]:
        """Return every evidence id delivered in this session."""
        return frozenset(
            evidence_id for event in self._events for evidence_id in event.evidence_ids
        )

    def _record_read(self, source: EventSource, records: Sequence[Alarm | Kpi | LogRecord]) -> None:
        """Append a read event carrying the delivered evidence ids."""
        ids = tuple(record.evidence_id for record in records)
        self._events.append(TraceEvent(kind=EventKind.READ, source=source, evidence_ids=ids))


def _for_node(records: tuple[RecordT, ...], node: str | None) -> tuple[RecordT, ...]:
    """Return every record, or only the records from one node."""
    if node is None:
        return records
    return tuple(record for record in records if record.node == node)
