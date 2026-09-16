import { joinList } from "../lib/dom";
import type { SampleTrace } from "../types/payload";
import { buildReadRows, trippedDetectors } from "./trace";

const CONFIDENCE_DECIMALS = 2;
const CLOSING =
  "Both runs are replayed from the committed responses, so this page calls no model.";

/** Wrap an identifier in backticks for rich text. */
function tick(value: string): string {
  return `\`${value}\``;
}

/** How many evidence sources the agent actually read. */
export function readCount(trace: SampleTrace): number {
  return buildReadRows(trace).filter((row) => row.status === "read").length;
}

/** What one agent concluded, how sure it was, and how much it read to get there. */
export function verdictSentence(trace: SampleTrace): string {
  const root = trace.rca.root_cause_nf ?? "no root cause";
  const outcome = trace.correct
    ? "which matches ground truth"
    : "which does not match ground truth";
  const confidence = trace.rca.confidence.toFixed(CONFIDENCE_DECIMALS);
  return `${tick(trace.agent)} read ${readCount(trace)} sources and named ${tick(root)} at confidence ${confidence}, ${outcome}.`;
}

/** Which detectors fired on one agent's run. */
export function detectorSentence(
  trace: SampleTrace,
  detectors: readonly string[],
): string {
  const tripped = trippedDetectors(trace, detectors).map(tick);
  if (tripped.length === 0) return `No detector fired on ${tick(trace.agent)}.`;
  return `On ${tick(trace.agent)}, ${joinList(tripped)} fired.`;
}

/** The templated comparison under the model trace, in rich text. */
export function modelTraceSummary(
  first: SampleTrace,
  second: SampleTrace,
  detectors: readonly string[],
): string {
  return [
    verdictSentence(first),
    verdictSentence(second),
    detectorSentence(first, detectors),
    detectorSentence(second, detectors),
    CLOSING,
  ].join(" ");
}
