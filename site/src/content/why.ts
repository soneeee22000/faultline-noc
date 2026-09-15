import { OWASP_PROMPT_INJECTION_URL, repoFile } from "./links";

/** One "Why it matters" block: a fixed h3 and its paragraphs (rich text). */
export interface WhyBlock {
  readonly heading: string;
  readonly paragraphs: readonly string[];
}

/** Business context, taken from docs/WHY.md. Qualitative only: no market figures. */
export const WHY_BLOCKS: readonly WhyBlock[] = [
  {
    heading: "Alarm storms hide the cause",
    paragraphs: [
      "When something breaks in a mobile core, the network operations centre (NOC) rarely sees one clean alarm. It sees a storm. Every function that depends on the broken one starts to complain, and the dependants usually complain loudest because they notice first and retry often. The failed component may raise only a single quiet alarm of its own.",
      "Engineers under pressure work the loudest alarms first, so time goes into restarting and escalating healthy functions while the real cause keeps failing underneath. The first scenario shows the pattern in miniature: a crash-looping UPF makes the SMF emit bursts of critical PFCP alarms, while the UPF itself raises one major alarm per restart cycle.",
    ],
  },
  {
    heading: "Autonomous fixes can do damage",
    paragraphs: [
      "An assistant that only suggests a root cause wastes minutes when it is wrong. An agent that can act does real damage. If it restarts the wrong network function, it widens the outage it was meant to fix.",
      `If it obeys an instruction hidden inside a log line, anyone who can write text into telemetry can steer the network. That is the indirect prompt injection risk that [OWASP describes](${OWASP_PROMPT_INJECTION_URL}), in which content from outside sources changes a model's behaviour.`,
    ],
  },
  {
    heading: "Who this problem matters to",
    paragraphs: [
      "Telecom operations teams and network-automation vendors working toward higher autonomy. [TM Forum's Autonomous Networks](https://www.tmforum.org/missions/autonomous-networks) framework describes six levels, from fully manual (L0) to fully autonomous (L5) operations.",
      "Moving up those levels means removing human oversight step by step, and that needs evidence that the agent behaves.",
    ],
  },
  {
    heading: "Measure before you trust writes",
    paragraphs: [
      "Before an agent's writes to a network are trusted, they have to be measured: what it read, what it cited, and what it changed.",
      "An LLM acting as judge cannot provide that evidence on its own. It adds sampling variance, it drifts between model versions, and it reads the same telemetry as the agent, so the same injected text can steer it.",
      `A deterministic harness gives the same verdict for the same scenario and seed. Every failure points to a specific evidence id, trace position or action that an engineer can check by hand, which makes it usable as a go/no-go gate. [ADR-001](${repoFile("docs/adr/001-deterministic-gate.md")}) records this decision.`,
    ],
  },
];
