import { barChartMarkup } from "../components/bar-chart";
import { bindHeatmap, heatmapMarkup } from "../components/heatmap";
import { BASELINE_AGENT, overallStat, payload } from "../data/payload";
import { bindDisclosures } from "../lib/disclosure";
import { code, esc, mount } from "../lib/dom";
import { icon } from "../lib/icons";
import { buildBarRows, scenarioBreakdown } from "../viewmodel/bars";
import { formatCount } from "../viewmodel/format";
import { buildMatrix } from "../viewmodel/matrix";

/** The harness check badge, with failures listed when it fails. */
function badgeMarkup(): string {
  const meta = payload.meta;
  const sub = `${meta.runs} runs, ${meta.seed_count} seeds per scenario`;
  if (meta.harness_pass)
    return `<div class="badge badge--pass" id="harness-badge">${icon("circle-check")}<span class="badge__label">Harness check: PASS</span><span class="badge__sub">${sub}</span></div>`;
  const failures = meta.failures
    .map((failure) => `<li>${esc(failure)}</li>`)
    .join("");
  return `<div class="badge badge--fail" id="harness-badge">${icon("circle-x")}<span class="badge__label">Harness check: FAIL</span><span class="badge__sub">${sub}</span><ul>${failures}</ul></div>`;
}

/** Both bar charts in report order. */
function chartsMarkup(): string {
  const meta = payload.meta;
  const accuracy = barChartMarkup({
    id: "chart-accuracy",
    title: "Top-1 accuracy, all scenarios",
    rows: buildBarRows(payload.accuracy_overall, meta.agents),
    tipFor: (row) =>
      scenarioBreakdown(
        payload.accuracy_per_scenario,
        row.agent,
        meta.scenarios,
      ).join("\n"),
  });
  const actions = barChartMarkup({
    id: "chart-actions",
    title:
      "Action correctness: every executed or proposed write targets the true root cause",
    rows: buildBarRows(payload.action_correctness, meta.agents),
    tipFor: (row) =>
      `${row.correct} of ${row.n} runs kept every executed or proposed write on the true root cause`,
  });
  return `<div class="results__charts" id="results-charts">${accuracy}${actions}</div>`;
}

/** "How to read these numbers": the three caveats. */
function caveatsMarkup(): string {
  const baseline = overallStat(payload.accuracy_overall, BASELINE_AGENT);
  return `<div class="caveats" id="results-caveats">
    <h3>How to read these numbers</h3>
    <p><strong>The harness discriminates; that is all this page shows.</strong> The agents here are a rule baseline, an oracle and mutants with planted defects. No LLM is called on this page, so nothing here shows that any AI works. Claude models are scored by the same detectors in the repo's model comparison.</p>
    <p><strong>These four scenarios are too easy.</strong> The rule baseline scores ${formatCount(baseline.correct, baseline.n)} on top-1 accuracy. Two harder scenarios defeat it, and they are what make the model comparison worth reading.</p>
    <p><strong>Simulated, not emulated.</strong> No protocol stack runs. The telemetry is synthetic and follows a hand-written dependency table, so nothing here shows how real core telemetry behaves.</p>
  </div>`;
}

/** Section 5: badge, bar charts, detection matrix and caveats. */
export function renderResults(): void {
  const meta = payload.meta;
  const matrix = buildMatrix(
    payload.detection_matrix,
    meta.agents,
    meta.detectors,
  );
  const section = mount(
    "results",
    `<div class="container">
      <div class="section-head">
        <h2 id="results-title">Results</h2>
        <p class="lede">From the committed run of ${code(meta.command)}: ${meta.agents.length} agents × ${meta.scenarios.length} scenarios × ${meta.seed_count} seeds. The page copies these figures; it does not run the harness.</p>
      </div>
      <div class="results">
        <div class="results__badge-row">${badgeMarkup()}</div>
        ${chartsMarkup()}
        ${heatmapMarkup(matrix)}
        ${caveatsMarkup()}
      </div>
    </div>`,
  );
  bindDisclosures(section);
  bindHeatmap(section);
}
