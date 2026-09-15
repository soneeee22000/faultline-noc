import {
  LIMITATIONS,
  type LeadItem,
  NOT_THIS,
  ROADMAP,
} from "../content/limits";
import { BASELINE_AGENT, overallStat, payload } from "../data/payload";
import { fill, mount, richText } from "../lib/dom";
import { formatCount } from "../viewmodel/format";

/** One list item with a bold lead. */
function itemMarkup(
  item: LeadItem,
  values: Record<string, string | number>,
): string {
  return `<li><strong>${richText(item.lead)}</strong> ${richText(fill(item.detail, values))}</li>`;
}

/** Section 7: limitations and roadmap. */
export function renderLimits(): void {
  const baseline = overallStat(payload.accuracy_overall, BASELINE_AGENT);
  const values = {
    baseline: formatCount(baseline.correct, baseline.n),
    scenarios: payload.scenarios.length,
    command: payload.meta.command,
  };
  const list = (items: readonly LeadItem[]): string =>
    items.map((item) => itemMarkup(item, values)).join("");
  mount(
    "limits",
    `<div class="container">
      <div class="section-head"><h2 id="limits-title">Limitations and roadmap</h2></div>
      <div class="limits">
        <div class="limits__col limits__col--wide" id="not-this"><h3>What this is not</h3><ul class="limits__list">${list(NOT_THIS)}</ul></div>
        <div class="limits__col"><h3>Limitations</h3><ul class="limits__list">${list(LIMITATIONS)}</ul></div>
        <div class="limits__col"><h3>Roadmap</h3><p class="muted">Planned, not built.</p><ol class="limits__list">${list(ROADMAP)}</ol></div>
      </div>
    </div>`,
  );
}
