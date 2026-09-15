"""Helpers shared by the oracle and mutant agents."""

from faultline_noc.evidence import EvidenceSession
from faultline_noc.models import Action, ActionKind, EvidenceRecord, FaultClass


def gather_all(evidence: EvidenceSession) -> frozenset[str]:
    """Read alarms, KPIs and logs, and return every evidence id delivered."""
    records: tuple[EvidenceRecord, ...] = (*evidence.alarms(), *evidence.kpis(), *evidence.logs())
    return frozenset(record.evidence_id for record in records)


def remediation_for(root_cause_nf: str | None, fault_class: FaultClass) -> tuple[Action, ...]:
    """Return the default remediation: restart a crash-looping NF, ticket a transport fault."""
    if root_cause_nf is None:
        return ()
    if fault_class == FaultClass.NF_CRASHLOOP:
        return (Action(kind=ActionKind.RESTART_NF, target=root_cause_nf),)
    return (Action(kind=ActionKind.OPEN_TICKET, target=root_cause_nf),)
