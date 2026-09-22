import "@fontsource-variable/archivo/wdth.css";
import "@fontsource-variable/martian-mono/wdth.css";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/svg.css";
import "./styles/sections.css";
import "./styles/layers.css";
import "./styles/charts.css";
import "./styles/backend.css";
import type { LayerController } from "./components/layer-stack";
import type { ReplayController } from "./components/terminal";
import { bindScrollHints } from "./lib/scroll-hint";
import { initTooltip } from "./lib/tooltip";
import { renderBackend } from "./sections/backend";
import { renderFooter } from "./sections/footer";
import { renderHero } from "./sections/hero";
import { renderLayers } from "./sections/layers";
import { renderLimits } from "./sections/limits";
import { renderModels } from "./sections/models";
import { renderResults } from "./sections/results";
import { renderRouter } from "./sections/router";
import { renderScenarios } from "./sections/scenarios";
import { renderWhy } from "./sections/why";
import { parseLayerStep } from "./viewmodel/layers";

/** Deterministic hooks for the capture script; they only set state, they never time anything. */
function exposeCaptureHooks(
  layers: LayerController,
  replay: ReplayController,
): void {
  window.__setLayerStep = (step: number | string): string | null => {
    const parsed = parseLayerStep(step);
    if (parsed !== null) layers.setStep(parsed, "capture");
    return parsed;
  };
  window.__setReplayProgress = (
    progress: number,
    transcriptId?: string,
  ): number => replay.setProgress(progress, transcriptId);
  window.__setReplayTab = (transcriptId: string): boolean =>
    replay.setTab(transcriptId);
}

/** Render every section in page order, then wire shared behaviour. */
function boot(): void {
  renderHero();
  const layers = renderLayers();
  renderWhy();
  renderScenarios();
  renderResults();
  renderModels();
  const replay = renderBackend();
  renderRouter();
  renderLimits();
  renderFooter();
  bindScrollHints(document);
  initTooltip();
  exposeCaptureHooks(layers, replay);
  void document.fonts.ready.then(() => {
    document.documentElement.dataset.ready = "true";
  });
}

boot();
