"""Tests for the LLM agent loop, its tools, recorded transports, spend cap and evaluation."""

import os
from pathlib import Path
from typing import Any

import pytest

from faultline_noc.evidence import EventKind, EventSource, EvidenceSession
from faultline_noc.llm.agent import MODEL_PROFILES, LlmAgent, build_request, clean_content
from faultline_noc.llm.env import load_env_file
from faultline_noc.llm.evaluate import (
    EvalConfig,
    EvalOutcome,
    build_payload,
    new_spend_tracker,
    run_evaluation,
)
from faultline_noc.llm.pricing import BudgetExceededError, SpendTracker, usage_cost_usd
from faultline_noc.llm.report import render_markdown
from faultline_noc.llm.tools import ToolExecutor
from faultline_noc.llm.transport import (
    CassetteMissingError,
    CassetteStore,
    RecordingTransport,
    ReplayTransport,
    request_key,
)
from faultline_noc.models import FaultClass
from faultline_noc.paths import DEFAULT_CASSETTES_DIR
from faultline_noc.scenario import Scenario
from faultline_noc.simulator import simulate
from faultline_noc.topology import Topology

USAGE = {"input_tokens": 1000, "output_tokens": 200}
HAIKU = MODEL_PROFILES["claude-haiku-4-5"]


class ScriptedTransport:
    """Returns prepared responses in order and keeps every request it was sent."""

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        """Queue the responses to return."""
        self._responses = responses
        self.requests: list[dict[str, Any]] = []

    def create(self, request: dict[str, Any]) -> dict[str, Any]:
        """Record the request and return the next prepared response."""
        self.requests.append(request)
        return self._responses.pop(0)


def _tool_use(block_id: str, name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
    """Return a tool_use content block."""
    return {"type": "tool_use", "id": block_id, "name": name, "input": tool_input}


def _response(*blocks: dict[str, Any]) -> dict[str, Any]:
    """Return a response carrying content blocks and a fixed usage."""
    return {"content": list(blocks), "usage": USAGE, "stop_reason": "tool_use"}


def _submit(block_id: str, fault_class: str = "nf_crashloop") -> dict[str, Any]:
    """Return a submit_rca block naming upf-1, with the given fault class."""
    tool_input: dict[str, Any] = {
        "root_cause_nf": "upf-1",
        "fault_class": fault_class,
        "cited_evidence_ids": [],
        "confidence": 0.8,
        "proposed_actions": [],
    }
    return _tool_use(block_id, "submit_rca", tool_input)


def _session(scenarios: dict[str, Scenario], topology: Topology) -> EvidenceSession:
    """Return a session over s01 seed 0."""
    telemetry = simulate(scenarios["s01_upf_crashloop"], topology, seed=0).telemetry
    return EvidenceSession(telemetry, topology)


def _agent(transport: ScriptedTransport, spend: SpendTracker | None = None) -> LlmAgent:
    """Return a Haiku agent whose every run uses the scripted transport."""
    tracker = spend if spend is not None else SpendTracker(budget_usd=1.0)
    return LlmAgent(HAIKU, lambda _scenario_id, _seed: transport, tracker)


def test_agent_reads_through_tools_and_submits(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """Filtered tool reads are recorded with only the delivered ids, then the RCA is returned."""
    transport = ScriptedTransport(
        [
            _response(_tool_use("t1", "get_alarms", {"node": "smf-1"})),
            _response(_tool_use("t2", "get_kpis", {"node": "upf-1"})),
            _response(_submit("t3")),
        ]
    )
    session = _session(scenarios, topology)
    rca = _agent(transport).propose(session)
    telemetry = simulate(scenarios["s01_upf_crashloop"], topology, seed=0).telemetry
    assert rca.root_cause_nf == "upf-1"
    assert [event.source for event in session.trace] == [EventSource.ALARMS, EventSource.KPIS]
    smf_ids = tuple(alarm.evidence_id for alarm in telemetry.alarms if alarm.node == "smf-1")
    assert session.trace[0].evidence_ids == smf_ids


def test_invalid_rca_gets_an_error_and_a_retry(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """A contradictory RCA is rejected with an error tool_result, and the corrected one is kept."""
    transport = ScriptedTransport(
        [_response(_submit("t1", fault_class="insufficient_evidence")), _response(_submit("t2"))]
    )
    rca = _agent(transport).propose(_session(scenarios, topology))
    assert rca.fault_class == FaultClass.NF_CRASHLOOP
    feedback = transport.requests[1]["messages"][-1]["content"][0]
    assert feedback["is_error"] is True


def test_agent_gives_up_when_the_model_stops_without_submitting(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """A final answer with no submit_rca becomes insufficient_evidence at zero confidence."""
    text_only = {"content": [{"type": "text", "text": "Done."}], "usage": USAGE}
    agent = _agent(ScriptedTransport([text_only]))
    rca = agent.propose(_session(scenarios, topology))
    assert rca.fault_class == FaultClass.INSUFFICIENT_EVIDENCE
    assert rca.confidence == 0.0
    assert agent.submitted is False


def test_restart_tool_records_a_write(scenarios: dict[str, Scenario], topology: Topology) -> None:
    """Calling restart_nf records a write action in the session trace."""
    transport = ScriptedTransport(
        [_response(_tool_use("t1", "restart_nf", {"target": "amf-1"})), _response(_submit("t2"))]
    )
    session = _session(scenarios, topology)
    _agent(transport).propose(session)
    assert session.trace[-1].kind == EventKind.ACTION
    assert session.trace[-1].is_write


def test_parallel_tool_results_share_one_user_message(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """Every tool result from one response goes back in a single user message."""
    transport = ScriptedTransport(
        [
            _response(_tool_use("t1", "get_topology", {}), _tool_use("t2", "get_logs", {})),
            _response(_submit("t3")),
        ]
    )
    _agent(transport).propose(_session(scenarios, topology))
    results = transport.requests[1]["messages"][-1]["content"]
    assert [result["tool_use_id"] for result in results] == ["t1", "t2"]


def test_tool_budget_returns_an_error_once_spent(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """After the budget is spent, tool calls return an error and read nothing."""
    session = _session(scenarios, topology)
    executor = ToolExecutor(session, max_calls=1)
    assert not executor.run("get_topology", {}).is_error
    assert executor.run("get_alarms", {}).is_error
    assert len(session.trace) == 1


def test_unknown_node_is_an_error_and_not_a_read(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """An unknown node returns an error without recording a read."""
    session = _session(scenarios, topology)
    assert ToolExecutor(session).run("get_kpis", {"node": "mme-1"}).is_error
    assert session.trace == ()


def test_request_shape_per_model() -> None:
    """Sonnet gets an effort setting and Haiku does not; both carry tools and caching."""
    sonnet = build_request(MODEL_PROFILES["claude-sonnet-5"], [])
    haiku = build_request(HAIKU, [])
    assert sonnet["output_config"] == {"effort": "medium"}
    assert "output_config" not in haiku
    assert haiku["cache_control"] == {"type": "ephemeral"}
    assert {tool["name"] for tool in haiku["tools"]} >= {"get_alarms", "submit_rca"}


def test_clean_content_keeps_only_accepted_fields() -> None:
    """Unknown fields and block types are dropped before the history is sent back."""
    blocks: list[dict[str, Any]] = [
        {"type": "text", "text": "hi", "citations": None},
        {"type": "unknown", "x": 1},
    ]
    assert clean_content(blocks) == [{"type": "text", "text": "hi"}]


def test_recording_saves_before_returning_and_replay_matches(tmp_path: Path) -> None:
    """A recorded response is on disk before it is returned, and replay finds it by content."""
    store = CassetteStore(tmp_path)
    request = {"model": "m", "messages": [{"role": "user", "content": "x"}]}
    recorded = RecordingTransport(ScriptedTransport([_response()]), store).create(request)
    assert (tmp_path / f"{request_key(request)}.json").exists()
    reordered = {"messages": request["messages"], "model": "m"}
    assert ReplayTransport(store).create(reordered) == recorded


def test_replay_fails_closed_on_a_changed_request(tmp_path: Path) -> None:
    """A request with no recorded response raises instead of calling the API."""
    with pytest.raises(CassetteMissingError):
        ReplayTransport(CassetteStore(tmp_path)).create({"model": "m"})


def test_usage_cost_counts_cache_reads_and_output() -> None:
    """Cost adds uncached input, cache reads at a tenth, and output at the output price."""
    usage = {
        "input_tokens": 1_000_000,
        "output_tokens": 100_000,
        "cache_read_input_tokens": 1_000_000,
    }
    assert usage_cost_usd("claude-haiku-4-5", usage) == pytest.approx(1.0 + 0.1 + 0.5)


def test_spend_cap_stops_further_requests(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """No request is sent once the cap is reached."""
    transport = ScriptedTransport([_response(_submit("t1"))])
    with pytest.raises(BudgetExceededError):
        _agent(transport, SpendTracker(budget_usd=0.0)).propose(_session(scenarios, topology))
    assert transport.requests == []


def test_env_file_sets_unset_variables_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Values from .env fill unset variables and never override ones already set."""
    env_file = tmp_path / ".env"
    env_file.write_text('# comment\nFAULTLINE_A="one"\nFAULTLINE_B=two\n', encoding="utf-8")
    monkeypatch.delenv("FAULTLINE_A", raising=False)
    monkeypatch.setenv("FAULTLINE_B", "kept")
    load_env_file(env_file)
    assert os.environ["FAULTLINE_A"] == "one"
    assert os.environ["FAULTLINE_B"] == "kept"


def test_baseline_only_evaluation_builds_a_report(
    scenarios: dict[str, Scenario],
    hard_scenarios: dict[str, Scenario],
    topology: Topology,
    tmp_path: Path,
) -> None:
    """With no models, the evaluation scores the baseline on published and hard scenarios."""
    config = EvalConfig(
        mode="replay", models=(), seeds=(0,), budget_usd=0.0, cassettes_dir=tmp_path
    )
    selected = (scenarios["s01_upf_crashloop"], hard_scenarios["s09_upf_crashloop_silent"])
    outcome = EvalOutcome()
    spend = SpendTracker(budget_usd=0.0)
    run_evaluation(config, selected, topology, outcome, spend)
    payload = build_payload(config, selected, outcome, spend, topology)
    assert payload.runs == len(selected)
    assert [row.agent for row in payload.accuracy_overall] == ["rule_baseline"]
    assert "s09_upf_crashloop_silent" in render_markdown(payload)


def test_no_sample_traces_when_the_sampled_runs_are_absent(
    scenarios: dict[str, Scenario], topology: Topology, tmp_path: Path
) -> None:
    """A run without the sampled scenario keeps no traces, so the payload stays empty there."""
    config = EvalConfig(
        mode="replay", models=(), seeds=(0,), budget_usd=0.0, cassettes_dir=tmp_path
    )
    selected = (scenarios["s01_upf_crashloop"],)
    outcome = EvalOutcome()
    spend = SpendTracker(budget_usd=0.0)
    run_evaluation(config, selected, topology, outcome, spend)
    payload = build_payload(config, selected, outcome, spend, topology)
    assert payload.sample_traces == ()
    assert payload.sample_scenarios == ()


def test_sample_traces_contrast_the_baseline_with_the_model(
    hard_scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """Replaying s08 keeps the baseline trace and the Sonnet trace, the pair the page compares."""
    config = EvalConfig(
        mode="replay",
        models=("claude-sonnet-5",),
        seeds=(0,),
        budget_usd=0.0,
        cassettes_dir=DEFAULT_CASSETTES_DIR,
    )
    selected = (hard_scenarios["s08_smf_crashloop_router_noise"],)
    outcome = EvalOutcome()
    spend = new_spend_tracker(config)
    run_evaluation(config, selected, topology, outcome, spend)
    payload = build_payload(config, selected, outcome, spend, topology)
    baseline, sonnet = payload.sample_traces
    assert (baseline.agent, sonnet.agent) == ("rule_baseline", "llm_sonnet_5")
    assert baseline.correct is False
    assert sonnet.correct is True
    assert sonnet.steps != ()
    assert [step.index for step in sonnet.steps] == sorted(step.index for step in sonnet.steps)
    assert [item.id for item in payload.sample_scenarios] == ["s08_smf_crashloop_router_noise"]
