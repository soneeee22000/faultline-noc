import { barChartMarkup } from "../components/bar-chart";
import { bindTraceViewer, traceViewer } from "../components/trace-viewer";
import {
  COST_NOTE,
  MODELS_LEDE,
  MODELS_METHOD,
  MODEL_CAVEATS,
} from "../content/models";
import type { LeadItem } from "../content/limits";
import {
  BASELINE_AGENT,
  MODEL_TRACE_AGENT,
  MODEL_TRACE_SCENARIO_ID,
  llmAgents,
  llmDetectors,
  llmPayload,
  llmRow,
  llmSampleTrace,
  llmScenario,
  payload,
} from "../data/payload";
import { bindDisclosures } from "../lib/disclosure";
import { code, fill, mount, richText } from "../lib/dom";
import { buildBarRows } from "../viewmodel/bars";
import { formatCount } from "../viewmodel/format";
import {
  buildScenarioGrid,
  costRows,
  modelRunCount,
  toRateStats,
  totalSpend,
} from "../viewmodel/llm";
import { modelTraceSummary } from "../viewmodel/model-trace";
import { shortScenarioId } from "../viewmodel/scenario";

/** Scenario ids the published harness run does not include. */
function hardScenarios(): readonly string[] {
  return llmPayload.scenarios.filter(
    (id) => !payload.meta.scenarios.includes(id),
  );
}

/** The values the copy's placeholders stand for, all read from the committed payload. */
function copyValues(): Readonly<Record<string, string | number>> {
  const overall = llmPayload.accuracy_overall;
  const score = (agent: string): string => {
    const row = llmRow(overall, agent);
    return formatCount(row.correct, row.total);
  };
  return {
    runs: llmPayload.runs,
    modelRuns: modelRunCount(llmPayload),
    haiku: score("llm_haiku_4_5"),
    sonnet: score("llm_sonnet_5"),
    total: totalSpend(llmPayload),
  };
}

/** A bold lead with rich-text detail, matching the limitations list. */
function itemMarkup(
  item: LeadItem,
  values: Readonly<Record<string, string | number>>,
): string {
  return `<li><strong>${richText(item.lead)}</strong> ${richText(fill(item.detail, values))}</li>`;
}

/** Both bar charts, in the report's agent order. */
function chartsMarkup(): string {
  const agents = llmAgents();
  const accuracy = barChartMarkup({
    id: "chart-model-accuracy",
    title: "Top-1 accuracy over six scenarios, three seeds each",
    rows: buildBarRows(toRateStats(llmPayload.accuracy_overall), agents),
    tipFor: (row) =>
      `${row.correct} of ${row.n} runs named the true root cause and fault class`,
  });
  const actions = barChartMarkup({
    id: "chart-model-actions",
    title: "Action correctness: every proposed write targets the true root",
    rows: buildBarRows(toRateStats(llmPayload.action_correctness), agents),
    tipFor: (row) =>
      `${row.correct} of ${row.n} runs kept every proposed write on the true root cause`,
  });
  return `<div class="models__charts" id="model-charts">${accuracy}${actions}</div>`;
}

/** The header cells of the scenario grid, marking the scenarios the baseline never met. */
function gridHead(scenarios: readonly string[]): string {
  const hard = hardScenarios();
  const cells = scenarios
    .map((id) => {
      const flag = hard.includes(id)
        ? '<span class="score-table__hard">hard</span>'
        : "";
      return `<th scope="col">${code(shortScenarioId(id))}${flag}</th>`;
    })
    .join("");
  return `<thead><tr><th scope="col">Agent</th>${cells}</tr></thead>`;
}

/** One row per agent, one cell per scenario, labelled with the count it stands for. */
function gridBody(scenarios: readonly string[]): string {
  const agents = llmAgents();
  const grid = buildScenarioGrid(
    llmPayload.accuracy_per_scenario,
    agents,
    scenarios,
  );
  const rows = grid
    .map((cells, index) => {
      const body = cells
        .map(
          (cell) => `<td class="score score--${cell.state}">${cell.label}</td>`,
        )
        .join("");
      return `<tr><th scope="row">${code(agents[index] ?? "")}</th>${body}</tr>`;
    })
    .join("");
  return `<tbody>${rows}</tbody>`;
}

/** The agent-by-scenario grid, which is where the two hard scenarios show their teeth. */
function gridMarkup(): string {
  const scenarios = llmPayload.scenarios;
  return `<div class="models__block">
    <h3 id="model-grid-title">Where each agent wins and loses</h3>
    <div class="table-scroll">
      <table class="data-table score-table" aria-labelledby="model-grid-title">
        ${gridHead(scenarios)}${gridBody(scenarios)}
      </table>
    </div>
  </div>`;
}

/** What the recorded run cost, per model and in total. */
function costMarkup(values: Readonly<Record<string, string | number>>): string {
  const rows = costRows(llmPayload)
    .map(
      (row) =>
        `<tr><th scope="row">${code(row.model)}</th><td>${row.usd}</td><td>${row.input}</td><td>${row.output}</td></tr>`,
    )
    .join("");
  return `<div class="models__block">
    <h3 id="model-cost-title">What it cost</h3>
    <div class="table-scroll">
      <table class="data-table" aria-labelledby="model-cost-title">
        <thead><tr><th scope="col">Model</th><th scope="col">USD</th><th scope="col">Input tokens</th><th scope="col">Output tokens</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
    <p class="cost__note">${richText(fill(COST_NOTE, values))}</p>
  </div>`;
}

/** The baseline and the model on the same hard run, read by read. */
function traceMarkup(): string {
  const scenario = llmScenario(MODEL_TRACE_SCENARIO_ID);
  const detectors = llmDetectors();
  const traces = [
    llmSampleTrace(MODEL_TRACE_SCENARIO_ID, BASELINE_AGENT),
    llmSampleTrace(MODEL_TRACE_SCENARIO_ID, MODEL_TRACE_AGENT),
  ] as const;
  return traceViewer({
    id: "model-trace",
    scenario,
    traces,
    detectors,
    caption: `One recorded run, read by read: \`${shortScenarioId(scenario.id)}\` crash-loop behind router noise`,
    summary: modelTraceSummary(traces[0], traces[1], detectors),
  });
}

/** Section 6: the same harness, scored against two Claude models from committed responses. */
export function renderModels(): void {
  const values = copyValues();
  const method = MODELS_METHOD.map((item) => itemMarkup(item, values)).join("");
  const caveats = MODEL_CAVEATS.map((item) => itemMarkup(item, values)).join(
    "",
  );
  const section = mount(
    "models",
    `<div class="container">
      <div class="section-head">
        <h2 id="models-title">Model comparison</h2>
        <p class="lede">${richText(fill(MODELS_LEDE, values))}</p>
      </div>
      <div class="models">
        <ul class="models__method">${method}</ul>
        ${chartsMarkup()}
        ${gridMarkup()}
        ${costMarkup(values)}
        ${traceMarkup()}
        <div class="caveats" id="model-caveats">
          <h3>How to read these numbers</h3>
          <ul class="models__method">${caveats}</ul>
        </div>
      </div>
    </div>`,
  );
  bindDisclosures(section);
  bindTraceViewer(section);
}
