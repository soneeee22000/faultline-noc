/** A rate with its Wilson 95% interval, as exported by `faultline_noc/export.py`. */
export interface RateStat {
  readonly agent: string;
  readonly scope: string;
  readonly correct: number;
  readonly n: number;
  readonly rate: number;
  readonly wilson_low: number;
  readonly wilson_high: number;
}

/** One agent-by-detector cell of the detection matrix. */
export interface DetectionCell {
  readonly agent: string;
  readonly detector: string;
  readonly tripped: number;
  readonly applicable: number;
}

/** A write action proposed or executed by an agent. */
export interface ActionSpec {
  readonly kind: string;
  readonly target: string;
}

/** The fault the simulator injects for a scenario. */
export interface InjectedFault {
  readonly kind: string;
  readonly target: string;
  readonly start_tick: number;
  readonly period: number;
  readonly down_ticks: number;
  readonly silent_root: boolean;
}

/** A log line planted in telemetry that instructs the agent to act. */
export interface LogInjection {
  readonly node: string;
  readonly tick: number;
  readonly text: string;
  readonly action: ActionSpec;
}

/** Scenario metadata and ground truth. */
export interface ScenarioInfo {
  readonly id: string;
  readonly trap: string;
  readonly injected_fault: InjectedFault | null;
  readonly injection: LogInjection | null;
  readonly root_nf: string | null;
  readonly fault_class: string;
  readonly symptom_nfs: readonly string[];
}

/** One recorded step of an evidence session. */
export interface TraceStep {
  readonly index: number;
  readonly kind: string;
  readonly source: string | null;
  readonly delivered_count: number;
  readonly shown_evidence_ids: readonly string[];
  readonly hidden_count: number;
  readonly action: ActionSpec | null;
}

/** The structured RCA an agent returns. */
export interface RcaOutput {
  readonly root_cause_nf: string | null;
  readonly fault_class: string;
  readonly cited_evidence_ids: readonly string[];
  readonly confidence: number;
  readonly actions: readonly ActionSpec[];
}

/** One detector verdict on one run. */
export interface DetectionVerdict {
  readonly detector: string;
  readonly applicable: boolean;
  readonly tripped: boolean;
}

/** A full sample run: reads in order, the RCA and the detections. */
export interface SampleTrace {
  readonly scenario_id: string;
  readonly agent: string;
  readonly seed: number;
  readonly injection_evidence_id: string | null;
  readonly steps: readonly TraceStep[];
  readonly rca: RcaOutput;
  readonly correct: boolean;
  readonly writes_on_root_only: boolean;
  readonly detections: readonly DetectionVerdict[];
}

/** Run metadata for the committed `--all` run. */
export interface RunMeta {
  readonly command: string;
  readonly seed_count: number;
  readonly seed_first: number;
  readonly seed_last: number;
  readonly runs: number;
  readonly agents: readonly string[];
  readonly scenarios: readonly string[];
  readonly detectors: readonly string[];
  readonly harness_pass: boolean;
  readonly failures: readonly string[];
}

/** A proportion with its interval, as exported by `faultline_noc/llm/evaluate.py`. */
export interface LlmAccuracyRow {
  readonly agent: string;
  readonly scope: string;
  readonly correct: number;
  readonly total: number;
  readonly interval: { readonly low: number; readonly high: number };
}

/** Input and output tokens billed for one model. */
export interface LlmTokenCount {
  readonly input: number;
  readonly output: number;
}

/** The whole `llm_results.json` payload: a replay of the committed cassettes. */
export interface LlmResultsPayload {
  readonly schema_version: number;
  readonly command: string;
  readonly models: readonly string[];
  readonly scenarios: readonly string[];
  readonly seeds: readonly number[];
  readonly runs: number;
  readonly spend_usd: Readonly<Record<string, number>>;
  readonly tokens: Readonly<Record<string, LlmTokenCount>>;
  readonly accuracy_overall: readonly LlmAccuracyRow[];
  readonly accuracy_per_scenario: readonly LlmAccuracyRow[];
  readonly action_correctness: readonly LlmAccuracyRow[];
  readonly detection_matrix: readonly DetectionCell[];
  readonly sample_scenarios: readonly ScenarioInfo[];
  readonly sample_traces: readonly SampleTrace[];
}

/** The whole `results.json` payload (schema version 1). */
export interface ResultsPayload {
  readonly schema_version: number;
  readonly meta: RunMeta;
  readonly accuracy_overall: readonly RateStat[];
  readonly accuracy_per_scenario: readonly RateStat[];
  readonly action_correctness: readonly RateStat[];
  readonly detection_matrix: readonly DetectionCell[];
  readonly scenarios: readonly ScenarioInfo[];
  readonly sample_traces: readonly SampleTrace[];
}
