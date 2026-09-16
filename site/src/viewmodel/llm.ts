import type {
  LlmAccuracyRow,
  LlmResultsPayload,
  RateStat,
} from "../types/payload";
import { formatCount } from "./format";

const USD_DECIMALS = 4;
const THOUSANDS = 3;

/** The agent name each API model id is reported under, from `MODEL_PROFILES`. */
const AGENT_BY_MODEL: Readonly<Record<string, string>> = {
  "claude-haiku-4-5": "llm_haiku_4_5",
  "claude-sonnet-5": "llm_sonnet_5",
};

/** How an agent scored on one scenario. */
export type CellState = "pass" | "partial" | "fail";

/** One cell of the agent-by-scenario grid. */
export interface GridCell {
  readonly agent: string;
  readonly scenario: string;
  readonly correct: number;
  readonly total: number;
  readonly label: string;
  readonly state: CellState;
}

/** One row of the cost table. */
export interface CostRow {
  readonly model: string;
  readonly agent: string;
  readonly usd: string;
  readonly input: string;
  readonly output: string;
}

/**
 * Wilson bounds are computed in floating point, so a bound for a 0 or 1 rate can land an epsilon
 * outside it; the shared bar geometry rejects an interval that excludes its own rate.
 */
function containing(low: number, rate: number, high: number): [number, number] {
  return [Math.min(low, rate), Math.max(high, rate)];
}

/** Convert one LLM row into the rate stat the shared bar chart and tables read. */
export function toRateStat(row: LlmAccuracyRow): RateStat {
  if (row.total <= 0)
    throw new RangeError(`Row ${row.agent}/${row.scope} covers no runs`);
  const rate = row.correct / row.total;
  const [low, high] = containing(row.interval.low, rate, row.interval.high);
  return {
    agent: row.agent,
    scope: row.scope,
    correct: row.correct,
    n: row.total,
    rate,
    wilson_low: low,
    wilson_high: high,
  };
}

/** Convert every row, keeping the report's order. */
export function toRateStats(rows: readonly LlmAccuracyRow[]): RateStat[] {
  return rows.map(toRateStat);
}

/** Classify a score: every run right, none right, or somewhere between. */
export function cellState(correct: number, total: number): CellState {
  if (total <= 0) throw new RangeError(`A cell covers no runs`);
  if (correct === total) return "pass";
  return correct === 0 ? "fail" : "partial";
}

/** One grid row per agent, one cell per scenario, in the given orders. */
export function buildScenarioGrid(
  rows: readonly LlmAccuracyRow[],
  agents: readonly string[],
  scenarios: readonly string[],
): GridCell[][] {
  const byKey = new Map(rows.map((row) => [`${row.agent}|${row.scope}`, row]));
  return agents.map((agent) =>
    scenarios.map((scenario) => {
      const row = byKey.get(`${agent}|${scenario}`);
      if (row === undefined)
        throw new Error(`No score for ${agent} on ${scenario}`);
      return {
        agent,
        scenario,
        correct: row.correct,
        total: row.total,
        label: formatCount(row.correct, row.total),
        state: cellState(row.correct, row.total),
      };
    }),
  );
}

/** Group digits in threes, e.g. `291768` becomes `291,768`. */
export function formatThousands(value: number): string {
  if (!Number.isInteger(value) || value < 0)
    throw new RangeError(`Expected a whole count, got ${value}`);
  const digits = String(value);
  const lead = digits.length % THOUSANDS || THOUSANDS;
  const groups = [digits.slice(0, lead)];
  for (let at = lead; at < digits.length; at += THOUSANDS) {
    groups.push(digits.slice(at, at + THOUSANDS));
  }
  return groups.join(",");
}

/** Format an amount in US dollars at the precision the report uses. */
export function formatUsd(amount: number): string {
  return `$${amount.toFixed(USD_DECIMALS)}`;
}

/** One cost row per model, in the payload's model order. */
export function costRows(payload: LlmResultsPayload): CostRow[] {
  return payload.models.map((model) => {
    const usd = payload.spend_usd[model];
    const tokens = payload.tokens[model];
    const agent = AGENT_BY_MODEL[model];
    if (usd === undefined || tokens === undefined || agent === undefined)
      throw new Error(`No spend recorded for ${model}`);
    return {
      model,
      agent,
      usd: formatUsd(usd),
      input: formatThousands(tokens.input),
      output: formatThousands(tokens.output),
    };
  });
}

/** What the whole recorded run cost, summed over the models. */
export function totalSpend(payload: LlmResultsPayload): string {
  const total = payload.models.reduce(
    (sum, model) => sum + (payload.spend_usd[model] ?? 0),
    0,
  );
  return formatUsd(total);
}

/** How many of the runs actually called a model, the rest being the rule baseline. */
export function modelRunCount(payload: LlmResultsPayload): number {
  return (
    payload.models.length * payload.scenarios.length * payload.seeds.length
  );
}
