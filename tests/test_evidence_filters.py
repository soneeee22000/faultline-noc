"""Tests for node-filtered reads, the run label and the unrecorded node lookup."""

from faultline_noc.evidence import EvidenceSession
from faultline_noc.scenario import Scenario
from faultline_noc.simulator import simulate
from faultline_noc.topology import Topology


def test_filtered_reads_deliver_only_that_nodes_ids(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """A node filter delivers and records only the ids from that node."""
    telemetry = simulate(scenarios["s01_upf_crashloop"], topology, seed=0).telemetry
    session = EvidenceSession(telemetry, topology)
    alarms = session.alarms("smf-1")
    kpis = session.kpis("upf-1")
    assert alarms and all(alarm.node == "smf-1" for alarm in alarms)
    assert kpis and all(kpi.node == "upf-1" for kpi in kpis)
    assert session.trace[0].evidence_ids == tuple(alarm.evidence_id for alarm in alarms)
    assert session.trace[1].evidence_ids == tuple(kpi.evidence_id for kpi in kpis)


def test_unfiltered_reads_are_unchanged(scenarios: dict[str, Scenario], topology: Topology) -> None:
    """Without a node, every record is delivered, as before."""
    telemetry = simulate(scenarios["s01_upf_crashloop"], topology, seed=0).telemetry
    session = EvidenceSession(telemetry, topology)
    assert session.logs() == telemetry.logs


def test_run_label_and_node_lookup_are_not_recorded(
    scenarios: dict[str, Scenario], topology: Topology
) -> None:
    """The run label and node lookup answer without adding trace events."""
    telemetry = simulate(scenarios["s07_log_injection"], topology, seed=3).telemetry
    session = EvidenceSession(telemetry, topology)
    assert session.run_label == ("s07_log_injection", 3)
    assert session.knows_node("nrf-1")
    assert not session.knows_node("mme-1")
    assert session.trace == ()
