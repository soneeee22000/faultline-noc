import type { SampleTrace, ScenarioInfo, TraceStep } from "../types/payload";

/** Evidence sources an agent can read, in the order the harness lists them. */
export const EVIDENCE_SOURCES = ["alarms", "kpis", "logs"] as const;

/** How many citation chips show before the disclosure button. */
export const CITATION_PREVIEW_COUNT = 4;

const READ_KIND = "read";
const TOPOLOGY_SOURCE = "topology";
const ID_PREFIX: Record<(typeof EVIDENCE_SOURCES)[number], string> = {
  alarms: "alm-",
  kpis: "kpi-",
  logs: "log-",
};

/** One row of the "Reads, in order" list. */
export interface ReadRow {
  readonly order: number | null;
  readonly source: string;
  readonly status: "read" | "not_read";
  readonly recordCount: number | null;
  readonly includesInjection: boolean;
}

/** One proposed or executed action with its safety flags. */
export interface ActionRow {
  readonly kind: string;
  readonly target: string;
  readonly offRoot: boolean;
  readonly injected: boolean;
}

/** A detector verdict reduced to a display state. */
export type DetectionState = "tripped" | "clear" | "not_applicable";

/** One detection row. */
export interface DetectionRow {
  readonly detector: string;
  readonly state: DetectionState;
}

/** A telemetry lane on the Telemetry plane: cited ids plus the delivered count. */
export interface LaneTags {
  readonly source: string;
  readonly ids: readonly string[];
  readonly delivered: number | null;
}

/** Read steps only, sorted by their recorded index. */
function readSteps(trace: SampleTrace): TraceStep[] {
  return trace.steps
    .filter((step) => step.kind === READ_KIND && step.source !== null)
    .sort((a, b) => a.index - b.index);
}

/** Reads in recorded order, followed by evidence sources the agent never read. */
export function buildReadRows(trace: SampleTrace): ReadRow[] {
  const reads = readSteps(trace);
  const injectionId = trace.injection_evidence_id;
  const rows: ReadRow[] = reads.map((step, position) => ({
    order: position + 1,
    source: step.source ?? "",
    status: "read",
    recordCount: step.source === TOPOLOGY_SOURCE ? null : step.delivered_count,
    includesInjection:
      injectionId !== null && step.shown_evidence_ids.includes(injectionId),
  }));
  const seen = new Set(reads.map((step) => step.source));
  const missing = EVIDENCE_SOURCES.filter((source) => !seen.has(source)).map(
    (source): ReadRow => ({
      order: null,
      source,
      status: "not_read",
      recordCount: null,
      includesInjection: false,
    }),
  );
  return [...rows, ...missing];
}

/** The agent's actions, flagged when off the true root or equal to the injected instruction. */
export function buildActionRows(
  trace: SampleTrace,
  scenario: ScenarioInfo,
): ActionRow[] {
  const injected = scenario.injection?.action ?? null;
  return trace.rca.actions.map((action) => ({
    kind: action.kind,
    target: action.target,
    offRoot: action.target !== scenario.root_nf,
    injected:
      injected !== null &&
      action.kind === injected.kind &&
      action.target === injected.target,
  }));
}

/** The display state of one detector on a trace, or null when the trace has no verdict. */
function detectionState(
  trace: SampleTrace,
  detector: string,
): DetectionState | null {
  const verdict = trace.detections.find((item) => item.detector === detector);
  if (verdict === undefined) return null;
  if (!verdict.applicable) return "not_applicable";
  return verdict.tripped ? "tripped" : "clear";
}

/** Detection rows in detector order; a missing verdict is a data error. */
export function buildDetectionRows(
  trace: SampleTrace,
  detectors: readonly string[],
): DetectionRow[] {
  return detectors.map((detector) => {
    const state = detectionState(trace, detector);
    if (state === null)
      throw new Error(`No verdict for ${detector} on ${trace.agent}`);
    return { detector, state };
  });
}

/** Detectors that fired on a trace, in detector order. */
export function trippedDetectors(
  trace: SampleTrace,
  detectors: readonly string[],
): string[] {
  return detectors.filter(
    (detector) => detectionState(trace, detector) === "tripped",
  );
}

/** Names of the trace-viewer rows whose content differs between two agents. */
export function traceDifferences(
  first: SampleTrace,
  second: SampleTrace,
  scenario: ScenarioInfo,
  detectors: readonly string[],
): string[] {
  const signature = (trace: SampleTrace): Record<string, string> => ({
    Reads: JSON.stringify(buildReadRows(trace)),
    Actions: JSON.stringify(buildActionRows(trace, scenario)),
    Detections: JSON.stringify(
      detectors.map((detector) => detectionState(trace, detector)),
    ),
  });
  const left = signature(first);
  const right = signature(second);
  return Object.keys(left).filter((row) => left[row] !== right[row]);
}

/** Split citations into the visible chips and a hidden count. */
export function citationPreview(
  ids: readonly string[],
  visible: number = CITATION_PREVIEW_COUNT,
): { shown: string[]; hiddenCount: number } {
  return {
    shown: ids.slice(0, visible),
    hiddenCount: Math.max(ids.length - visible, 0),
  };
}

/** Cited ids grouped per evidence source, with the delivered count of that source's read. */
export function laneTags(trace: SampleTrace, perLane: number): LaneTags[] {
  const reads = readSteps(trace);
  return EVIDENCE_SOURCES.map((source) => ({
    source,
    ids: trace.rca.cited_evidence_ids
      .filter((id) => id.startsWith(ID_PREFIX[source]))
      .slice(0, perLane),
    delivered:
      reads.find((step) => step.source === source)?.delivered_count ?? null,
  }));
}
