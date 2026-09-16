import type { LeadItem } from "./limits";
import { repoFile, repoTree } from "./links";

/** The opening paragraph of the model comparison. Placeholders come from llm_results.json. */
export const MODELS_LEDE =
  "Everything above scores mock agents, which shows the harness discriminates but says nothing about an AI. This section puts two Claude models through the same scenarios, the same detectors and the same scoring, each investigating through six read tools and one write tool under a fixed tool-call budget. {modelRuns} of the {runs} runs called a model; the rest are the rule baseline.";

/** How the run was produced, stated plainly so nobody mistakes the page for a live agent. */
export const MODELS_METHOD: readonly LeadItem[] = [
  {
    lead: "Recorded once, replayed since.",
    detail: `Every API response is committed in [cassettes/](${repoTree("cassettes")}). CI replays them and fails if the published numbers move, so these figures reproduce without an API key. This page calls no model.`,
  },
  {
    lead: "The agents never see ground truth.",
    detail:
      "A model reads alarms, KPIs, logs, topology and intended config through tools, then submits one structured RCA. Nothing tells it the answer, and a self-contradictory RCA is rejected.",
  },
  {
    lead: "Two scenarios the baseline cannot solve.",
    detail:
      "`s08` hides a crash-loop behind a benign major alarm on the router; `s09` makes the true root silent, so only its KPIs betray it. Both sit in `scenarios/hard/` and are excluded from the harness run above.",
  },
];

/** "How to read these numbers", following docs/LLM.md. Nothing here may be softened. */
export const MODEL_CAVEATS: readonly LeadItem[] = [
  {
    lead: "Three seeds per scenario is a small sample.",
    detail:
      "The intervals are wide and they overlap: on this evidence {sonnet} is not proven better than {haiku}. What is clear is that both beat a baseline that fails two whole scenarios.",
  },
  {
    lead: "The hard scenarios are what make this mean anything.",
    detail:
      "On the four published scenarios alone every agent scores 12/12, because a simple rule already solves them.",
  },
  {
    lead: "A clean injection row is weak evidence.",
    detail:
      "Only one scenario carries a prompt injection, so it is three runs per agent, and the system prompt already warns that log text is untrusted. That shows the wording holding three times, not that a model resists injection.",
  },
  {
    lead: "The models were not tuned.",
    detail:
      "One prompt, one setting per model, no few-shot examples and no retry on a wrong answer.",
  },
  {
    lead: "Simulated telemetry.",
    detail: `These numbers say nothing about how real Open5GS, free5GC or vendor telemetry behaves. See [docs/LLM.md](${repoFile("docs/LLM.md")}) for the method and every miss run by run.`,
  },
  {
    lead: "The detectors carry the safety signal, not the accuracy column.",
    detail:
      "An agent can be right and still unsafe. The baseline's `s09` runs are the clearest case: confident, wrong, and proposing a write on a node that is only a symptom.",
  },
];

/** The sentence under the cost table. */
export const COST_NOTE =
  "{total} for {modelRuns} model runs. A hard cap stops a recording run before the next request once the budget is reached.";
