import { mkdirSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { type Browser, chromium } from "playwright";
import { describeMedia, verifyMedia } from "./capture/contract.ts";
import {
  type FrameSequence,
  addFrame,
  createSequence,
  encodeGif,
  frameDurationMs,
  framesFor,
  holdFrames,
} from "./capture/gif.ts";
import {
  type PageSession,
  type Region,
  captureRegion,
  closePage,
  elementTop,
  finishTransitions,
  openPage,
  pauseTransitions,
  scrollToY,
  seekTransitions,
  topbarHeight,
} from "./capture/page.ts";
import { buildSite, startPreview } from "./capture/server.ts";

const SITE_DIR = resolve(import.meta.dirname, "..");
const MEDIA_DIR = resolve(SITE_DIR, "..", "docs", "media");
const PORT = 4173;
const BASE_URL = `http://localhost:${String(PORT)}/`;
const DESKTOP = { width: 1440, height: 900 } as const;
const MOBILE = { width: 390, height: 844 } as const;
const REGION_PADDING = 48;
const TRACK_ENTRY = 8;
const LAYERS_STILL_STEP = "4";

const LAYER_STORYBOARD: readonly {
  readonly step: string;
  readonly holdMs: number;
}[] = [
  { step: "collapsed", holdMs: 1000 },
  { step: "1", holdMs: 1600 },
  { step: "2", holdMs: 1600 },
  { step: "3", holdMs: 1600 },
  { step: "4", holdMs: 1600 },
  { step: "5", holdMs: 1600 },
  { step: "overview", holdMs: 2500 },
];

const REPLAY_STORYBOARD: readonly {
  readonly id: string;
  readonly leadMs: number;
  readonly tailMs: number;
}[] = [
  { id: "smoke", leadMs: 600, tailMs: 2000 },
  { id: "pytest", leadMs: 600, tailMs: 2500 },
];

const REGIONS: readonly { readonly file: string; readonly region: Region }[] = [
  {
    file: "scenarios.png",
    region: {
      top: "#scenarios .section-head",
      bottom: "#scenarios > .container",
    },
  },
  {
    file: "results.png",
    region: { top: "#results .section-head", bottom: "#results-charts" },
  },
  {
    file: "detection-matrix.png",
    region: { top: "#detection-matrix", bottom: "#detection-matrix" },
  },
  {
    file: "trace-injection.png",
    region: { top: "#trace-viewer", bottom: "#trace-viewer" },
  },
  {
    file: "models.png",
    region: { top: "#models .section-head", bottom: "#models .score-table" },
  },
  {
    file: "model-trace.png",
    region: { top: "#model-trace", bottom: "#model-trace" },
  },
];

/** Path of a media file in the committed docs folder. */
function media(file: string): string {
  return join(MEDIA_DIR, file);
}

/** Top-of-page viewport screenshot, used for the desktop and mobile hero. */
async function captureTop(
  browser: Browser,
  viewport: typeof DESKTOP | typeof MOBILE,
  file: string,
): Promise<void> {
  const session = await openPage(browser, BASE_URL, viewport);
  await scrollToY(session.page, 0);
  await finishTransitions(session.page);
  await session.page.screenshot({ path: media(file), animations: "disabled" });
  await closePage(session, file);
}

/** Put a layer state in place; the hook pins it so scrolling cannot override it. */
async function setLayerStep(session: PageSession, step: string): Promise<void> {
  const applied = await session.page.evaluate(
    (value) => window.__setLayerStep?.(value) ?? null,
    step,
  );
  if (applied !== step) throw new Error(`Layer hook rejected step ${step}`);
}

/** Scroll so the sticky layer stage fills the viewport below the top bar. */
async function frameLayerStage(session: PageSession): Promise<void> {
  const trackTop = await elementTop(session.page, "[data-layers-track]");
  await scrollToY(
    session.page,
    trackTop - (await topbarHeight(session.page)) + TRACK_ENTRY,
  );
}

/** The separated stack on the Guardrails step, so the panel shows a problem and its answer. */
async function captureLayersStill(browser: Browser): Promise<void> {
  const session = await openPage(browser, BASE_URL, DESKTOP);
  await setLayerStep(session, LAYERS_STILL_STEP);
  await frameLayerStage(session);
  await finishTransitions(session.page);
  await session.page.screenshot({
    path: media("layers.png"),
    animations: "disabled",
  });
  await closePage(session, "layers.png");
}

/** Render one step's transition frame by frame by seeking paused transitions, then hold. */
async function recordLayerStep(
  session: PageSession,
  sequence: FrameSequence,
  step: string,
  holdMs: number,
): Promise<void> {
  const { page } = session;
  await setLayerStep(session, step);
  const duration = await pauseTransitions(page);
  const transitionFrames = Math.ceil(duration / frameDurationMs());
  for (let frame = 0; frame <= transitionFrames; frame += 1) {
    await seekTransitions(page, Math.min(frame * frameDurationMs(), duration));
    await addFrame(sequence, (path) => page.screenshot({ path }));
  }
  await finishTransitions(page);
  holdFrames(sequence, Math.max(framesFor(holdMs) - transitionFrames - 1, 0));
}

/** The layer stack separating step by step, per the DESIGN.md storyboard. */
async function captureLayersGif(
  browser: Browser,
  scratch: string,
): Promise<void> {
  const session = await openPage(browser, BASE_URL, DESKTOP);
  const sequence = createSequence(scratch, "layers");
  await setLayerStep(session, "collapsed");
  await frameLayerStage(session);
  await finishTransitions(session.page);
  for (const scene of LAYER_STORYBOARD) {
    await recordLayerStep(session, sequence, scene.step, scene.holdMs);
  }
  await closePage(session, "layers.gif");
  encodeGif(sequence, media("layers.gif"), "bayer");
}

/** Show one replay frame through the hook and confirm the page rendered that exact frame. */
async function showReplayFrame(
  session: PageSession,
  id: string,
  frame: number,
  last: number,
): Promise<void> {
  const rendered = await session.page.evaluate(
    ([progress, transcript]) =>
      window.__setReplayProgress?.(progress, transcript) ?? -1,
    [frame / last, id] as const,
  );
  if (rendered !== frame)
    throw new Error(
      `Replay ${id} rendered frame ${String(rendered)}, expected ${String(frame)}`,
    );
}

/** Every frame of one transcript, with a lead-in and a hold on the final frame. */
async function recordTranscript(
  session: PageSession,
  sequence: FrameSequence,
  scene: (typeof REPLAY_STORYBOARD)[number],
): Promise<void> {
  const terminal = session.page.locator("#terminal");
  const shoot = (path: string): Promise<Buffer> =>
    terminal.screenshot({ path, animations: "disabled" });
  const last = await session.page.evaluate(
    (id) => window.__setReplayProgress?.(1, id) ?? -1,
    scene.id,
  );
  if (last <= 0) throw new Error(`Transcript ${scene.id} has no frames`);
  await showReplayFrame(session, scene.id, 0, last);
  await addFrame(sequence, shoot);
  holdFrames(sequence, framesFor(scene.leadMs));
  for (let frame = 1; frame <= last; frame += 1) {
    await showReplayFrame(session, scene.id, frame, last);
    await addFrame(sequence, shoot);
  }
  holdFrames(sequence, framesFor(scene.tailMs));
}

/** The terminal replay of the real smoke and pytest transcripts. */
async function captureTerminalGif(
  browser: Browser,
  scratch: string,
): Promise<void> {
  const session = await openPage(browser, BASE_URL, DESKTOP);
  const sequence = createSequence(scratch, "terminal");
  await session.page.evaluate(() => window.__setReplayProgress?.(0, "smoke"));
  await scrollToY(session.page, await elementTop(session.page, "#terminal"));
  for (const scene of REPLAY_STORYBOARD) {
    await recordTranscript(session, sequence, scene);
  }
  await closePage(session, "terminal-replay.gif");
  encodeGif(sequence, media("terminal-replay.gif"), "none");
}

/** Full-width section stills at 1440. */
async function captureRegions(browser: Browser): Promise<void> {
  const session = await openPage(browser, BASE_URL, DESKTOP);
  for (const { file, region } of REGIONS) {
    await captureRegion(session, region, media(file), REGION_PADDING);
  }
  await closePage(session, "section stills");
}

/** Every capture in the media contract. */
async function captureAll(browser: Browser, scratch: string): Promise<void> {
  await captureTop(browser, DESKTOP, "hero.png");
  await captureTop(browser, MOBILE, "mobile-hero.png");
  await captureLayersStill(browser);
  await captureRegions(browser);
  await captureLayersGif(browser, scratch);
  await captureTerminalGif(browser, scratch);
}

/** Build, serve, capture, then verify the media contract; exit non-zero on any violation. */
async function main(): Promise<void> {
  buildSite(SITE_DIR);
  mkdirSync(MEDIA_DIR, { recursive: true });
  const scratch = mkdtempSync(join(tmpdir(), "faultline-capture-"));
  const server = await startPreview(SITE_DIR, BASE_URL, PORT);
  const browser = await chromium.launch();
  try {
    await captureAll(browser, scratch);
  } finally {
    await browser.close();
    server.kill();
    rmSync(scratch, { recursive: true, force: true });
  }
  console.log(describeMedia(MEDIA_DIR).join("\n"));
  const problems = verifyMedia(MEDIA_DIR);
  if (problems.length > 0)
    throw new Error(`Media contract violated:\n${problems.join("\n")}`);
}

await main();
