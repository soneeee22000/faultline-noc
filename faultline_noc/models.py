"""Core data models shared by the simulator, agents, detectors and scorer."""

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

MIN_CONFIDENCE = 0.0
MAX_CONFIDENCE = 1.0


class FrozenModel(BaseModel):
    """Immutable pydantic base model that rejects unknown fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class NodeKind(StrEnum):
    """Kinds of network element in the simulated 5G SA core."""

    GNB = "gnb"
    AMF = "amf"
    SMF = "smf"
    UPF = "upf"
    NRF = "nrf"
    ROUTER = "router"


class Interface(StrEnum):
    """Logical interfaces between NFs (TS 23.501 clauses 4.2.6 and 4.2.7)."""

    N2 = "N2"
    N3 = "N3"
    N4 = "N4"
    N11 = "N11"
    NNRF = "Nnrf"


class Severity(StrEnum):
    """Alarm severities, declared from least to most severe."""

    WARNING = "warning"
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        """Return the position of the severity in the ordering, warning being lowest."""
        return list(Severity).index(self)


class FaultClass(StrEnum):
    """Fault classes an RCA can report, including the no-fault answer."""

    NF_CRASHLOOP = "nf_crashloop"
    TRANSPORT_FLAP = "transport_flap"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class Alarm(FrozenModel):
    """An alarm raised by a node at a tick."""

    evidence_id: str
    tick: int = Field(ge=0)
    node: str
    severity: Severity
    code: str
    text: str


class Kpi(FrozenModel):
    """A KPI sample reported by a node at a tick."""

    evidence_id: str
    tick: int = Field(ge=0)
    node: str
    name: str
    value: float


class LogRecord(FrozenModel):
    """A log line written by a node at a tick."""

    evidence_id: str
    tick: int = Field(ge=0)
    node: str
    level: str
    message: str


EvidenceRecord = Alarm | Kpi | LogRecord


class Telemetry(FrozenModel):
    """All alarms, KPIs and logs produced by one simulation run."""

    scenario_id: str
    seed: int
    alarms: tuple[Alarm, ...]
    kpis: tuple[Kpi, ...]
    logs: tuple[LogRecord, ...]

    def canonical_bytes(self) -> bytes:
        """Return the UTF-8 JSON serialization used for byte-identity checks."""
        return self.model_dump_json().encode("utf-8")

    def evidence_ids(self) -> tuple[str, ...]:
        """Return every evidence id in the run, alarms first, then KPIs, then logs."""
        records: tuple[EvidenceRecord, ...] = (*self.alarms, *self.kpis, *self.logs)
        return tuple(record.evidence_id for record in records)


class ActionKind(StrEnum):
    """Actions an agent can request."""

    RESTART_NF = "restart_nf"
    OPEN_TICKET = "open_ticket"


WRITE_ACTION_KINDS: frozenset[ActionKind] = frozenset({ActionKind.RESTART_NF})


class Action(FrozenModel):
    """An action on a node; writes change network state, tickets do not."""

    kind: ActionKind
    target: str

    @property
    def is_write(self) -> bool:
        """Return True when the action would change network state."""
        return self.kind in WRITE_ACTION_KINDS


def check_root_matches_class(root_cause_nf: str | None, fault_class: FaultClass) -> None:
    """Raise ValueError when a root cause and a fault class contradict each other."""
    no_fault = fault_class == FaultClass.INSUFFICIENT_EVIDENCE
    if no_fault and root_cause_nf is not None:
        raise ValueError("insufficient_evidence must not name a root cause node")
    if not no_fault and root_cause_nf is None:
        raise ValueError(f"{fault_class} requires a root cause node")


class RCA(FrozenModel):
    """Root cause analysis returned by an agent."""

    root_cause_nf: str | None
    fault_class: FaultClass
    cited_evidence_ids: tuple[str, ...]
    confidence: float = Field(ge=MIN_CONFIDENCE, le=MAX_CONFIDENCE)
    actions: tuple[Action, ...] = ()

    @model_validator(mode="after")
    def _root_matches_class(self) -> Self:
        """Reject an RCA whose root cause contradicts its fault class."""
        check_root_matches_class(self.root_cause_nf, self.fault_class)
        return self


class GroundTruth(FrozenModel):
    """What the injector actually did in a run; given only to the allowlisted oracle and mutants."""

    root_cause_nf: str | None
    fault_class: FaultClass
    symptom_nfs: tuple[str, ...]
    causal_evidence_ids: tuple[str, ...]
    injected_action: Action | None = None
    injection_evidence_id: str | None = None

    @model_validator(mode="after")
    def _root_matches_class(self) -> Self:
        """Reject ground truth whose root cause contradicts its fault class."""
        check_root_matches_class(self.root_cause_nf, self.fault_class)
        return self
