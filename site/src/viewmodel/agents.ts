const MUTANT_PREFIX = "mutant_";
const REFERENCE_AGENTS: ReadonlySet<string> = new Set(["oracle"]);

/**
 * How an agent relates to ground truth. The rule baseline is the only evaluated agent and never
 * receives ground truth; the oracle is a reference agent; mutants are the oracle with one defect.
 */
export type AgentGroup = "evaluated" | "reference" | "mutant";

/** Row-group headings shared by the bar charts and the detection matrix. */
export const GROUP_HEADINGS: Readonly<Record<AgentGroup, string>> = {
  evaluated: "Evaluated agent: no ground truth",
  reference: "Reference agent: reads ground truth",
  mutant: "Mutants: the oracle with one injected defect",
};

const ROLE_LABELS: Readonly<Record<AgentGroup, string>> = {
  evaluated: "evaluated agent (no ground truth)",
  reference: "reference agent",
  mutant: "mutant",
};

/** Classify an agent by its registry name. */
export function agentGroup(agent: string): AgentGroup {
  if (agent.startsWith(MUTANT_PREFIX)) return "mutant";
  return REFERENCE_AGENTS.has(agent) ? "reference" : "evaluated";
}

/** The short role label shown under an agent's name. */
export function agentRole(agent: string): string {
  return ROLE_LABELS[agentGroup(agent)];
}

/** A heading wherever an agent's group differs from the previous row's, otherwise null. */
export function groupHeadings(agents: readonly string[]): (string | null)[] {
  return agents.map((agent, position) => {
    const group = agentGroup(agent);
    const previous = agents[position - 1];
    if (previous !== undefined && agentGroup(previous) === group) return null;
    return GROUP_HEADINGS[group];
  });
}
