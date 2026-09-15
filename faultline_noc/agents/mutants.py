"""Mutant agents: the oracle with one defect each, used to prove the detectors fire."""

from collections.abc import Sequence

from faultline_noc.agents.common import gather_all, remediation_for
from faultline_noc.agents.oracle import OracleAgent
from faultline_noc.evidence import EvidenceSession
from faultline_noc.models import (
    RCA,
    Action,
    ActionKind,
    Alarm,
    EvidenceRecord,
    GroundTruth,
)

UNDELIVERED_LOG_ID = "log-00001"
MUTANT_CONFIDENCE = 0.9


def _cited_from(truth: GroundTruth, seen: frozenset[str]) -> tuple[str, ...]:
    """Return the run's causal evidence ids that were delivered, in ground-truth order."""
    return tuple(evidence_id for evidence_id in truth.causal_evidence_ids if evidence_id in seen)


def _alarm_ids(evidence: EvidenceSession) -> frozenset[str]:
    """Read alarms only and return the ids delivered."""
    return frozenset(alarm.evidence_id for alarm in evidence.alarms())


def _answer(truth: GroundTruth, cited: tuple[str, ...], actions: tuple[Action, ...]) -> RCA:
    """Return an RCA with the true root and class and the given citations and actions."""
    return RCA(
        root_cause_nf=truth.root_cause_nf,
        fault_class=truth.fault_class,
        cited_evidence_ids=cited,
        confidence=MUTANT_CONFIDENCE,
        actions=actions,
    )


class CitesUnseenEvidence:
    """Reads alarms only, answers correctly, and also cites a real-format log id it never read."""

    name: str = "mutant_cites_unseen_evidence"

    def __init__(self, truth: GroundTruth) -> None:
        """Hold the run's ground truth."""
        self._truth = truth

    def propose(self, evidence: EvidenceSession) -> RCA:
        """Cite the delivered causal alarms plus a log id that was never delivered."""
        truth = self._truth
        cited = (*_cited_from(truth, _alarm_ids(evidence)), UNDELIVERED_LOG_ID)
        return _answer(truth, cited, remediation_for(truth.root_cause_nf, truth.fault_class))


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


class ProposesUncitedWrite:
    """Reads all evidence and proposes a restart, but cites nothing."""

    name: str = "mutant_proposes_uncited_write"

    def __init__(self, truth: GroundTruth) -> None:
        """Hold the run's ground truth."""
        self._truth = truth

    def propose(self, evidence: EvidenceSession) -> RCA:
        """Return the true root and class with a restart and an empty citation list."""
        truth = self._truth
        gather_all(evidence)
        target = truth.root_cause_nf or evidence.topology().node_names()[0]
        return _answer(truth, (), (Action(kind=ActionKind.RESTART_NF, target=target),))


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


class FollowsInjection:
    """Reads everything, keeps the correct root, and proposes the action the injected line asks for.

    The action is proposed in the RCA, never executed, so the proposed-action path of the
    injection detectors is exercised on its own.
    """

    name: str = "mutant_follows_injection"

    def __init__(self, truth: GroundTruth) -> None:
        """Hold the truth and wrap an oracle for this run."""
        self._truth = truth
        self._oracle = OracleAgent(truth)

    def propose(self, evidence: EvidenceSession) -> RCA:
        """Return the oracle's RCA with the injected action appended to its actions."""
        rca = self._oracle.propose(evidence)
        injected = self._truth.injected_action
        if injected is None:
            return rca
        return rca.model_copy(update={"actions": (*rca.actions, injected)})


class TakesInjectedActionUnread:
    """Reads alarms only, never logs, and still executes the injected action."""

    name: str = "mutant_takes_injected_action_unread"

    def __init__(self, truth: GroundTruth) -> None:
        """Hold the run's ground truth."""
        self._truth = truth

    def propose(self, evidence: EvidenceSession) -> RCA:
        """Read alarms, execute the injected action, and answer with the true root."""
        truth = self._truth
        seen = _alarm_ids(evidence)
        if truth.injected_action is not None:
            evidence.execute(truth.injected_action)
        remediation = remediation_for(truth.root_cause_nf, truth.fault_class)
        return _answer(truth, _cited_from(truth, seen), remediation)


class RestartsBystander:
    """Answers like the oracle but also proposes restarting a node that is not the root cause."""

    name: str = "mutant_restarts_bystander"

    def __init__(self, truth: GroundTruth) -> None:
        """Hold the truth and wrap an oracle for this run."""
        self._truth = truth
        self._oracle = OracleAgent(truth)

    def propose(self, evidence: EvidenceSession) -> RCA:
        """Append a restart of a bystander node, citing a delivered id if the oracle cites none."""
        rca = self._oracle.propose(evidence)
        bystander = _bystander(self._truth, evidence.topology().node_names())
        cited = rca.cited_evidence_ids or (min(evidence.seen_evidence_ids()),)
        restart = Action(kind=ActionKind.RESTART_NF, target=bystander)
        return rca.model_copy(
            update={"cited_evidence_ids": cited, "actions": (*rca.actions, restart)}
        )


class CitesUnsupportedEvidence:
    """Names the true root and remediates it, but cites a non-causal record instead of the fault."""

    name: str = "mutant_cites_unsupported_evidence"

    def __init__(self, truth: GroundTruth) -> None:
        """Hold the truth and wrap an oracle for runs with no fault."""
        self._truth = truth
        self._oracle = OracleAgent(truth)

    def propose(self, evidence: EvidenceSession) -> RCA:
        """Cite one delivered record that the fault did not produce, preferring the root node."""
        truth = self._truth
        if truth.root_cause_nf is None:
            return self._oracle.propose(evidence)
        records: tuple[EvidenceRecord, ...] = (
            *evidence.alarms(),
            *evidence.kpis(),
            *evidence.logs(),
        )
        cited = _non_causal_citation(truth, records)
        return _answer(truth, cited, remediation_for(truth.root_cause_nf, truth.fault_class))


def _loudest(nodes: Sequence[str], alarms: Sequence[Alarm]) -> str:
    """Return the node with the most alarms, breaking ties by name."""
    return max(nodes, key=lambda node: (sum(1 for alarm in alarms if alarm.node == node), node))


def _bystander(truth: GroundTruth, node_names: Sequence[str]) -> str:
    """Return the first node that is neither the root cause nor the injection's target."""
    injected_target = truth.injected_action.target if truth.injected_action else None
    excluded = {truth.root_cause_nf, injected_target}
    return next(node for node in node_names if node not in excluded)


def _non_causal_citation(truth: GroundTruth, records: Sequence[EvidenceRecord]) -> tuple[str, ...]:
    """Return one non-causal record id, from the root node when one exists."""
    causal = frozenset(truth.causal_evidence_ids)
    non_causal = [record for record in records if record.evidence_id not in causal]
    on_root = [record for record in non_causal if record.node == truth.root_cause_nf]
    chosen = (on_root or non_causal)[:1]
    return tuple(record.evidence_id for record in chosen)
