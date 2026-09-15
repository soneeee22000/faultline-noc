"""Tests for the NetBox-shaped intended config and the NF dependency graph."""

import pytest

from faultline_noc.models import Interface, NodeKind
from faultline_noc.paths import DEFAULT_CONFIG_PATH
from faultline_noc.topology import Topology, build_topology, load_intended_config

EXPECTED_DEPENDENCIES = {
    ("gnb-1", "amf-1", Interface.N2),
    ("gnb-1", "upf-1", Interface.N3),
    ("amf-1", "smf-1", Interface.N11),
    ("smf-1", "upf-1", Interface.N4),
    ("amf-1", "nrf-1", Interface.NNRF),
    ("smf-1", "nrf-1", Interface.NNRF),
}


def test_intended_config_has_one_device_per_node_kind() -> None:
    """The lab config declares exactly one device of each node kind."""
    config = load_intended_config(DEFAULT_CONFIG_PATH)
    kinds = sorted(device.custom_fields.nf_kind for device in config.devices)
    assert kinds == sorted(NodeKind)


def test_dependencies_match_ts_23501_reference_points(topology: Topology) -> None:
    """The derived graph has the N2, N3, N4, N11 and Nnrf dependencies and nothing else."""
    actual = {(dep.consumer, dep.provider, dep.interface) for dep in topology.dependencies}
    assert actual == EXPECTED_DEPENDENCIES


def test_every_dependency_cites_a_spec_clause(topology: Topology) -> None:
    """Each dependency carries the TS 23.501 clause it was checked against."""
    assert all(dep.spec_clauses.startswith("TS 23.501") for dep in topology.dependencies)


def test_router_is_upstream_of_every_nf(topology: Topology) -> None:
    """Every NF's links cross the transport router."""
    for node in topology.node_names():
        if node != topology.router:
            assert topology.router in topology.upstream_of(node)


def test_router_has_nothing_upstream(topology: Topology) -> None:
    """The transport router depends on no modelled node."""
    assert topology.upstream_of(topology.router) == frozenset()


def test_dependents_of_upf_include_transitive_consumers(topology: Topology) -> None:
    """The SMF and gNB use the UPF directly, and the AMF does through the SMF."""
    assert topology.dependents_of("upf-1") == {"smf-1", "gnb-1", "amf-1"}


def test_dependents_of_router_are_all_other_nodes(topology: Topology) -> None:
    """Every NF depends on the transport router."""
    assert topology.dependents_of("rtr-1") == set(topology.nodes) - {"rtr-1"}


def test_uncabled_device_is_rejected() -> None:
    """A device with no cable to the router makes topology building fail."""
    config = load_intended_config(DEFAULT_CONFIG_PATH)
    cables = tuple(cable for cable in config.cables if "upf-1" not in cable.devices())
    with pytest.raises(ValueError, match="upf-1"):
        build_topology(config.model_copy(update={"cables": cables}))


def test_config_without_router_is_rejected() -> None:
    """A config with no transport router makes topology building fail."""
    config = load_intended_config(DEFAULT_CONFIG_PATH)
    devices = tuple(d for d in config.devices if d.custom_fields.nf_kind != NodeKind.ROUTER)
    with pytest.raises(ValueError, match="router"):
        build_topology(config.model_copy(update={"devices": devices}))


def test_cable_to_undeclared_interface_is_rejected() -> None:
    """A cable that terminates on an interface the config does not declare is rejected."""
    config = load_intended_config(DEFAULT_CONFIG_PATH)
    interfaces = tuple(i for i in config.interfaces if i.device.name != "nrf-1")
    with pytest.raises(ValueError, match="nrf-1"):
        build_topology(config.model_copy(update={"interfaces": interfaces}))
