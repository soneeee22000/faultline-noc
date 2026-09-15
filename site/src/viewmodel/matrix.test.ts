import { describe, expect, it } from "vitest";
import type { DetectionCell } from "../types/payload";
import {
  agentGroup,
  buildMatrix,
  cellDescription,
  cellTone,
  heatBin,
} from "./matrix";

describe("matrix cell state", () => {
  it("bins a zero rate and an empty denominator into the zero class", () => {
    expect(heatBin(0, 800)).toBe(0);
    expect(heatBin(0, 0)).toBe(0);
  });

  it("uses inclusive upper edges at 25% and 50%", () => {
    expect(heatBin(1, 800)).toBe(1);
    expect(heatBin(200, 800)).toBe(1);
    expect(heatBin(201, 800)).toBe(2);
    expect(heatBin(400, 800)).toBe(2);
    expect(heatBin(401, 800)).toBe(3);
  });

  it("reserves the top class for a rate of exactly one", () => {
    expect(heatBin(799, 800)).toBe(3);
    expect(heatBin(800, 800)).toBe(4);
  });

  it("rejects impossible counts", () => {
    expect(() => heatBin(5, 4)).toThrow();
    expect(() => heatBin(-1, 4)).toThrow();
  });

  it("picks the text tone per bin so contrast is never chosen by eye", () => {
    expect(cellTone(0)).toBe("muted");
    expect(cellTone(1)).toBe("ink");
    expect(cellTone(2)).toBe("ground");
    expect(cellTone(3)).toBe("ground");
    expect(cellTone(4)).toBe("ground");
  });

  it("classifies the evaluated baseline apart from the truth-aware reference agents", () => {
    expect(agentGroup("rule_baseline")).toBe("evaluated");
    expect(agentGroup("oracle")).toBe("reference");
    expect(agentGroup("mutant_blames_symptom")).toBe("mutant");
  });

  it("templates the cell description from the counts", () => {
    const cell: DetectionCell = {
      agent: "mutant_writes_before_gathering",
      detector: "write_on_non_root",
      tripped: 200,
      applicable: 800,
    };
    expect(cellDescription(cell)).toBe(
      "write_on_non_root tripped on 200 of 800 applicable runs for mutant_writes_before_gathering.",
    );
  });
});

describe("buildMatrix", () => {
  const cells: DetectionCell[] = [
    { agent: "oracle", detector: "b", tripped: 0, applicable: 10 },
    { agent: "rule_baseline", detector: "a", tripped: 0, applicable: 10 },
    { agent: "oracle", detector: "a", tripped: 0, applicable: 10 },
    { agent: "rule_baseline", detector: "b", tripped: 10, applicable: 10 },
  ];

  it("orders rows by the agent list and columns by the detector list", () => {
    const view = buildMatrix(cells, ["rule_baseline", "oracle"], ["a", "b"]);
    expect(view.columns).toEqual(["a", "b"]);
    expect(view.rows.map((row) => row.agent)).toEqual([
      "rule_baseline",
      "oracle",
    ]);
    expect(view.rows[0]?.cells.map((cell) => cell.label)).toEqual([
      "0/10",
      "10/10",
    ]);
    expect(view.rows[0]?.cells[1]?.bin).toBe(4);
  });

  it("fails loudly when a cell is missing instead of rendering a blank", () => {
    expect(() =>
      buildMatrix(cells, ["rule_baseline", "oracle"], ["a", "b", "c"]),
    ).toThrow(/rule_baseline.*c/);
  });
});
