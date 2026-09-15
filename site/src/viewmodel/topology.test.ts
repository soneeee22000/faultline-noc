import { describe, expect, it } from "vitest";
import config from "../../../config/intended_config.json";
import type { ScenarioInfo } from "../types/payload";
import {
  LOGICAL_EDGES,
  NODE_LAYOUT,
  buildTopology,
  nodeRoles,
} from "./topology";

describe("topology from the intended config", () => {
  const topology = buildTopology(config);

  it("reads every device from the config", () => {
    expect(topology.nodes).toEqual([
      "gnb-1",
      "amf-1",
      "smf-1",
      "upf-1",
      "nrf-1",
      "rtr-1",
    ]);
  });

  it("derives one cable per config cable, each terminating on the router", () => {
    expect(topology.cables).toHaveLength(config.cables.length);
    expect(
      topology.cables.every(([a, b]) => a === "rtr-1" || b === "rtr-1"),
    ).toBe(true);
  });

  it("only draws dependency edges between nodes that exist in the config", () => {
    const names = new Set(topology.nodes);
    for (const edge of LOGICAL_EDGES) {
      expect(names.has(edge.from)).toBe(true);
      expect(names.has(edge.to)).toBe(true);
    }
  });

  it("mirrors the six kind dependencies of faultline_noc/topology.py", () => {
    expect(
      LOGICAL_EDGES.map((edge) => `${edge.from}>${edge.to}:${edge.label}`),
    ).toEqual([
      "gnb-1>amf-1:N2",
      "gnb-1>upf-1:N3",
      "amf-1>smf-1:N11",
      "smf-1>upf-1:N4",
      "amf-1>nrf-1:Nnrf",
      "smf-1>nrf-1:Nnrf",
    ]);
  });

  it("has a layout position for every node", () => {
    for (const node of topology.nodes) {
      expect(NODE_LAYOUT[node]).toBeDefined();
    }
  });
});

describe("nodeRoles", () => {
  const scenario: ScenarioInfo = {
    id: "s07_log_injection",
    trap: "t",
    injected_fault: null,
    injection: {
      node: "amf-1",
      tick: 1,
      text: "x",
      action: { kind: "restart_nf", target: "amf-1" },
    },
    root_nf: "nrf-1",
    fault_class: "nf_crashloop",
    symptom_nfs: ["amf-1", "smf-1"],
  };

  it("marks root, symptom and injection target independently", () => {
    expect(nodeRoles(scenario, "nrf-1")).toEqual({
      root: true,
      symptom: false,
      injectionTarget: false,
    });
    expect(nodeRoles(scenario, "amf-1")).toEqual({
      root: false,
      symptom: true,
      injectionTarget: true,
    });
    expect(nodeRoles(scenario, "upf-1")).toEqual({
      root: false,
      symptom: false,
      injectionTarget: false,
    });
  });
});
