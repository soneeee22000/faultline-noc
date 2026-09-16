import { describe, expect, it } from "vitest";
import type { LlmAccuracyRow, LlmResultsPayload } from "../types/payload";
import {
  buildScenarioGrid,
  cellState,
  costRows,
  formatThousands,
  formatUsd,
  modelRunCount,
  toRateStat,
  totalSpend,
} from "./llm";

/** The float the Wilson bound actually carries for a 0/3 score in the committed payload. */
const ZERO_LOW = 5.551115123125783e-17;

function row(
  agent: string,
  scope: string,
  correct: number,
  total: number,
  low = 0,
  high = 1,
): LlmAccuracyRow {
  return { agent, scope, correct, total, interval: { low, high } };
}

describe("toRateStat", () => {
  it("renames total to n and flattens the interval", () => {
    const stat = toRateStat(row("llm_sonnet_5", "all", 17, 18, 0.74, 0.99));
    expect(stat.n).toBe(18);
    expect(stat.rate).toBeCloseTo(17 / 18);
    expect([stat.wilson_low, stat.wilson_high]).toEqual([0.74, 0.99]);
  });

  it("pulls a floating-point bound back onto a zero rate, so the bar geometry accepts it", () => {
    const stat = toRateStat(row("rule_baseline", "s08", 0, 3, ZERO_LOW, 0.56));
    expect(stat.rate).toBe(0);
    expect(stat.wilson_low).toBe(0);
    expect(stat.wilson_low).toBeLessThanOrEqual(stat.rate);
  });

  it("pulls a floating-point bound back onto a perfect rate", () => {
    const stat = toRateStat(row("llm_sonnet_5", "s01", 3, 3, 0.43, 1 - 1e-17));
    expect(stat.wilson_high).toBe(1);
  });

  it("throws on a row covering no runs", () => {
    expect(() => toRateStat(row("ghost", "all", 0, 0))).toThrow(/no runs/);
  });
});

describe("cellState", () => {
  it("separates a clean sweep, a partial score and a total miss", () => {
    expect(cellState(3, 3)).toBe("pass");
    expect(cellState(2, 3)).toBe("partial");
    expect(cellState(0, 3)).toBe("fail");
  });
});

describe("buildScenarioGrid", () => {
  const rows = [
    row("rule_baseline", "s01", 3, 3),
    row("rule_baseline", "s08", 0, 3),
    row("llm_sonnet_5", "s01", 3, 3),
    row("llm_sonnet_5", "s08", 3, 3),
  ];

  it("keeps the given agent and scenario order rather than sorting", () => {
    const grid = buildScenarioGrid(
      rows,
      ["llm_sonnet_5", "rule_baseline"],
      ["s08", "s01"],
    );
    expect(grid[0]?.[0]?.agent).toBe("llm_sonnet_5");
    expect(grid[1]?.[0]?.scenario).toBe("s08");
  });

  it("labels each cell as a count and marks the baseline's miss", () => {
    const grid = buildScenarioGrid(rows, ["rule_baseline"], ["s08"]);
    expect(grid[0]?.[0]?.label).toBe("0 / 3");
    expect(grid[0]?.[0]?.state).toBe("fail");
  });

  it("throws when a pair has no score", () => {
    expect(() => buildScenarioGrid(rows, ["rule_baseline"], ["s99"])).toThrow(
      /s99/,
    );
  });
});

describe("formatThousands", () => {
  it("groups digits in threes", () => {
    expect(formatThousands(291768)).toBe("291,768");
    expect(formatThousands(999)).toBe("999");
    expect(formatThousands(1000)).toBe("1,000");
    expect(formatThousands(0)).toBe("0");
  });

  it("throws on a value that is not a whole count", () => {
    expect(() => formatThousands(1.5)).toThrow(RangeError);
  });
});

describe("cost", () => {
  const payload = {
    models: ["claude-haiku-4-5", "claude-sonnet-5"],
    scenarios: ["s01", "s05", "s06", "s07", "s08", "s09"],
    seeds: [0, 1, 2],
    spend_usd: { "claude-haiku-4-5": 0.3339, "claude-sonnet-5": 0.4087 },
    tokens: {
      "claude-haiku-4-5": { input: 291768, output: 18289 },
      "claude-sonnet-5": { input: 275667, output: 15302 },
    },
  } as unknown as LlmResultsPayload;

  it("formats dollars at the report's precision", () => {
    expect(formatUsd(0.3339)).toBe("$0.3339");
  });

  it("joins each model to the agent it is reported under", () => {
    expect(costRows(payload).map((item) => item.agent)).toEqual([
      "llm_haiku_4_5",
      "llm_sonnet_5",
    ]);
    expect(costRows(payload)[0]?.input).toBe("291,768");
  });

  it("totals the recorded spend", () => {
    expect(totalSpend(payload)).toBe("$0.7426");
  });

  it("counts only the runs that called a model", () => {
    expect(modelRunCount(payload)).toBe(36);
  });
});
