import { describe, expect, it } from "vitest";
import {
  frameAt,
  frameForProgress,
  gutterMark,
  lastFrame,
  parseTranscript,
} from "./transcript";

const RAW =
  "# $ pytest | Python 3.12.13 | 2026-09-15\n....  [100%]\n186 passed in 8.13s\n";

describe("transcript header parsing", () => {
  it("splits the header into command, Python version and date", () => {
    const transcript = parseTranscript(RAW);
    expect(transcript.command).toBe("pytest");
    expect(transcript.python).toBe("3.12.13");
    expect(transcript.date).toBe("2026-09-15");
  });

  it("keeps the body verbatim without the trailing newline", () => {
    expect(parseTranscript(RAW).lines).toEqual([
      "....  [100%]",
      "186 passed in 8.13s",
    ]);
  });

  it("keeps commands that contain spaces and flags", () => {
    const transcript = parseTranscript(
      "# $ python -m faultline_noc --smoke | Python 3.11.9 | 2026-01-02\nx",
    );
    expect(transcript.command).toBe("python -m faultline_noc --smoke");
    expect(transcript.python).toBe("3.11.9");
  });

  it("accepts Windows line endings", () => {
    expect(parseTranscript(RAW.replaceAll("\n", "\r\n")).lines).toHaveLength(2);
  });

  it("preserves blank lines inside the body", () => {
    const transcript = parseTranscript(
      "# $ a | Python 3.12.0 | 2026-09-15\none\n\ntwo\n",
    );
    expect(transcript.lines).toEqual(["one", "", "two"]);
  });

  it("rejects a transcript without a valid header", () => {
    expect(() => parseTranscript("186 passed\n")).toThrow(/header/);
  });
});

describe("replay frames", () => {
  const transcript = parseTranscript(RAW);

  it("types the command one character per frame first", () => {
    expect(frameAt(transcript, 0)).toEqual({
      typed: "",
      visibleLines: 0,
      complete: false,
    });
    expect(frameAt(transcript, 3).typed).toBe("pyt");
    expect(frameAt(transcript, 6)).toEqual({
      typed: "pytest",
      visibleLines: 0,
      complete: false,
    });
  });

  it("then reveals one output line per frame", () => {
    expect(frameAt(transcript, 7).visibleLines).toBe(1);
    expect(frameAt(transcript, 8)).toEqual({
      typed: "pytest",
      visibleLines: 2,
      complete: true,
    });
  });

  it("clamps frames outside the range", () => {
    expect(frameAt(transcript, -4).typed).toBe("");
    expect(frameAt(transcript, 999).complete).toBe(true);
    expect(lastFrame(transcript)).toBe(8);
  });

  it("maps progress in 0..1 onto frames deterministically", () => {
    expect(frameForProgress(transcript, 0)).toBe(0);
    expect(frameForProgress(transcript, 0.5)).toBe(4);
    expect(frameForProgress(transcript, 1)).toBe(8);
    expect(frameForProgress(transcript, 7)).toBe(8);
    expect(frameForProgress(transcript, Number.NaN)).toBe(0);
  });
});

describe("gutter marks", () => {
  it("marks passing summary lines", () => {
    expect(gutterMark("PASS: every mutant tripped its own detector")).toBe(
      "pass",
    );
    expect(gutterMark("186 passed in 8.13s")).toBe("pass");
  });

  it("marks failures and lets a failure win over a pass count", () => {
    expect(gutterMark("FAILED tests/test_cli.py::test_smoke")).toBe("fail");
    expect(gutterMark("1 failed, 185 passed in 8.00s")).toBe("fail");
    expect(gutterMark("FAIL: mutant escaped")).toBe("fail");
    expect(gutterMark("src/x.py:3: error: bad type")).toBe("fail");
  });

  it("leaves ordinary lines unmarked", () => {
    expect(gutterMark("| rule_baseline | 4 / 4 | 1.000 |")).toBeNull();
    expect(
      gutterMark("Success: no issues found in 34 source files"),
    ).toBeNull();
    expect(gutterMark("")).toBeNull();
  });
});
