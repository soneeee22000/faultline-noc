"""Keyword baseline router: deterministic rules, no model, every network write gated.

It splits the request into clauses, ignores quoted material, pasted log lines and sentences that
carry an instruction-override phrase, scores each clause against a keyword list per agent, and
merges consecutive clauses for the same agent into one step. A write is granted only for a clause
that opens with a write imperative and names a target, and always requires confirmation.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from faultline_noc.router.lexicon import (
    agent_scores,
    is_write_command,
    names_write_target,
    user_clauses,
)
from faultline_noc.router.models import Agent, Capability, RoutePlan, RouteStep

STRONG_SIGNAL_SCORE = 2
STRONG_CLAUSE_CONFIDENCE = 0.85
WEAK_CLAUSE_CONFIDENCE = 0.6
MULTI_STEP_DISCOUNT = 0.85
CLARIFY_CONFIDENCE = 0.6
REF_SEPARATOR = ":"
OBJECTIVE_JOINER = "; "
NO_SIGNAL_QUESTION = "Do you want an explanation, a test run, or an incident investigation?"
NO_TARGET_QUESTION = "Which network function or resource should be changed?"
TIE_QUESTION = "Should this be explained, tested or investigated?"
REF_AFFINITY: Mapping[Agent, frozenset[str]] = {
    Agent.KNOWLEDGE: frozenset({"lab", "doc"}),
    Agent.TESTING: frozenset({"lab", "cluster", "test-run", "test-suite"}),
    Agent.INCIDENT: frozenset({"alarm", "cluster", "test-run", "ticket", "nf"}),
}


@dataclass(frozen=True)
class ClauseSignal:
    """What one clause asks for, or the reason it cannot be routed."""

    text: str
    agent: Agent | None
    write: bool = False
    confidence: float = WEAK_CLAUSE_CONFIDENCE
    question: str | None = None


def classify_clause(clause: str) -> ClauseSignal:
    """Return the agent a clause asks for, a clarification question, or no signal."""
    if is_write_command(clause):
        if not names_write_target(clause):
            return ClauseSignal(clause, None, question=NO_TARGET_QUESTION)
        return ClauseSignal(clause, Agent.INCIDENT, write=True, confidence=STRONG_CLAUSE_CONFIDENCE)
    scores = agent_scores(clause)
    best = max(scores.values())
    if best == 0:
        return ClauseSignal(clause, None)
    leaders = [agent for agent, score in scores.items() if score == best]
    if len(leaders) > 1:
        return ClauseSignal(clause, None, question=TIE_QUESTION)
    strong = best >= STRONG_SIGNAL_SCORE
    confidence = STRONG_CLAUSE_CONFIDENCE if strong else WEAK_CLAUSE_CONFIDENCE
    return ClauseSignal(clause, leaders[0], confidence=confidence)


def merge_signals(signals: Sequence[ClauseSignal]) -> tuple[ClauseSignal, ...]:
    """Merge consecutive routed clauses for the same agent into one signal."""
    merged: list[ClauseSignal] = []
    for signal in signals:
        previous = merged[-1] if merged else None
        if previous is None or previous.agent != signal.agent:
            merged.append(signal)
            continue
        merged[-1] = ClauseSignal(
            text=previous.text + OBJECTIVE_JOINER + signal.text,
            agent=signal.agent,
            write=previous.write or signal.write,
            confidence=min(previous.confidence, signal.confidence),
        )
    return tuple(merged)


def refs_for(agent: Agent, available_context: Sequence[str]) -> tuple[str, ...]:
    """Return the available refs whose type this agent usually needs, in the given order."""
    wanted = REF_AFFINITY[agent]
    return tuple(ref for ref in available_context if ref.split(REF_SEPARATOR)[0] in wanted)


def step_for(signal: ClauseSignal, available_context: Sequence[str]) -> RouteStep:
    """Return the route step for a routed signal; a write step always needs confirmation."""
    if signal.agent is None:
        raise ValueError("an unrouted clause has no step")
    capabilities = (
        (Capability.READ, Capability.NETWORK_WRITE) if signal.write else (Capability.READ,)
    )
    return RouteStep(
        agent=signal.agent,
        objective=signal.text,
        context_refs=refs_for(signal.agent, available_context),
        allowed_capabilities=capabilities,
        requires_confirmation=signal.write,
    )


def clarification(question: str) -> RoutePlan:
    """Return a plan that asks the user a question instead of routing."""
    return RoutePlan(
        steps=(),
        requires_clarification=True,
        clarification_question=question,
        confidence=CLARIFY_CONFIDENCE,
    )


class KeywordBaseline:
    """Deterministic keyword router, the only router here that is not a deliberate mutant."""

    name: str = "keyword_baseline"

    def route(self, request: str, available_context: tuple[str, ...]) -> RoutePlan:
        """Return a plan from keyword rules, clarifying when a clause is unclear or unrouted."""
        signals = [classify_clause(clause) for clause in user_clauses(request)]
        questions = [signal.question for signal in signals if signal.question is not None]
        if questions:
            return clarification(questions[0])
        routed = merge_signals([signal for signal in signals if signal.agent is not None])
        if not routed:
            return clarification(NO_SIGNAL_QUESTION)
        confidence = min(signal.confidence for signal in routed)
        if len(routed) > 1:
            confidence *= MULTI_STEP_DISCOUNT
        return RoutePlan(
            steps=tuple(step_for(signal, available_context) for signal in routed),
            requires_clarification=False,
            clarification_question=None,
            confidence=confidence,
        )
