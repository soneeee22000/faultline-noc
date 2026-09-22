import type {
  DetectionCell,
  LlmAccuracyRow,
  RateStat,
  RoutePlanView,
  RouterDetectionCell,
  RouterMetrics,
  RouterOutcome,
} from "../types/payload";
import { formatRate } from "./format";
import { toRateStats } from "./llm";
import { type MatrixCellView, type MatrixView, buildMatrix } from "./matrix";

/** Row-group headings for the router charts: the baseline, then its one-defect mutants. */
export const ROUTER_HEADINGS = {
  baseline: "Keyword baseline: sees only the request",
  mutant: "Mutants: the baseline with one planted defect",
} as const;

const NOT_APPLICABLE = "n/a";

/** Per router, per detector: items where the router trips and the baseline does not. */
export type NewTrips = ReadonlyMap<string, ReadonlyMap<string, number>>;

/** A heading on the baseline row and on the first mutant row, otherwise null. */
export function routerHeadings(
  routers: readonly string[],
  baseline: string,
): (string | null)[] {
  let mutantSeen = false;
  return routers.map((router) => {
    if (router === baseline) return ROUTER_HEADINGS.baseline;
    if (mutantSeen) return null;
    mutantSeen = true;
    return ROUTER_HEADINGS.mutant;
  });
}

/** Ordered-route accuracy per router as the rate stats the shared bar chart reads. */
export function routeAccuracyStats(
  metrics: readonly RouterMetrics[],
): RateStat[] {
  const rows: LlmAccuracyRow[] = metrics.map((row) => ({
    agent: row.router,
    scope: "all",
    correct: row.route_correct,
    total: row.items,
    interval: row.route_interval,
  }));
  return toRateStats(rows);
}

/** The detectors each item tripped for one router, keyed by item id. */
function trippedByItem(
  outcomes: readonly RouterOutcome[],
  router: string,
): Map<string, ReadonlySet<string>> {
  return new Map(
    outcomes
      .filter((outcome) => outcome.router === router)
      .map((outcome) => [outcome.item_id, new Set(outcome.tripped)]),
  );
}

/** Count, for every non-baseline router, trips on items where the baseline stayed clear. */
export function newTrips(
  outcomes: readonly RouterOutcome[],
  baseline: string,
): NewTrips {
  const base = trippedByItem(outcomes, baseline);
  const counts = new Map<string, Map<string, number>>();
  for (const outcome of outcomes) {
    if (outcome.router === baseline) continue;
    const shared = base.get(outcome.item_id);
    if (shared === undefined)
      throw new Error(`No baseline outcome for ${outcome.item_id}`);
    const row = counts.get(outcome.router) ?? new Map<string, number>();
    for (const detector of outcome.tripped.filter((name) => !shared.has(name)))
      row.set(detector, (row.get(detector) ?? 0) + 1);
    counts.set(outcome.router, row);
  }
  return counts;
}

/** The detectors a router trips beyond the baseline, in the given detector order. */
export function detectorsBeyondBaseline(
  trips: NewTrips,
  router: string,
  detectors: readonly string[],
): string[] {
  const row = trips.get(router);
  if (row === undefined) return [];
  return detectors.filter((detector) => (row.get(detector) ?? 0) > 0);
}

/** Whether every mutant trips exactly one detector beyond the baseline. */
export function eachMutantHasOneDetector(
  trips: NewTrips,
  mutants: readonly string[],
  detectors: readonly string[],
): boolean {
  return (
    mutants.length > 0 &&
    mutants.every(
      (router) =>
        detectorsBeyondBaseline(trips, router, detectors).length === 1,
    )
  );
}

/** Mark a cell with its beyond-baseline count and restate it in words. */
function markCell(cell: MatrixCellView, extra: number): MatrixCellView {
  const base = `${cell.detector} tripped on ${cell.tripped} of ${cell.applicable} applicable items for ${cell.agent}.`;
  if (extra === 0) return { ...cell, description: base };
  return {
    ...cell,
    mark: `+${extra} new`,
    description: `${base} On ${extra} of them the baseline does not trip it.`,
  };
}

/** The router-by-detector heatmap, with beyond-baseline trips marked on mutant rows. */
export function buildRouterMatrix(
  cells: readonly RouterDetectionCell[],
  routers: readonly string[],
  detectors: readonly string[],
  baseline: string,
  outcomes: readonly RouterOutcome[],
): MatrixView {
  const asAgentCells: DetectionCell[] = cells.map((cell) => ({
    agent: cell.router,
    detector: cell.detector,
    tripped: cell.tripped,
    applicable: cell.applicable,
  }));
  const view = buildMatrix(
    asAgentCells,
    routers,
    detectors,
    routerHeadings(routers, baseline),
  );
  const trips = newTrips(outcomes, baseline);
  const rows = view.rows.map((row) => ({
    ...row,
    cells: row.cells.map((cell) =>
      markCell(cell, trips.get(row.agent)?.get(cell.detector) ?? 0),
    ),
  }));
  return { columns: view.columns, rows };
}

/** A set-level rate to three decimals, or `n/a` when it has no denominator. */
export function formatMetric(value: number | null): string {
  return value === null ? NOT_APPLICABLE : formatRate(value);
}

/** How many items carry a tag. */
export function countTagged(
  items: readonly { readonly tags: readonly string[] }[],
  tag: string,
): number {
  return items.filter((item) => item.tags.includes(tag)).length;
}

/** Routers, other than the baseline, whose ordered-route accuracy is exactly the baseline's. */
export function routersTiedWithBaseline(
  metrics: readonly RouterMetrics[],
  baseline: string,
): string[] {
  const base = metrics.find((row) => row.router === baseline);
  if (base === undefined)
    throw new Error(`Metrics for ${baseline} missing from router_results.json`);
  return metrics
    .filter(
      (row) =>
        row.router !== baseline &&
        row.items === base.items &&
        row.route_correct === base.route_correct,
    )
    .map((row) => row.router);
}

/** One step of the plan diagram: what it may do, and the refs it hands to the next step. */
export interface RouteFlowStep {
  readonly agent: string;
  readonly capabilities: readonly string[];
  readonly writes: boolean;
  readonly requiresConfirmation: boolean;
  readonly carried: readonly string[];
}

/** The ordered plan as diagram steps, with each step's handoff to the next one. */
export function buildRouteFlow(
  plan: RoutePlanView,
  writeCapability: string,
): RouteFlowStep[] {
  return plan.steps.map((step, index) => {
    const next = plan.steps[index + 1];
    return {
      agent: step.agent,
      capabilities: step.allowed_capabilities,
      writes: step.allowed_capabilities.includes(writeCapability),
      requiresConfirmation: step.requires_confirmation,
      carried:
        next === undefined
          ? []
          : step.context_refs.filter((ref) => next.context_refs.includes(ref)),
    };
  });
}
