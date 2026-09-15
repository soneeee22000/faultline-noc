import { describe, expect, it } from "vitest";
import { formatCount, formatInterval, formatRate, formatTick } from "./format";

describe("rate formatting", () => {
  it("formats rates to three decimals like the markdown report", () => {
    expect(formatRate(1)).toBe("1.000");
    expect(formatRate(0.25)).toBe("0.250");
    expect(formatRate(0)).toBe("0.000");
  });

  it("formats Wilson intervals with brackets and three decimals", () => {
    expect(formatInterval(0.995221, 1)).toBe("[0.995, 1.000]");
    expect(formatInterval(0.221237, 0.281152)).toBe("[0.221, 0.281]");
  });

  it("formats counts with spaced slashes", () => {
    expect(formatCount(200, 800)).toBe("200 / 800");
  });

  it("formats axis ticks to two decimals", () => {
    expect(formatTick(0)).toBe("0.00");
    expect(formatTick(0.75)).toBe("0.75");
    expect(formatTick(1)).toBe("1.00");
  });

  it("rejects rates outside the unit interval", () => {
    expect(() => formatRate(1.5)).toThrow();
    expect(() => formatRate(-0.1)).toThrow();
  });
});
