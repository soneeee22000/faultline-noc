import type { RateStat } from "../types/payload";
import { type AgentGroup, agentGroup, groupHeadings } from "./agents";
import { formatCount, formatInterval, formatRate } from "./format";

/** Axis ticks on the 0 to 1 scale shared by both bar charts. */
export const AXIS_TICKS: readonly number[] = [0, 0.25, 0.5, 0.75, 1];

/** One bar row: an agent's rate, its Wilson interval and report-formatted labels. */
export interface BarRow {
  readonly agent: string;
  readonly group: AgentGroup;
  readonly groupHeading: string | null;
  readonly correct: number;
  readonly n: number;
  readonly rate: number;
  readonly low: number;
  readonly high: number;
  readonly countLabel: string;
  readonly rateLabel: string;
  readonly intervalLabel: string;
  readonly isZero: boolean;
}

/** Find the stat for an agent or fail loudly. */
function statFor(
  stats: readonly RateStat[],
  agent: string,
  scope?: string,
): RateStat {
  const found = stats.find(
    (stat) =>
      stat.agent === agent && (scope === undefined || stat.scope === scope),
  );
  if (found === undefined)
    throw new Error(
      `No rate stat for ${agent}${scope === undefined ? "" : ` in ${scope}`}`,
    );
  return found;
}

/** Build bar rows in the report's agent order; values are never re-sorted. */
export function buildBarRows(
  stats: readonly RateStat[],
  agents: readonly string[],
): BarRow[] {
  const headings = groupHeadings(agents);
  return agents.map((agent, position) => {
    const stat = statFor(stats, agent);
    return {
      agent,
      group: agentGroup(agent),
      groupHeading: headings[position] ?? null,
      correct: stat.correct,
      n: stat.n,
      rate: stat.rate,
      low: stat.wilson_low,
      high: stat.wilson_high,
      countLabel: formatCount(stat.correct, stat.n),
      rateLabel: formatRate(stat.rate),
      intervalLabel: formatInterval(stat.wilson_low, stat.wilson_high),
      isZero: stat.correct === 0,
    };
  });
}

/** Per-scenario `correct/n` lines for one agent, in scenario order. */
export function scenarioBreakdown(
  perScenario: readonly RateStat[],
  agent: string,
  scenarios: readonly string[],
): string[] {
  return scenarios.map((scenario) => {
    const stat = statFor(perScenario, agent, scenario);
    return `${scenario} ${stat.correct}/${stat.n}`;
  });
}
