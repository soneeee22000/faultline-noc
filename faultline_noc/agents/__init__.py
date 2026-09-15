"""Agents under evaluation: a rule baseline, an oracle and deliberately broken mutants."""

from faultline_noc.agents.baseline import RuleBaseline
from faultline_noc.agents.mutants import (
    UNDELIVERED_LOG_ID,
    BlamesSymptom,
    CitesUnseenEvidence,
    CitesUnsupportedEvidence,
    FollowsInjection,
    ProposesUncitedWrite,
    RestartsBystander,
    TakesInjectedActionUnread,
    WritesBeforeGathering,
)
from faultline_noc.agents.oracle import OracleAgent
from faultline_noc.agents.protocol import Agent, AgentFactory, TruthAwareFactory
from faultline_noc.agents.registry import (
    DEFAULT_AGENTS,
    TRUTH_AWARE_FACTORIES,
    AgentSpec,
    BlindAgent,
    TruthAwareAgent,
    build_agent,
)

__all__ = [
    "DEFAULT_AGENTS",
    "TRUTH_AWARE_FACTORIES",
    "UNDELIVERED_LOG_ID",
    "Agent",
    "AgentFactory",
    "AgentSpec",
    "BlamesSymptom",
    "BlindAgent",
    "CitesUnseenEvidence",
    "CitesUnsupportedEvidence",
    "FollowsInjection",
    "OracleAgent",
    "ProposesUncitedWrite",
    "RestartsBystander",
    "RuleBaseline",
    "TakesInjectedActionUnread",
    "TruthAwareAgent",
    "TruthAwareFactory",
    "WritesBeforeGathering",
    "build_agent",
]
