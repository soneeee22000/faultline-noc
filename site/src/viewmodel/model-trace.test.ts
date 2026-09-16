import { describe, expect, it } from "vitest";
import type { SampleTrace } from "../types/payload";
import {
  detectorSentence,
  modelTraceSummary,
  readCount,
  verdictSentence,
} from "./model-trace";

const DETECTORS = ["symptom_blamed", "citation_unsupported"] as const;

function trace(
  agent: string,
  root: string | null,
  correct: boolean,
  confidence: number,
  sources: readonly string[],
  tripped: readonly string[],
): SampleTrace {
  return {
    scenario_id: "s08_smf_crashloop_router_noise",
    agent,
    seed: 0,
    injection_evidence_id: null,
    steps: sources.map((source, index) => ({
      index,
      kind: "read",
      source,
      delivered_count: 1,
      shown_evidence_ids: [],
      hidden_count: 0,
      action: null,
    })),
    rca: {
      root_cause_nf: root,
      fault_class: "nf_crashloop",
      cited_evidence_ids: [],
      confidence,
      actions: [],
    },
    correct,
    writes_on_root_only: true,
    detections: DETECTORS.map((detector) => ({
      detector,
      applicable: true,
      tripped: tripped.includes(detector),
    })),
  };
}

const BASELINE = trace(
  "rule_baseline",
  "rtr-1",
  false,
  1,
  ["topology", "alarms"],
  ["citation_unsupported"],
);
const SONNET = trace(
  "llm_sonnet_5",
  "smf-1",
  true,
  0.9,
  ["topology", "alarms", "logs", "kpis"],
  [],
);

describe("readCount", () => {
  it("counts the sources the agent actually read", () => {
    expect(readCount(BASELINE)).toBe(2);
    expect(readCount(SONNET)).toBe(4);
  });
});

describe("verdictSentence", () => {
  it("reports a wrong answer with the confidence it was given", () => {
    const sentence = verdictSentence(BASELINE);
    expect(sentence).toContain("confidence 1.00");
    expect(sentence).toContain("does not match ground truth");
  });

  it("reports a correct answer as matching", () => {
    expect(verdictSentence(SONNET)).toContain("which matches ground truth");
  });

  it("names the absence of a root cause rather than printing null", () => {
    const quiet = trace("llm_haiku_4_5", null, false, 0, ["alarms"], []);
    expect(verdictSentence(quiet)).toContain("no root cause");
  });
});

describe("detectorSentence", () => {
  it("lists the detectors that fired", () => {
    expect(detectorSentence(BASELINE, DETECTORS)).toContain(
      "citation_unsupported",
    );
  });

  it("says so plainly when none fired", () => {
    expect(detectorSentence(SONNET, DETECTORS)).toBe(
      "No detector fired on `llm_sonnet_5`.",
    );
  });
});

describe("modelTraceSummary", () => {
  it("never claims the agents are mocks, because one of them is a model", () => {
    const summary = modelTraceSummary(BASELINE, SONNET, DETECTORS);
    expect(summary).not.toContain("mock");
    expect(summary).toContain("replayed from the committed responses");
  });

  it("covers both agents", () => {
    const summary = modelTraceSummary(BASELINE, SONNET, DETECTORS);
    expect(summary).toContain("rule_baseline");
    expect(summary).toContain("llm_sonnet_5");
  });
});
