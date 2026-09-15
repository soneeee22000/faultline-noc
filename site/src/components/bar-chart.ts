import { disclosureButton } from "../lib/disclosure";
import { code, esc, richText } from "../lib/dom";
import { barGeometry, chartSummary } from "../viewmodel/bar-geometry";
import { AXIS_TICKS, type BarRow } from "../viewmodel/bars";
import { formatTick } from "../viewmodel/format";

const BAR_HEIGHT = 12;
const WHISKER_Y = 6;
const CAP_TOP = 2;
const CAP_BOTTOM = 10;
const BAR_RADIUS = 4;
const ZERO_STUB_WIDTH = 2;

/** What a bar chart shows and how each row explains itself. */
export interface BarChartOptions {
  readonly id: string;
  readonly title: string;
  readonly rows: readonly BarRow[];
  readonly tipFor: (row: BarRow) => string;
}

/** The filled bar: square at the baseline, rounded at the data end, or a stub for zero. */
function barMarkup(row: BarRow): string {
  const geometry = barGeometry(row.rate, row.low, row.high);
  if (geometry.isZero)
    return `<rect class="svg-bar" width="${ZERO_STUB_WIDTH}" height="${BAR_HEIGHT}"/>`;
  return `<rect class="svg-bar" width="${geometry.barPercent}%" height="${BAR_HEIGHT}" rx="${BAR_RADIUS}"/><rect class="svg-bar" width="${geometry.squarePercent}%" height="${BAR_HEIGHT}"/>`;
}

/** Whisker lines from low to high with 8px caps, drawn in a given class. */
function whiskerLines(low: number, high: number, className: string): string {
  return [
    `<line class="${className}" x1="${low}%" x2="${high}%" y1="${WHISKER_Y}" y2="${WHISKER_Y}"/>`,
    `<line class="${className}" x1="${low}%" x2="${low}%" y1="${CAP_TOP}" y2="${CAP_BOTTOM}"/>`,
    `<line class="${className}" x1="${high}%" x2="${high}%" y1="${CAP_TOP}" y2="${CAP_BOTTOM}"/>`,
  ].join("");
}

/** The bar line of one row: track, bar, and a haloed Wilson whisker. */
function barSvg(row: BarRow): string {
  const geometry = barGeometry(row.rate, row.low, row.high);
  const low = geometry.lowPercent;
  const high = geometry.highPercent;
  return `<svg class="bar-row__bar" width="100%" height="${BAR_HEIGHT}" aria-hidden="true" focusable="false">
    <rect class="svg-track" width="100%" height="${BAR_HEIGHT}"/>${barMarkup(row)}
    ${whiskerLines(low, high, "whisker-halo")}${whiskerLines(low, high, "whisker")}
  </svg>`;
}

/** One focusable row: label line and bar line. */
function rowMarkup(row: BarRow, tip: string): string {
  const divider =
    row.groupHeading === null
      ? ""
      : `<li class="bar-divider">${esc(row.groupHeading)}</li>`;
  return `${divider}<li class="bar-row" tabindex="0" data-tip="${esc(tip)}">
    <div class="bar-row__label">${code(row.agent)}<span class="bar-row__values"><span>${row.countLabel}</span><strong>${row.rateLabel}</strong><span class="bar-row__interval">${row.intervalLabel}</span></span></div>
    ${barSvg(row)}
  </li>`;
}

/** Gridlines behind the rows and the tick labels below them. */
function axisMarkup(): { grid: string; ticks: string } {
  const lines = AXIS_TICKS.map(
    (tick) =>
      `<line class="${tick === 0 ? "grid-baseline" : "grid-line"}" x1="${tick * 100}%" x2="${tick * 100}%" y1="0" y2="100%"/>`,
  ).join("");
  const ticks = AXIS_TICKS.map(
    (tick) =>
      `<span class="bar-axis__tick" style="--at: ${tick * 100}%">${formatTick(tick)}</span>`,
  ).join("");
  return {
    grid: `<svg class="bar-chart__grid" width="100%" height="100%" aria-hidden="true" focusable="false">${lines}</svg>`,
    ticks: `<div class="bar-axis" aria-hidden="true">${ticks}</div>`,
  };
}

/** The table view with the same values as the bars. */
function tableMarkup(options: BarChartOptions): string {
  const body = options.rows
    .map(
      (row) =>
        `<tr><th scope="row">${code(row.agent)}</th><td>${row.countLabel}</td><td>${row.rateLabel}</td><td>${row.intervalLabel}</td></tr>`,
    )
    .join("");
  return `<div class="table-scroll" id="${options.id}-table" hidden><table class="data-table">
    <caption class="sr-only">${esc(options.title)}</caption>
    <thead><tr><th scope="col">Agent</th><th scope="col">Correct / N</th><th scope="col">Rate</th><th scope="col">Wilson 95% interval</th></tr></thead>
    <tbody>${body}</tbody></table></div>`;
}

/** A horizontal bar chart with Wilson whiskers, a summary, and a table toggle. */
export function barChartMarkup(options: BarChartOptions): string {
  const axis = axisMarkup();
  const rows = options.rows
    .map((row) => rowMarkup(row, options.tipFor(row)))
    .join("");
  return `<figure class="bar-chart" id="${options.id}" aria-labelledby="${options.id}-title" aria-describedby="${options.id}-desc">
    <figcaption class="bar-chart__head"><h3 id="${options.id}-title">${esc(options.title)}</h3><p class="bar-chart__desc" id="${options.id}-desc">${richText(chartSummary(options.rows))} Whiskers show Wilson 95% intervals.</p></figcaption>
    <div class="bar-chart__plot">${axis.grid}<ol class="bar-list">${rows}</ol></div>
    ${axis.ticks}
    ${disclosureButton(`${options.id}-table`, "Show table", "Hide table")}
    ${tableMarkup(options)}
  </figure>`;
}
