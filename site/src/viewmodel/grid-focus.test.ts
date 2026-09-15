import { describe, expect, it } from "vitest";
import { moveCell } from "./grid-focus";

const SIZE = { rows: 10, cols: 7 } as const;

describe("moveCell", () => {
  it("moves one cell per arrow key", () => {
    expect(moveCell({ row: 2, col: 3 }, "ArrowRight", SIZE)).toEqual({ row: 2, col: 4 });
    expect(moveCell({ row: 2, col: 3 }, "ArrowLeft", SIZE)).toEqual({ row: 2, col: 2 });
    expect(moveCell({ row: 2, col: 3 }, "ArrowDown", SIZE)).toEqual({ row: 3, col: 3 });
    expect(moveCell({ row: 2, col: 3 }, "ArrowUp", SIZE)).toEqual({ row: 1, col: 3 });
  });

  it("stops at the edges instead of wrapping", () => {
    expect(moveCell({ row: 0, col: 0 }, "ArrowLeft", SIZE)).toEqual({ row: 0, col: 0 });
    expect(moveCell({ row: 0, col: 0 }, "ArrowUp", SIZE)).toEqual({ row: 0, col: 0 });
    expect(moveCell({ row: 9, col: 6 }, "ArrowRight", SIZE)).toEqual({ row: 9, col: 6 });
    expect(moveCell({ row: 9, col: 6 }, "ArrowDown", SIZE)).toEqual({ row: 9, col: 6 });
  });

  it("jumps to the row ends with Home and End", () => {
    expect(moveCell({ row: 4, col: 3 }, "Home", SIZE)).toEqual({ row: 4, col: 0 });
    expect(moveCell({ row: 4, col: 3 }, "End", SIZE)).toEqual({ row: 4, col: 6 });
  });

  it("ignores keys that do not navigate, so Tab still leaves the grid", () => {
    expect(moveCell({ row: 4, col: 3 }, "Tab", SIZE)).toBeNull();
    expect(moveCell({ row: 4, col: 3 }, "Enter", SIZE)).toBeNull();
  });
});
