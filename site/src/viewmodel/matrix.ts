import type { DetectionCell } from "../types/payload";
import { type AgentGroup, agentGroup, groupHeadings } from "./agents";

export { agentGroup } from "./agents";

/** Five ordinal classes of trip rate, 0 (none) to 4 (every applicable run). */
export type HeatBin = 0 | 1 | 2 | 3 | 4;

/** Text colour role chosen per bin so every cell keeps AA contrast. */
export type CellTone = "muted" | "ink" | "ground";

const LOW_EDGE = 0.25;
const MID_EDGE = 0.5;
const TONE_BY_BIN: Record<HeatBin, CellTone> = {
  0: "muted",
  1: "ink",
  2: "ground",
  3: "ground",
  4: "ground",
};

/** One rendered heatmap cell. */
export interface MatrixCellView extends DetectionCell {
  readonly bin: HeatBin;
  readonly tone: CellTone;
  readonly label: string;
  readonly description: string;
}

/** One heatmap row: an agent and its cells in detector order. */
export interface MatrixRowView {
  readonly agent: string;
  readonly group: AgentGroup;
  readonly groupHeading: string | null;
  readonly cells: readonly MatrixCellView[];
}

/** The whole heatmap view-model. */
export interface MatrixView {
  readonly columns: readonly string[];
  readonly rows: readonly MatrixRowView[];
}

/** Bin a trip count into the five-class ramp; edges at 25% and 50% are inclusive. */
export function heatBin(tripped: number, applicable: number): HeatBin {
  if (tripped < 0 || tripped > applicable) {
    throw new RangeError(`Impossible detection count ${tripped}/${applicable}`);
  }
  if (tripped === 0) return 0;
  if (tripped === applicable) return 4;
  const rate = tripped / applicable;
  if (rate <= LOW_EDGE) return 1;
  return rate <= MID_EDGE ? 2 : 3;
}

/** The text tone for a bin. */
export function cellTone(bin: HeatBin): CellTone {
  return TONE_BY_BIN[bin];
}

/** A plain-language sentence describing one cell, templated from its counts. */
export function cellDescription(cell: DetectionCell): string {
  return `${cell.detector} tripped on ${cell.tripped} of ${cell.applicable} applicable runs for ${cell.agent}.`;
}

/** Decorate one raw cell with its bin, tone and labels. */
function toCellView(cell: DetectionCell): MatrixCellView {
  const bin = heatBin(cell.tripped, cell.applicable);
  return {
    ...cell,
    bin,
    tone: cellTone(bin),
    label: `${cell.tripped}/${cell.applicable}`,
    description: cellDescription(cell),
  };
}

/** Arrange detection cells into rows by agent order and columns by detector order. */
export function buildMatrix(
  cells: readonly DetectionCell[],
  agents: readonly string[],
  detectors: readonly string[],
): MatrixView {
  const index = new Map(
    cells.map((cell) => [`${cell.agent}|${cell.detector}`, cell]),
  );
  const headings = groupHeadings(agents);
  const rows = agents.map((agent, position) => ({
    agent,
    group: agentGroup(agent),
    groupHeading: headings[position] ?? null,
    cells: detectors.map((detector) => {
      const cell = index.get(`${agent}|${detector}`);
      if (cell === undefined)
        throw new Error(`Missing detection cell for ${agent} x ${detector}`);
      return toCellView(cell);
    }),
  }));
  return { columns: detectors, rows };
}
