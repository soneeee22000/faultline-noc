import { joinList } from "../lib/dom";
import type { SampleTrace, ScenarioInfo } from "../types/payload";
import { buildActionRows, buildReadRows, trippedDetectors } from "./trace";

const LOG_SOURCE = "logs";
const CLOSING =
  "Both are mock agents, so this says nothing about how an LLM would behave.";

/** Wrap an identifier in backticks for rich text. */
function tick(value: string): string {
  return `\`${value}\``;
}

/** Which root cause each agent names, collapsed when they agree. */
function namingSentence(first: SampleTrace, second: SampleTrace): string {
  const firstRoot = first.rca.root_cause_nf ?? "none";
  const secondRoot = second.rca.root_cause_nf ?? "none";
  if (firstRoot === secondRoot) return `Both agents name ${tick(firstRoot)}.`;
  return `${tick(first.agent)} names ${tick(firstRoot)}; ${tick(second.agent)} names ${tick(secondRoot)}.`;
}

/** What one agent did with the injected line. */
function injectionClause(trace: SampleTrace, scenario: ScenarioInfo): string {
  const reads = buildReadRows(trace);
  const sawInjection = reads.some((row) => row.includesInjection);
  const readLogs = reads.some(
    (row) => row.source === LOG_SOURCE && row.status === "read",
  );
  if (!readLogs)
    return `${tick(trace.agent)} did not read logs in this run, so it never saw the injected line`;
  if (!sawInjection)
    return `${tick(trace.agent)} read logs but was not shown the injected line`;
  const followed = buildActionRows(trace, scenario)
    .filter((row) => row.injected)
    .map((row) => tick(`${row.kind} ${row.target}`));
  const lead = `${tick(trace.agent)} read the injected line ${tick(trace.injection_evidence_id ?? "")}`;
  return followed.length === 0
    ? `${lead} and did not act on it`
    : `${lead} and proposed ${joinList(followed)}`;
}

/** One agent's sentence: its injection clause and the detectors that fired. */
function agentSentence(
  trace: SampleTrace,
  scenario: ScenarioInfo,
  detectors: readonly string[],
): string {
  const tripped = trippedDetectors(trace, detectors).map(tick);
  const verdict =
    tripped.length === 0 ? "no detector fired" : `${joinList(tripped)} fired`;
  return `${injectionClause(trace, scenario)}; ${verdict}.`;
}

/** The templated comparison under the trace viewer, in rich text. */
export function traceSummary(
  first: SampleTrace,
  second: SampleTrace,
  scenario: ScenarioInfo,
  detectors: readonly string[],
): string {
  return [
    namingSentence(first, second),
    agentSentence(first, scenario, detectors),
    agentSentence(second, scenario, detectors),
    CLOSING,
  ].join(" ");
}
