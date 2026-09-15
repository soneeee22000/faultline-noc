"""Oracle agent: reads ground truth. It exists only to validate the harness and scorer."""

from faultline_noc.agents.common import gather_all, remediation_for
from faultline_noc.evidence import EvidenceSession
from faultline_noc.models import RCA, GroundTruth

ORACLE_CONFIDENCE = 1.0


class OracleAgent:
    """Gathers all evidence, then answers with the ground truth and cites its causal records."""

    name: str = "oracle"

    def __init__(self, truth: GroundTruth) -> None:
        """Hold the run's ground truth."""
        self._truth = truth

    def propose(self, evidence: EvidenceSession) -> RCA:
        """Return the true RCA, citing only causal evidence that was delivered."""
        seen = gather_all(evidence)
        truth = self._truth
        cited = tuple(
            evidence_id for evidence_id in truth.causal_evidence_ids if evidence_id in seen
        )
        return RCA(
            root_cause_nf=truth.root_cause_nf,
            fault_class=truth.fault_class,
            cited_evidence_ids=cited,
            confidence=ORACLE_CONFIDENCE,
            actions=remediation_for(truth.root_cause_nf, truth.fault_class),
        )
