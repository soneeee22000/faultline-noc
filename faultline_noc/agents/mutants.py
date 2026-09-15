"""Mutant agents: the oracle with exactly one defect each, used to prove the detectors fire."""

from collections.abc import Sequence

from faultline_noc.agents.oracle import OracleAgent
from faultline_noc.evidence import EvidenceSession
from faultline_noc.models import RCA, Action, ActionKind, Alarm, GroundTruth

FABRICATED_EVIDENCE_ID = "alm-fabricated-00001"
MUTANT_CONFIDENCE = 0.9


class CitesUnseenEvidence:
    """Answers like the oracle but also cites an evidence id it was never given."""

    name: str = "mutant_cites_unseen_evidence"

    def __init__(self, truth: GroundTruth) -> None:
        """Wrap an oracle for this run."""
        self._oracle = OracleAgent(truth)

    def propose(self, evidence: EvidenceSession) -> RCA:
        """Return the oracle's RCA with one fabricated citation appended."""
        rca = self._oracle.propose(evidence)
        cited = (*rca.cited_evidence_ids, FABRICATED_EVIDENCE_ID)
        return rca.model_copy(update={"cited_evidence_ids": cited})


class WritesBeforeGathering:
    """Restarts a node before reading any evidence, then answers like the oracle."""

    name: str = "mutant_writes_before_gathering"

    def __init__(self, truth: GroundTruth) -> None:
        """Hold the truth and wrap an oracle for this run."""
        self._truth = truth
        self._oracle = OracleAgent(truth)

    def propose(self, evidence: EvidenceSession) -> RCA:
        """Issue a restart first, then gather and answer."""
        target = self._truth.root_cause_nf or evidence.topology().node_names()[0]
        evidence.execute(Action(kind=ActionKind.RESTART_NF, target=target))
        return self._oracle.propose(evidence)


class BlamesSymptom:
    """Blames the loudest symptom NF instead of the root cause, and proposes no action."""

    name: str = "mutant_blames_symptom"

    def __init__(self, truth: GroundTruth) -> None:
        """Hold the truth and wrap an oracle for runs with no symptoms."""
        self._truth = truth
        self._oracle = OracleAgent(truth)

    def propose(self, evidence: EvidenceSession) -> RCA:
        """Return an RCA naming the symptom NF with the most alarms."""
        truth = self._truth
        if not truth.symptom_nfs:
            return self._oracle.propose(evidence)
        alarms = evidence.alarms()
        loudest = _loudest(truth.symptom_nfs, alarms)
        return RCA(
            root_cause_nf=loudest,
            fault_class=truth.fault_class,
            cited_evidence_ids=tuple(
                alarm.evidence_id for alarm in alarms if alarm.node == loudest
            ),
            confidence=MUTANT_CONFIDENCE,
        )


def _loudest(nodes: Sequence[str], alarms: Sequence[Alarm]) -> str:
    """Return the node with the most alarms, breaking ties by name."""
    return max(nodes, key=lambda node: (sum(1 for alarm in alarms if alarm.node == node), node))
