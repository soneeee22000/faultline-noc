"""The Agent protocol every evaluated agent implements, and the two factory shapes."""

from collections.abc import Callable
from typing import Protocol

from faultline_noc.evidence import EvidenceSession
from faultline_noc.models import RCA, GroundTruth


class Agent(Protocol):
    """Reads evidence through a session and proposes a root cause analysis."""

    name: str

    def propose(self, evidence: EvidenceSession) -> RCA:
        """Return an RCA built only from what was read through the session."""
        ...


AgentFactory = Callable[[], Agent]
"""Builds an evaluated agent. It takes no arguments, so it cannot receive ground truth."""

TruthAwareFactory = Callable[[GroundTruth], Agent]
"""Builds a harness control from ground truth. Only allowlisted factories may use this shape."""
