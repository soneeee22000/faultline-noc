import { describe, expect, it } from "vitest";
import type { RateStat } from "../types/payload";
import { GROUP_HEADINGS } from "./agents";
import { AXIS_TICKS, buildBarRows, scenarioBreakdown } from "./bars";

/** Build a rate stat for tests. */
function stat(
  agent: string,
  scope: string,
  correct: number,
  n: number,
): RateStat {
  return {
    agent,
    scope,
    correct,
    n,
    rate: correct / n,
    wilson_low: 0.1,
    wilson_high: 0.9,
  };
}

describe("buildBarRows", () => {
  const stats = [
    stat("mutant_blames_symptom", "all", 200, 800),
    stat("rule_baseline", "all", 800, 800),
    stat("oracle", "all", 800, 800),
    stat("mutant_restarts_bystander", "all", 0, 800),
  ];
  const order = [
    "rule_baseline",
    "oracle",
    "mutant_blames_symptom",
    "mutant_restarts_bystander",
  ];

  it("keeps the report order instead of sorting by value", () => {
    expect(buildBarRows(stats, order).map((row) => row.agent)).toEqual(order);
  });

  it("heads each agent group once, so the baseline is never grouped with the truth-aware agents", () => {
    const rows = buildBarRows(stats, order);
    expect(rows.map((row) => row.groupHeading)).toEqual([
      GROUP_HEADINGS.evaluated,
      GROUP_HEADINGS.reference,
      GROUP_HEADINGS.mutant,
      null,
    ]);
  });

  it("carries report-formatted labels", () => {
    const row = buildBarRows(stats, order)[2];
    expect(row?.countLabel).toBe("200 / 800");
    expect(row?.rateLabel).toBe("0.250");
    expect(row?.intervalLabel).toBe("[0.100, 0.900]");
  });

  it("flags a zero rate so it draws a stub rather than nothing", () => {
    expect(buildBarRows(stats, order)[3]?.isZero).toBe(true);
    expect(buildBarRows(stats, order)[0]?.isZero).toBe(false);
  });

  it("throws when an agent has no stat", () => {
    expect(() => buildBarRows(stats, [...order, "ghost"])).toThrow(/ghost/);
  });

  it("uses quarter ticks from zero to one", () => {
    expect(AXIS_TICKS).toEqual([0, 0.25, 0.5, 0.75, 1]);
  });
});

describe("scenarioBreakdown", () => {
  it("lists one line per scenario in scenario order", () => {
    const perScenario = [
      stat("rule_baseline", "s05", 200, 200),
      stat("rule_baseline", "s01", 199, 200),
      stat("oracle", "s01", 200, 200),
    ];
    expect(
      scenarioBreakdown(perScenario, "rule_baseline", ["s01", "s05"]),
    ).toEqual(["s01 199/200", "s05 200/200"]);
  });
});
