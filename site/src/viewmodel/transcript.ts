const HEADER_PATTERN = /^# \$ (.+) \| Python (\S+) \| (\d{4}-\d{2}-\d{2})$/;
const FAIL_PATTERN = /\bFAILED\b|\bFAIL\b|\bfailed\b|\berror\b/;
const PASS_PATTERN = /^PASS\b|\bpassed\b/;

/** A captured transcript: the header fields and the verbatim output lines. */
export interface Transcript {
  readonly command: string;
  readonly python: string;
  readonly date: string;
  readonly lines: readonly string[];
}

/** What one replay frame shows. */
export interface ReplayFrame {
  readonly typed: string;
  readonly visibleLines: number;
  readonly complete: boolean;
}

/** Gutter status for a transcript line. */
export type GutterMark = "pass" | "fail" | null;

/** Parse a transcript written by `scripts/refresh_site_data.py`. */
export function parseTranscript(raw: string): Transcript {
  const [header = "", ...body] = raw.replaceAll("\r\n", "\n").split("\n");
  const match = HEADER_PATTERN.exec(header);
  if (match === null) {
    throw new Error(`Transcript header missing or malformed: "${header}"`);
  }
  if (body.at(-1) === "") body.pop();
  return {
    command: match[1] ?? "",
    python: match[2] ?? "",
    date: match[3] ?? "",
    lines: body,
  };
}

/** The final frame index: the command fully typed and every line shown. */
export function lastFrame(transcript: Transcript): number {
  return transcript.command.length + transcript.lines.length;
}

/** Pure frame model: first type the command one character per frame, then one line per frame. */
export function frameAt(transcript: Transcript, frame: number): ReplayFrame {
  const final = lastFrame(transcript);
  const clamped = Number.isNaN(frame)
    ? 0
    : Math.min(Math.max(Math.floor(frame), 0), final);
  const commandLength = transcript.command.length;
  return {
    typed: transcript.command.slice(0, Math.min(clamped, commandLength)),
    visibleLines: Math.max(clamped - commandLength, 0),
    complete: clamped === final,
  };
}

/** Map progress in [0, 1] to a frame index; out-of-range input is clamped. */
export function frameForProgress(
  transcript: Transcript,
  progress: number,
): number {
  const bounded = Number.isNaN(progress)
    ? 0
    : Math.min(Math.max(progress, 0), 1);
  return Math.round(bounded * lastFrame(transcript));
}

/** Classify a line for the gutter; a failure wins over a pass count on the same line. */
export function gutterMark(line: string): GutterMark {
  if (FAIL_PATTERN.test(line)) return "fail";
  return PASS_PATTERN.test(line) ? "pass" : null;
}
