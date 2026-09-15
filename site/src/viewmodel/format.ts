const RATE_DECIMALS = 3;
const TICK_DECIMALS = 2;

/** Throw unless the value is a finite number in [0, 1]. */
function assertUnitInterval(value: number): void {
  if (!Number.isFinite(value) || value < 0 || value > 1) {
    throw new RangeError(`Expected a value in [0, 1], got ${value}`);
  }
}

/** Format a rate the way the markdown report does, e.g. `0.250`. */
export function formatRate(rate: number): string {
  assertUnitInterval(rate);
  return rate.toFixed(RATE_DECIMALS);
}

/** Format a Wilson interval the way the markdown report does, e.g. `[0.221, 0.281]`. */
export function formatInterval(low: number, high: number): string {
  return `[${formatRate(low)}, ${formatRate(high)}]`;
}

/** Format a count against its denominator, e.g. `200 / 800`. */
export function formatCount(correct: number, n: number): string {
  return `${correct} / ${n}`;
}

/** Format an axis tick on the 0 to 1 scale, e.g. `0.75`. */
export function formatTick(value: number): string {
  assertUnitInterval(value);
  return value.toFixed(TICK_DECIMALS);
}
