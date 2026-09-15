import { topologyMarkup } from "../components/topology-svg";
import { payload } from "../data/payload";
import { breakable, code, esc, joinList, mount } from "../lib/dom";
import { icon } from "../lib/icons";
import type { ScenarioInfo } from "../types/payload";
import { scenarioTitle } from "../viewmodel/scenario";
import { nodeRoles } from "../viewmodel/topology";

const CARD_WIDTH = 280;
const CARD_HEIGHT = 160;
const TOPOLOGY_PAD_X = 28;
const TOPOLOGY_PAD_Y = 22;
const NODE_RADIUS = 7;

/** The mini topology with root cause, symptoms and injection target marked. */
function topologySvg(scenario: ScenarioInfo): string {
  const label =
    scenario.root_nf === null
      ? "Topology with no faulty node"
      : `Topology: root cause ${scenario.root_nf}; symptoms ${scenario.symptom_nfs.join(", ")}`;
  const markup = topologyMarkup({
    width: CARD_WIDTH,
    height: CARD_HEIGHT,
    padX: TOPOLOGY_PAD_X,
    padY: TOPOLOGY_PAD_Y,
    nodeRadius: NODE_RADIUS,
    showInterfaces: false,
    roleOf: (node) => nodeRoles(scenario, node),
  });
  return `<svg class="scenario-card__topology" viewBox="0 0 ${CARD_WIDTH} ${CARD_HEIGHT}" role="img" aria-label="${esc(label)}">${markup}</svg>`;
}

/** The role legend under the topology, in text and glyphs. */
function rolesMarkup(scenario: ScenarioInfo): string {
  if (scenario.root_nf === null)
    return `<ul class="scenario-card__roles"><li class="state state--muted">${icon("circle")}<span>No fault: the right answer is ${code(scenario.fault_class)}</span></li></ul>`;
  const symptoms = joinList(scenario.symptom_nfs.map(code));
  const injection =
    scenario.injection === null
      ? ""
      : `<li class="state state--trip">${icon("message-square-warning")}<span>injection target ${code(scenario.injection.node)}</span></li>`;
  return `<ul class="scenario-card__roles">
    <li class="state state--trip">${icon("diamond", "icon--filled")}<span>root cause ${code(scenario.root_nf)}</span></li>
    <li class="state">${icon("circle")}<span>symptoms ${symptoms}</span></li>${injection}
  </ul>`;
}

/** One scenario card. */
function cardMarkup(scenario: ScenarioInfo): string {
  const titleId = `scenario-${scenario.id}-title`;
  return `<li><article class="scenario-card" aria-labelledby="${titleId}">
    <p class="scenario-card__id"><code>${breakable(scenario.id)}</code></p>
    <h3 id="${titleId}">${esc(scenarioTitle(scenario))}</h3>
    ${topologySvg(scenario)}
    ${rolesMarkup(scenario)}
    <p><strong>The trap.</strong> ${esc(scenario.trap)}.</p>
    <dl class="scenario-card__meta">
      <div><dt>Expected fault class</dt><dd>${code(scenario.fault_class)}</dd></div>
      <div><dt>Root NF</dt><dd>${code(scenario.root_nf ?? "none")}</dd></div>
    </dl>
  </article></li>`;
}

/** Section 4: one card per scenario in the committed run. */
export function renderScenarios(): void {
  const count = payload.scenarios.length;
  mount(
    "scenarios",
    `<div class="container">
      <div class="section-head">
        <h2 id="scenarios-title">Scenarios</h2>
        <p class="lede">${count} seeded scenarios. Each card marks the injected root cause against the functions that only show symptoms, and names the trap it tests.</p>
      </div>
      <ul class="scenario-grid">${payload.scenarios.map(cardMarkup).join("")}</ul>
    </div>`,
  );
}
