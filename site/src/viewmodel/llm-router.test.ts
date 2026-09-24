import { describe, expect, it } from "vitest";
import routerLlmResults from "../data/router_llm_results.json";
import routerResults from "../data/router_results.json";
import type { LlmRouterPayload, RouterResultsPayload } from "../types/payload";
import {
  formatCost,
  itemStatus,
  modelMisses,
  modelRouterRows,
} from "./llm-router";

const payload: LlmRouterPayload = routerLlmResults;
const baseline: RouterResultsPayload = routerResults;

describe("modelRouterRows", () => {
  const rows = modelRouterRows(payload);

  it("gives one row per router, baseline first and free", () => {
    expect(rows.map((row) => row.router)).toEqual(payload.meta.routers);
    expect(rows[0]?.isBaseline).toBe(true);
    expect(rows[0]?.costUsd).toBe(0);
  });

  it("matches the baseline's committed router_results.json numbers", () => {
    const committed = baseline.metrics.find(
      (row) => row.router === payload.meta.baseline,
    );
    expect(rows[0]?.correct).toBe(committed?.route_correct);
    expect(rows[0]?.unsafeWrites).toBe(0);
  });

  it("adds each router's recorded costs up to the payload total", () => {
    const total = rows.reduce((sum, row) => sum + row.costUsd, 0);
    expect(total).toBeCloseTo(payload.meta.cost_usd, 5);
  });

  it("reports malformed counts straight from the payload meta", () => {
    for (const row of rows.filter((entry) => !entry.isBaseline)) {
      expect(row.malformed).toBe(payload.meta.malformed[row.router]);
    }
  });
});

describe("itemStatus", () => {
  it("ranks malformed over unsafe over wrong", () => {
    expect(
      itemStatus({ correct: false, tripped: ["unsafe_write"], malformed: "x" }),
    ).toBe("malformed");
    expect(itemStatus({ correct: false, tripped: ["unsafe_write"] })).toBe(
      "unsafe",
    );
    expect(itemStatus({ correct: false, tripped: ["misroute"] })).toBe("wrong");
    expect(itemStatus({ correct: true, tripped: [] })).toBe("correct");
  });

  it("never calls a malformed answer correct", () => {
    for (const outcome of payload.outcomes.filter(
      (entry) => entry.malformed !== null,
    )) {
      expect(outcome.correct).toBe(false);
      expect(outcome.plan).toBeNull();
    }
  });
});

describe("modelMisses", () => {
  const misses = modelMisses(payload, baseline.outcomes);

  it("lists exactly the items some model did not get right", () => {
    const expected = new Set(
      payload.outcomes
        .filter((outcome) => itemStatus(outcome) !== "correct")
        .map((o) => o.item_id),
    );
    expect(new Set(misses.map((miss) => miss.itemId))).toEqual(expected);
  });

  it("shows the baseline first, then each model", () => {
    for (const miss of misses) {
      expect(miss.statuses.map((entry) => entry.router)).toEqual(
        payload.meta.routers,
      );
    }
  });
});

describe("formatCost", () => {
  it("formats dollars to three decimals and the free baseline as $0", () => {
    expect(formatCost(0)).toBe("$0");
    expect(formatCost(0.119228)).toBe("$0.119");
  });
});
