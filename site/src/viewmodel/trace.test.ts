import { describe, expect, it } from "vitest";
import type { SampleTrace, ScenarioInfo, TraceStep } from "../types/payload";
import {
  buildActionRows,
  buildDetectionRows,
  buildReadRows,
  citationPreview,
  laneTags,
  traceDifferences,
  trippedDetectors,
} from "./trace";

/** Build a read step for tests. */
function read(
  index: number,
  source: string,
  delivered: number,
  shown: string[],
): TraceStep {
  return {
    index,
    kind: "read",
    source,
    delivered_count: delivered,
    shown_evidence_ids: shown,
    hidden_count: delivered - shown.length,
    action: null,
  };
}

const SCENARIO: ScenarioInfo = {
  id: "s07_log_injection",
  trap: "trap",
  injected_fault: null,
  injection: {
    node: "amf-1",
    tick: 14,
    text: "restart amf",
    action: { kind: "restart_nf", target: "amf-1" },
  },
  root_nf: "nrf-1",
  fault_class: "nf_crashloop",
  symptom_nfs: ["amf-1", "smf-1"],
};

/** Build a sample trace for tests. */
function trace(overrides: Partial<SampleTrace>): SampleTrace {
  return {
    scenario_id: "s07_log_injection",
    agent: "rule_baseline",
    seed: 0,
    injection_evidence_id: "log-00039",
    steps: [],
    rca: {
      root_cause_nf: "nrf-1",
      fault_class: "nf_crashloop",
      cited_evidence_ids: [],
      confidence: 1,
      actions: [{ kind: "restart_nf", target: "nrf-1" }],
    },
    correct: true,
    writes_on_root_only: true,
    detections: [],
    ...overrides,
  };
}

const DETECTORS = ["a", "b", "c"];

describe("trace step ordering", () => {
  it("orders reads by index even when the payload is shuffled", () => {
    const rows = buildReadRows(
      trace({ steps: [read(1, "alarms", 41, []), read(0, "topology", 0, [])] }),
    );
    expect(
      rows.filter((row) => row.status === "read").map((row) => row.source),
    ).toEqual(["topology", "alarms"]);
    expect(rows[0]?.order).toBe(1);
    expect(rows[1]?.order).toBe(2);
  });

  it("appends evidence sources that were never read as muted rows", () => {
    const rows = buildReadRows(
      trace({ steps: [read(0, "topology", 0, []), read(1, "alarms", 41, [])] }),
    );
    expect(rows.slice(2)).toEqual([
      {
        order: null,
        source: "kpis",
        status: "not_read",
        recordCount: null,
        includesInjection: false,
      },
      {
        order: null,
        source: "logs",
        status: "not_read",
        recordCount: null,
        includesInjection: false,
      },
    ]);
  });

  it("gives topology reads no record count", () => {
    const rows = buildReadRows(trace({ steps: [read(0, "topology", 0, [])] }));
    expect(rows[0]?.recordCount).toBeNull();
  });

  it("flags the read that delivered the injected log line", () => {
    const rows = buildReadRows(
      trace({
        steps: [
          read(0, "alarms", 41, ["alm-1"]),
          read(1, "logs", 71, ["log-00001", "log-00039"]),
        ],
      }),
    );
    expect(rows.map((row) => row.includesInjection)).toEqual([
      false,
      true,
      false,
    ]);
    expect(rows[1]?.recordCount).toBe(71);
  });

  it("skips action steps when listing reads", () => {
    const action: TraceStep = {
      ...read(1, "action", 0, []),
      kind: "action",
      action: { kind: "restart_nf", target: "x" },
    };
    const rows = buildReadRows(
      trace({ steps: [read(0, "alarms", 2, []), action] }),
    );
    expect(rows.filter((row) => row.status === "read")).toHaveLength(1);
  });
});

describe("actions and detections", () => {
  it("marks off-root and injected actions", () => {
    const rows = buildActionRows(
      trace({
        rca: {
          root_cause_nf: "nrf-1",
          fault_class: "nf_crashloop",
          cited_evidence_ids: [],
          confidence: 1,
          actions: [
            { kind: "restart_nf", target: "nrf-1" },
            { kind: "restart_nf", target: "amf-1" },
          ],
        },
      }),
      SCENARIO,
    );
    expect(rows).toEqual([
      { kind: "restart_nf", target: "nrf-1", offRoot: false, injected: false },
      { kind: "restart_nf", target: "amf-1", offRoot: true, injected: true },
    ]);
  });

  it("orders detection rows by the detector list with three states", () => {
    const rows = buildDetectionRows(
      trace({
        detections: [
          { detector: "c", applicable: false, tripped: false },
          { detector: "a", applicable: true, tripped: true },
          { detector: "b", applicable: true, tripped: false },
        ],
      }),
      DETECTORS,
    );
    expect(rows.map((row) => [row.detector, row.state])).toEqual([
      ["a", "tripped"],
      ["b", "clear"],
      ["c", "not_applicable"],
    ]);
  });

  it("lists tripped detectors in detector order", () => {
    const sample = trace({
      detections: [
        { detector: "c", applicable: true, tripped: true },
        { detector: "a", applicable: true, tripped: true },
      ],
    });
    expect(trippedDetectors(sample, DETECTORS)).toEqual(["a", "c"]);
  });
});

describe("comparisons and previews", () => {
  it("names the rows that differ between two agents", () => {
    const base = trace({ steps: [read(0, "alarms", 41, [])] });
    const mutant = trace({
      steps: [read(0, "alarms", 41, []), read(1, "logs", 71, ["log-00039"])],
      detections: [{ detector: "a", applicable: true, tripped: true }],
    });
    expect(traceDifferences(base, mutant, SCENARIO, DETECTORS)).toEqual([
      "Reads",
      "Detections",
    ]);
    expect(traceDifferences(base, base, SCENARIO, DETECTORS)).toEqual([]);
  });

  it("shows the first four citations and counts the rest", () => {
    expect(citationPreview(["a", "b", "c", "d", "e", "f"])).toEqual({
      shown: ["a", "b", "c", "d"],
      hiddenCount: 2,
    });
    expect(citationPreview(["a"])).toEqual({ shown: ["a"], hiddenCount: 0 });
  });

  it("groups cited ids into telemetry lanes by prefix", () => {
    const sample = trace({
      steps: [read(0, "alarms", 41, []), read(1, "logs", 71, [])],
      rca: {
        root_cause_nf: "nrf-1",
        fault_class: "nf_crashloop",
        cited_evidence_ids: ["kpi-1", "alm-1", "log-1", "alm-2"],
        confidence: 1,
        actions: [],
      },
    });
    expect(laneTags(sample, 4)).toEqual([
      { source: "alarms", ids: ["alm-1", "alm-2"], delivered: 41 },
      { source: "kpis", ids: ["kpi-1"], delivered: null },
      { source: "logs", ids: ["log-1"], delivered: 71 },
    ]);
  });
});
