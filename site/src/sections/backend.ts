import {
  type ReplayController,
  initTerminal,
  terminalMarkup,
} from "../components/terminal";
import { bindTraceViewer, traceViewer } from "../components/trace-viewer";
import {
  BASELINE_AGENT,
  INJECTION_MUTANT,
  INJECTION_SCENARIO_ID,
  TRANSCRIPTS,
  payload,
  sampleTrace,
  scenarioById,
} from "../data/payload";
import { bindDisclosures } from "../lib/disclosure";
import { mount, query } from "../lib/dom";

/** Section 6: the terminal replay of captured transcripts and the s07 trace viewer. */
export function renderBackend(): ReplayController {
  const viewer = traceViewer({
    scenario: scenarioById(INJECTION_SCENARIO_ID),
    traces: [
      sampleTrace(INJECTION_SCENARIO_ID, BASELINE_AGENT),
      sampleTrace(INJECTION_SCENARIO_ID, INJECTION_MUTANT),
    ],
    detectors: payload.meta.detectors,
  });
  const section = mount(
    "backend",
    `<div class="container">
      <div class="section-head">
        <h2 id="backend-title">Back end</h2>
        <p class="lede">A Python CLI. Below are captured transcripts of the smoke run, the test suite and the type checker, then one recorded run traced read by read.</p>
      </div>
      <div class="backend">
        ${terminalMarkup(TRANSCRIPTS)}
        ${viewer}
      </div>
    </div>`,
  );
  bindDisclosures(section);
  bindTraceViewer(section);
  return initTerminal(
    query(section, "[data-terminal]", HTMLElement),
    TRANSCRIPTS,
  );
}
