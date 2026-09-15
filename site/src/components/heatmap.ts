import { breakable, closestTarget, code, esc } from "../lib/dom";
import { moveCell } from "../viewmodel/grid-focus";
import type { HeatBin, MatrixCellView, MatrixView } from "../viewmodel/matrix";

const HIGHLIGHT_CLASS = "is-highlighted";
const SCALE: readonly { readonly bin: HeatBin; readonly label: string }[] = [
  { bin: 0, label: "0" },
  { bin: 1, label: "up to 25%" },
  { bin: 2, label: "up to 50%" },
  { bin: 3, label: "under 100%" },
  { bin: 4, label: "100%" },
];

/** The five-swatch scale legend. */
function legendMarkup(): string {
  const items = SCALE.map(
    (step) =>
      `<li class="heat-legend__item"><span class="heat-legend__swatch heat--${step.bin}" aria-hidden="true"></span>${step.label}</li>`,
  ).join("");
  return `<div class="heat-legend"><p class="heat-legend__caption" id="heat-legend-caption">Share of applicable runs where the detector fired</p><ul class="heat-legend__scale" aria-labelledby="heat-legend-caption">${items}</ul></div>`;
}

/** One cell with its count label and templated description; only the first cell is a Tab stop. */
function cellMarkup(
  cell: MatrixCellView,
  rowIndex: number,
  colIndex: number,
): string {
  const tabindex = rowIndex === 0 && colIndex === 0 ? 0 : -1;
  return `<td class="heat heat--${cell.bin} heat-tone--${cell.tone}" tabindex="${tabindex}" data-row="${rowIndex}" data-col="${colIndex}" data-tip="${esc(cell.description)}">${cell.label}</td>`;
}

/** Table body rows, with a group heading wherever the agent group changes. */
function bodyMarkup(view: MatrixView): string {
  const span = view.columns.length + 1;
  return view.rows
    .map((row, rowIndex) => {
      const divider =
        row.groupHeading === null
          ? ""
          : `<tr class="matrix__divider"><th scope="rowgroup" colspan="${span}">${esc(row.groupHeading)}</th></tr>`;
      const cells = row.cells
        .map((cell, colIndex) => cellMarkup(cell, rowIndex, colIndex))
        .join("");
      return `${divider}<tr><th scope="row">${code(row.agent)}</th>${cells}</tr>`;
    })
    .join("");
}

/** The detection matrix as a heatmap table with legend, note and scroll region. */
export function heatmapMarkup(view: MatrixView): string {
  const headers = view.columns
    .map(
      (detector) => `<th scope="col"><code>${breakable(detector)}</code></th>`,
    )
    .join("");
  return `<figure class="matrix" id="detection-matrix" aria-labelledby="matrix-title">
    <figcaption class="matrix__head">
      <h3 id="matrix-title">Detection matrix</h3>
      ${legendMarkup()}
      <p class="matrix__note">An orange cell on a mutant row is the harness catching a planted defect. The rule baseline and oracle rows must stay at zero.</p>
      <p class="matrix__hint">Scroll sideways for all ${view.columns.length} detectors.</p>
      <p class="sr-only" id="matrix-keys">The matrix is one Tab stop. Use the arrow keys, Home and End to move between cells.</p>
    </figcaption>
    <div class="table-scroll matrix__scroll" role="region" aria-label="Detection matrix, scrolls horizontally">
      <table class="matrix__table" aria-describedby="matrix-keys" data-rows="${view.rows.length}" data-cols="${view.columns.length}">
        <thead><tr><th scope="col" class="matrix__corner">Agent</th>${headers}</tr></thead>
        <tbody>${bodyMarkup(view)}</tbody>
      </table>
    </div>
  </figure>`;
}

/** Mark the focused or hovered cell's row and column. */
function highlight(table: HTMLElement, cell: HTMLElement | null): void {
  table
    .querySelectorAll(`.${HIGHLIGHT_CLASS}`)
    .forEach((element) => element.classList.remove(HIGHLIGHT_CLASS));
  if (cell === null) return;
  const { row, col } = cell.dataset;
  table
    .querySelectorAll(`td[data-row="${row}"], td[data-col="${col}"]`)
    .forEach((element) => element.classList.add(HIGHLIGHT_CLASS));
}

/** Move the single Tab stop to another cell and focus it. */
function focusCell(
  table: HTMLElement,
  from: HTMLElement,
  row: number,
  col: number,
): void {
  const target = table.querySelector<HTMLElement>(
    `td[data-row="${row}"][data-col="${col}"]`,
  );
  if (target === null || target === from) return;
  from.tabIndex = -1;
  target.tabIndex = 0;
  target.focus();
}

/** Arrow keys, Home and End move focus between cells (a roving tabindex). */
function bindCellKeys(table: HTMLElement): void {
  const size = {
    rows: Number(table.dataset.rows),
    cols: Number(table.dataset.cols),
  };
  table.addEventListener("keydown", (event) => {
    const cell = closestTarget(event, "td[data-row]");
    if (cell === null || !(event instanceof KeyboardEvent)) return;
    const position = {
      row: Number(cell.dataset.row),
      col: Number(cell.dataset.col),
    };
    const next = moveCell(position, event.key, size);
    if (next === null) return;
    event.preventDefault();
    focusCell(table, cell, next.row, next.col);
  });
}

/** Wire row and column highlighting for pointer and keyboard. */
export function bindHeatmap(root: HTMLElement): void {
  const table = root.querySelector<HTMLElement>(".matrix__table");
  if (table === null) return;
  const onEnter = (event: Event): void => {
    const target = event.target;
    highlight(
      table,
      target instanceof HTMLElement ? target.closest("td") : null,
    );
  };
  table.addEventListener("pointerover", onEnter);
  table.addEventListener("focusin", onEnter);
  table.addEventListener("pointerleave", () => highlight(table, null));
  table.addEventListener("focusout", () => highlight(table, null));
  bindCellKeys(table);
}
