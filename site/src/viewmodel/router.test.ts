import { describe, expect, it } from "vitest";
import routerResults from "../data/router_results.json";
import type {
  RouterDetectionCell,
  RouterMetrics,
  RouterOutcome,
  RouterResultsPayload,
} from "../types/payload";
import {
  ROUTER_HEADINGS,
  buildRouteFlow,
  buildRouterMatrix,
  countTagged,
  detectorsBeyondBaseline,
  eachMutantHasOneDetector,
  formatMetric,
  newTrips,
  routeAccuracyStats,
  routerHeadings,
  routersTiedWithBaseline,
} from "./router";

const BASELINE = "keyword_baseline";
const DETECTORS = ["misroute", "unsafe_write"] as const;
const EMPTY_PLAN = {
  steps: [],
  requires_clarification: true,
  clarification_question: "Which one?",
  confidence: 0.5,
};

function outcome(
  router: string,
  itemId: string,
  tripped: readonly string[],
): RouterOutcome {
  return {
    router,
    item_id: itemId,
    correct: tripped.length === 0,
    tripped,
    plan: EMPTY_PLAN,
  };
}

function metrics(
  router: string,
  correct: number,
  items: number,
): RouterMetrics {
  return {
    router,
    items,
    route_correct: correct,
    route_accuracy: correct / items,
    route_interval: { low: 0.2, high: 0.9 },
    macro_f1: 0.5,
    clarification_precision: null,
    clarification_recall: 1,
    handoff_completeness: 1,
    handoff_precision: 1,
    unsafe_write_gate_recall: 1,
    injection_resistance: 1,
    write_grant_recall: 1,
    brier: 0.1,
    ece: 0.1,
  };
}

const OUTCOMES: readonly RouterOutcome[] = [
  outcome(BASELINE, "r1", ["misroute"]),
  outcome(BASELINE, "r2", []),
  outcome("mutant_a", "r1", ["misroute"]),
  outcome("mutant_a", "r2", ["misroute"]),
  outcome("mutant_b", "r1", []),
  outcome("mutant_b", "r2", ["unsafe_write", "misroute"]),
];

describe("router headings", () => {
  it("heads the baseline row and the first mutant row only", () => {
    expect(
      routerHeadings([BASELINE, "mutant_a", "mutant_b"], BASELINE),
    ).toEqual([ROUTER_HEADINGS.baseline, ROUTER_HEADINGS.mutant, null]);
  });
});

describe("route accuracy stats", () => {
  it("maps route counts onto the shared rate stat", () => {
    const [stat] = routeAccuracyStats([metrics(BASELINE, 40, 52)]);
    expect(stat?.agent).toBe(BASELINE);
    expect(stat?.n).toBe(52);
    expect(stat?.rate).toBeCloseTo(40 / 52);
    expect([stat?.wilson_low, stat?.wilson_high]).toEqual([0.2, 0.9]);
  });
});

describe("trips beyond the baseline", () => {
  const trips = newTrips(OUTCOMES, BASELINE);

  it("ignores a trip the baseline shares on the same item", () => {
    expect(trips.get("mutant_a")?.get("misroute")).toBe(1);
  });

  it("counts every detector a mutant adds", () => {
    expect(detectorsBeyondBaseline(trips, "mutant_b", DETECTORS)).toEqual([
      "misroute",
      "unsafe_write",
    ]);
    expect(
      eachMutantHasOneDetector(trips, ["mutant_a", "mutant_b"], DETECTORS),
    ).toBe(false);
    expect(eachMutantHasOneDetector(trips, ["mutant_a"], DETECTORS)).toBe(true);
  });

  it("never reports the baseline against itself", () => {
    expect(trips.has(BASELINE)).toBe(false);
  });

  it("fails loudly when the baseline has no outcome for an item", () => {
    expect(() => newTrips([outcome("mutant_a", "r9", [])], BASELINE)).toThrow(
      /r9/,
    );
  });

  it("holds for the committed run: each mutant adds trips under one detector", () => {
    const payload: RouterResultsPayload = routerResults;
    const meta = payload.meta;
    const mutants = meta.routers.filter((router) => router !== meta.baseline);
    const committed = newTrips(payload.outcomes, meta.baseline);
    expect(eachMutantHasOneDetector(committed, mutants, meta.detectors)).toBe(
      true,
    );
  });
});

describe("router matrix", () => {
  const cells: RouterDetectionCell[] = [
    BASELINE,
    "mutant_a",
    "mutant_b",
  ].flatMap((router) =>
    DETECTORS.map((detector) => ({
      router,
      detector,
      tripped: 1,
      applicable: 2,
    })),
  );
  const view = buildRouterMatrix(
    cells,
    [BASELINE, "mutant_a", "mutant_b"],
    DETECTORS,
    BASELINE,
    OUTCOMES,
  );

  it("marks only cells with trips the baseline does not share", () => {
    const marks = view.rows.map((row) =>
      row.cells.map((cell) => cell.mark ?? null),
    );
    expect(marks).toEqual([
      [null, null],
      ["+1 new", null],
      ["+1 new", "+1 new"],
    ]);
  });

  it("describes a cell in items, not runs", () => {
    expect(view.rows[1]?.cells[0]?.description).toBe(
      "misroute tripped on 1 of 2 applicable items for mutant_a. On 1 of them the baseline does not trip it.",
    );
  });
});

describe("router formatting", () => {
  it("prints a missing denominator as n/a, not zero", () => {
    expect(formatMetric(null)).toBe("n/a");
    expect(formatMetric(0)).toBe("0.000");
    expect(formatMetric(0.769231)).toBe("0.769");
  });

  it("counts tagged items", () => {
    expect(
      countTagged(
        [{ tags: ["single", "injection"] }, { tags: ["multi"] }],
        "injection",
      ),
    ).toBe(1);
  });
});

describe("routers tied with the baseline", () => {
  it("names every router the route-accuracy chart cannot separate from the baseline", () => {
    const tied = routersTiedWithBaseline(
      [
        metrics(BASELINE, 40, 52),
        metrics("mutant_a", 40, 52),
        metrics("mutant_b", 19, 52),
      ],
      BASELINE,
    );
    expect(tied).toEqual(["mutant_a"]);
  });

  it("fails loudly when the baseline has no metrics row", () => {
    expect(() => routersTiedWithBaseline([metrics("mutant_a", 1, 2)], BASELINE))
      .toThrow(/keyword_baseline/);
  });

  it("holds for the committed run: two mutants score exactly the baseline", () => {
    const payload: RouterResultsPayload = routerResults;
    const tied = routersTiedWithBaseline(payload.metrics, payload.meta.baseline);
    expect(tied).toEqual(["mutant_drops_context", "mutant_ungated_write"]);
  });
});

describe("route flow", () => {
  const plan = {
    steps: [
      {
        agent: "incident",
        objective: "Roll back",
        context_refs: ["cluster:a", "nf:smf-1"],
        allowed_capabilities: ["read", "network_write"],
        requires_confirmation: true,
      },
      {
        agent: "testing",
        objective: "Rerun",
        context_refs: ["cluster:a", "test-suite:registration"],
        allowed_capabilities: ["read"],
        requires_confirmation: false,
      },
    ],
    requires_clarification: false,
    clarification_question: null,
    confidence: 0.72,
  };

  it("marks the write step and its gate", () => {
    const [first, second] = buildRouteFlow(plan, "network_write");
    expect(first?.writes).toBe(true);
    expect(first?.requiresConfirmation).toBe(true);
    expect(second?.writes).toBe(false);
  });

  it("carries only the refs the next step also holds, and nothing past the last step", () => {
    const [first, second] = buildRouteFlow(plan, "network_write");
    expect(first?.carried).toEqual(["cluster:a"]);
    expect(second?.carried).toEqual([]);
  });

  it("draws the committed plan the contract section shows", () => {
    const payload: RouterResultsPayload = routerResults;
    const outcome = payload.outcomes.find(
      (entry) =>
        entry.router === payload.meta.baseline &&
        entry.item_id === "r34_rollback_then_retest",
    );
    const steps = buildRouteFlow(outcome?.plan ?? EMPTY_PLAN, "network_write");
    expect(steps.map((step) => step.agent)).toEqual(["incident", "testing"]);
    expect(steps[0]?.carried).toEqual(["cluster:cluster-a"]);
  });
});
