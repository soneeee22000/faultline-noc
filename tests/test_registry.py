"""Tests that ground truth reaches only allowlisted agents."""

import inspect

import pytest

import faultline_noc.agents as agents_package
from faultline_noc.agents import (
    DEFAULT_AGENTS,
    TRUTH_AWARE_FACTORIES,
    Agent,
    BlindAgent,
    RuleBaseline,
    TruthAwareAgent,
    build_agent,
)
from faultline_noc.evidence import EvidenceSession
from faultline_noc.models import RCA, FaultClass, GroundTruth

NO_FAULT_TRUTH = GroundTruth(
    root_cause_nf=None,
    fault_class=FaultClass.INSUFFICIENT_EVIDENCE,
    symptom_nfs=(),
    causal_evidence_ids=(),
)


class _PeekingAgent:
    """A non-allowlisted agent that would like to read ground truth."""

    name: str = "peeking"

    def __init__(self, truth: GroundTruth) -> None:
        """Hold the truth it should never be given."""
        self._truth = truth

    def propose(self, evidence: EvidenceSession) -> RCA:
        """Answer from the truth it was handed."""
        return RCA(
            root_cause_nf=self._truth.root_cause_nf,
            fault_class=self._truth.fault_class,
            cited_evidence_ids=(),
            confidence=1.0,
        )


def _accepts_ground_truth(factory: object) -> bool:
    """Return True when calling the factory with one GroundTruth argument would bind."""
    try:
        inspect.signature(factory).bind(NO_FAULT_TRUTH)  # type: ignore[arg-type]
    except TypeError:
        return False
    return True


def test_every_default_agent_that_accepts_truth_is_allowlisted() -> None:
    """A default agent whose factory can take a GroundTruth argument must be on the allowlist."""
    for spec in DEFAULT_AGENTS:
        if _accepts_ground_truth(spec.factory):
            assert isinstance(spec, TruthAwareAgent)
            assert spec.factory in TRUTH_AWARE_FACTORIES


def test_blind_default_agents_cannot_accept_ground_truth() -> None:
    """Every blind agent's factory binds with no arguments and refuses a GroundTruth."""
    blind = [spec for spec in DEFAULT_AGENTS if isinstance(spec, BlindAgent)]
    assert blind
    for spec in blind:
        inspect.signature(spec.factory).bind()
        assert not _accepts_ground_truth(spec.factory)


def test_exported_agent_classes_that_accept_truth_are_allowlisted() -> None:
    """Any agent class the package exports that takes a GroundTruth is on the allowlist."""
    for name in agents_package.__all__:
        exported = getattr(agents_package, name)
        if not inspect.isclass(exported) or not hasattr(exported, "propose"):
            continue
        if exported is Agent:
            continue
        if _accepts_ground_truth(exported):
            assert exported in TRUTH_AWARE_FACTORIES, name


def test_truth_aware_spec_refuses_a_non_allowlisted_factory() -> None:
    """Wrapping a non-allowlisted factory as truth-aware raises before any run."""
    with pytest.raises(ValueError, match="allowlisted"):
        TruthAwareAgent(_PeekingAgent)


def test_build_agent_calls_a_blind_factory_with_no_arguments() -> None:
    """A blind spec is built without ground truth."""
    agent = build_agent(BlindAgent(RuleBaseline), NO_FAULT_TRUTH)
    assert agent.name == RuleBaseline.name
