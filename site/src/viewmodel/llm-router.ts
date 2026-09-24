import type {
  LlmRouterOutcome,
  LlmRouterPayload,
  RouterDetectionCell,
  RouterOutcome,
} from "../types/payload";

const UNSAFE_WRITE = "unsafe_write";

/** One row of the model-router comparison. */
export interface ModelRouterRow {
  readonly router: string;
  readonly isBaseline: boolean;
  readonly correct: number;
  readonly items: number;
  readonly low: number;
  readonly high: number;
  readonly unsafeWrites: number;
  readonly malformed: number;
  readonly injection: number | null;
  readonly brier: number;
  readonly costUsd: number;
}

/** How one router did on one item. */
export type ItemStatus = "correct" | "wrong" | "malformed" | "unsafe";

/** An item that at least one model router got wrong, with every router's status on it. */
export interface ModelMiss {
  readonly itemId: string;
  readonly statuses: readonly {
    readonly router: string;
    readonly status: ItemStatus;
  }[];
}

/** Items tripped by `unsafe_write` for one router, or a loud failure when the cell is missing. */
function unsafeWrites(
  cells: readonly RouterDetectionCell[],
  router: string,
): number {
  const cell = cells.find(
    (entry) => entry.router === router && entry.detector === UNSAFE_WRITE,
  );
  if (cell === undefined)
    throw new Error(
      `No ${UNSAFE_WRITE} cell for ${router} in router_llm_results.json`,
    );
  return cell.tripped;
}

/** Total recorded cost for one router's outcomes; the baseline costs nothing. */
function routerCost(
  outcomes: readonly LlmRouterOutcome[],
  router: string,
): number {
  return outcomes
    .filter((outcome) => outcome.router === router)
    .reduce((total, outcome) => total + outcome.cost_usd, 0);
}

/** One row per router in payload order, baseline first. */
export function modelRouterRows(
  payload: LlmRouterPayload,
): readonly ModelRouterRow[] {
  return payload.metrics.map((metrics) => ({
    router: metrics.router,
    isBaseline: metrics.router === payload.meta.baseline,
    correct: metrics.route_correct,
    items: metrics.items,
    low: metrics.route_interval.low,
    high: metrics.route_interval.high,
    unsafeWrites: unsafeWrites(payload.detection_matrix, metrics.router),
    malformed: payload.meta.malformed[metrics.router] ?? 0,
    injection: metrics.injection_resistance,
    brier: metrics.brier,
    costUsd: routerCost(payload.outcomes, metrics.router),
  }));
}

/** The status of one outcome: malformed and unsafe outrank a plain wrong answer. */
export function itemStatus(outcome: {
  readonly correct: boolean;
  readonly tripped: readonly string[];
  readonly malformed?: string | null;
}): ItemStatus {
  if (outcome.malformed) return "malformed";
  if (outcome.tripped.includes(UNSAFE_WRITE)) return "unsafe";
  return outcome.correct ? "correct" : "wrong";
}

/** Every item a model router did not get right, with the baseline's status beside it. */
export function modelMisses(
  payload: LlmRouterPayload,
  baselineOutcomes: readonly RouterOutcome[],
): readonly ModelMiss[] {
  const models = payload.meta.routers.filter(
    (router) => router !== payload.meta.baseline,
  );
  const missed = [
    ...new Set(
      payload.outcomes
        .filter((outcome) => itemStatus(outcome) !== "correct")
        .map((outcome) => outcome.item_id),
    ),
  ];
  return missed.map((itemId) => {
    const baseline = baselineOutcomes.find(
      (outcome) =>
        outcome.router === payload.meta.baseline && outcome.item_id === itemId,
    );
    if (baseline === undefined)
      throw new Error(
        `Baseline outcome for ${itemId} missing from router_results.json`,
      );
    const rest = models.map((router) => {
      const outcome = payload.outcomes.find(
        (entry) => entry.router === router && entry.item_id === itemId,
      );
      if (outcome === undefined)
        throw new Error(
          `Outcome ${router}/${itemId} missing from router_llm_results.json`,
        );
      return { router, status: itemStatus(outcome) };
    });
    return {
      itemId,
      statuses: [
        { router: payload.meta.baseline, status: itemStatus(baseline) },
        ...rest,
      ],
    };
  });
}

/** Format a recorded cost in dollars, e.g. `$0.119`; the baseline shows `$0`. */
export function formatCost(costUsd: number): string {
  if (costUsd === 0) return "$0";
  return `$${costUsd.toFixed(3)}`;
}
