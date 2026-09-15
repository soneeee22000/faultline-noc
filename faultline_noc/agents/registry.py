"""Which agents the runner builds, and the allowlist of agents that may be given ground truth."""

from dataclasses import dataclass

from faultline_noc.agents.baseline import RuleBaseline
from faultline_noc.agents.mutants import (
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
from faultline_noc.models import GroundTruth

TRUTH_AWARE_FACTORIES: frozenset[TruthAwareFactory] = frozenset(
    {
        OracleAgent,
        CitesUnseenEvidence,
        WritesBeforeGathering,
        ProposesUncitedWrite,
        BlamesSymptom,
        FollowsInjection,
        TakesInjectedActionUnread,
        RestartsBystander,
        CitesUnsupportedEvidence,
    }
)


@dataclass(frozen=True)
class BlindAgent:
    """An evaluated agent. Its factory takes no arguments, so it never receives ground truth."""

    factory: AgentFactory


@dataclass(frozen=True)
class TruthAwareAgent:
    """A harness control built from ground truth: the oracle or a mutant, and nothing else."""

    factory: TruthAwareFactory

    def __post_init__(self) -> None:
        """Refuse any factory that is not on the truth-aware allowlist."""
        if self.factory not in TRUTH_AWARE_FACTORIES:
            raise ValueError(f"{self.factory!r} is not allowlisted to receive ground truth")


AgentSpec = BlindAgent | TruthAwareAgent


def build_agent(spec: AgentSpec, truth: GroundTruth) -> Agent:
    """Build one agent for a run, passing ground truth only to allowlisted controls."""
    if isinstance(spec, TruthAwareAgent):
        return spec.factory(truth)
    return spec.factory()


DEFAULT_AGENTS: tuple[AgentSpec, ...] = (
    BlindAgent(RuleBaseline),
    TruthAwareAgent(OracleAgent),
    TruthAwareAgent(CitesUnseenEvidence),
    TruthAwareAgent(WritesBeforeGathering),
    TruthAwareAgent(ProposesUncitedWrite),
    TruthAwareAgent(BlamesSymptom),
    TruthAwareAgent(FollowsInjection),
    TruthAwareAgent(TakesInjectedActionUnread),
    TruthAwareAgent(RestartsBystander),
    TruthAwareAgent(CitesUnsupportedEvidence),
)
