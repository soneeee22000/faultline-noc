/** Copy for one layer of the stack. Placeholders in braces are filled from results.json. */
export interface LayerCopy {
  readonly step: "1" | "2" | "3" | "4" | "5";
  readonly name: string;
  readonly heading: string;
  readonly problem: string;
  readonly answer: readonly string[];
  readonly caveat: string | null;
}

/** The five layers, bottom (network) to top (scorecard). Wording follows docs/WHY.md. */
export const LAYERS: readonly LayerCopy[] = [
  {
    step: "1",
    name: "Network",
    heading: "Network: a simulated 5G SA core",
    problem:
      "You cannot grade a root cause analysis without knowing the true root cause, and real outages rarely come with a label.",
    answer: [
      "A seeded simulator of a small 5G standalone core (gNB, AMF, SMF, UPF, NRF and one transport router) injects a known fault.",
      "Its dependency model was checked against 3GPP TS 23.501.",
      "The same seed gives byte-identical telemetry.",
    ],
    caveat: "Simulated, not emulated. No protocol stack runs.",
  },
  {
    step: "2",
    name: "Telemetry",
    heading: "Telemetry: alarms, KPIs and logs, each with an `evidence_id`",
    problem:
      "An agent can claim evidence it never saw, and nobody can tell afterwards. Logs are free text, so anything can be written into them, including instructions addressed to an AI.",
    answer: [
      "Every alarm, KPI and log record carries an `evidence_id`.",
      "The agent reads through a recorded session, so the harness knows exactly which records were delivered and in what order.",
    ],
    caveat: null,
  },
  {
    step: "3",
    name: "Agent",
    heading: "Agent: a structured RCA",
    problem: "Free-text diagnoses cannot be scored consistently.",
    answer: [
      "The agent returns a structured, schema-validated RCA: root cause NF, fault class, cited evidence ids, confidence and proposed actions.",
      "Ground truth reaches only the reference agents (the oracle and the mutants), never an evaluated agent.",
      "The agents here are mocks: a rule baseline, an oracle and mutants. No LLM is called.",
    ],
    caveat: null,
  },
  {
    step: "4",
    name: "Guardrails",
    heading: "Guardrails: {detectors} deterministic detectors",
    problem:
      "A correct diagnosis can still come with an unsafe action, such as a write before any evidence was read, a restart of a healthy node, or an order taken from a log line.",
    answer: [
      "Deterministic detectors check the recorded trace and the RCA.",
      "They catch cited ids that were never delivered, writes made before gathering evidence, a blamed symptom, following or taking an injected action, writes on a non-root node, and citations with no causal support.",
      "Every pass or fail judgment is code. There is no LLM judge.",
    ],
    caveat: null,
  },
  {
    step: "5",
    name: "Scorecard",
    heading:
      "Scorecard: accuracy, action correctness, detection matrix, harness check",
    problem:
      "A single accuracy number hides unsafe behaviour, and a harness that never fails proves nothing.",
    answer: [
      "The scorecard reports top-1 accuracy and action correctness with Wilson intervals, plus a detection matrix.",
      "A harness check runs mutant agents, each with one known defect. Each must trip its own detector and nothing else, and the command exits non-zero if any fails that test.",
    ],
    caveat:
      "This shows the harness discriminates, not that any AI works. The rule baseline scores {baseline} on top-1 accuracy, which means the scenarios are still too easy.",
  },
];
