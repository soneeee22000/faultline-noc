import { esc } from "../lib/dom";
import { iconAt } from "../lib/icons";
import { svgCircle, svgRect, svgText } from "../lib/svg";
import type {
  ResultsPayload,
  SampleTrace,
  ScenarioInfo,
} from "../types/payload";
import { formatCount } from "../viewmodel/format";
import { buildMatrix } from "../viewmodel/matrix";
import { shortScenarioId } from "../viewmodel/scenario";
import {
  type DetectionRow,
  buildActionRows,
  buildDetectionRows,
  citationPreview,
  laneTags,
} from "../viewmodel/trace";
import { topologyMarkup } from "./topology-svg";

const WIDTH = 520;
const HEIGHT = 340;
const MARGIN = 24;
const CHIP_HEIGHT = 28;
const CHIP_RADIUS = 2;
const ICON = 16;
const GLYPH_RAISE = 13;
const CONFIDENCE_DECIMALS = 2;
const INJECTED_PREFIX = "injected_";
const DETAIL = "surface-detail";
const RUN_LABEL_Y = 30;

/** Plane 1 geometry: padding around the topology. */
const NETWORK = Object.freeze({ padX: 56, padY: 48, nodeRadius: 7 });

/** Plane 2 geometry: three lanes of cited-id chips. */
const TELEMETRY = Object.freeze({
  runLabelY: 26,
  titleY: 56,
  chipsTop: 72,
  chipPitch: 36,
  chipTextX: 10,
  chipTextBaseline: 19,
  countY: 322,
  laneWidth: 150,
  lanePitch: 162,
  tagsPerLane: 4,
  logLane: 2,
  iconInsetX: 8,
  iconInsetY: 6,
  injectedTextX: 30,
  injectedLabelGap: 50,
});

/** Plane 3 geometry: the RCA card's key/value rows, citations and actions. */
const RCA = Object.freeze({
  valueX: 210,
  rootY: 70,
  faultY: 100,
  confidenceY: 130,
  citationsLabelY: 160,
  citationChipY: 172,
  citationTextY: 191,
  citationTextX: 8,
  citationPitch: 104,
  citationWidth: 96,
  citationMoreY: 222,
  actionsLabelY: 240,
  actionTop: 262,
  actionPitch: 32,
  actionTextInset: 24,
  actionFlagX: 260,
});

/** Plane 4 geometry: the detector breaker panel. */
const GUARDRAILS = Object.freeze({
  top: 70,
  rowPitch: 38,
  nameX: 44,
  stateX: 300,
  stateTextGap: 6,
  bracketX: 30,
  bracketOverhangTop: 5,
  bracketOverhangBottom: 6,
});

/** Plane 5 geometry: badge, run count, glyph matrix and mini bars. */
const SCORECARD = Object.freeze({
  badgeWidth: 270,
  badgeHeight: 44,
  badgeRadius: 4,
  badgeIconInset: 12,
  badgeIcon: 20,
  badgeTextX: 42,
  badgeTextBaseline: 28,
  runsY: 124,
  runsSubY: 152,
  baselineLabelY: 250,
  accuracyBarY: 272,
  actionsBarY: 310,
  miniBarOffset: 8,
  miniBarHeight: 10,
  glyphCell: 18,
  matrixOriginX: 340,
  matrixOriginY: 28,
  matrixCaptionGap: 20,
  emptyDotRadius: 2.5,
  diamondHalf: 7,
});

/** Wrap plane content in a decorative SVG in plane coordinates. */
function surface(content: string): string {
  return `<svg class="plane-surface" viewBox="0 0 ${WIDTH} ${HEIGHT}" aria-hidden="true" focusable="false">${content}</svg>`;
}

/** A small label naming which recorded run a surface shows. */
function runLabel(trace: SampleTrace): string {
  return `${trace.agent}, ${shortScenarioId(trace.scenario_id)} seed ${trace.seed}`;
}

/** Plane 1: the committed topology with interface labels. */
export function networkSurface(): string {
  return surface(
    topologyMarkup({
      width: WIDTH,
      height: HEIGHT,
      padX: NETWORK.padX,
      padY: NETWORK.padY,
      nodeRadius: NETWORK.nodeRadius,
      showInterfaces: true,
      roleOf: () => null,
    }),
  );
}

/** One telemetry lane: header, cited id chips and the delivered count. */
function laneMarkup(
  lane: ReturnType<typeof laneTags>[number],
  index: number,
): string {
  const x = MARGIN + index * TELEMETRY.lanePitch;
  const chips = lane.ids
    .map((id, row) => {
      const y = TELEMETRY.chipsTop + row * TELEMETRY.chipPitch;
      const extra = row === 0 ? "" : ` class="${DETAIL}"`;
      return `<g${extra}>${svgRect(x, y, TELEMETRY.laneWidth, CHIP_HEIGHT, "svg-chip", CHIP_RADIUS)}${svgText(x + TELEMETRY.chipTextX, y + TELEMETRY.chipTextBaseline, id, "svg-mono")}</g>`;
    })
    .join("");
  const count =
    lane.delivered === null ? "not read" : `${lane.delivered} records`;
  const title = lane.source.charAt(0).toUpperCase() + lane.source.slice(1);
  return `${svgText(x, TELEMETRY.titleY, title, "svg-text svg-strong")}${chips}${svgText(x, TELEMETRY.countY, count, "svg-mono svg-mono--small svg-muted")}`;
}

/** The injected log line chip under the logs lane. */
function injectedChip(injectedId: string): string {
  const x = MARGIN + TELEMETRY.logLane * TELEMETRY.lanePitch;
  const y = TELEMETRY.chipsTop + TELEMETRY.tagsPerLane * TELEMETRY.chipPitch;
  return `${svgRect(x, y, TELEMETRY.laneWidth, CHIP_HEIGHT, "svg-chip--trip", CHIP_RADIUS)}${iconAt("message-square-warning", x + TELEMETRY.iconInsetX, y + TELEMETRY.iconInsetY, ICON, "svg-icon svg-icon--trip")}${svgText(x + TELEMETRY.injectedTextX, y + TELEMETRY.chipTextBaseline, injectedId, "svg-mono svg-trip")}${svgText(x, y + TELEMETRY.injectedLabelGap, "injected", "svg-text svg-trip")}`;
}

/** Plane 2: alarms, KPIs and logs with real cited ids and the injected log line. */
export function telemetrySurface(trace: SampleTrace): string {
  const lanes = laneTags(trace, TELEMETRY.tagsPerLane).map(laneMarkup).join("");
  const injectedId = trace.injection_evidence_id;
  const injected = injectedId === null ? "" : injectedChip(injectedId);
  return surface(
    `${svgText(MARGIN, TELEMETRY.runLabelY, runLabel(trace), "svg-mono svg-mono--small svg-muted")}${lanes}${injected}`,
  );
}

/** One key and value line on the RCA card. */
function keyValue(y: number, key: string, value: string, extra = ""): string {
  return `<g${extra === "" ? "" : ` class="${extra}"`}>${svgText(MARGIN, y, key, "svg-mono svg-mono--small svg-muted")}${svgText(RCA.valueX, y, value, "svg-mono")}</g>`;
}

/** The glyph and flag text for one action row. */
function actionGlyph(offRoot: boolean, injected: boolean, y: number): string {
  if (!offRoot)
    return iconAt(
      "circle-check",
      MARGIN,
      y - GLYPH_RAISE,
      ICON,
      "svg-icon svg-icon--pass",
    );
  const flag = injected ? "not the root cause, injected" : "not the root cause";
  return `${iconAt("diamond", MARGIN, y - GLYPH_RAISE, ICON, "svg-icon svg-icon--trip svg-icon--filled")}${svgText(RCA.actionFlagX, y, flag, "svg-text svg-trip")}`;
}

/** Action rows on the RCA card, flagged when off the root cause. */
function actionLines(trace: SampleTrace, scenario: ScenarioInfo): string {
  return buildActionRows(trace, scenario)
    .map((row, index) => {
      const y = RCA.actionTop + index * RCA.actionPitch;
      const text = svgText(
        MARGIN + RCA.actionTextInset,
        y,
        `${row.kind} ${row.target}`,
        row.offRoot ? "svg-mono svg-trip" : "svg-mono",
      );
      return `${actionGlyph(row.offRoot, row.injected, y)}${text}`;
    })
    .join("");
}

/** The first cited ids as chips, then a "+N more" count. */
function citationChips(trace: SampleTrace): string {
  const preview = citationPreview(trace.rca.cited_evidence_ids);
  const chips = preview.shown
    .map((id, index) => {
      const x = MARGIN + index * RCA.citationPitch;
      return `${svgRect(x, RCA.citationChipY, RCA.citationWidth, CHIP_HEIGHT, "svg-chip", CHIP_RADIUS)}${svgText(x + RCA.citationTextX, RCA.citationTextY, id, "svg-mono svg-mono--small")}`;
    })
    .join("");
  const more =
    preview.hiddenCount > 0
      ? svgText(
          MARGIN,
          RCA.citationMoreY,
          `+${preview.hiddenCount} more`,
          "svg-mono svg-mono--small svg-muted",
        )
      : "";
  return `${chips}${more}`;
}

/** Plane 3: the structured RCA from one recorded mutant run. */
export function agentSurface(
  trace: SampleTrace,
  scenario: ScenarioInfo,
): string {
  const chips = citationChips(trace);
  return surface(
    `${svgText(MARGIN, RUN_LABEL_Y, runLabel(trace), "svg-mono svg-mono--small svg-muted")}` +
      keyValue(RCA.rootY, "root_cause_nf", trace.rca.root_cause_nf ?? "none") +
      keyValue(RCA.faultY, "fault_class", trace.rca.fault_class) +
      keyValue(
        RCA.confidenceY,
        "confidence",
        trace.rca.confidence.toFixed(CONFIDENCE_DECIMALS),
        DETAIL,
      ) +
      `<g class="${DETAIL}">${svgText(MARGIN, RCA.citationsLabelY, "cited_evidence_ids", "svg-mono svg-mono--small svg-muted")}${chips}</g>` +
      svgText(
        MARGIN,
        RCA.actionsLabelY,
        "actions",
        "svg-mono svg-mono--small svg-muted",
      ) +
      actionLines(trace, scenario),
  );
}

/** Baseline y of a detector row. */
function detectorY(index: number): number {
  return GUARDRAILS.top + index * GUARDRAILS.rowPitch;
}

/** One detector row: name, glyph and state text. */
function detectorLine(row: DetectionRow, index: number): string {
  const y = detectorY(index);
  const tripped = row.state === "tripped";
  const glyph = tripped
    ? iconAt(
        "diamond",
        GUARDRAILS.stateX,
        y - GLYPH_RAISE,
        ICON,
        "svg-icon svg-icon--trip svg-icon--filled",
      )
    : iconAt(
        "circle",
        GUARDRAILS.stateX,
        y - GLYPH_RAISE,
        ICON,
        "svg-icon svg-icon--pass",
      );
  const label = row.state === "not_applicable" ? "n/a" : row.state;
  const state = svgText(
    GUARDRAILS.stateX + ICON + GUARDRAILS.stateTextGap,
    y,
    label,
    tripped ? "svg-text svg-trip" : "svg-text svg-pass",
  );
  return `${svgText(GUARDRAILS.nameX, y, row.detector, "svg-mono")}${glyph}${state}`;
}

/** A bracket and label grouping the prompt-injection detectors. */
function injectionGroup(rows: readonly DetectionRow[]): string {
  const indexes = rows
    .map((row, index) =>
      row.detector.startsWith(INJECTED_PREFIX) ? index : -1,
    )
    .filter((index) => index >= 0);
  const first = indexes[0];
  const last = indexes.at(-1);
  if (first === undefined || last === undefined) return "";
  const top = detectorY(first) - GLYPH_RAISE - GUARDRAILS.bracketOverhangTop;
  const bottom = detectorY(last) + GUARDRAILS.bracketOverhangBottom;
  const middle =
    GUARDRAILS.top +
    ((first + last) / 2) * GUARDRAILS.rowPitch +
    GUARDRAILS.bracketOverhangBottom;
  return `<g class="${DETAIL}"><line class="svg-rule" x1="${GUARDRAILS.bracketX}" x2="${GUARDRAILS.bracketX}" y1="${top}" y2="${bottom}"/>${svgText(WIDTH - MARGIN, middle, "Prompt injection", "svg-text svg-muted", "end")}</g>`;
}

/** Plane 4: the seven detectors as a breaker panel for one recorded run. */
export function guardrailsSurface(
  trace: SampleTrace,
  detectors: readonly string[],
): string {
  const rows = buildDetectionRows(trace, detectors);
  const lines = rows.map(detectorLine).join("");
  const group = injectionGroup(rows);
  return surface(
    `${svgText(MARGIN, RUN_LABEL_Y, runLabel(trace), "svg-mono svg-mono--small svg-muted")}${group}${lines}`,
  );
}

/** A filled diamond centred on a point. */
function diamondPath(cx: number, cy: number, bin: number): string {
  const half = SCORECARD.diamondHalf;
  return `<path class="svg-heat-${bin}" d="M${cx} ${cy - half}L${cx + half} ${cy}L${cx} ${cy + half}L${cx - half} ${cy}Z"/>`;
}

/** The 10 by 7 glyph grid mirroring the detection matrix. */
function glyphGrid(payload: ResultsPayload): string {
  const view = buildMatrix(
    payload.detection_matrix,
    payload.meta.agents,
    payload.meta.detectors,
  );
  const cell = SCORECARD.glyphCell;
  const glyphs = view.rows
    .flatMap((row, rowIndex) =>
      row.cells.map((item, colIndex) => {
        const cx = SCORECARD.matrixOriginX + colIndex * cell + cell / 2;
        const cy = SCORECARD.matrixOriginY + rowIndex * cell + cell / 2;
        if (item.bin === 0)
          return svgCircle(cx, cy, SCORECARD.emptyDotRadius, "svg-dot");
        return diamondPath(cx, cy, item.bin);
      }),
    )
    .join("");
  const captionY =
    SCORECARD.matrixOriginY +
    view.rows.length * cell +
    SCORECARD.matrixCaptionGap;
  return `<g class="${DETAIL}">${glyphs}${svgText(SCORECARD.matrixOriginX, captionY, "detection matrix", "svg-text svg-muted")}</g>`;
}

/** A labelled mini bar for one overall rate. */
function miniBar(y: number, label: string, correct: number, n: number): string {
  const track = WIDTH - 2 * MARGIN;
  const barY = y + SCORECARD.miniBarOffset;
  const height = SCORECARD.miniBarHeight;
  return `${svgText(MARGIN, y, `${label} ${formatCount(correct, n)}`, "svg-mono svg-mono--small")}${svgRect(MARGIN, barY, track, height, "svg-track")}${svgRect(MARGIN, barY, (track * correct) / Math.max(n, 1), height, "svg-bar")}`;
}

/** The harness check badge in the plane's top-left corner. */
function harnessBadge(pass: boolean): string {
  const tone = pass ? "pass" : "trip";
  return `${svgRect(MARGIN, MARGIN, SCORECARD.badgeWidth, SCORECARD.badgeHeight, `svg-chip--${tone}`, SCORECARD.badgeRadius)}${iconAt(pass ? "circle-check" : "circle-x", MARGIN + SCORECARD.badgeIconInset, MARGIN + SCORECARD.badgeIconInset, SCORECARD.badgeIcon, `svg-icon svg-icon--${tone}`)}${svgText(MARGIN + SCORECARD.badgeTextX, MARGIN + SCORECARD.badgeTextBaseline, `Harness check: ${pass ? "PASS" : "FAIL"}`, `svg-text svg-strong svg-${tone}`)}`;
}

/** Plane 5: harness badge, run count, matrix glyphs and the baseline's two rates. */
export function scorecardSurface(
  payload: ResultsPayload,
  baselineAgent: string,
): string {
  const meta = payload.meta;
  const accuracy = payload.accuracy_overall.find(
    (stat) => stat.agent === baselineAgent,
  );
  const actions = payload.action_correctness.find(
    (stat) => stat.agent === baselineAgent,
  );
  const counts = `${svgText(MARGIN, SCORECARD.runsY, `${meta.runs} runs`, "svg-text svg-large svg-strong")}${svgText(MARGIN, SCORECARD.runsSubY, esc(`${meta.agents.length} agents × ${meta.scenarios.length} scenarios × ${meta.seed_count} seeds`), "svg-text svg-muted")}`;
  const bars =
    accuracy === undefined || actions === undefined
      ? ""
      : `<g class="${DETAIL}">${svgText(MARGIN, SCORECARD.baselineLabelY, baselineAgent, "svg-mono svg-mono--small svg-muted")}${miniBar(SCORECARD.accuracyBarY, "top-1 accuracy", accuracy.correct, accuracy.n)}${miniBar(SCORECARD.actionsBarY, "action correctness", actions.correct, actions.n)}</g>`;
  return surface(
    `${harnessBadge(meta.harness_pass)}${counts}${glyphGrid(payload)}${bars}`,
  );
}
