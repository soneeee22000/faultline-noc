import { disclosureButton } from "../lib/disclosure";
import { closestTarget, code, richText } from "../lib/dom";
import { icon } from "../lib/icons";
import type { SampleTrace, ScenarioInfo } from "../types/payload";
import { agentRole } from "../viewmodel/agents";
import { shortScenarioId } from "../viewmodel/scenario";
import {
  type DetectionRow,
  buildActionRows,
  buildDetectionRows,
  buildReadRows,
  citationPreview,
  traceDifferences,
} from "../viewmodel/trace";
import { traceSummary } from "../viewmodel/trace-summary";

/** The two traces the viewer compares, the evaluated agent first. */
export interface TraceViewerInput {
  readonly scenario: ScenarioInfo;
  readonly traces: readonly [SampleTrace, SampleTrace];
  readonly detectors: readonly string[];
}

const DETECTION_GLYPH: Readonly<Record<DetectionRow["state"], string>> = {
  tripped: `<span class="state state--trip">${icon("diamond", "icon--filled")}tripped</span>`,
  clear: `<span class="state state--pass">${icon("circle")}clear</span>`,
  not_applicable: `<span class="state state--muted">${icon("circle")}not applicable</span>`,
};

/** Reads in order, then sources never read, with the injected line flagged. */
function readsCell(trace: SampleTrace): string {
  const items = buildReadRows(trace).map((row) => {
    if (row.status === "not_read")
      return `<li class="trace-read trace-read--missing"><span class="state state--muted">${icon("circle")}${row.source}: not read</span></li>`;
    const count =
      row.recordCount === null
        ? ""
        : ` <span class="muted">(${row.recordCount} records)</span>`;
    const injection = row.includesInjection
      ? `<span class="trace-read__sub">includes ${code(trace.injection_evidence_id ?? "")}<span class="chip chip--trip">${icon("message-square-warning")}injected</span></span>`
      : "";
    return `<li class="trace-read"><code class="trace-read__order">${row.order}</code>${row.source}${count}${injection}</li>`;
  });
  return `<ol class="trace-list">${items.join("")}</ol>`;
}

/** Root cause and fault class, checked against ground truth. */
function rootCell(trace: SampleTrace): string {
  const verdict = trace.correct
    ? `<span class="state state--pass">${icon("circle-check")}matches ground truth</span>`
    : `<span class="state state--trip">${icon("circle-x")}does not match ground truth</span>`;
  return `<p class="trace-pair">${code(trace.rca.root_cause_nf ?? "none")} ${code(trace.rca.fault_class)}</p>${verdict}`;
}

/** The first citations as chips, the rest behind a disclosure. */
function citationsCell(trace: SampleTrace, column: number): string {
  const ids = trace.rca.cited_evidence_ids;
  const preview = citationPreview(ids);
  const chip = (id: string): string => `<li class="chip chip--code">${id}</li>`;
  const shown = `<ul class="chip-list">${preview.shown.map(chip).join("")}</ul>`;
  if (preview.hiddenCount === 0)
    return `<p class="muted">${ids.length} ids</p>${shown}`;
  const regionId = `trace-citations-${column}`;
  const rest = ids.slice(preview.shown.length).map(chip).join("");
  return `<p class="muted">${ids.length} ids</p>${shown}${disclosureButton(regionId, `Show all ${ids.length} citations`, "Hide extra citations")}<ul class="chip-list" id="${regionId}" hidden>${rest}</ul>`;
}

/** Actions with off-root and injected flags. */
function actionsCell(trace: SampleTrace, scenario: ScenarioInfo): string {
  const items = buildActionRows(trace, scenario).map((row) => {
    const flags = row.offRoot
      ? `<span class="state state--trip">${icon("diamond", "icon--filled")}not the root cause</span>`
      : "";
    const injected = row.injected
      ? `<span class="chip chip--trip">${icon("message-square-warning")}injected</span>`
      : "";
    return `<li class="trace-action${row.offRoot ? " trace-action--trip" : ""}">${code(`${row.kind} ${row.target}`)}${flags}${injected}</li>`;
  });
  return `<ul class="trace-list">${items.join("")}</ul>`;
}

/** Seven detector rows with glyph and text states. */
function detectionsCell(
  trace: SampleTrace,
  detectors: readonly string[],
): string {
  const rows = buildDetectionRows(trace, detectors);
  const tripped = rows.filter((row) => row.state === "tripped").length;
  const items = rows
    .map(
      (row) =>
        `<li class="trace-detection">${code(row.detector)}${DETECTION_GLYPH[row.state]}</li>`,
    )
    .join("");
  return `<p class="muted">${tripped} tripped, ${rows.length - tripped} not tripped</p><ul class="trace-list">${items}</ul>`;
}

/** One aligned row: a label and one cell per agent. */
function rowMarkup(label: string, cells: readonly string[]): string {
  const columns = cells
    .map(
      (cell, column) =>
        `<div class="trace__cell" data-col="${column}">${cell}</div>`,
    )
    .join("");
  return `<div class="trace__row"><div class="trace__label">${label}</div>${columns}</div>`;
}

/** Scenario, seed and the injected line in the viewer header. */
function headerMarkup(input: TraceViewerInput): string {
  const [first] = input.traces;
  const injection = input.scenario.injection;
  const injected =
    injection === null || first.injection_evidence_id === null
      ? ""
      : `<span class="trace__injected">injected line: ${code(first.injection_evidence_id)}<span class="chip chip--trip">${icon("message-square-warning")}injected</span>on ${code(injection.node)}</span>`;
  return `<div class="trace__header"><p>${code(input.scenario.id)}, seed ${first.seed}</p>${injected}</div>`;
}

/** Segmented control and difference strip for narrow screens. */
function switcherMarkup(input: TraceViewerInput): string {
  const [first, second] = input.traces;
  const buttons = input.traces
    .map(
      (trace, column) =>
        `<button type="button" class="segmented__button" data-trace-show="${column}" aria-pressed="${column === 0}">${code(trace.agent)}</button>`,
    )
    .join("");
  const differences = traceDifferences(
    first,
    second,
    input.scenario,
    input.detectors,
  )
    .map((row) => `<li class="chip">${row}</li>`)
    .join("");
  return `<div class="trace__switcher"><div class="segmented" role="group" aria-label="Agent to show">${buttons}</div><p class="trace__diff">Rows that differ:</p><ul class="chip-list">${differences}</ul></div>`;
}

/** The s07 trace viewer comparing two agents read by read. */
export function traceViewer(input: TraceViewerInput): string {
  const { traces, scenario, detectors } = input;
  const each = (
    build: (trace: SampleTrace, column: number) => string,
  ): string[] => traces.map((trace, column) => build(trace, column));
  const heads = each(
    (trace) =>
      `<p class="trace__agent">${code(trace.agent)}</p><p class="muted">${agentRole(trace.agent)}</p>`,
  );
  return `<figure class="trace" id="trace-viewer" data-trace data-show="0" aria-labelledby="trace-title">
    <figcaption class="trace__caption"><h3 id="trace-title">One recorded run, read by read: ${code(shortScenarioId(scenario.id))} prompt injection</h3></figcaption>
    ${headerMarkup(input)}${switcherMarkup(input)}
    <div class="trace__grid">
      ${rowMarkup("", heads)}
      ${rowMarkup("Reads, in order", each(readsCell))}
      ${rowMarkup("Root cause", each(rootCell))}
      ${rowMarkup("Citations", each(citationsCell))}
      ${rowMarkup(
        "Actions",
        each((trace) => actionsCell(trace, scenario)),
      )}
      ${rowMarkup(
        `Detections (${detectors.length})`,
        each((trace) => detectionsCell(trace, detectors)),
      )}
    </div>
    <p class="trace__summary">${richText(traceSummary(traces[0], traces[1], scenario, detectors))}</p>
  </figure>`;
}

/** Wire the narrow-screen segmented control. */
export function bindTraceViewer(root: HTMLElement): void {
  const viewer = root.querySelector<HTMLElement>("[data-trace]");
  if (viewer === null) return;
  viewer.addEventListener("click", (event) => {
    const button = closestTarget(event, "[data-trace-show]");
    if (button === null) return;
    viewer.dataset.show = button.dataset.traceShow ?? "0";
    viewer.querySelectorAll("[data-trace-show]").forEach((item) => {
      item.setAttribute("aria-pressed", String(item === button));
    });
  });
}
