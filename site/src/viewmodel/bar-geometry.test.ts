import { describe, expect, it } from "vitest";
import type { RateStat } from "../types/payload";
import { barGeometry, chartSummary } from "./bar-geometry";
import { buildBarRows } from "./bars";

/** Build a rate stat for tests. */
function stat(agent: string, correct: number, n: number): RateStat {
  return {
    agent,
    scope: "all",
    correct,
    n,
    rate: correct / n,
    wilson_low: 0.221237,
    wilson_high: 0.281152,
  };
}

describe("bar geometry", () => {
  it("converts a rate and its Wilson interval to percentages of the track", () => {
    expect(barGeometry(0.25, 0.221237, 0.281152)).toEqual({
      barPercent: 25,
      squarePercent: 12.5,
      lowPercent: 22.1,
      highPercent: 28.1,
      isZero: false,
    });
  });

  it("flags a zero rate so the renderer draws a stub", () => {
    expect(barGeometry(0, 0, 0.004779)).toEqual({
      barPercent: 0,
      squarePercent: 0,
      lowPercent: 0,
      highPercent: 0.5,
      isZero: true,
    });
  });

  it("keeps a full bar inside the track", () => {
    expect(barGeometry(1, 0.995221, 1).highPercent).toBe(100);
  });

  it("rejects an interval that does not contain the rate", () => {
    expect(() => barGeometry(0.5, 0.6, 0.7)).toThrow(/interval/);
  });
});

describe("chart summary", () => {
  const order = ["rule_baseline", "oracle", "mutant_blames_symptom"];

  it("counts perfect scores and names the lowest agent", () => {
    const rows = buildBarRows(
      [
        stat("rule_baseline", 800, 800),
        stat("oracle", 800, 800),
        stat("mutant_blames_symptom", 200, 800),
      ],
      order,
    );
    expect(chartSummary(rows)).toBe(
      "2 of 3 agents score 1.000. Lowest: `mutant_blames_symptom` at 0.250.",
    );
  });

  it("joins agents that tie for the lowest score", () => {
    const rows = buildBarRows(
      [
        stat("rule_baseline", 800, 800),
        stat("oracle", 600, 800),
        stat("mutant_blames_symptom", 600, 800),
      ],
      order,
    );
    expect(chartSummary(rows)).toBe(
      "1 of 3 agents score 1.000. Lowest: `oracle` and `mutant_blames_symptom` at 0.750.",
    );
  });

  it("says so when every agent has the same score", () => {
    const rows = buildBarRows(
      order.map((agent) => stat(agent, 800, 800)),
      order,
    );
    expect(chartSummary(rows)).toBe("All 3 agents score 1.000.");
  });
});
