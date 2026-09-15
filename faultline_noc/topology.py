"""NetBox-shaped intended config and the NF dependency graph derived from it."""

from collections import deque
from pathlib import Path

from faultline_noc.models import FrozenModel, Interface, NodeKind

ACTIVE_CABLE_STATUS = "connected"

KIND_DEPENDENCIES: tuple[tuple[NodeKind, NodeKind, Interface, str], ...] = (
    (NodeKind.GNB, NodeKind.AMF, Interface.N2, "TS 23.501 4.2.7"),
    (NodeKind.GNB, NodeKind.UPF, Interface.N3, "TS 23.501 4.2.7"),
    (NodeKind.AMF, NodeKind.SMF, Interface.N11, "TS 23.501 4.2.7"),
    (NodeKind.SMF, NodeKind.UPF, Interface.N4, "TS 23.501 4.2.7, 6.3.3.2; TS 29.244 1"),
    (NodeKind.AMF, NodeKind.NRF, Interface.NNRF, "TS 23.501 4.2.6, 6.3.1, 6.3.2"),
    (NodeKind.SMF, NodeKind.NRF, Interface.NNRF, "TS 23.501 4.2.6, 6.3.1"),
)


class SlugRef(FrozenModel):
    """NetBox nested reference by slug."""

    slug: str


class StatusRef(FrozenModel):
    """NetBox status object."""

    value: str


class DeviceCustomFields(FrozenModel):
    """Custom fields this project adds to a NetBox device."""

    nf_kind: NodeKind


class Device(FrozenModel):
    """Subset of a NetBox dcim/devices record."""

    id: int
    name: str
    role: SlugRef
    site: SlugRef
    status: StatusRef
    custom_fields: DeviceCustomFields


class DeviceRef(FrozenModel):
    """NetBox nested reference to a device by name."""

    name: str


class InterfaceRecord(FrozenModel):
    """Subset of a NetBox dcim/interfaces record."""

    id: int
    device: DeviceRef
    name: str
    enabled: bool


class Termination(FrozenModel):
    """One end of a cable: a device and one of its interfaces."""

    device: str
    interface: str


class Cable(FrozenModel):
    """Subset of a NetBox dcim/cables record."""

    id: int
    a_terminations: tuple[Termination, ...]
    b_terminations: tuple[Termination, ...]
    status: StatusRef

    def terminations(self) -> tuple[Termination, ...]:
        """Return both ends of the cable."""
        return (*self.a_terminations, *self.b_terminations)

    def devices(self) -> frozenset[str]:
        """Return the names of the devices the cable connects."""
        return frozenset(end.device for end in self.terminations())


class IntendedConfig(FrozenModel):
    """The intended state of the lab, shaped like a NetBox export."""

    source_note: str
    devices: tuple[Device, ...]
    interfaces: tuple[InterfaceRecord, ...]
    cables: tuple[Cable, ...]


class Dependency(FrozenModel):
    """A consumer NF that needs a provider NF over an interface."""

    consumer: str
    provider: str
    interface: Interface
    spec_clauses: str


class Topology(FrozenModel):
    """Nodes, the single transport router every link crosses, and NF dependencies."""

    nodes: dict[str, NodeKind]
    router: str
    dependencies: tuple[Dependency, ...]

    def node_names(self) -> tuple[str, ...]:
        """Return node names in sorted order."""
        return tuple(sorted(self.nodes))

    def providers_of(self, node: str) -> frozenset[str]:
        """Return the NFs a node consumes directly."""
        return frozenset(dep.provider for dep in self.dependencies if dep.consumer == node)

    def upstream_of(self, node: str) -> frozenset[str]:
        """Return the providers a node needs plus the router its links cross."""
        if node == self.router:
            return frozenset()
        return self.providers_of(node) | {self.router}

    def dependents_of(self, node: str) -> frozenset[str]:
        """Return every node that depends on this one, directly or transitively."""
        if node == self.router:
            return frozenset(self.nodes) - {self.router}
        found: set[str] = set()
        queue = deque([node])
        while queue:
            current = queue.popleft()
            for dep in self.dependencies:
                if dep.provider == current and dep.consumer not in found:
                    found.add(dep.consumer)
                    queue.append(dep.consumer)
        return frozenset(found)


def load_intended_config(path: Path) -> IntendedConfig:
    """Load and validate the NetBox-shaped intended config JSON."""
    return IntendedConfig.model_validate_json(path.read_text(encoding="utf-8"))


def build_topology(config: IntendedConfig) -> Topology:
    """Build the dependency graph, checking that the config's cabling supports it."""
    nodes = {device.name: device.custom_fields.nf_kind for device in config.devices}
    router = _single_router(nodes)
    _require_declared_interfaces(config)
    _require_router_links(config, nodes, router)
    return Topology(nodes=nodes, router=router, dependencies=_dependencies(nodes))


def _single_router(nodes: dict[str, NodeKind]) -> str:
    """Return the one transport router, or raise if there is not exactly one."""
    routers = [name for name, kind in nodes.items() if kind == NodeKind.ROUTER]
    if len(routers) != 1:
        raise ValueError(f"expected exactly one transport router, found {len(routers)}")
    return routers[0]


def _require_declared_interfaces(config: IntendedConfig) -> None:
    """Raise if a cable terminates on an interface the config does not declare."""
    declared = {(item.device.name, item.name) for item in config.interfaces}
    undeclared = sorted(
        f"{end.device}:{end.interface}"
        for cable in config.cables
        for end in cable.terminations()
        if (end.device, end.interface) not in declared
    )
    if undeclared:
        raise ValueError(f"cables terminate on undeclared interfaces: {undeclared}")


def _require_router_links(config: IntendedConfig, nodes: dict[str, NodeKind], router: str) -> None:
    """Raise if any NF lacks a connected cable to the transport router."""
    cabled: set[str] = set()
    for cable in config.cables:
        if cable.status.value == ACTIVE_CABLE_STATUS and router in cable.devices():
            cabled |= cable.devices() - {router}
    missing = sorted(set(nodes) - {router} - cabled)
    if missing:
        raise ValueError(f"not cabled to transport router {router}: {missing}")


def _dependencies(nodes: dict[str, NodeKind]) -> tuple[Dependency, ...]:
    """Instantiate the kind-level dependency table for the nodes present."""
    by_kind: dict[NodeKind, list[str]] = {}
    for name in sorted(nodes):
        by_kind.setdefault(nodes[name], []).append(name)
    return tuple(
        Dependency(consumer=consumer, provider=provider, interface=interface, spec_clauses=clauses)
        for consumer_kind, provider_kind, interface, clauses in KIND_DEPENDENCIES
        for consumer in by_kind.get(consumer_kind, [])
        for provider in by_kind.get(provider_kind, [])
    )
