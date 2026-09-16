import { repoFile } from "./links";

/** A list item with a bold lead and rich-text detail. Placeholders in braces come from results.json. */
export interface LeadItem {
  readonly lead: string;
  readonly detail: string;
}

/** "What this is not", following docs/WHY.md. */
export const NOT_THIS: readonly LeadItem[] = [
  {
    lead: "Not a product.",
    detail:
      "It is a portfolio piece and a research harness. It does not measure time saved in a real NOC.",
  },
  {
    lead: "Not an emulation or a digital twin.",
    detail:
      "No protocol stack runs. The telemetry is synthetic and follows a hand-written dependency table, so nothing here shows how real core telemetry behaves.",
  },
  {
    lead: "The agents on this page are mocks.",
    detail: `They are a rule baseline, an oracle and mutants, so these figures show that the harness tells good behaviour from bad, not that any AI works. Claude models are scored by the same detectors in [docs/LLM.md](${repoFile("docs/LLM.md")}).`,
  },
  {
    lead: "These four scenarios are too easy.",
    detail: `The rule baseline scores {baseline}. Two harder scenarios defeat it, and they are what make the model comparison in [docs/LLM.md](${repoFile("docs/LLM.md")}) worth reading.`,
  },
  {
    lead: "This page does not run the harness.",
    detail: "Its figures are copied from a committed run of `{command}`.",
  },
];

/** Limitations, following the README. */
export const LIMITATIONS: readonly LeadItem[] = [
  {
    lead: "It proves the harness discriminates, not that any AI works.",
    detail: `The agents here are mocks. See [docs/RESULTS.md](${repoFile("docs/RESULTS.md")}).`,
  },
  {
    lead: "These four scenarios are too easy.",
    detail: `The rule baseline scores {baseline} once it filters the only major noise code. It fails both harder scenarios in the model comparison ([docs/LLM.md](${repoFile("docs/LLM.md")})), which rests on three seeds each.`,
  },
  {
    lead: "Simulated, not emulated.",
    detail: `No protocol stack runs. Telemetry follows a hand-written dependency table with one-hop, consumer-side symptoms. See [docs/nf-model.md](${repoFile("docs/nf-model.md")}).`,
  },
  {
    lead: "The session returns everything.",
    detail: "No query tools, filters or tool-call budget.",
  },
  {
    lead: "Truth isolation is a type, an allowlist and a test,",
    detail: `not process isolation. Detector coverage gaps are listed in [docs/HARNESS.md](${repoFile("docs/HARNESS.md")}).`,
  },
  {
    lead: "The baseline's noise filter is a catalog lookup.",
    detail: "A new noise code would get past it until the catalog is updated.",
  },
  {
    lead: "Confidence is not calibrated,",
    detail: `and this page covers {scenarios} scenarios. Two harder ones live in \`scenarios/hard/\` and are scored in the model comparison ([docs/LLM.md](${repoFile("docs/LLM.md")})).`,
  },
];

/** Roadmap, following the README. Nothing here is built yet. */
export const ROADMAP: readonly LeadItem[] = [
  {
    lead: "MCP server",
    detail:
      "with read tools (`get_alarms`, `get_kpis`, `get_logs`, `get_topology`, `get_config`, `diff_config_against_intent`) and one write tool (`restart_nf`), contract-tested against the simulator.",
  },
  {
    lead: "Safety gate",
    detail:
      "in front of writes: dry run on a cloned simulation, approval token, append-only audit log, automatic rollback on a failed post-check.",
  },
  {
    lead: "LangGraph agent",
    detail:
      "(triage, hypothesize, gather under a tool budget, verify citations, propose) on the same RCA schema, with mock, replay and real-model planners.",
  },
  {
    lead: "More seeds and models",
    detail: `in the recorded model comparison ([docs/LLM.md](${repoFile("docs/LLM.md")})), plus an alarms-only, no-tools model baseline, to narrow the intervals.`,
  },
  {
    lead: "Harder scenarios:",
    detail:
      "N4/PFCP association loss, delayed NRF unreachability, SMF config drift, second-order symptoms, service-affecting noise and overlapping faults.",
  },
];
