export {};

declare global {
  interface Window {
    /** Capture hook: set the layer stack to 0 (collapsed), 1..5 (a plane) or 6 (overview). */
    __setLayerStep?: (step: number | string) => string | null;
    /** Capture hook: show the terminal replay at progress 0..1, optionally on a transcript tab. */
    __setReplayProgress?: (progress: number, transcriptId?: string) => number;
    /** Capture hook: switch the terminal replay to a transcript tab without playing it. */
    __setReplayTab?: (transcriptId: string) => boolean;
  }
}
