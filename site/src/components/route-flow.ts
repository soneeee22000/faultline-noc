import { esc, joinList } from "../lib/dom";
import { round, svgLine, svgRect, svgText } from "../lib/svg";
import type { RouteFlowStep } from "../viewmodel/router";

/** Geometry of the plan diagram, in the user units of a 360-wide viewBox. */
const FLOW = Object.freeze({
  width: 360,
  headBaseline: 26,
  headHeight: 40,
  stepHeight: 54,
  gap: 44,
  bottom: 14,
  stepX: 14,
  stepWidth: 332,
  textX: 26,
  rightX: 334,
  lineA: 21,
  lineB: 41,
  arrowX: 44,
  arrowGap: 8,
  arrowHead: 7,
  arrowHalfWidth: 5,
  labelX: 58,
  labelRaise: 4,
  radius: 4,
});

/** The viewBox height for a plan of this many steps. */
function flowHeight(steps: number): number {
  return (
    FLOW.headHeight +
    steps * FLOW.stepHeight +
    Math.max(steps - 1, 0) * FLOW.gap +
    FLOW.bottom
  );
}

/** The y of a step box's top edge. */
function stepTop(index: number): number {
  return FLOW.headHeight + index * (FLOW.stepHeight + FLOW.gap);
}

/** The gate line of a write step: the field that makes the write safe. */
function gateMarkup(step: RouteFlowStep, top: number): string {
  if (!step.writes) return "";
  const tone = step.requiresConfirmation ? "svg-pass" : "svg-trip";
  return svgText(
    FLOW.rightX,
    top + FLOW.lineB,
    `requires_confirmation ${String(step.requiresConfirmation)}`,
    `svg-mono svg-mono--small ${tone}`,
    "end",
  );
}

/** One `RouteStep`: its position and agent on the left, what it may do on the right. */
function stepMarkup(step: RouteFlowStep, index: number): string {
  const top = stepTop(index);
  const tone = step.writes ? "svg-trip" : "svg-muted";
  return `<g>${svgRect(FLOW.stepX, top, FLOW.stepWidth, FLOW.stepHeight, "svg-node svg-node--other", FLOW.radius)}${svgText(FLOW.textX, top + FLOW.lineA, `step ${index + 1}`, "svg-mono svg-mono--small svg-muted")}${svgText(FLOW.textX, top + FLOW.lineB, step.agent, "svg-mono")}${svgText(FLOW.rightX, top + FLOW.lineA, step.capabilities.join(" · "), `svg-mono svg-mono--small ${tone}`, "end")}${gateMarkup(step, top)}</g>`;
}

/** The refs an arrow carries, kept to one line. */
function carriedLabel(carried: readonly string[]): string {
  const first = carried[0] ?? "";
  return carried.length > 1 ? `${first} +${carried.length - 1}` : first;
}

/** The label beside an arrow, naming the context this step hands to the next. */
function carriedMarkup(step: RouteFlowStep, from: number, to: number): string {
  if (step.carried.length === 0) return "";
  return svgText(
    FLOW.labelX,
    (from + to) / 2 + FLOW.labelRaise,
    `carries ${carriedLabel(step.carried)}`,
    "svg-mono svg-mono--small svg-muted svg-halo",
  );
}

/** The ordering arrow between two steps: the plan is a sequence, not a set. */
function arrowMarkup(step: RouteFlowStep, index: number): string {
  const from = stepTop(index) + FLOW.stepHeight + FLOW.arrowGap;
  const to = stepTop(index + 1) - FLOW.arrowGap;
  const tip = round(to);
  const base = round(to - FLOW.arrowHead);
  const head = `<polygon class="svg-arrow" points="${round(FLOW.arrowX)},${tip} ${round(FLOW.arrowX - FLOW.arrowHalfWidth)},${base} ${round(FLOW.arrowX + FLOW.arrowHalfWidth)},${base}"/>`;
  const shaft = svgLine(
    FLOW.arrowX,
    from,
    FLOW.arrowX,
    to - FLOW.arrowHead,
    "svg-dep",
  );
  return `${shaft}${head}${carriedMarkup(step, from, to)}`;
}

/** One step, read aloud: who acts, what it may do, and whether its write is gated. */
function stepSentence(step: RouteFlowStep, index: number): string {
  const gate = step.writes
    ? `, ${step.requiresConfirmation ? "requiring confirmation" : "with no confirmation"}`
    : "";
  const handoff =
    step.carried.length === 0
      ? ""
      : `, carrying ${joinList([...step.carried])} to the next step`;
  return `step ${index + 1}, ${step.agent}, may ${joinList([...step.capabilities])}${gate}${handoff}`;
}

/** The whole diagram as one sentence, for anyone who cannot see it. */
function flowLabel(steps: readonly RouteFlowStep[]): string {
  return `RoutePlan: ${steps.map(stepSentence).join("; then ")}.`;
}

/** A `RoutePlan` as an ordered flow: boxed steps, arrows, and the context each one hands on. */
export function routeFlowMarkup(steps: readonly RouteFlowStep[]): string {
  const height = flowHeight(steps.length);
  const outline = svgRect(
    1,
    1,
    FLOW.width - 2,
    height - 2,
    "svg-rule",
    FLOW.radius,
  );
  const head = `${svgText(FLOW.textX, FLOW.headBaseline, "RoutePlan", "svg-mono")}${svgText(FLOW.rightX, FLOW.headBaseline, `${steps.length} ordered steps`, "svg-mono svg-mono--small svg-muted", "end")}`;
  const boxes = steps.map(stepMarkup).join("");
  const arrows = steps
    .slice(0, -1)
    .map((step, index) => arrowMarkup(step, index))
    .join("");
  return `<svg class="route-flow" viewBox="0 0 ${FLOW.width} ${height}" role="img" aria-label="${esc(flowLabel(steps))}">${outline}${head}${boxes}${arrows}</svg>`;
}
