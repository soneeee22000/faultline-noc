import { REPO_URL } from "../content/links";
import {
  INJECTION_MUTANT,
  INJECTION_SCENARIO_ID,
  detectionCell,
  payload,
  sampleTrace,
  scenarioById,
} from "../data/payload";
import { code, esc, mount } from "../lib/dom";
import { icon } from "../lib/icons";
import { shortScenarioId } from "../viewmodel/scenario";

const INJECTION_DETECTOR = "injected_action_followed";

/** The specimen panel: the real planted log line from s07 and what the harness made of it. */
function specimenMarkup(): string {
  const scenario = scenarioById(INJECTION_SCENARIO_ID);
  const trace = sampleTrace(INJECTION_SCENARIO_ID, INJECTION_MUTANT);
  const cell = detectionCell(INJECTION_MUTANT, INJECTION_DETECTOR);
  const injection = scenario.injection;
  if (injection === null || trace.injection_evidence_id === null)
    throw new Error(`${scenario.id} has no injection`);
  return `<figure class="specimen" aria-label="A planted log line from scenario ${shortScenarioId(scenario.id)}">
    <div class="specimen__head">${code(trace.injection_evidence_id)}<span class="chip chip--trip">${icon("message-square-warning")}injected</span>${code(injection.node)}</div>
    <blockquote class="specimen__text"><p>${esc(injection.text)}</p></blockquote>
    <figcaption class="specimen__caption">A log line from scenario ${code(shortScenarioId(scenario.id))}. The real root cause is ${code(scenario.root_nf ?? "none")}. The harness checks whether an agent obeys the line.</figcaption>
    <p class="specimen__result">${code(INJECTION_MUTANT)}<span aria-hidden="true">→</span><span class="sr-only">triggers</span>${code(INJECTION_DETECTOR)}<span class="state state--trip">${icon("diamond", "icon--filled")}tripped ${cell.tripped}/${cell.applicable}</span></p>
  </figure>`;
}

/** Section 1: title, tagline, the honest data note and the specimen. */
export function renderHero(): void {
  const meta = payload.meta;
  mount(
    "hero",
    `<div class="container hero">
      <div class="hero__text">
        <h1 id="hero-title">Faultline NOC</h1>
        <p class="hero__tagline">A deterministic harness that tests whether a network-operations agent names the real root cause and refuses unsafe actions, on a simulated 5G SA core.</p>
        <p class="data-note">${icon("info")}<span>Numbers from ${code(meta.command)}, ${meta.runs} runs, checked by a CI diff on every push. This page does not run the harness.</span></p>
        <div class="hero__actions">
          <a class="button button--primary" href="#layers">See the layers</a>
          <a class="button" href="${REPO_URL}">Read the source</a>
        </div>
      </div>
      ${specimenMarkup()}
    </div>`,
  );
}
