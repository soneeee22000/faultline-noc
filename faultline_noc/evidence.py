"""Evidence session: the only surface an agent uses to read telemetry or request actions."""

from collections.abc import Sequence
from enum import StrEnum

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

    def alarms(self) -> tuple[Alarm, ...]:
        """Return all alarms and record the ids delivered."""
        self._record_read(EventSource.ALARMS, self._telemetry.alarms)
        return self._telemetry.alarms

    def kpis(self) -> tuple[Kpi, ...]:
        """Return all KPI samples and record the ids delivered."""
        self._record_read(EventSource.KPIS, self._telemetry.kpis)
        return self._telemetry.kpis

    def logs(self) -> tuple[LogRecord, ...]:
        """Return all log lines and record the ids delivered."""
        self._record_read(EventSource.LOGS, self._telemetry.logs)
        return self._telemetry.logs

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
