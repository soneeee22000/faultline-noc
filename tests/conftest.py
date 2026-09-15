"""Shared pytest fixtures: the topology and the scenario set loaded from the repo."""

import pytest

from faultline_noc.paths import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_HARD_SCENARIOS_DIR,
    DEFAULT_SCENARIOS_DIR,
)
from faultline_noc.scenario import Scenario, load_scenarios
from faultline_noc.topology import Topology, build_topology, load_intended_config

SCENARIO_IDS = ("s01_upf_crashloop", "s05_transport_flap", "s06_no_fault", "s07_log_injection")
FAULTED_SCENARIO_IDS = ("s01_upf_crashloop", "s05_transport_flap", "s07_log_injection")
HARD_SCENARIO_IDS = ("s08_smf_crashloop_router_noise", "s09_upf_crashloop_silent")


@pytest.fixture(scope="session")
def topology() -> Topology:
    """Return the topology built from the repo's NetBox-shaped intended config."""
    return build_topology(load_intended_config(DEFAULT_CONFIG_PATH))


@pytest.fixture(scope="session")
def scenarios() -> dict[str, Scenario]:
    """Return every scenario in the repo keyed by scenario id."""
    return {scenario.id: scenario for scenario in load_scenarios(DEFAULT_SCENARIOS_DIR)}


@pytest.fixture(scope="session")
def hard_scenarios() -> dict[str, Scenario]:
    """Return the hard scenarios, which the published harness run does not include."""
    return {scenario.id: scenario for scenario in load_scenarios(DEFAULT_HARD_SCENARIOS_DIR)}
