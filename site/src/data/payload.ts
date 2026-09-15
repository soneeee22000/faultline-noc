import type {
  DetectionCell,
  RateStat,
  ResultsPayload,
  SampleTrace,
  ScenarioInfo,
} from "../types/payload";
import { type Transcript, parseTranscript } from "../viewmodel/transcript";
import results from "./results.json";
import mypyRaw from "./transcripts/mypy.txt?raw";
import pytestRaw from "./transcripts/pytest.txt?raw";
import smokeRaw from "./transcripts/smoke.txt?raw";

/** The committed `python -m faultline_noc --all --json` payload, bundled at build time. */
export const payload: ResultsPayload = results;

/** A transcript tab: a stable id and the parsed transcript. */
export interface TranscriptEntry {
  readonly id: string;
  readonly transcript: Transcript;
}

/** The captured transcripts, in replay order. */
export const TRANSCRIPTS: readonly TranscriptEntry[] = [
  { id: "smoke", transcript: parseTranscript(smokeRaw) },
  { id: "pytest", transcript: parseTranscript(pytestRaw) },
  { id: "mypy", transcript: parseTranscript(mypyRaw) },
];

/** The scenario whose sample traces the page compares. */
export const INJECTION_SCENARIO_ID = "s07_log_injection";
/** The evaluated agent shown in the trace viewer; it never receives ground truth. */
export const BASELINE_AGENT = "rule_baseline";
/** The mutant shown in the trace viewer and on the Agent plane. */
export const INJECTION_MUTANT = "mutant_follows_injection";

/** A scenario by id, or a loud failure. */
export function scenarioById(id: string): ScenarioInfo {
  const scenario = payload.scenarios.find((item) => item.id === id);
  if (scenario === undefined)
    throw new Error(`Scenario ${id} missing from results.json`);
  return scenario;
}

/** A sample trace by scenario and agent, or a loud failure. */
export function sampleTrace(scenarioId: string, agent: string): SampleTrace {
  const trace = payload.sample_traces.find(
    (item) => item.scenario_id === scenarioId && item.agent === agent,
  );
  if (trace === undefined)
    throw new Error(
      `Sample trace ${scenarioId}/${agent} missing from results.json`,
    );
  return trace;
}

/** One detection-matrix cell, or a loud failure. */
export function detectionCell(agent: string, detector: string): DetectionCell {
  const cell = payload.detection_matrix.find(
    (item) => item.agent === agent && item.detector === detector,
  );
  if (cell === undefined)
    throw new Error(
      `Detection cell ${agent}/${detector} missing from results.json`,
    );
  return cell;
}

/** An overall rate stat for an agent, or a loud failure. */
export function overallStat(
  stats: readonly RateStat[],
  agent: string,
): RateStat {
  const stat = stats.find((item) => item.agent === agent);
  if (stat === undefined)
    throw new Error(`Rate stat for ${agent} missing from results.json`);
  return stat;
}
