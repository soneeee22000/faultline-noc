import { barChartMarkup } from "../components/bar-chart";
import { bindHeatmap, heatmapMarkup } from "../components/heatmap";
import { routeFlowMarkup } from "../components/route-flow";
import type { LeadItem } from "../content/limits";
import {
  ACCURACY_CAVEAT,
  ACCURACY_CAVEAT_UNTIED,
  CALIBRATION_CAVEAT,
  CONTRACT_POINTS,
  DEPLOYMENT_NEEDS,
  GATE_POINTS,
  ROUTER_DATA_NOTE,
  ROUTER_LEDE,
  ROUTER_LIMITS,
  ROUTER_LINKS,
  ROUTER_MATRIX_NOTE,
  ROUTER_MATRIX_VERDICT,
  ROUTER_MATRIX_VERDICT_MIXED,
  ROUTER_RESULTS_LEDE,
  ROUTER_TITLE,
} from "../content/router";
import {
  CLARIFY_EXAMPLE_ITEM_ID,
  INJECTION_EXAMPLE_ITEM_ID,
  ROUTE_EXAMPLE_ITEM_ID,
  routerItem,
  routerMetrics,
  routerOutcome,
  routerPayload,
} from "../data/payload";
import { bindDisclosures } from "../lib/disclosure";
import { code, esc, fill, joinList, mount, richText } from "../lib/dom";
import { icon } from "../lib/icons";
import type {
  RoutePlanView,
  RouteStepView,
  RouterMetrics,
} from "../types/payload";
import { buildBarRows } from "../viewmodel/bars";
import { formatCount, formatInterval, formatRate } from "../viewmodel/format";
import {
  buildRouteFlow,
  buildRouterMatrix,
  countTagged,
  detectorsBeyondBaseline,
  eachMutantHasOneDetector,
  formatMetric,
  newTrips,
  routeAccuracyStats,
  routerHeadings,
  routersTiedWithBaseline,
} from "../viewmodel/router";

type Values = Readonly<Record<string, string | number>>;

const UNGATED_MUTANT = "mutant_ungated_write";
const WRITE_CAPABILITY = "network_write";
const UNSAFE_WRITE = "unsafe_write";
const MISROUTE = "misroute";

/** Routers other than the baseline, in report order. */
function mutants(): readonly string[] {
  const meta = routerPayload.meta;
  return meta.routers.filter((router) => router !== meta.baseline);
}

/** A detection cell's `tripped/applicable` label, or a loud failure. */
function cellLabel(router: string, detector: string): string {
  const cell = routerPayload.detection_matrix.find(
    (entry) => entry.router === router && entry.detector === detector,
  );
  if (cell === undefined)
    throw new Error(
      `Cell ${router}/${detector} missing from router_results.json`,
    );
  return `${cell.tripped}/${cell.applicable}`;
}

/** Every value the copy's placeholders stand for, all read from the committed payload. */
function copyValues(): Values {
  const meta = routerPayload.meta;
  const baseline = routerMetrics(meta.baseline);
  const ungated = routerMetrics(UNGATED_MUTANT);
  return {
    command: meta.command,
    items: meta.items,
    bins: meta.calibration_bins,
    mutants: mutants().length,
    detectors: meta.detectors.length,
    tied: routersTiedWithBaseline(routerPayload.metrics, meta.baseline).length,
    injectionItems: countTagged(routerPayload.items, "injection"),
    injection: formatMetric(baseline.injection_resistance),
    gate: formatMetric(baseline.unsafe_write_gate_recall),
    grant: formatMetric(baseline.write_grant_recall),
    ungated: UNGATED_MUTANT,
    ungatedGate: formatMetric(ungated.unsafe_write_gate_recall),
    baseline: formatCount(baseline.route_correct, baseline.items),
    interval: formatInterval(
      baseline.route_interval.low,
      baseline.route_interval.high,
    ),
    baselineMisroute: cellLabel(meta.baseline, MISROUTE),
    routerDoc: ROUTER_LINKS.doc,
  };
}

/** A bold lead with rich-text detail, matching the other sections' lists. */
function listMarkup(items: readonly LeadItem[], values: Values): string {
  return items
    .map(
      (item) =>
        `<li><strong>${richText(item.lead)}</strong> ${richText(fill(item.detail, values))}</li>`,
    )
    .join("");
}

/** Refs or capabilities as mono chips. */
function chips(values: readonly string[]): string {
  return values
    .map((value) => `<span class="chip chip--code">${esc(value)}</span>`)
    .join("");
}

/** One field row of a step card. */
function field(name: string, value: string): string {
  return `<div><dt>${code(name)}</dt><dd>${value}</dd></div>`;
}

/** One `RouteStep`, field by field, from a committed plan. */
function stepMarkup(step: RouteStepView, index: number): string {
  return `<li class="route-step">
    <p class="route-step__head"><code>RouteStep</code><span class="muted">step ${index + 1}</span></p>
    <dl class="route-step__fields">
      ${field("agent", code(step.agent))}
      ${field("objective", esc(step.objective))}
      ${field("context_refs", chips(step.context_refs))}
      ${field("allowed_capabilities", chips(step.allowed_capabilities))}
      ${field("requires_confirmation", code(String(step.requires_confirmation)))}
    </dl>
  </li>`;
}

/** The plan-level fields shown above its steps. */
function planHead(plan: RoutePlanView): string {
  return `<p class="route-plan__head"><code>RoutePlan</code><span class="muted">${code("requires_clarification")} ${code(String(plan.requires_clarification))} · ${code("confidence")} ${code(formatRate(plan.confidence))}</span></p>`;
}

/** The clarification outcome: a plan with no steps and one question. */
function clarifyMarkup(): string {
  const item = routerItem(CLARIFY_EXAMPLE_ITEM_ID);
  const plan = routerOutcome(routerPayload.meta.baseline, item.id).plan;
  return `<div class="route-plan route-plan--clarify">
    <p class="route-diagram__label">Or, when the request is ambiguous: ${code(item.id)}</p>
    <blockquote class="route-diagram__request"><p>${esc(item.request)}</p></blockquote>
    ${planHead(plan)}
    <dl class="route-step__fields">
      ${field("steps", code(`[${plan.steps.length === 0 ? "" : "…"}]`))}
      ${field("clarification_question", esc(plan.clarification_question ?? ""))}
    </dl>
    <p class="muted route-plan__note">An outcome of the plan, not a fourth agent.</p>
  </div>`;
}

/** The shape of the plan, drawn: ordered steps, the write gate, and the context handed on. */
function flowMarkup(plan: RoutePlanView, itemId: string): string {
  const steps = buildRouteFlow(plan, WRITE_CAPABILITY);
  return `<div class="route-diagram__flow">
    <p class="route-diagram__label">The shape of the plan for ${code(itemId)}</p>
    ${routeFlowMarkup(steps)}
  </div>`;
}

/** The contract drawn from two committed plans: an ordered route and a clarification. */
function contractMarkup(): string {
  const item = routerItem(ROUTE_EXAMPLE_ITEM_ID);
  const plan = routerOutcome(routerPayload.meta.baseline, item.id).plan;
  return `<figure class="route-diagram" id="route-contract" aria-labelledby="route-contract-caption">
    <figcaption class="route-diagram__caption" id="route-contract-caption">A ${code("RoutePlan")} as an ordered list of ${code("RouteStep")} objects, then two items from the challenge set and the plans the keyword baseline returned for them, field by field.</figcaption>
    ${flowMarkup(plan, item.id)}
    <div class="route-diagram__body">
      <div class="route-plan">
        <p class="route-diagram__label">Request ${code(item.id)}</p>
        <blockquote class="route-diagram__request"><p>${esc(item.request)}</p></blockquote>
        ${planHead(plan)}
        <ol class="route-plan__steps">${plan.steps.map(stepMarkup).join("")}</ol>
      </div>
      ${clarifyMarkup()}
    </div>
  </figure>`;
}

/** The injection item: a quoted log line that asks for a write, and the plan that grants none. */
function injectionMarkup(): string {
  const item = routerItem(INJECTION_EXAMPLE_ITEM_ID);
  const outcome = routerOutcome(routerPayload.meta.baseline, item.id);
  const writes = outcome.plan.steps.some((step) =>
    step.allowed_capabilities.includes(WRITE_CAPABILITY),
  );
  const agents = joinList(outcome.plan.steps.map((step) => code(step.agent)));
  const state = outcome.tripped.includes(UNSAFE_WRITE)
    ? `<span class="state state--trip">${icon("diamond", "icon--filled")}${code(UNSAFE_WRITE)} tripped</span>`
    : `<span class="state state--pass">${icon("circle")}${code(UNSAFE_WRITE)} clear</span>`;
  return `<figure class="specimen router__specimen" aria-label="Challenge item ${esc(item.id)}">
    <div class="specimen__head">${code(item.id)}<span class="chip chip--trip">${icon("message-square-warning")}injected</span></div>
    <blockquote class="specimen__text"><p>${esc(item.request)}</p></blockquote>
    <figcaption class="specimen__caption">The user asked a question. The instruction sits inside a quoted log line.</figcaption>
    <p class="specimen__result">${code(routerPayload.meta.baseline)}<span aria-hidden="true">→</span><span class="sr-only">plans</span><span class="specimen__plan">${agents}, ${writes ? "grants a write" : `no ${code(WRITE_CAPABILITY)}`}</span>${state}</p>
  </figure>`;
}

/** The harness check badge, with failures listed when it fails. */
function badgeMarkup(): string {
  const meta = routerPayload.meta;
  const sub = `${meta.items} items, ${meta.routers.length} routers`;
  if (meta.harness_pass)
    return `<div class="badge badge--pass" id="router-badge">${icon("circle-check")}<span class="badge__label">Harness check: PASS</span><span class="badge__sub">${sub}</span></div>`;
  const failures = meta.failures
    .map((failure) => `<li>${esc(failure)}</li>`)
    .join("");
  return `<div class="badge badge--fail" id="router-badge">${icon("circle-x")}<span class="badge__label">Harness check: FAIL</span><span class="badge__sub">${sub}</span><ul>${failures}</ul></div>`;
}

/** Ordered-route accuracy per router with Wilson whiskers, in report order. */
function accuracyMarkup(values: Values): string {
  const meta = routerPayload.meta;
  const headings = routerHeadings(meta.routers, meta.baseline);
  const rows = buildBarRows(
    routeAccuracyStats(routerPayload.metrics),
    meta.routers,
  ).map((row, index) => ({ ...row, groupHeading: headings[index] ?? null }));
  const chart = barChartMarkup({
    id: "chart-router-accuracy",
    title: `Ordered-route accuracy over ${meta.items} authored items`,
    rows,
    tipFor: (row) =>
      `${row.correct} of ${row.n} items got the exact ordered route, counting the clarification outcome`,
    subject: { one: "Router", many: "routers" },
  });
  const caveat = values.tied === 0 ? ACCURACY_CAVEAT_UNTIED : ACCURACY_CAVEAT;
  return `<div class="router__chart">${chart}<p class="router__caveat">${richText(fill(caveat, values))}</p></div>`;
}

/** The mutant-to-detector pairs the committed run shows beyond the baseline. */
function verdictMarkup(values: Values): string {
  const meta = routerPayload.meta;
  const trips = newTrips(routerPayload.outcomes, meta.baseline);
  if (!eachMutantHasOneDetector(trips, mutants(), meta.detectors))
    return `<p class="router__verdict">${richText(fill(ROUTER_MATRIX_VERDICT_MIXED, values))}</p>`;
  const pairs = joinList(
    mutants().map(
      (router) =>
        `\`${router}\` → \`${detectorsBeyondBaseline(trips, router, meta.detectors).join("")}\``,
    ),
  );
  return `<p class="router__verdict">${richText(fill(ROUTER_MATRIX_VERDICT, { ...values, pairs }))}</p>`;
}

/** The router-by-detector heatmap, reusing the results section's component. */
function matrixMarkup(values: Values): string {
  const meta = routerPayload.meta;
  const view = buildRouterMatrix(
    routerPayload.detection_matrix,
    meta.routers,
    meta.detectors,
    meta.baseline,
    routerPayload.outcomes,
  );
  const extraLegend = `<p class="heat-legend__item">${icon("crosshair")}<span>+N new: trips on items where the baseline stays clear</span></p>`;
  const heatmap = heatmapMarkup(view, {
    id: "router-matrix",
    titleId: "router-matrix-title",
    captionId: "router-legend-caption",
    keysId: "router-matrix-keys",
    title: "Detection matrix: router × detector",
    caption: "Share of applicable items where the detector fired",
    note: ROUTER_MATRIX_NOTE,
    rowHeader: "Router",
    extraLegend,
  });
  return `${heatmap}${verdictMarkup(values)}`;
}

/** The safety columns first, then quality, then the two pairs and calibration. */
const METRIC_HEADERS: readonly string[] = [
  "Router",
  "Gate recall",
  "Injection resistance",
  "Write-grant recall",
  "Macro-F1",
  "Clarification P / R",
  "Handoff P / R",
  "Brier",
  "ECE",
];

/** A precision and recall pair in one cell, either half of which may have no denominator. */
function pair(precision: number | null, recall: number | null): string {
  return `${formatMetric(precision)} / ${formatMetric(recall)}`;
}

/** One router's row: the same numbers the report prints, with neither half of a pair dropped. */
function metricsRow(row: RouterMetrics): string {
  const cells = [
    formatMetric(row.unsafe_write_gate_recall),
    formatMetric(row.injection_resistance),
    formatMetric(row.write_grant_recall),
    formatMetric(row.macro_f1),
    pair(row.clarification_precision, row.clarification_recall),
    pair(row.handoff_precision, row.handoff_completeness),
    formatMetric(row.brier),
    formatMetric(row.ece),
  ]
    .map((value) => `<td>${value}</td>`)
    .join("");
  return `<tr><th scope="row">${code(row.router)}</th>${cells}</tr>`;
}

/** Safety and calibration metrics per router, with the small-n caveat. */
function metricsTableMarkup(values: Values): string {
  const rows = routerPayload.metrics.map(metricsRow).join("");
  const headers = METRIC_HEADERS.map(
    (label) => `<th scope="col">${label}</th>`,
  ).join("");
  return `<div class="models__block" id="router-metrics">
    <h3 id="router-metrics-title">Safety and calibration, per router</h3>
    <p class="scroll-hint" data-scroll-region="router-metrics-scroll">Scroll sideways for all ${METRIC_HEADERS.length - 1} metrics.</p>
    <div class="table-scroll" id="router-metrics-scroll" role="region" aria-labelledby="router-metrics-title" tabindex="0">
      <table class="data-table" aria-labelledby="router-metrics-title">
        <thead><tr>${headers}</tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
    <p class="cost__note">Clarification and handoff are reported as precision / recall, where handoff recall is completeness: handing every available ref to every step costs precision. ${richText(fill(CALIBRATION_CAVEAT, values))} A rate with no denominator prints as ${code("n/a")}, not zero.</p>
  </div>`;
}

/** The limits and what a real deployment would need, side by side from 768. */
function limitsMarkup(values: Values): string {
  return `<div class="limits router__limits">
    <div class="limits__col" id="router-limits"><h3>Honest limits</h3><ul class="limits__list">${listMarkup(ROUTER_LIMITS, values)}</ul></div>
    <div class="limits__col" id="router-needs"><h3>What real deployment would need</h3><ol class="limits__list">${listMarkup(DEPLOYMENT_NEEDS, values)}</ol></div>
  </div>`;
}

/** The design doc, the ADR and the command that reproduces every number. */
function linksMarkup(): string {
  return `<div class="router__links" id="router-links">
    <div class="router__actions">
      <a class="button" href="${ROUTER_LINKS.doc}">Read docs/ROUTER.md</a>
      <a class="button" href="${ROUTER_LINKS.adr}">Read ADR-002</a>
    </div>
    <p class="data-note">${icon("info")}<span>Reproduce the metrics, the matrix and the verdict: ${code(routerPayload.meta.command)}. Adding ${code("--json router_results.json")} writes the payload this section is built from, per item and per plan.</span></p>
  </div>`;
}

/** A design note: routing one request across three specialists, and the harness that scores it. */
export function renderRouter(): void {
  const values = copyValues();
  const section = mount(
    "router",
    `<div class="container">
      <div class="section-head">
        <p><span class="label-badge">Design note</span></p>
        <h2 id="router-title">${esc(ROUTER_TITLE)}</h2>
        <p class="lede">${esc(ROUTER_LEDE)}</p>
        <p class="data-note">${icon("info")}<span>${richText(fill(ROUTER_DATA_NOTE, values))}</span></p>
      </div>
      <div class="models router">
        <div class="models__block">
          <h3 id="route-contract-title">The contract</h3>
          <ul class="models__method">${listMarkup(CONTRACT_POINTS, values)}</ul>
          ${contractMarkup()}
        </div>
        <div class="models__block router__gate">
          <h3>The safety gate</h3>
          <div class="router__gate-body">
            <ul class="models__method">${listMarkup(GATE_POINTS, values)}</ul>
            ${injectionMarkup()}
          </div>
        </div>
        <div class="models__block" id="router-results">
          <p class="lede">${richText(fill(ROUTER_RESULTS_LEDE, values))}</p>
          <div class="results__badge-row">${badgeMarkup()}</div>
          ${accuracyMarkup(values)}
          ${matrixMarkup(values)}
        </div>
        ${metricsTableMarkup(values)}
        ${limitsMarkup(values)}
        ${linksMarkup()}
      </div>
    </div>`,
  );
  bindDisclosures(section);
  bindHeatmap(section);
}
