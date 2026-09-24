import type {
  DetectionCell,
  LlmAccuracyRow,
  LlmResultsPayload,
  LlmRouterPayload,
  RateStat,
  ResultsPayload,
  RouterItem,
  RouterMetrics,
  RouterOutcome,
  RouterResultsPayload,
  SampleTrace,
  ScenarioInfo,
} from "../types/payload";
import { type Transcript, parseTranscript } from "../viewmodel/transcript";
import llmResults from "./llm_results.json";
import results from "./results.json";
import routerLlmResults from "./router_llm_results.json";
import routerResults from "./router_results.json";
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

/** The committed `python -m faultline_noc.llm --replay` payload, bundled at build time. */
export const llmPayload: LlmResultsPayload = llmResults;

/** The hard scenario whose run the model section shows read by read. */
export const MODEL_TRACE_SCENARIO_ID = "s08_smf_crashloop_router_noise";
/** The model compared against the rule baseline in that trace. */
export const MODEL_TRACE_AGENT = "llm_sonnet_5";

/** Every agent scored in the model comparison, in report order. */
export function llmAgents(): readonly string[] {
  return llmPayload.accuracy_overall.map((row) => row.agent);
}

/** Every detector scored in the model comparison, in report order. */
export function llmDetectors(): readonly string[] {
  return [...new Set(llmPayload.detection_matrix.map((cell) => cell.detector))];
}

/** An LLM accuracy row for one agent over one scope, or a loud failure. */
export function llmRow(
  rows: readonly LlmAccuracyRow[],
  agent: string,
  scope = "all",
): LlmAccuracyRow {
  const row = rows.find((item) => item.agent === agent && item.scope === scope);
  if (row === undefined)
    throw new Error(`Row ${agent}/${scope} missing from llm_results.json`);
  return row;
}

/** A sample trace from the model run, or a loud failure. */
export function llmSampleTrace(scenarioId: string, agent: string): SampleTrace {
  const trace = llmPayload.sample_traces.find(
    (item) => item.scenario_id === scenarioId && item.agent === agent,
  );
  if (trace === undefined)
    throw new Error(
      `Sample trace ${scenarioId}/${agent} missing from llm_results.json`,
    );
  return trace;
}

/** A sampled scenario's metadata and ground truth, or a loud failure. */
export function llmScenario(id: string): ScenarioInfo {
  const scenario = llmPayload.sample_scenarios.find((item) => item.id === id);
  if (scenario === undefined)
    throw new Error(`Scenario ${id} missing from llm_results.json`);
  return scenario;
}

/** The committed `python -m faultline_noc.router --all` payload, bundled at build time. */
export const routerPayload: RouterResultsPayload = routerResults;

/** A multi-step item with a gated write, drawn as the route contract. */
export const ROUTE_EXAMPLE_ITEM_ID = "r34_rollback_then_retest";
/** An ambiguous item whose right answer is a clarification. */
export const CLARIFY_EXAMPLE_ITEM_ID = "r38_restart_it";
/** An item whose quoted log line asks for a restart the user never requested. */
export const INJECTION_EXAMPLE_ITEM_ID = "r05_quoted_log_injection";

/** A challenge item by id, or a loud failure. */
export function routerItem(id: string): RouterItem {
  const item = routerPayload.items.find((entry) => entry.id === id);
  if (item === undefined)
    throw new Error(`Item ${id} missing from router_results.json`);
  return item;
}

/** One router's outcome on one item, or a loud failure. */
export function routerOutcome(router: string, itemId: string): RouterOutcome {
  const outcome = routerPayload.outcomes.find(
    (entry) => entry.router === router && entry.item_id === itemId,
  );
  if (outcome === undefined)
    throw new Error(
      `Outcome ${router}/${itemId} missing from router_results.json`,
    );
  return outcome;
}

/** One router's set-level metrics, or a loud failure. */
export function routerMetrics(router: string): RouterMetrics {
  const row = routerPayload.metrics.find((entry) => entry.router === router);
  if (row === undefined)
    throw new Error(`Metrics for ${router} missing from router_results.json`);
  return row;
}

/** The committed `python -m faultline_noc.router.llm --replay --all --json` payload. */
export const llmRouterPayload: LlmRouterPayload = routerLlmResults;
