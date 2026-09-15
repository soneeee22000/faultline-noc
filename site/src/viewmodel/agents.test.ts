import { describe, expect, it } from "vitest";
import { GROUP_HEADINGS, agentGroup, agentRole, groupHeadings } from "./agents";

describe("agent groups", () => {
  it("never labels the rule baseline as a reference agent", () => {
    expect(agentGroup("rule_baseline")).toBe("evaluated");
    expect(agentRole("rule_baseline")).toBe("evaluated agent (no ground truth)");
  });

  it("labels the oracle as a reference agent and mutants as mutants", () => {
    expect(agentRole("oracle")).toBe("reference agent");
    expect(agentRole("mutant_follows_injection")).toBe("mutant");
  });

  it("says in every heading whether the group receives ground truth", () => {
    expect(GROUP_HEADINGS.evaluated).toMatch(/no ground truth/);
    expect(GROUP_HEADINGS.reference).toMatch(/ground truth/);
    expect(GROUP_HEADINGS.mutant).toMatch(/oracle/);
  });

  it("emits a heading only where the group changes", () => {
    expect(
      groupHeadings(["rule_baseline", "oracle", "mutant_a", "mutant_b"]),
    ).toEqual([
      GROUP_HEADINGS.evaluated,
      GROUP_HEADINGS.reference,
      GROUP_HEADINGS.mutant,
      null,
    ]);
    expect(groupHeadings([])).toEqual([]);
  });
});
