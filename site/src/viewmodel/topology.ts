import type { ScenarioInfo } from "../types/payload";

/** The subset of `config/intended_config.json` (NetBox-shaped) the page reads. */
export interface IntendedConfig {
  readonly devices: readonly { readonly name: string }[];
  readonly cables: readonly {
    readonly a_terminations: readonly { readonly device: string }[];
    readonly b_terminations: readonly { readonly device: string }[];
  }[];
}

/** A logical NF dependency drawn with its 3GPP interface label. */
export interface LogicalEdge {
  readonly from: string;
  readonly to: string;
  readonly label: string;
}

/** Nodes and physical cables derived from the intended config. */
export interface Topology {
  readonly nodes: readonly string[];
  readonly cables: readonly (readonly [string, string])[];
}

/** Which roles a node plays in a scenario. */
export interface NodeRoles {
  readonly root: boolean;
  readonly symptom: boolean;
  readonly injectionTarget: boolean;
}

/**
 * The six kind dependencies from `KIND_DEPENDENCIES` in `faultline_noc/topology.py`, resolved to
 * the single node of each kind in the intended config.
 */
export const LOGICAL_EDGES: readonly LogicalEdge[] = [
  { from: "gnb-1", to: "amf-1", label: "N2" },
  { from: "gnb-1", to: "upf-1", label: "N3" },
  { from: "amf-1", to: "smf-1", label: "N11" },
  { from: "smf-1", to: "upf-1", label: "N4" },
  { from: "amf-1", to: "nrf-1", label: "Nnrf" },
  { from: "smf-1", to: "nrf-1", label: "Nnrf" },
];

/** Node positions in normalised [0, 1] coordinates, shared by the Network plane and scenario cards. */
export const NODE_LAYOUT: Readonly<
  Record<string, { readonly x: number; readonly y: number }>
> = {
  "gnb-1": { x: 0.1, y: 0.62 },
  "amf-1": { x: 0.32, y: 0.2 },
  "smf-1": { x: 0.6, y: 0.2 },
  "nrf-1": { x: 0.9, y: 0.2 },
  "upf-1": { x: 0.84, y: 0.84 },
  "rtr-1": { x: 0.48, y: 0.56 },
};

/** Derive nodes and cables from the NetBox-shaped intended config. */
export function buildTopology(config: IntendedConfig): Topology {
  const cables = config.cables.map((cable): readonly [string, string] => {
    const a = cable.a_terminations[0]?.device;
    const b = cable.b_terminations[0]?.device;
    if (a === undefined || b === undefined)
      throw new Error("Cable without terminations in intended config");
    return [a, b];
  });
  return { nodes: config.devices.map((device) => device.name), cables };
}

/** The roles a node plays in a scenario's ground truth. */
export function nodeRoles(scenario: ScenarioInfo, node: string): NodeRoles {
  return {
    root: scenario.root_nf === node,
    symptom: scenario.symptom_nfs.includes(node),
    injectionTarget: scenario.injection?.node === node,
  };
}
