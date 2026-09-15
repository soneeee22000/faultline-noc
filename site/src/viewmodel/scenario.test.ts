import { describe, expect, it } from "vitest";
import type { ScenarioInfo } from "../types/payload";
import { nfLabel, scenarioTitle, shortScenarioId } from "./scenario";

/** Build a scenario for tests. */
function scenario(overrides: Partial<ScenarioInfo>): ScenarioInfo {
  return {
    id: "s01_upf_crashloop",
    trap: "t",
    injected_fault: {
      kind: "nf_crashloop",
      target: "upf-1",
      start_tick: 8,
      period: 4,
      down_ticks: 2,
    },
    injection: null,
    root_nf: "upf-1",
    fault_class: "nf_crashloop",
    symptom_nfs: [],
    ...overrides,
  };
}

describe("scenario titles", () => {
  it("names the NF kind from the node name", () => {
    expect(nfLabel("upf-1")).toBe("UPF");
    expect(nfLabel("gnb-1")).toBe("gNB");
    expect(nfLabel("rtr-1")).toBe("Router");
    expect(nfLabel("xyz-9")).toBe("xyz-9");
  });

  it("titles a fault by NF kind and fault kind", () => {
    expect(scenarioTitle(scenario({}))).toBe("UPF crash-loop");
    expect(
      scenarioTitle(
        scenario({
          injected_fault: {
            kind: "transport_flap",
            target: "rtr-1",
            start_tick: 1,
            period: 5,
            down_ticks: 1,
          },
        }),
      ),
    ).toBe("Router transport flap");
  });

  it("titles the control scenario and the injection scenario", () => {
    expect(scenarioTitle(scenario({ injected_fault: null }))).toBe(
      "No-fault control",
    );
    const injection = {
      node: "amf-1",
      tick: 14,
      text: "x",
      action: { kind: "restart_nf", target: "amf-1" },
    };
    expect(
      scenarioTitle(
        scenario({
          injected_fault: {
            kind: "nf_crashloop",
            target: "nrf-1",
            start_tick: 6,
            period: 6,
            down_ticks: 2,
          },
          injection,
        }),
      ),
    ).toBe("NRF crash-loop with log injection");
  });

  it("shortens scenario ids to their numeric prefix", () => {
    expect(shortScenarioId("s07_log_injection")).toBe("s07");
  });
});
