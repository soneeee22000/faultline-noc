import type { TranscriptEntry } from "../data/payload";
import {
  closestTarget,
  esc,
  prefersReducedMotion,
  query,
  queryAll,
} from "../lib/dom";
import { icon } from "../lib/icons";
import {
  frameAt,
  frameForProgress,
  gutterMark,
  lastFrame,
} from "../viewmodel/transcript";

const TYPE_INTERVAL_MS = 24;
const LINE_INTERVAL_MS = 40;
const AUTOPLAY_VISIBILITY = 0.5;
const GUTTER_TEXT = { pass: "passed", fail: "failed" } as const;
const TAB_DELTAS: Readonly<Record<string, number>> = {
  ArrowLeft: -1,
  ArrowRight: 1,
};

/** Imperative handle used by the capture hooks. */
export interface ReplayController {
  setProgress(progress: number, transcriptId?: string): number;
  setTab(transcriptId: string): boolean;
}

interface ReplayState {
  index: number;
  frame: number;
  playing: boolean;
  lastTime: number | null;
  run: number;
  captured: boolean;
}

interface TerminalContext {
  readonly pre: HTMLElement;
  readonly body: HTMLElement;
  readonly tabs: readonly HTMLButtonElement[];
  readonly playButton: HTMLButtonElement;
  readonly command: HTMLElement;
  readonly meta: HTMLElement;
  readonly entries: readonly TranscriptEntry[];
  readonly lines: readonly (readonly string[])[];
  readonly state: ReplayState;
}

/** The "Python x, date" line from a transcript header. */
function metaText(entry: TranscriptEntry): string {
  return `Python ${entry.transcript.python}, ${entry.transcript.date}`;
}

/** One transcript tab. */
function tabMarkup(entry: TranscriptEntry, position: number): string {
  const selected = position === 0;
  return `<button class="terminal__tab" type="button" role="tab" id="terminal-tab-${entry.id}" data-transcript="${entry.id}" aria-selected="${selected}" aria-controls="terminal-panel" tabindex="${selected ? 0 : -1}"><code>${esc(entry.transcript.command)}</code></button>`;
}

/** Play or Pause button content. */
function playLabel(playing: boolean): string {
  return playing
    ? `${icon("pause")}<span>Pause</span>`
    : `${icon("play")}<span>Play</span>`;
}

/** The terminal replay markup for the given transcripts. */
export function terminalMarkup(entries: readonly TranscriptEntry[]): string {
  const first = entries[0];
  if (first === undefined) throw new Error("No transcripts to replay");
  return `<div class="terminal" id="terminal" role="group" aria-labelledby="terminal-label" data-terminal>
    <div class="terminal__tabs" role="tablist" aria-label="Captured transcripts">${entries.map(tabMarkup).join("")}</div>
    <div class="terminal__bar">
      <div>
        <p class="terminal__label" id="terminal-label">Replay of a real local run: <code data-term-command>${esc(first.transcript.command)}</code></p>
        <p class="terminal__meta" data-term-meta>${esc(metaText(first))}</p>
      </div>
      <div class="terminal__controls">
        <button class="button" type="button" data-term-action="play">${playLabel(false)}</button>
        <button class="button" type="button" data-term-action="restart">${icon("rotate-ccw")}<span>Restart</span></button>
        <button class="button" type="button" data-term-action="all">${icon("list-end")}<span>Show all</span></button>
      </div>
    </div>
    <div class="terminal__body" id="terminal-panel" role="tabpanel" aria-labelledby="terminal-tab-${first.id}" tabindex="0"><pre class="terminal__pre" data-term-pre></pre></div>
    <p class="terminal__footer">This page replays a captured transcript. It does not run the harness.</p>
  </div>`;
}

/** One output line with its gutter mark; the transcript text itself is verbatim. */
function lineMarkup(line: string): string {
  const mark = gutterMark(line);
  const gutter =
    mark === null
      ? ""
      : `${icon(mark === "pass" ? "circle-check" : "circle-x", `gutter-icon--${mark}`)}<span class="sr-only">${GUTTER_TEXT[mark]}</span>`;
  return `<span class="term-line"><span class="term-gutter">${gutter}</span><span class="term-text">${esc(line)}</span></span>`;
}

/** Draw the current frame; follow the newest line while playing or capturing. */
function renderFrame(context: TerminalContext, follow: boolean): void {
  const entry = context.entries[context.state.index];
  const lines = context.lines[context.state.index];
  if (entry === undefined || lines === undefined) return;
  const frame = frameAt(entry.transcript, context.state.frame);
  const caret =
    frame.complete || frame.visibleLines > 0
      ? ""
      : '<span class="term-caret" aria-hidden="true"></span>';
  const prompt = `<span class="term-line"><span class="term-gutter"></span><span class="term-text"><span class="term-prompt">$</span> ${esc(frame.typed)}${caret}</span></span>`;
  context.pre.innerHTML = prompt + lines.slice(0, frame.visibleLines).join("");
  if (follow) context.body.scrollTop = context.body.scrollHeight;
}

/** Advance playback on animation frames at the typing or line cadence. */
function advance(context: TerminalContext, run: number, now: number): void {
  const { state } = context;
  const entry = context.entries[state.index];
  if (!state.playing || state.run !== run || entry === undefined) return;
  const interval =
    state.frame < entry.transcript.command.length
      ? TYPE_INTERVAL_MS
      : LINE_INTERVAL_MS;
  state.lastTime ??= now;
  if (now - state.lastTime >= interval) {
    state.lastTime = now;
    state.frame += 1;
    renderFrame(context, true);
  }
  if (state.frame >= lastFrame(entry.transcript)) {
    setPlaying(context, false);
    return;
  }
  requestAnimationFrame((time) => advance(context, run, time));
}

/** Start or stop playback. */
function setPlaying(context: TerminalContext, playing: boolean): void {
  const { state } = context;
  state.playing = playing;
  state.lastTime = null;
  state.run += 1;
  context.playButton.innerHTML = playLabel(playing);
  const run = state.run;
  if (playing) requestAnimationFrame((time) => advance(context, run, time));
}

/** Switch tabs; the new tab starts at frame 0, or fully shown under reduced motion. */
function selectIndex(
  context: TerminalContext,
  index: number,
  autoplay: boolean,
): void {
  const entry = context.entries[index];
  if (entry === undefined) return;
  setPlaying(context, false);
  context.state.index = index;
  context.tabs.forEach((tab, position) => {
    tab.setAttribute("aria-selected", String(position === index));
    tab.tabIndex = position === index ? 0 : -1;
  });
  context.body.setAttribute("aria-labelledby", `terminal-tab-${entry.id}`);
  context.command.textContent = entry.transcript.command;
  context.meta.textContent = metaText(entry);
  const reduced = prefersReducedMotion();
  context.state.frame = reduced ? lastFrame(entry.transcript) : 0;
  renderFrame(context, false);
  if (autoplay && !reduced) setPlaying(context, true);
}

/** Play, Pause, Restart and Show all. */
function handleAction(
  context: TerminalContext,
  action: string | undefined,
): void {
  const entry = context.entries[context.state.index];
  if (entry === undefined) return;
  const final = lastFrame(entry.transcript);
  if (action === "all" || action === "restart") {
    setPlaying(context, false);
    context.state.frame = action === "all" ? final : 0;
    renderFrame(context, action === "all");
    if (action === "restart") setPlaying(context, true);
    return;
  }
  if (context.state.playing) return setPlaying(context, false);
  if (context.state.frame >= final) context.state.frame = 0;
  setPlaying(context, true);
}

/** Tab clicks, arrow keys between tabs, and control buttons. */
function bindEvents(root: HTMLElement, context: TerminalContext): void {
  root.addEventListener("click", (event) => {
    const tab = closestTarget(event, "[data-transcript]");
    if (tab !== null)
      return selectIndex(
        context,
        context.tabs.indexOf(tab as HTMLButtonElement),
        true,
      );
    const control = closestTarget(event, "[data-term-action]");
    if (control !== null) handleAction(context, control.dataset.termAction);
  });
  query(root, "[role=tablist]", HTMLElement).addEventListener(
    "keydown",
    (event) => {
      const delta = TAB_DELTAS[event.key];
      if (delta === undefined) return;
      const next =
        (context.state.index + delta + context.tabs.length) %
        context.tabs.length;
      selectIndex(context, next, true);
      context.tabs[next]?.focus();
    },
  );
}

/** Autoplay once when the terminal is half visible, unless motion is reduced or a capture took over. */
function bindAutoplay(context: TerminalContext): void {
  if (prefersReducedMotion()) return;
  const observer = new IntersectionObserver(
    (records) => {
      if (!records.some((record) => record.isIntersecting)) return;
      observer.disconnect();
      if (!context.state.captured) setPlaying(context, true);
    },
    { threshold: AUTOPLAY_VISIBILITY },
  );
  observer.observe(context.body);
}

/** Wire the rendered terminal and return the capture controller. */
export function initTerminal(
  root: HTMLElement,
  entries: readonly TranscriptEntry[],
): ReplayController {
  const context: TerminalContext = {
    pre: query(root, "[data-term-pre]", HTMLElement),
    body: query(root, ".terminal__body", HTMLElement),
    tabs: queryAll(root, "[data-transcript]", HTMLButtonElement),
    playButton: query(root, '[data-term-action="play"]', HTMLButtonElement),
    command: query(root, "[data-term-command]", HTMLElement),
    meta: query(root, "[data-term-meta]", HTMLElement),
    entries,
    lines: entries.map((entry) => entry.transcript.lines.map(lineMarkup)),
    state: {
      index: 0,
      frame: 0,
      playing: false,
      lastTime: null,
      run: 0,
      captured: false,
    },
  };
  selectIndex(context, 0, false);
  bindEvents(root, context);
  bindAutoplay(context);
  return createReplayController(context);
}

/** The controller behind `__setReplayProgress` and `__setReplayTab`. */
function createReplayController(context: TerminalContext): ReplayController {
  const indexOf = (id: string): number =>
    context.entries.findIndex((entry) => entry.id === id);
  return {
    /** Switch to a transcript tab without playing it. */
    setTab(transcriptId: string): boolean {
      const index = indexOf(transcriptId);
      if (index < 0) return false;
      context.state.captured = true;
      selectIndex(context, index, false);
      return true;
    },
    /** Stop playback and show the frame for progress in [0, 1]. */
    setProgress(progress: number, transcriptId?: string): number {
      context.state.captured = true;
      setPlaying(context, false);
      const index =
        transcriptId === undefined
          ? context.state.index
          : indexOf(transcriptId);
      if (index >= 0 && index !== context.state.index)
        selectIndex(context, index, false);
      const entry = context.entries[context.state.index];
      context.state.frame =
        entry === undefined ? 0 : frameForProgress(entry.transcript, progress);
      renderFrame(context, true);
      return context.state.frame;
    },
  };
}
