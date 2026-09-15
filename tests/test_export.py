"""Tests for the JSON export of a harness run that feeds the project page."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from faultline_noc.__main__ import main
from faultline_noc.agents import FollowsInjection, RuleBaseline
from faultline_noc.evidence import EventSource
from faultline_noc.export import (
    MAX_IDS_PER_READ,
    SCHEMA_VERSION,
    PayloadMeta,
    ResultsPayload,
    SampleTrace,
    build_payload,
    payload_json,
)
from faultline_noc.runner import RunResult, run_matrix
from faultline_noc.scenario import Scenario
from faultline_noc.scoring import accuracy_by, actions_correct, detection_matrix, harness_failures
from faultline_noc.topology import Topology

SEEDS = (0, 1)
COMMAND = "python -m faultline_noc --all --seeds 2"
INJECTION_SCENARIO = "s07_log_injection"


@pytest.fixture(scope="module")
def results(scenarios: dict[str, Scenario], topology: Topology) -> tuple[RunResult, ...]:
    """Return every default agent on every repo scenario at two seeds."""
    return run_matrix(tuple(scenarios.values()), topology, SEEDS)


@pytest.fixture(scope="module")
def payload(
    results: tuple[RunResult, ...], scenarios: dict[str, Scenario], topology: Topology
) -> ResultsPayload:
    """Return the payload built from the shared results."""
    failures = harness_failures(results)
    return build_payload(
        results, SEEDS, failures, tuple(scenarios.values()), topology, command=COMMAND
    )


def _trace(payload: ResultsPayload, scenario_id: str, agent: str) -> SampleTrace:
    """Return the one sample trace for a scenario and agent."""
    (trace,) = [
        item
        for item in payload.sample_traces
        if (item.scenario_id, item.agent) == (scenario_id, agent)
    ]
    return trace


def test_payload_round_trips_through_json(payload: ResultsPayload) -> None:
    """Serialising and validating the JSON gives back an equal payload."""
    restored = ResultsPayload.model_validate_json(payload_json(payload))
    assert restored == payload
    assert restored.schema_version == SCHEMA_VERSION


def test_json_is_newline_terminated_and_has_no_timestamps(payload: ResultsPayload) -> None:
    """The JSON text ends in a newline and carries no date or time fields."""
    text = payload_json(payload)
    assert text.endswith("}\n")
    lowered = text.lower()
    assert "timestamp" not in lowered
    assert "generated_at" not in lowered


def test_meta_describes_the_run(payload: ResultsPayload, results: tuple[RunResult, ...]) -> None:
    """Meta records the command, the run shape and the harness verdict."""
    meta = payload.meta
    assert meta.command == COMMAND
    assert (meta.seed_count, meta.seed_first, meta.seed_last) == (len(SEEDS), 0, 1)
    assert meta.runs == len(results)
    assert meta.agents[0] == RuleBaseline.name
    assert INJECTION_SCENARIO in meta.scenarios
    assert meta.harness_pass is True
    assert meta.failures == ()


def test_accuracy_rows_equal_the_scorer(
    payload: ResultsPayload, results: tuple[RunResult, ...]
) -> None:
    """Every rate row carries the scorer's counts and Wilson bounds."""
    pairs = (
        (payload.accuracy_overall, accuracy_by(results, per_scenario=False)),
        (payload.accuracy_per_scenario, accuracy_by(results, per_scenario=True)),
        (
            payload.action_correctness,
            accuracy_by(results, per_scenario=False, outcome=actions_correct),
        ),
    )
    for exported, scored in pairs:
        assert [(row.agent, row.scope, row.correct, row.n) for row in exported] == [
            (row.agent, row.scope, row.correct, row.total) for row in scored
        ]
        for out_row, score_row in zip(exported, scored, strict=True):
            assert out_row.rate == pytest.approx(score_row.accuracy, abs=1e-6)
            assert out_row.wilson_low == pytest.approx(score_row.interval.low, abs=1e-6)
            assert out_row.wilson_high == pytest.approx(score_row.interval.high, abs=1e-6)


def test_detection_matrix_equals_the_scorer(
    payload: ResultsPayload, results: tuple[RunResult, ...]
) -> None:
    """The exported matrix is the scorer's matrix, cell for cell."""
    assert payload.detection_matrix == detection_matrix(results)
    detectors = tuple(dict.fromkeys(cell.detector for cell in detection_matrix(results)))
    assert payload.meta.detectors == detectors


def test_same_seeds_give_byte_identical_json(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """Two independent runs over the same seeds serialise to the same bytes."""
    texts = []
    for _ in range(2):
        runs = run_matrix(tuple(scenarios.values()), topology, SEEDS)
        built = build_payload(
            runs,
            SEEDS,
            harness_failures(runs),
            tuple(scenarios.values()),
            topology,
            command=COMMAND,
        )
        texts.append(payload_json(built).encode("utf-8"))
    assert texts[0] == texts[1]


def test_harness_pass_mirrors_failures(
    results: tuple[RunResult, ...], scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """A non-empty failure list makes harness_pass false and is carried through verbatim."""
    failures = ("oracle on s01_upf_crashloop seed 0: unexpected symptom_blamed",)
    built = build_payload(
        results, SEEDS, failures, tuple(scenarios.values()), topology, command=COMMAND
    )
    assert built.meta.harness_pass is False
    assert built.meta.failures == failures


def test_meta_rejects_a_pass_that_contradicts_failures(payload: ResultsPayload) -> None:
    """Meta cannot claim a pass while listing failures."""
    data = payload.meta.model_dump()
    data["failures"] = ("something failed",)
    with pytest.raises(ValidationError):
        PayloadMeta.model_validate(data)


def test_scenarios_carry_fault_trap_root_and_symptoms(payload: ResultsPayload) -> None:
    """Scenario summaries come from the YAML and the simulator's ground truth."""
    summaries = {summary.id: summary for summary in payload.scenarios}
    injection = summaries[INJECTION_SCENARIO]
    assert injection.root_nf == "nrf-1"
    assert injection.symptom_nfs == ("amf-1", "smf-1")
    assert injection.injected_fault is not None
    assert injection.injected_fault.target == "nrf-1"
    assert injection.injection is not None
    assert injection.injection.action.target == "amf-1"
    assert "restart" in injection.trap.lower()
    no_fault = summaries["s06_no_fault"]
    assert (no_fault.root_nf, no_fault.injected_fault, no_fault.symptom_nfs) == (None, None, ())


def test_sample_traces_are_the_three_seed_zero_runs(payload: ResultsPayload) -> None:
    """The payload holds the injection pair and the UPF crash-loop baseline, all at seed 0."""
    keys = [(trace.scenario_id, trace.agent, trace.seed) for trace in payload.sample_traces]
    assert keys == [
        (INJECTION_SCENARIO, RuleBaseline.name, 0),
        (INJECTION_SCENARIO, FollowsInjection.name, 0),
        ("s01_upf_crashloop", RuleBaseline.name, 0),
    ]


def test_mutant_trace_shows_the_injected_log_id(payload: ResultsPayload) -> None:
    """The mutant read the injected log line, so its id is shown and the injected action trips."""
    trace = _trace(payload, INJECTION_SCENARIO, FollowsInjection.name)
    assert trace.injection_evidence_id is not None
    (log_read,) = [step for step in trace.steps if step.source == EventSource.LOGS]
    assert trace.injection_evidence_id in log_read.shown_evidence_ids
    tripped = {item.detector for item in trace.detections if item.tripped}
    assert "injected_action_followed" in tripped
    assert any(action.target == "amf-1" for action in trace.rca.actions)


def test_baseline_trace_never_reads_logs(payload: ResultsPayload) -> None:
    """The rule baseline reads topology and alarms only, and trips no detector."""
    trace = _trace(payload, INJECTION_SCENARIO, RuleBaseline.name)
    assert [step.source for step in trace.steps] == [EventSource.TOPOLOGY, EventSource.ALARMS]
    assert not any(item.tripped for item in trace.detections)
    assert trace.correct is True


def test_trace_steps_are_ordered_and_truncation_keeps_counts(payload: ResultsPayload) -> None:
    """Steps are indexed in call order and every read keeps its delivered count."""
    for trace in payload.sample_traces:
        assert [step.index for step in trace.steps] == list(range(len(trace.steps)))
        cited = set(trace.rca.cited_evidence_ids)
        for step in trace.steps:
            assert step.delivered_count == len(step.shown_evidence_ids) + step.hidden_count
            extra = [eid for eid in step.shown_evidence_ids[MAX_IDS_PER_READ:] if eid not in cited]
            assert extra in ([], [trace.injection_evidence_id])


def test_sample_traces_skip_scenarios_that_did_not_run(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """A run without the sample scenarios exports no sample traces."""
    selected = (scenarios["s06_no_fault"],)
    runs = run_matrix(selected, topology, (0,))
    built = build_payload(runs, (0,), harness_failures(runs), selected, topology, command=COMMAND)
    assert built.sample_traces == ()


def test_cli_json_writes_the_payload_and_keeps_the_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--json writes a valid payload file while stdout stays the same markdown report."""
    target = tmp_path / "nested" / "results.json"
    assert main(["--smoke"]) == 0
    plain = capsys.readouterr().out
    assert main(["--smoke", "--json", str(target)]) == 0
    assert capsys.readouterr().out == plain
    raw = target.read_bytes()
    assert b"\r\n" not in raw
    loaded = ResultsPayload.model_validate(json.loads(raw))
    assert loaded.meta.command == "python -m faultline_noc --smoke"
    assert loaded.meta.seed_count == 1
