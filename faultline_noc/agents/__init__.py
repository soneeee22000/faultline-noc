"""Agents under evaluation: a rule baseline, an oracle and deliberately broken mutants."""

from faultline_noc.agents.baseline import RuleBaseline
from faultline_noc.agents.mutants import (
    FABRICATED_EVIDENCE_ID,
    BlamesSymptom,
    CitesUnseenEvidence,
    WritesBeforeGathering,
)
from faultline_noc.agents.oracle import OracleAgent
from faultline_noc.agents.protocol import Agent, AgentFactory

__all__ = [
    "FABRICATED_EVIDENCE_ID",
    "Agent",
    "AgentFactory",
    "BlamesSymptom",
    "CitesUnseenEvidence",
    "OracleAgent",
    "RuleBaseline",
    "WritesBeforeGathering",
]
