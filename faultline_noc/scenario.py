"""YAML scenario schema: noise profile, injected fault, optional log injection, expected label."""

from pathlib import Path
from typing import Self

import yaml
from pydantic import Field, model_validator

from faultline_noc.models import Action, FaultClass, FrozenModel, check_root_matches_class
from faultline_noc.topology import Topology

PROBABILITY_MIN = 0.0
PROBABILITY_MAX = 1.0
SCENARIO_ID_PATTERN = r"^s\d{2}_[a-z0-9_]+$"


class NoiseSpec(FrozenModel):
    """Per-node, per-tick probabilities of background alarms and logs."""

    warning_alarm_rate: float = Field(ge=PROBABILITY_MIN, le=PROBABILITY_MAX)
    major_alarm_rate: float = Field(ge=PROBABILITY_MIN, le=PROBABILITY_MAX)
    info_log_rate: float = Field(ge=PROBABILITY_MIN, le=PROBABILITY_MAX)


class FaultSpec(FrozenModel):
    """A periodic fault: down for down_ticks at the start of every period, from start_tick."""

    kind: FaultClass
    target: str
    start_tick: int = Field(ge=0)
    period: int = Field(ge=1)
    down_ticks: int = Field(ge=1)

    @model_validator(mode="after")
    def _check_shape(self) -> Self:
        """Reject a no-fault class and a down time longer than the period."""
        if self.kind == FaultClass.INSUFFICIENT_EVIDENCE:
            raise ValueError("a fault cannot have class insufficient_evidence")
        if self.down_ticks > self.period:
            raise ValueError("down_ticks must not exceed period")
        return self

    def is_down(self, tick: int) -> bool:
        """Return True when the fault is active at the tick."""
        if tick < self.start_tick:
            return False
        return (tick - self.start_tick) % self.period < self.down_ticks

    def is_cycle_start(self, tick: int) -> bool:
        """Return True on the first down tick of each cycle."""
        return tick >= self.start_tick and (tick - self.start_tick) % self.period == 0


class InjectionSpec(FrozenModel):
    """Untrusted text written into a log line, and the action it tries to trigger."""

    node: str
    tick: int = Field(ge=0)
    text: str = Field(min_length=1)
    action: Action


class ExpectedLabel(FrozenModel):
    """The answer a correct RCA gives for the scenario."""

    root_cause_nf: str | None
    fault_class: FaultClass

    @model_validator(mode="after")
    def _root_matches_class(self) -> Self:
        """Reject a label whose root cause contradicts its fault class."""
        check_root_matches_class(self.root_cause_nf, self.fault_class)
        return self


class Scenario(FrozenModel):
    """A labelled scenario loaded from scenarios/*.yaml."""

    id: str = Field(pattern=SCENARIO_ID_PATTERN)
    title: str
    ticks: int = Field(ge=1)
    noise: NoiseSpec
    fault: FaultSpec | None = None
    injection: InjectionSpec | None = None
    expected: ExpectedLabel

    @model_validator(mode="after")
    def _events_inside_run(self) -> Self:
        """Reject a fault or injection scheduled after the last tick."""
        if self.fault is not None and self.fault.start_tick >= self.ticks:
            raise ValueError("fault.start_tick must be before the last tick")
        if self.injection is not None and self.injection.tick >= self.ticks:
            raise ValueError("injection.tick must be before the last tick")
        return self


def load_scenario(path: Path) -> Scenario:
    """Load one scenario file and check that its id matches the file name."""
    scenario = Scenario.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    if scenario.id != path.stem:
        raise ValueError(f"scenario id {scenario.id!r} does not match file {path.stem!r}")
    return scenario


def load_scenarios(directory: Path) -> tuple[Scenario, ...]:
    """Load every scenario in a directory, sorted by file name."""
    paths = sorted(directory.glob("*.yaml"))
    if not paths:
        raise FileNotFoundError(f"no scenario files in {directory}")
    return tuple(load_scenario(path) for path in paths)


def check_against_topology(scenario: Scenario, topology: Topology) -> None:
    """Raise ValueError if the scenario names unknown nodes or puts a fault on the wrong kind."""
    unknown = sorted(set(_referenced_nodes(scenario)) - set(topology.nodes))
    if unknown:
        raise ValueError(f"{scenario.id} references unknown nodes: {unknown}")
    if scenario.fault is not None:
        _check_fault_target(scenario.fault, topology)


def _referenced_nodes(scenario: Scenario) -> list[str]:
    """Return every node name the scenario mentions."""
    names = [scenario.expected.root_cause_nf]
    if scenario.fault is not None:
        names.append(scenario.fault.target)
    if scenario.injection is not None:
        names.extend((scenario.injection.node, scenario.injection.action.target))
    return [name for name in names if name is not None]


def _check_fault_target(fault: FaultSpec, topology: Topology) -> None:
    """Require transport flaps on the router and crash-loops on an NF."""
    on_router = fault.target == topology.router
    if fault.kind == FaultClass.TRANSPORT_FLAP and not on_router:
        raise ValueError(f"transport_flap must target the router {topology.router}")
    if fault.kind == FaultClass.NF_CRASHLOOP and on_router:
        raise ValueError("nf_crashloop must target an NF, not the router")
