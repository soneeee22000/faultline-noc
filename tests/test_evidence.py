"""Tests for the evidence session that records what an agent read and did."""

from faultline_noc.evidence import EventKind, EventSource, EvidenceSession
from faultline_noc.models import Action, ActionKind
from faultline_noc.scenario import Scenario
from faultline_noc.simulator import simulate
from faultline_noc.topology import Topology


def _session(scenarios: dict[str, Scenario], topology: Topology) -> EvidenceSession:
    """Build a session over s01 seed 0."""
    telemetry = simulate(scenarios["s01_upf_crashloop"], topology, seed=0).telemetry
    return EvidenceSession(telemetry, topology)


def test_session_records_reads_in_call_order(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """Reads appear in the trace in the order they were made, with the ids delivered."""
    session = _session(scenarios, topology)
    session.topology()
    alarms = session.alarms()
    session.logs()
    sources = [event.source for event in session.trace]
    assert sources == [EventSource.TOPOLOGY, EventSource.ALARMS, EventSource.LOGS]
    assert session.trace[1].evidence_ids == tuple(alarm.evidence_id for alarm in alarms)


def test_topology_read_does_not_count_as_gathering_evidence(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """Reading the topology is not evidence; reading KPIs is."""
    session = _session(scenarios, topology)
    session.topology()
    session.kpis()
    assert not session.trace[0].gathers_evidence
    assert session.trace[1].gathers_evidence


def test_execute_records_the_action(scenarios: dict[str, Scenario], topology: Topology) -> None:
    """A requested restart is recorded as a write action event."""
    session = _session(scenarios, topology)
    action = Action(kind=ActionKind.RESTART_NF, target="upf-1")
    session.execute(action)
    event = session.trace[-1]
    assert event.kind == EventKind.ACTION
    assert event.action == action
    assert event.is_write
    assert session.seen_evidence_ids() == frozenset()


def test_ticket_is_not_a_write(scenarios: dict[str, Scenario], topology: Topology) -> None:
    """Opening a ticket is recorded but does not count as a write."""
    session = _session(scenarios, topology)
    session.execute(Action(kind=ActionKind.OPEN_TICKET, target="rtr-1"))
    assert not session.trace[-1].is_write
