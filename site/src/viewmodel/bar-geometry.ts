import { joinList } from "../lib/dom";
import type { BarRow } from "./bars";
import { formatRate } from "./format";

const PERCENT = 100;
const PERCENT_PRECISION = 10;
const HALF = 2;
const PERFECT_RATE = 1;

/** Positions on a bar track, as percentages of the track width. */
export interface BarGeometry {
  readonly barPercent: number;
  readonly squarePercent: number;
  readonly lowPercent: number;
  readonly highPercent: number;
  readonly isZero: boolean;
}

/** A unit-interval value as a percentage rounded to one decimal. */
function toPercent(value: number): number {
  return Math.round(value * PERCENT * PERCENT_PRECISION) / PERCENT_PRECISION;
}

/** Bar length, the square baseline half, and Wilson whisker ends for one rate. */
export function barGeometry(
  rate: number,
  low: number,
  high: number,
): BarGeometry {
  if (low > rate || high < rate) {
    throw new RangeError(`Wilson interval [${low}, ${high}] excludes ${rate}`);
  }
  const barPercent = toPercent(rate);
  return {
    barPercent,
    squarePercent: barPercent / HALF,
    lowPercent: toPercent(low),
    highPercent: toPercent(high),
    isZero: rate === 0,
  };
}

/** A one-sentence chart description: perfect scores and the lowest agents. */
export function chartSummary(rows: readonly BarRow[]): string {
  const rates = rows.map((row) => row.rate);
  const lowest = Math.min(...rates);
  const perfect = rows.filter((row) => row.rate === PERFECT_RATE).length;
  if (rates.every((rate) => rate === lowest)) {
    return `All ${rows.length} agents score ${formatRate(lowest)}.`;
  }
  const lowestAgents = rows
    .filter((row) => row.rate === lowest)
    .map((row) => `\`${row.agent}\``);
  return `${perfect} of ${rows.length} agents score ${formatRate(PERFECT_RATE)}. Lowest: ${joinList(lowestAgents)} at ${formatRate(lowest)}.`;
}
