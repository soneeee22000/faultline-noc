"""Rule baseline: topology-aware alarm correlation with no LLM."""

from collections.abc import Sequence

from faultline_noc.agents.common import remediation_for
from faultline_noc.evidence import EvidenceSession
from faultline_noc.models import RCA, Alarm, FaultClass, NodeKind, Severity
from faultline_noc.topology import Topology

MIN_FAULT_SEVERITY = Severity.MAJOR
MIN_ALARMS_PER_NODE = 2
MIN_ALARMING_NODES = 2
INSUFFICIENT_CONFIDENCE = 0.5
NON_SERVICE_AFFECTING_CODES: frozenset[str] = frozenset({"NTP_OFFSET_HIGH"})
ALARM_CODE_FAULTS: dict[str, FaultClass] = {
    "NF_PROCESS_RESTART": FaultClass.NF_CRASHLOOP,
    "LINK_FLAP": FaultClass.TRANSPORT_FLAP,
}


class RuleBaseline:
    """Blames the most upstream node with repeated serious alarms.

    A node is alarming when it has at least MIN_ALARMS_PER_NODE alarms at major or above whose
    code its alarm catalog does not mark as non-service-affecting.
    A fault is declared only when at least MIN_ALARMING_NODES nodes are alarming. Among the
    alarming nodes whose providers and transport are quiet, the one that explains the most
    other alarming nodes wins. It reads topology and alarms only, never logs.
    """

    name: str = "rule_baseline"

    def propose(self, evidence: EvidenceSession) -> RCA:
        """Correlate serious alarms over the dependency graph and return an RCA."""
        topology = evidence.topology()
        alarming = _alarming_nodes(evidence.alarms())
        root = _pick_root(alarming, topology) if len(alarming) >= MIN_ALARMING_NODES else None
        if root is None:
            return RCA(
                root_cause_nf=None,
                fault_class=FaultClass.INSUFFICIENT_EVIDENCE,
                cited_evidence_ids=(),
                confidence=INSUFFICIENT_CONFIDENCE,
            )
        fault_class = _classify(root, alarming[root], topology)
        return RCA(
            root_cause_nf=root,
            fault_class=fault_class,
            cited_evidence_ids=tuple(alarm.evidence_id for alarm in alarming[root]),
            confidence=_explained_share(root, alarming, topology),
            actions=remediation_for(root, fault_class),
        )


def _alarming_nodes(alarms: Sequence[Alarm]) -> dict[str, tuple[Alarm, ...]]:
    """Group serious, service-affecting alarms by node, keeping nodes with repeated ones."""
    grouped: dict[str, list[Alarm]] = {}
    for alarm in alarms:
        if _is_service_affecting(alarm):
            grouped.setdefault(alarm.node, []).append(alarm)
    return {
        node: tuple(items) for node, items in grouped.items() if len(items) >= MIN_ALARMS_PER_NODE
    }


def _is_service_affecting(alarm: Alarm) -> bool:
    """Return True for an alarm at major or above whose code is not catalogued as benign."""
    serious = alarm.severity.rank >= MIN_FAULT_SEVERITY.rank
    return serious and alarm.code not in NON_SERVICE_AFFECTING_CODES


def _pick_root(alarming: dict[str, tuple[Alarm, ...]], topology: Topology) -> str | None:
    """Return the alarming node with quiet upstream that explains the most alarming nodes."""
    names = frozenset(alarming)
    candidates = [node for node in names if not topology.upstream_of(node) & names]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda node: (-len(topology.dependents_of(node) & names), -len(alarming[node]), node),
    )


def _classify(root: str, alarms: Sequence[Alarm], topology: Topology) -> FaultClass:
    """Classify from the root's own alarm codes, falling back on the node kind."""
    for alarm in alarms:
        if alarm.code in ALARM_CODE_FAULTS:
            return ALARM_CODE_FAULTS[alarm.code]
    if topology.nodes[root] == NodeKind.ROUTER:
        return FaultClass.TRANSPORT_FLAP
    return FaultClass.NF_CRASHLOOP


def _explained_share(
    root: str, alarming: dict[str, tuple[Alarm, ...]], topology: Topology
) -> float:
    """Return the share of alarming nodes that are the root or depend on it."""
    explained = ({root} | topology.dependents_of(root)) & set(alarming)
    return len(explained) / len(alarming)
