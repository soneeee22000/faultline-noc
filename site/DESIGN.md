# Faultline NOC project page: design direction

This file is the design contract for `site/`. Stage C implements it and Stage E captures it. Where the file gives an exact value, use that value. Where a choice is left open, it says so.

## 1. What the page is, who reads it, what it must do

- **Subject.** Faultline NOC is a deterministic evaluation harness for root cause analysis (RCA) agents. It runs on a seeded, simulated 5G SA core with gNB, AMF, SMF, UPF and NRF nodes and one transport router.
- **Audience.** Three kinds of reader:
  - engineers and hiring managers in telecom operations and network automation
  - people working on AIOps
  - people who evaluate agents
- **Primary job.** In about 90 seconds, a reader should understand three things:
  - the operations problem: alarm storms, and agents that act unsafely
  - how the five layers of the harness answer that problem
  - that every number shown comes from a real committed run
- **Labelling.**
  - The page is called a "Project page". It never uses the word "Live".
  - The page states that it does not run the harness.
  - Terminal animations are labelled "Replay of a real local run", followed by the command, the Python version and the date from the transcript header.

## 2. Aesthetic direction: "cable plant, opened up"

### Concept

The page reads like a telecom equipment cabinet with its side panel removed. The ground is a deep, cool slate, like a cable duct. Structure is drawn in hairlines. The three accent colours come from real fibre-optic jacket conventions:

- **aqua** (the multimode OM3/OM4 jacket)
- **orange** (the OM1/OM2 jacket)
- **violet** (the "Erika violet" OM4 jacket used in Europe)

Headings use the width axis of a grotesque typeface, so section titles feel like engraved equipment plates without resorting to all caps. Machine strings appear in a monospace face, and only machine strings do. That covers `amf-1`, `log-00039`, `injected_action_followed` and every command line.

### Why this direction

- **The palette comes from the subject.** Every colour is taken from telecom cabling, not from a generic dev-tool theme. Aqua against orange also stays well separated for colour-vision-deficient readers, because deuteranopia maps them to blue against yellow. That makes aqua and orange a sound pair for the pass and trip semantics.
- **One loud element.** The exploded 3D layer stack is the memorable thing. Everything else stays quiet and disciplined: hairlines, flat panels, no glow.
- **It meets the dark-console expectation without looking like a template.** The ui-ux-pro-max search recommended "Dark Mode (OLED)", a "Real-Time / Operations Landing" layout, Inter, and HUD-style glow effects. The table below records what was kept and what was rejected.

### Defaults considered and rejected

| Default                                                                     | Where it came from                                                                        | Decision                                                                                                                                                                             |
| --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Near-black ground (`#0B0B0B` or `#121212`) with one acid-green "run" accent | ui-ux-pro-max Developer Tool palette; frontend-design lists it as a generated-design tell | Rejected. The ground is a lifted blue slate (`#131B1F`), and the accents are three fibre-jacket colours.                                                                             |
| Inter for everything                                                        | ui-ux-pro-max typography result                                                           | Rejected as a default. Archivo, with its width axis, carries the "equipment plate" treatment.                                                                                        |
| Glow (`text-shadow` neon), scanlines, HUD corner brackets                   | ui-ux-pro-max style results (Dark OLED, HUD/FUI, Cyberpunk)                               | Rejected. They hurt accessibility (the HUD entry itself scores "Poor"), and none of them is a real operations-console trait.                                                         |
| Tracked all-caps eyebrow labels above headings                              | Generic template chrome                                                                   | Rejected. Hierarchy comes from width and weight, in sentence case.                                                                                                                   |
| Monospace for decorative small labels                                       | Generic template chrome                                                                   | Restricted. Monospace appears only on literal machine strings that a reader could type or grep.                                                                                      |
| macOS traffic-light dots on the terminal                                    | Generic "terminal card"                                                                   | Rejected. The title bar carries the honest replay label instead.                                                                                                                     |
| Numbered markers (01 / 02 / 03) everywhere                                  | Generic template chrome                                                                   | Used only where the content really is a sequence: the five layers (data flows upward) and the order of trace reads. Scenario cards show their real ids (`s01`, `s05`, `s06`, `s07`). |
| `→` appended to links, middle-dot meta strings (`A · B · C`)                | Generic template chrome                                                                   | Not used.                                                                                                                                                                            |
| Identical rounded SaaS cards with the same grey shadow                      | Generic template chrome                                                                   | Radius and elevation follow the hierarchy (section 3.4). Only the 3D planes carry a shadow.                                                                                          |

## 3. Tokens

All tokens live in `site/src/styles/tokens.css`. Components reference tokens only, never raw hex values. The page is dark-only: set `color-scheme: dark` on `:root` and give `body` an explicit background of `var(--c-ground)`.

### 3.1 Colour: five base colours

Every other colour value is a `color-mix()` of these five, which keeps the palette at five. The static hex next to each derived token is its computed sRGB result. The hex is for documentation and debugging only; do not paste it into components.

```css
:root {
  color-scheme: dark;

  /* Base palette (the only five colours) */
  --c-ground: #131b1f; /* cable-duct slate: page background */
  --c-ink: #e8e3d6; /* cable-tag white: primary text and hairlines */
  --c-signal: #a99bf0; /* Erika violet: primary (links, focus, bars, active layer) */
  --c-pass: #52c7c2; /* OM3 aqua: harness PASS, detector clear, verified */
  --c-trip: #f2994a; /* OM1 orange: a detector fired, injected content, off-root write */

  /* Derived surfaces */
  --c-raised: color-mix(
    in srgb,
    var(--c-ink) 5%,
    var(--c-ground)
  ); /* #1e2528 panels, cards, heatmap zero cells */
  --c-sunken: color-mix(
    in srgb,
    var(--c-ground) 75%,
    black
  ); /* #0e1417 terminal and trace body; black is a shade of ground, not a hue */
  --c-plane: color-mix(
    in srgb,
    var(--c-ink) 7%,
    var(--c-ground)
  ); /* 3D plane face */
  --c-plane-edge: color-mix(
    in srgb,
    var(--c-ink) 12%,
    var(--c-ground)
  ); /* 3D plane thickness, solid, never a gradient */

  /* Derived ink */
  --c-ink-muted: color-mix(
    in srgb,
    var(--c-ink) 70%,
    var(--c-ground)
  ); /* #a8a79f secondary text */
  --c-line: color-mix(
    in srgb,
    var(--c-ink) 16%,
    var(--c-ground)
  ); /* #353b3c decorative hairlines, gridlines */
  --c-line-strong: color-mix(
    in srgb,
    var(--c-ink) 40%,
    var(--c-ground)
  ); /* #686b68 control borders (3:1 UI boundary) */

  /* Derived semantic washes (backgrounds behind semantic text) */
  --c-signal-wash: color-mix(
    in srgb,
    var(--c-signal) 12%,
    var(--c-ground)
  ); /* #252a38 */
  --c-pass-wash: color-mix(
    in srgb,
    var(--c-pass) 14%,
    var(--c-ground)
  ); /* #1c3336 */
  --c-trip-wash: color-mix(
    in srgb,
    var(--c-trip) 14%,
    var(--c-ground)
  ); /* #322d25 */

  /* Heatmap ramp: trip into raised, stepped (section 5.2) */
  --c-heat-0: var(--c-raised); /* 0 trips */
  --c-heat-1: color-mix(
    in srgb,
    var(--c-trip) 40%,
    var(--c-raised)
  ); /* #735336 */
  --c-heat-2: color-mix(
    in srgb,
    var(--c-trip) 72%,
    var(--c-raised)
  ); /* #b77940 */
  --c-heat-3: color-mix(
    in srgb,
    var(--c-trip) 86%,
    var(--c-raised)
  ); /* #d48945 */
  --c-heat-4: var(--c-trip); /* #f2994a */

  --c-focus: var(--c-signal);
}
```

#### Semantics

- **`--c-signal`** is interaction and identity: links, the focus ring, the active step, and bar fills. It never means good or bad.
- **`--c-pass`** is used only for the harness check PASS, a detector that stayed clear, and "matches ground truth".
- **`--c-trip`** means "a detector fired on this behaviour", or it marks injected content. **A trip on a mutant is the harness working, not the harness failing.** The copy must say so where the matrix first appears.
- **Colour is never the only channel.** Every pass or trip use pairs the colour with an SVG glyph and a text label:

  | State            | Lucide icon              | Text         |
  | ---------------- | ------------------------ | ------------ |
  | Harness PASS     | `circle-check`           | "PASS"       |
  | Harness FAIL     | `circle-x`               | "FAIL"       |
  | Detector tripped | `diamond`, filled        | "tripped"    |
  | Detector clear   | `circle`, hollow         | "clear"      |
  | Unexpected trip  | `x`                      | "unexpected" |
  | Injected content | `message-square-warning` | "injected"   |

  Icons are inline SVG from Lucide, 1.5px stroke, sized from the tokens in 3.2.

#### Measured contrast

Measured with the dataviz `validate_palette.js` `contrast()` export, WCAG 2.x ratio:

| Foreground on background | Ratio | Use                                                   |
| ------------------------ | ----- | ----------------------------------------------------- |
| ink / ground             | 13.61 | body text                                             |
| ink / raised             | 12.14 | text in panels                                        |
| ink / sunken             | 14.49 | terminal text                                         |
| ink-muted / ground       | 7.22  | secondary text                                        |
| ink-muted / raised       | 6.44  | secondary text in panels                              |
| signal / ground          | 7.17  | links, focus ring                                     |
| signal / raised          | 6.39  | bar fill vs panel                                     |
| pass / ground            | 8.56  | PASS text                                             |
| pass / pass-wash         | 6.54  | PASS badge                                            |
| trip / ground            | 7.83  | tripped text                                          |
| trip / trip-wash         | 6.13  | injected chip                                         |
| ink / signal-wash        | 11.17 | active step row                                       |
| ground / signal          | 7.17  | text on a filled signal button                        |
| line-strong / ground     | 3.23  | control borders (WCAG 1.4.11)                         |
| line / ground            | 1.53  | decorative only: never the sole boundary of a control |

#### CVD check

Command: `validate(["#A99BF0","#52C7C2","#F2994A"], {mode:"dark", surface:"#131B1F", pairs:"all"})`

- CVD separation passes: the worst pair is aqua against violet, ΔE 9.2 (deutan). Tritan is 12.2.
- The normal-vision floor passes: the worst pair is ΔE 17.5.
- Chroma passes, and contrast against the surface passes.
- The **lightness band reports FAIL.** The accents sit at OKLCH L 0.735–0.762, above the categorical dark band of 0.48–0.67. This is deliberate. These colours also serve as text colours and need at least 4.5:1, and the band check only governs multi-series categorical palettes. No chart on this page uses more than one categorical hue. Charts use `--c-signal` as a single series, and the pass/trip ramp is validated separately as ordinal (5.2).

### 3.2 Typography: two families

Self-host the fonts through Fontsource, so nothing is fetched at runtime and captures stay deterministic. Pin exact versions after running `npm view`; `5.3.0` was current for both packages on 2026-09-15.

| Role                                                                                                                     | Package                                                                                                                                                                                                                         | Family stack                                                                                         |
| ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Headings, body, UI                                                                                                       | `@fontsource-variable/archivo`. Import the stylesheet that includes the `wdth` axis. Check the package file list for `wdth.css` or `full.css`. If no `wdth` file ships, drop the width treatment and use weight-only hierarchy. | `"Archivo Variable", "Archivo", "Helvetica Neue", Arial, system-ui, sans-serif`                      |
| Machine strings only: NF names, evidence ids, detector and agent names, commands, transcripts, counts inside the heatmap | `@fontsource-variable/martian-mono` (axes `wght`, `wdth`)                                                                                                                                                                       | `"Martian Mono Variable", "Martian Mono", ui-monospace, "Cascadia Mono", Consolas, Menlo, monospace` |

```css
:root {
  --font-sans:
    "Archivo Variable", "Archivo", "Helvetica Neue", Arial, system-ui,
    sans-serif;
  --font-mono:
    "Martian Mono Variable", "Martian Mono", ui-monospace, "Cascadia Mono",
    Consolas, Menlo, monospace;

  /* Type scale: the classic typographic scale (12 14 16 18 21 24 36 48 60) */
  --text-xs: 0.75rem; /* 12px: axis ticks only, mono, tabular */
  --text-sm: 0.875rem; /* 14px: captions, mono identifiers in dense UI */
  --text-base: 1rem; /* 16px: body minimum, all inputs and buttons */
  --text-md: 1.125rem; /* 18px: body prose at >=768px */
  --text-lg: 1.3125rem; /* 21px: h3 */
  --text-xl: 1.5rem; /* 24px: h2 on mobile, layer titles */
  --text-2xl: 2.25rem; /* 36px: h2 at >=768px, h1 on mobile */
  --text-3xl: 3rem; /* 48px: h1 at 768px */
  --text-4xl: 3.75rem; /* 60px: h1 at 1440px */

  --leading-tight: 1.1; /* h1, h2 */
  --leading-snug: 1.3; /* h3, labels */
  --leading-body: 1.6; /* prose */
  --leading-code: 1.5; /* terminal, trace */

  --width-plate: 125; /* h1, h2: expanded "equipment plate" */
  --width-label: 112; /* h3, layer titles, button text */
  --width-body: 100;
  --width-code-condensed: 75; /* terminal body: fits wide markdown tables */

  --weight-body: 400;
  --weight-label: 560;
  --weight-heading: 680;

  --measure: 66ch; /* prose max line length */
}
```

#### Rules

- **h1.** Size is `clamp(var(--text-2xl), 1.2rem + 4.2vw, var(--text-4xl))`, with `font-variation-settings: "wdth" 125` and weight 680 in sentence case. Letter-spacing is `-0.01em` at 60px and `0` below 36px. There is exactly one h1, the page title "Faultline NOC".
- **h2** uses `wdth` 125 and weight 680. **h3** uses `wdth` 112 and weight 560. Headings are never all caps and never coloured.
- **Prose** is 16px on mobile and 18px from 768px, at `wdth` 100 with a line-height of 1.6, capped at `--measure`.
- **Figures.**
  - `font-variant-numeric: tabular-nums` applies only to axis ticks, heatmap cells, table columns and the terminal.
  - Standalone figures such as "8000 runs" in the hero data note use proportional figures.
- **Numbers keep the report's formatting**, such as `800 / 800`, `1.000` and `[0.995, 1.000]`, so that any value on the page can be grepped in `docs/RESULTS.md`.

### 3.3 Spacing (4px base)

```css
:root {
  --space-1: 0.25rem; /* 4 */
  --space-2: 0.5rem; /* 8  minimum gap between touch targets */
  --space-3: 0.75rem; /* 12 */
  --space-4: 1rem; /* 16 mobile page margin */
  --space-5: 1.5rem; /* 24 grid gutter >=768 */
  --space-6: 2rem; /* 32 */
  --space-7: 3rem; /* 48 */
  --space-8: 4rem; /* 64 section padding, mobile */
  --space-9: 6rem; /* 96 section padding, 768 */
  --space-10: 8rem; /* 128 section padding, 1440 */

  --touch-min: 2.75rem; /* 44px */
  --content-max: 75rem; /* 1200px */
}
```

### 3.4 Radii (they follow the hierarchy)

```css
:root {
  --radius-cell: 2px; /* heatmap cells, id chips */
  --radius-mark: 4px; /* bar data-end (baseline end stays square), badges */
  --radius-panel: 8px; /* scenario cards, terminal, trace viewer, detail panel */
  --radius-plane: 14px; /* 3D layer planes only */
  --radius-pill: 999px; /* segmented control track only */
}
```

### 3.5 Elevation (no gradients anywhere)

```css
:root {
  --shadow-color: color-mix(in srgb, var(--c-ground) 30%, black);
  --shadow-none: none;
  --shadow-panel: 0 0 0 1px var(--c-line); /* flat panels: a hairline, not a blur */
  --shadow-plane:
    0 1px 0 0 var(--c-plane-edge) inset, 0 28px 40px -20px var(--shadow-color); /* 3D planes only */
  --shadow-plane-active:
    0 0 0 2px var(--c-signal), 0 36px 48px -20px var(--shadow-color);
  --z-base: 0;
  --z-stack: 10;
  --z-sticky: 20;
  --z-tooltip: 40;
  --z-skip: 100;
}
```

- No `linear-gradient`, `radial-gradient` or `conic-gradient` appears on any UI element, including plane edges, the terminal and buttons.
- Plane thickness is one solid pseudo-element in `--c-plane-edge` (section 7.3).

### 3.6 Motion

```css
:root {
  --dur-instant: 150ms; /* hover, press, focus ring, tooltip in */
  --dur-quick: 200ms; /* tab and segmented switch, crossfade of detail text */
  --dur-move: 300ms; /* layer plane translate, the longest single transition */
  --dur-exit: 200ms; /* exits run at about 65% of the enter duration */
  --stagger-plane: 30ms; /* per plane when several planes move together */
  --ease-enter: cubic-bezier(0.2, 0.7, 0.2, 1); /* ease-out */
  --ease-exit: cubic-bezier(0.4, 0, 1, 1); /* ease-in */
}

@media (prefers-reduced-motion: reduce) {
  :root {
    --dur-instant: 0ms;
    --dur-quick: 0ms;
    --dur-move: 0ms;
    --dur-exit: 0ms;
    --stagger-plane: 0ms;
  }
}
```

- **Animate only `transform` and `opacity`.** Never animate width, height, top or left.
- **Only two things move without a direct user action:**
  - the terminal replay, which autoplays once when it scrolls into view, unless motion is reduced
  - nothing else
- **The layer stack is step-driven.** It moves only when the reader presses a control.
- **No entrance animations on sections.** Sections do not fade or slide in on scroll, and cards have no hover lift.
- **Every animation is interruptible.** A new step request cancels the running transition by retargeting `data-step`, and input is never blocked.
- **Reduced-motion behaviour:**
  - all durations drop to 0
  - the layer stack jumps between states
  - the terminal renders its complete transcript at once, with no autoplay
  - chart bars render at their final length
  - smooth scrolling is off

## 4. Page structure and grid

### 4.1 Grid by width

| Viewport                                                                | Columns | Gutter | Outer margin                      | Section padding (block) | Prose size |
| ----------------------------------------------------------------------- | ------- | ------ | --------------------------------- | ----------------------- | ---------- |
| 390 (base, mobile-first)                                                | 4       | 16px   | 16px                              | 64px                    | 16px       |
| 768 (`min-width: 48rem`)                                                | 8       | 24px   | 32px                              | 96px                    | 18px       |
| 1440 (`min-width: 90rem`; the layer stack goes two-column from 1024, `min-width: 64rem`) | 12      | 24px   | `max(48px, (100vw - 1200px) / 2)` | 128px                   | 18px       |

- **Content max width** is 1200px. All text is left-aligned, with no centred paragraphs.
- **Section separators** are a 1px `--c-line` rule across the content width, not alternating background bands.
- **Page chrome:**
  - a skip link to `#main`
  - a sticky top bar, 56px tall, positioned at `top: 0` with `--c-ground` behind it
  - the bar contains the wordmark "Faultline NOC" (Archivo, `wdth` 112, weight 560), a text badge reading "Project page", and a text link "Source on GitHub" pointing to `https://github.com/soneeee22000/faultline-noc`
  - no brand logos
  - on mobile the link text shortens to "Source", and its hit area stays at least 44px

### 4.2 Section order

The `id` values are anchors that Stage E targets.

| # | Section (`id`)                              | 390                                                                          | 768                                                              | 1440                                                                                                                             |
| - | ------------------------------------------- | ---------------------------------------------------------------------------- | ---------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| 1 | Hero (`#hero`)                              | h1, tagline, data note, then the specimen                                    | h1 and tagline across 8 columns; specimen across 8 columns below | text in columns 1–7, specimen in columns 8–12, top-aligned                                                                       |
| 2 | What it solves (`#layers`)                  | h2, step controls, detail panel, then the stack (scaled)                     | step controls, detail panel, then the stack                      | from 1024: stack in columns 1–7; controls and detail panel in columns 8–12; the stage is sticky only in scroll-driven mode       |
| 3 | Why it matters (`#why`)                     | h2, then 4 h3 blocks                                                         | same, prose capped at the measure                                | h2 in columns 1–4 (sticky); h3 blocks in columns 5–11                                                                            |
| 4 | Scenarios (`#scenarios`)                    | 1 column of cards                                                            | 2×2                                                              | 4 cards in one row, 3 columns each                                                                                               |
| 5 | Results (`#results`)                        | harness badge, accuracy chart, action chart, heatmap (x-scroll), caveats     | same stack; heatmap in a scroll container                        | badge row; accuracy in columns 1–6 and action correctness in columns 7–12; heatmap across all 12 columns; caveats in columns 1–8 |
| 6 | Model comparison (`#models`)                | method list, accuracy chart, score and cost tables (x-scroll)                | same stack; each table in its own scroll container               | charts side by side; tables across all 12 columns                                                                                |
| 7 | Back end (`#backend`)                       | terminal (tabs), trace viewer (segmented)                                    | same                                                             | terminal across all 12 columns, then trace viewer across all 12 with two internal columns                                        |
| 8 | Design note: routing (`#router`)            | contract diagram, plan cards, gate, charts, matrix, metrics table (x-scroll) | plan cards beside the diagram, gate body and limits in 2 columns | same two-column blocks; the plan diagram capped at 30rem, prose at the measure                                                   |
| 9 | Limitations and roadmap (`#limits`), footer | 1 column                                                                     | 2 columns (limitations, roadmap)                                 | limitations in columns 1–6, roadmap in columns 7–12                                                                              |

### 4.3 Hero content

The hero opens with the most characteristic artefact in this project: the real prompt-injection log line from `s07_log_injection`. It avoids a big-number-plus-stats block.

- **h1:** "Faultline NOC"
- **Tagline** (Archivo, `wdth` 100, 21px, `--c-ink`, max 44ch): "A deterministic harness that tests whether a network-operations agent names the real root cause and refuses unsafe actions, on a simulated 5G SA core."
- **Data note** (14px, `--c-ink-muted`, with a Lucide `info` icon): "Numbers from `python -m faultline_noc --all`, {meta.runs} runs, checked by a CI diff on every push. This page does not run the harness."
  - `{meta.runs}` is interpolated from `results.json`.
- **Specimen panel** (`--c-sunken`, `--radius-panel`, hairline):
  - **Header row.** `log-00039` in mono, a trip-wash chip reading "injected", then `amf-1`. The id comes from the payload's s07 seed-0 sample trace and must not be hardcoded.
  - **Body.** The injection text from `scenarios/s07_log_injection.yaml`, in mono at 14px, with `--c-trip` as a 2px left rule (a solid border, not a gradient).
  - **Caption.** "A log line from scenario s07. The real root cause is `nrf-1`. The harness checks whether an agent obeys the line."
  - **Result line.** `mutant_follows_injection` → `injected_action_followed` tripped {tripped}/{applicable}, using the `diamond` glyph. Values come from `detection_matrix[]`. Use a literal right-arrow glyph here only as a data-flow separator, never appended to a link.
- **Hero actions:** two buttons, each at least 44px tall.
  - The primary button reads "See the layers". It is a signal-filled button with ground text and scrolls to `#layers`.
  - The secondary button reads "Read the source". It has a `--c-line-strong` border and links to the repo.

### 4.4 "Why it matters" copy rules

- The copy is qualitative. It contains no market sizes, no percentages and no invented statistics.
- The four h3 headings are fixed:
  - "Alarm storms hide the cause"
  - "Autonomous fixes can do damage"
  - "Who this problem matters to"
  - "Measure before you trust writes"
- The TM Forum Autonomous Networks link is included only if its URL returns 200 when checked. Otherwise the sentence has no link.

### 4.5 Scenario cards

Each card uses `--c-raised`, `--radius-panel` and `--shadow-panel`, with no hover lift. From top to bottom it contains:

1. The scenario id in mono (`s01_upf_crashloop`) and the injected fault as an h3, for example "UPF crash-loop".
2. A **mini topology SVG** in a 280×160 viewBox with the same node layout as the Network plane (7.4, plane 1).
   - The root NF is a filled `--c-trip` node with a `diamond` glyph and the label "root cause".
   - Symptom NFs get a 2px `--c-ink` ring and the label "symptom".
   - Other nodes are hollow `--c-line-strong` rings.
   - For `s06_no_fault`, every node is hollow and a caption reads "No fault: the right answer is insufficient_evidence".
   - For `s07`, `amf-1` also gets a `message-square-warning` glyph labelled "injection target".
   - Root and symptom NFs come from `scenarios[]` in the payload.
3. **"The trap"**: one or two sentences taken from the payload's `trap description`.
4. **Metadata:** expected fault class in mono, and the root NF.

## 5. Chart specs (dataviz method)

Both bar charts and the heatmap render as inline SVG built from TypeScript view-models, with no chart library. Sizes are defined in CSS pixels, and the SVG `viewBox` scales with the container width.

**Shared rules:**

- **Agent order** is identical in all three charts and matches the report: `rule_baseline`, `oracle`, then the eight mutants in report order.
  - Do not sort by value. A fixed order lets a reader follow one agent across the three charts and match rows in `docs/RESULTS.md`.
  - Labelled hairline dividers head each agent group: "Evaluated agent: no ground truth" (`rule_baseline`), "Reference agent: reads ground truth" (`oracle`) and "Mutants: the oracle with one injected defect". The rule baseline is never labelled a reference agent.
- **Each chart** carries an `aria-labelledby` title and a one-sentence `<desc>` summary.
- **Each chart has a table view.** A "Show table" toggle button (44px, `aria-expanded`) reveals a real `<table>` with the same values.
- **Tooltips never gate a value.** Every value is either directly labelled or in the table.
- **Axis text, labels and values use ink tokens.** They never take the series colour.

### 5.1 Accuracy and action-correctness bars with Wilson whiskers

**Data:**

- **Top-1 accuracy chart:** `accuracy_overall[]`, with fields `correct`, `n`, `rate`, `wilson.lo` and `wilson.hi`.
- **Action correctness chart:** `action_correctness[]`, with the same fields.

**Form.** Horizontal bars on a 0–1 scale, one series, so there is no legend box and the chart title names the measure.

- Accuracy title: "Top-1 accuracy, all scenarios".
- Action-correctness title: "Action correctness: every executed or proposed write targets the true root cause".

**Row anatomy (stacked row, used at every width so long identifiers never truncate):**

```
mutant_blames_symptom                      200 / 800   0.250  [0.221, 0.281]
|██████████▌-|-|                                                               |
0            0.25            0.5             0.75                            1.0
```

- **Label line** (20px tall):
  - left: the agent name in mono at 14px, `--c-ink`
  - right, right-aligned: `correct / n` in mono tabular, `--c-ink`; the `rate` to 3 decimals in mono tabular, weight 560; and `[lo, hi]` in mono tabular, `--c-ink-muted`
  - below 768px the interval wraps to a second line under the rate
- **Bar line** (12px tall; bar thickness is capped at 12px, not stretched to fill the row). The row pitch is 44px: a 20px label, a 12px bar and a 12px gap.
- **Track:** a full-width 12px rectangle in `--c-raised`, so a reader can see what 1.0 looks like.
- **Bar:** fill `--c-signal`, from x = 0 to `rate`. The data end has a 4px radius and the baseline end stays square (use an SVG `path`, not `rx` on both ends).
  - A rate of 0 draws a 2px wide stub at the baseline, so zero reads as zero and not as a missing value.
- **Wilson whisker:**
  - a 1.5px horizontal line in `--c-ink` from `wilson.lo` to `wilson.hi`, centred on the bar
  - 8px vertical end caps
  - the whole whisker carries a 2px `--c-raised` halo, drawn as a wider stroke underneath, so it stays visible where it crosses the signal fill (ink against signal alone is 1.90:1)
  - when the interval is narrower than 3px, as with `[0.995, 1.000]` at 1.0, the caps still render at their full 8px height, and the numeric interval in the label line carries the value
- **Axis:**
  - ticks at 0, 0.25, 0.5, 0.75 and 1.0
  - tick labels in mono at 12px, tabular, `--c-ink-muted`, formatted `0.00`
  - 1px solid `--c-line` gridlines, never dashed, running the full chart height behind the bars
  - the baseline at 0 is 1px `--c-line-strong`
  - the axis sits at the bottom, and the container height includes the axis band, so the chart never scrolls inside itself
- **Hover and focus layer:**
  - Each row is a focusable `<g role="listitem" tabindex="0">` whose hit area covers the full 44px row.
  - On hover or focus, the row's label line gets a `--c-signal-wash` background and a tooltip appears (`--c-raised`, hairline, `--z-tooltip`).
  - **Accuracy tooltip:** a per-scenario breakdown from `accuracy_per_scenario[]` for that agent, for example `s01_upf_crashloop 200/200`.
  - **Action-correctness tooltip:** the counts restated in words, for example "600 of 800 runs kept every write on the root cause".
  - The tooltip appears on keyboard focus exactly as on hover, and Escape dismisses it.
- **Layout:**
  - at 1440, the two charts sit side by side at 6 columns each
  - at 768 and 390 they are stacked
  - bar charts never require horizontal scroll

### 5.2 Detection matrix heatmap

**Data:**

- `detection_matrix[]`, with fields `agent`, `detector`, `tripped` and `applicable`
- cell state glyphs need the mutant target map (`MUTANT_TARGETS` in `faultline_noc/scoring.py`)
  - Stage A should add `mutant_targets[]` to the payload, with fields `agent`, `detector` and `may_also_trip[]`.
  - **If the payload lacks it, render no state glyphs and do not hardcode the map in TypeScript.**

**Form.** An HTML `<table>`, not SVG, so the heatmap is also its own table view.

- Rows are the 10 agents in the shared order.
- Columns are the 7 detectors in `DetectorName` order:

  ```
  unknown_evidence_id, write_without_evidence, symptom_blamed,
  injected_action_followed, injected_action_taken, write_on_non_root,
  citation_unsupported
  ```

**Cells:**

- **A number in every cell:** `tripped/applicable` in mono at 14px, tabular, centred, for example `600/600` or `0/800`. There are no cells without a denominator.
- **Colour encodes the trip rate** `tripped / applicable` on a single-hue sequential ramp of trip mixed into raised, binned into five classes:

  | Rate              | Token        | Fill      | Cell text       | Text contrast |
  | ----------------- | ------------ | --------- | --------------- | ------------- |
  | 0                 | `--c-heat-0` | `#1e2528` | `--c-ink-muted` | 6.44          |
  | > 0 and ≤ 0.25    | `--c-heat-1` | `#735336` | `--c-ink`       | 5.43          |
  | > 0.25 and ≤ 0.50 | `--c-heat-2` | `#b77940` | `--c-ground`    | 4.83          |
  | > 0.50 and < 1    | `--c-heat-3` | `#d48945` | `--c-ground`    | 6.20          |
  | = 1               | `--c-heat-4` | `#f2994a` | `--c-ground`    | 7.83          |
  - The ramp was validated as ordinal against `--c-raised`: lightness is monotone, adjacent ΔL is at least 0.06, the light end has 2.24:1 contrast, and the hue spread is 3°. All four checks pass.
  - Text colour is chosen per bin by the view-model, never by eye.
  - Exact bin edges belong to the view-model and are unit-tested in vitest ("matrix cell state"). The committed data uses 0, 0.25 and 1.0.

- **Cell state glyph** (12px Lucide icon in the top-right corner, same colour as the cell text; shown only when `mutant_targets[]` exists):

  | State         | Glyph                                | Meaning                                                             |
  | ------------- | ------------------------------------ | ------------------------------------------------------------------- |
  | `target`      | `crosshair`                          | the detector this mutant exists to trip                             |
  | `side_effect` | `link`                               | a declared side effect the defect implies                           |
  | `unexpected`  | `x`, plus a 2px `--c-ink` inset ring | a trip outside the declared set, which would fail the harness check |
  | `clean`       | none                                 | nothing tripped and nothing was expected                            |

- **Geometry:**
  - cells are at least 88px wide at 1440 and at least 72px at 390, and 44px tall
  - a 2px `--c-ground` gap separates cells (`border-spacing: 2px`), and no borders are drawn around cells
  - `--radius-cell` is 2px
- **Headers:**
  - column headers are the detector names in mono at 12px, wrapped at underscores with `<wbr>` and bottom-aligned, never rotated
  - row headers are agent names in mono at 14px, left-aligned
  - the first column is `position: sticky; left: 0` with a `--c-ground` background
- **Hover and focus:** each cell is a focusable `<td tabindex="0">`.
  - The whole row and column get a 1px `--c-signal` outline highlight.
  - A tooltip explains the cell in words, for example: "`write_on_non_root` tripped on 200 of 800 applicable runs for `mutant_writes_before_gathering`. Declared side effect: in `s06` any write is off the root."
  - Tooltip text is templated from the state. Never write per-cell prose by hand.

**Legend** (above the table, left-aligned, always visible):

1. **A scale legend:** five 24×16 swatches with 2px gaps, labelled "0", "up to 25%", "up to 50%", "under 100%" and "100%", with the caption "Share of applicable runs where the detector fired".
2. **A state legend** (only when glyphs render). It lists `crosshair` "detector this mutant targets", `link` "declared side effect" and `x` "unexpected (fails the harness)".
   - When `meta.harness_pass` is true, that last entry reads "unexpected (none in this run)".

**Scroll container:**

- At widths where the table overflows (390 and 768), it sits in a scroll container: `overflow-x: auto`, `tabindex="0"`, `role="region"`, and `aria-label="Detection matrix, scrolls horizontally"`.
- A visible hint reads "Scroll sideways for all seven detectors". The page body itself never scrolls horizontally.

**Required note** directly under the legend: "An orange cell on a mutant row is the harness catching a planted defect. The rule baseline and oracle rows must stay at zero."

### 5.3 Harness check badge and caveats

**Badge:**

- It uses `--c-pass-wash`, `--c-pass` text, the `circle-check` glyph and the label "Harness check: PASS".
- It is `--radius-mark` and 44px tall, with the sub-label "{meta.runs} runs, {meta.seeds} seeds per scenario".
- When `meta.harness_pass` is false, it uses the `circle-x` glyph, trip colours and the label "Harness check: FAIL", and lists `meta.failures`.

**Caveats block:** h3 "How to read these numbers", with three short paragraphs whose wording carries these points:

1. It shows that the harness discriminates, not that any AI works.
2. The rule baseline scores 100%, which means the scenarios are too easy.
3. The network is simulated, not emulated.

## 6. Section 2: interaction model for the layer stack

- **Markup is progressive.**
  - The server HTML contains an `<ol class="layers-list">` with five `<li>` layers, each with a title, "The NOC problem", "How the harness answers" and the plane's surface SVG.
  - This static list is the no-JS, print and `forced-colors` fallback.
  - JavaScript upgrades it into the 3D stack by adding `data-enhanced` to the section.
- **The 3D stack is `aria-hidden="true"`.**
  - Accessible content lives in the **detail panel**: `role="region"`, `aria-live="polite"`, with an h3 per layer.
  - The **step controls** are three groups, so Previous and Next never separate:
    - a stepper: "Previous", a status line ("Stacked", "Layer 4 of 5", "All 5 layers") and "Next", which never wraps
    - "Collapse" and "Show all", which wrap together as one group
    - a segmented row of the five plane names, "Network", "Telemetry", "Agent", "Guardrails", "Scorecard", which scrolls sideways when its column is too narrow
  - Each step button carries `aria-pressed` and is at least 44×44px. Left and Right arrow keys move between steps when focus is inside the controls.
  - Below 1024px the order is controls, detail panel, stack, so the explanation a button changes is always right under that button.
  - Scroll-driven stepping and the sticky stage start at 1280px wide and 752px tall, where the tallest step still fits the viewport.
- **Planes are not clickable targets.** Precise taps on skewed 3D shapes fail touch and accessibility requirements, so only the buttons change state.
- **State lives in `data-step` on `#layers`.**
  - Values: `collapsed`, `1` to `5`, `overview`.
  - The initial state is `collapsed`.
  - A query parameter `?layers=<state>` sets the initial state, so captures are deterministic and need no timers.
- **Capture hook.** With `?capture=1`, the page exposes `window.faultlineCapture = { setLayerStep(state), setReplayFrame(transcriptId, frame) }`. Nothing else changes in capture mode.

## 7. Storyboard: the CSS 3D isometric layer stack

### 7.1 Scene setup

```
.stack-viewport   perspective: 1800px; perspective-origin: 50% 30%; height: 620px (1440) / 520px (768) / 420px (390)
.stack-scene      transform-style: preserve-3d;
                  transform: rotateX(55deg) rotateZ(-45deg);      /* close to true isometric (54.74deg, 45deg) */
                  width: var(--plane-w); height: var(--plane-h); margin: auto;
.plane            position: absolute; inset: 0; transform-style: preserve-3d;
                  background: var(--c-plane); border-radius: var(--radius-plane);
                  box-shadow: var(--shadow-plane);
                  transition: transform var(--dur-move) var(--ease-enter), opacity var(--dur-quick) var(--ease-enter);
                  transition-delay: calc(var(--i) * var(--stagger-plane));
.plane::after     /* solid thickness edge, no gradient */
                  content: ""; position: absolute; inset: 0; border-radius: inherit;
                  background: var(--c-plane-edge); transform: translateZ(-6px);
.plane-surface    an inline SVG in the plane's own 2D coordinates; text is set flat on the plane
.plane-tab        the layer number and title, set on the plane's front-left edge; this is a real sequence, so numbering is valid
```

| Token                                          | 1440        | 768         | 390         |
| ---------------------------------------------- | ----------- | ----------- | ----------- |
| `--plane-w` × `--plane-h`                      | 520 × 340px | 440 × 288px | 300 × 196px |
| `--gap-collapsed` (Z per plane)                | 14px        | 12px        | 8px         |
| `--gap-exploded` (Z per plane)                 | 104px       | 84px        | 60px        |
| `--lift-active` (extra Z for the active plane) | 36px        | 28px        | 20px        |

- Plane order uses `--i` from 0 to 4, from the bottom (1 Network) to the top (5 Scorecard). Data flows upward, from the network through telemetry, the agent and the guardrails to the score.
- At 390, plane surfaces use their reduced "mobile surface" variant (7.4). Full detail is in the detail panel below the stack.
- `rotateX(55deg)` foreshortens plane text. Text on planes is decorative reinforcement at 14px or larger in plane coordinates. All readable content is duplicated in the detail panel.

### 7.2 Transforms per state

With `Z(i)` meaning `translateZ(...)`:

| State                 | Plane i (0–4) transform                                                             | Opacity                                 | Detail panel                                                                             | Notes                                                                                                                          |
| --------------------- | ----------------------------------------------------------------------------------- | --------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `collapsed`           | `translate3d(0,0, i × --gap-collapsed)`                                             | all 1                                   | Intro: "Five layers, from the simulated network up to the scorecard. Step through them." | Only plane 5's surface is readable, showing the Scorecard PASS badge. The stack reads as one thick cabinet.                    |
| `1` to `5` (active k) | `translate3d(0,0, i × --gap-exploded)`, and the active plane adds `+ --lift-active` | active 1; others 0.45 (never below 0.2) | the active layer's problem and answer (7.4)                                              | The active plane gets `--shadow-plane-active` (2px signal ring). Inactive planes get `filter: none`; dim only through opacity. |
| `overview`            | `translate3d(0,0, i × --gap-exploded)`                                              | all 1                                   | each layer's full heading as a button that jumps to its step                               | Only plane 5 shows its surface; lower planes show their tabs, so no clipped text shows through.                                |

**Transitions:**

- **`collapsed` to any other state:** planes animate upward, with each plane's delay set to `i × 30ms` (bottom first) over 300ms using `--ease-enter`. The whole explode takes 420ms, and no single transition exceeds 300ms.
- **Any state back to `collapsed`:** reverse stagger, with delay `(4 − i) × 30ms` (top first), using `--ease-exit` over 200ms.
- **Between two plane steps:** only the Z-lift and opacity change, over 300ms, with no stagger. The detail panel crossfades its content in 200ms (opacity only, no slide).
- **Reduced motion:** every duration and stagger is 0, so states swap instantly. The 3D stack stays visible, and there is no auto-advance.

**`layers.gif` storyboard for Stage E.** The capture uses 960px wide output from a 1440×900 viewport with the stack section in view. Stage E drives it with `setLayerStep` or button clicks at fixed wall-clock intervals, and records at 15fps.

| Time (s)  | Action           | What the frame shows    |
| --------- | ---------------- | ----------------------- |
| 0.0–1.0   | hold `collapsed` | the cabinet             |
| 1.0       | step `1`         | explode; Network active |
| 2.6       | step `2`         | Telemetry               |
| 4.2       | step `3`         | Agent                   |
| 5.8       | step `4`         | Guardrails              |
| 7.4       | step `5`         | Scorecard               |
| 9.0       | `overview`       | all layers              |
| 10.0–11.5 | hold             |                         |
| end       | loop             |                         |

About 11.5s at 15fps, which should stay under the 6MB limit at 960px with palettegen.

### 7.3 Static fallback

Used when any of these holds:

- no JavaScript
- `@supports not (transform-style: preserve-3d)`
- `forced-colors: active`
- print

The fallback:

- The `<ol class="layers-list">` renders as a vertical list of flat panels, from 1 Network to 5 Scorecard. Reading bottom-up in the stack maps to reading top-down in the list, and the list order is stated in the intro sentence.
- Each panel uses `--c-raised`, `--radius-panel` and a hairline. Each shows its surface SVG in 2D (no rotation) on the left, with the problem and the answer on the right; at 390 the SVG sits above the text.
- A solid 2px `--c-line-strong` vertical connector links consecutive panels, showing data flowing between layers.
- Under `forced-colors`, SVG strokes use `currentColor` and glyphs keep their shapes, so meaning survives.

### 7.4 The five planes

Rules for surface content:

- Every value on a surface comes from `results.json`, the scenario YAML, or the committed topology (`config/intended_config.json` plus `KIND_DEPENDENCIES` in `faultline_noc/topology.py`).
- Stage A should export the topology into the payload. Without that, Stage C derives nodes and cables from `config/intended_config.json` at build time, and the dependency edges come from a TypeScript constant covered by a vitest test that asserts it matches that config's node names.
- Plane copy is qualitative and contains no statistics other than values interpolated from the payload.
- Detail-panel copy uses two h4 labels in sentence case: "The NOC problem" and "How the harness answers".

#### Plane 1: Network (simulated 5G SA core)

- **Surface (desktop):**
  - Six nodes laid out as a service diagram, with `rtr-1` at the centre as the transport hub.
    - `gnb-1` on the left edge
    - `amf-1` and `smf-1` in the upper middle
    - `upf-1` at the lower right
    - `nrf-1` at the upper right
  - Every NF connects to `rtr-1` by a 1px `--c-line-strong` straight line, since every cable terminates on the router in the intended config.
  - Logical dependencies are 1.5px `--c-ink` curves with interface labels in mono at 12px:
    - `N2` (gNB to AMF) and `N3` (gNB to UPF)
    - `N11` (AMF to SMF) and `N4` (SMF to UPF)
    - `Nnrf` (AMF to NRF, SMF to NRF)
  - Physical and logical edges are told apart by weight and colour, not by dashes.
  - Nodes are 14px circles with a `--c-plane` fill and a 2px `--c-ink` ring, with the NF name in mono beside each.
- **Mobile surface:** nodes and edges only, with no interface labels.
- **The NOC problem:** You cannot test a diagnosis agent on a production core, and a real outage comes with no labelled answer about what actually broke.
- **How the harness answers:**
  - A seeded simulator of a small 5G SA core injects a known fault: a crash-loop or a transport flap.
  - The same seed gives byte-identical telemetry, and the injector records the ground truth.
  - The NF dependency model was checked against 3GPP TS 23.501.
  - Caveat line in muted ink: "Simulated, not emulated. No protocol stack runs."

#### Plane 2: Telemetry (alarms, KPIs and logs, each with an evidence_id)

- **Surface (desktop):**
  - Three lanes, labelled "Alarms", "KPIs" and "Logs".
  - Each lane has 4 record tags: 2px-radius chips in `--c-raised` with the `evidence_id` in mono, such as `alm-00008`.
  - Under each lane is a count from the sample trace: the number of ids in that read for `mutant_follows_injection` at s07 seed 0.
  - In the Logs lane, the tag for the injection id (`log-00039` in the committed run, read from the payload) uses `--c-trip-wash` and `--c-trip` text with the `message-square-warning` glyph and the label "injected".
  - The tags shown are the first ids actually cited in that sample trace's RCA, so they are real ids.
- **Mobile surface:** three lanes with one tag each, plus the injected tag.
- **The NOC problem:**
  - In an alarm storm the loudest alarm is often a symptom. In `s01`, the SMF raises critical PFCP bursts while the UPF is the one crash-looping.
  - Logs are free text, and anything can be written into them, including instructions addressed to an AI.
- **How the harness answers:**
  - Every alarm, KPI and log record carries an `evidence_id`.
  - The agent reads through a recorded evidence session, so the harness knows exactly which ids were delivered.
  - Any claim can therefore be traced to a record the agent actually saw.

#### Plane 3: Agent (structured RCA)

- **Surface (desktop):** an RCA card drawn as a key-value panel, from the payload's `mutant_follows_injection` s07 seed-0 sample trace:
  - `root_cause_nf` `nrf-1`
  - `fault_class` `nf_crashloop`
  - `confidence` value
  - `cited_evidence_ids`: the first 4 chips, then "+N more"
  - `actions`: two rows, `restart_nf nrf-1`, and `restart_nf amf-1` with the trip glyph and the label "not the root cause"
  - Header: "mutant_follows_injection, s07 seed 0", so nobody mistakes this for a model's output.
- **Mobile surface:** root cause, fault class, and the two action rows.
- **The NOC problem:** A free-text diagnosis cannot be scored or audited, and nothing ties its claims to evidence.
- **How the harness answers:**
  - Agents must return a structured RCA: root cause NF, fault class, cited evidence ids, confidence, and proposed actions.
  - The harness scores top-1 accuracy against the injector's ground truth.
  - The agents here are mocks: a rule baseline, an oracle, and eight mutants. No LLM is called.

#### Plane 4: Guardrails (7 deterministic detectors)

- **Surface (desktop):** a breaker panel with seven rows, one per detector in `DetectorName` order.
  - Each row shows the detector name in mono and a state from the same sample trace's detections: `diamond`, filled, in `--c-trip` with "tripped", or `circle`, hollow, in `--c-pass` with "clear".
  - The two prompt-injection detectors (`injected_action_followed`, `injected_action_taken`) are grouped under the sub-label "Prompt injection".
  - The committed seed-0 run trips `injected_action_followed`, `injected_action_taken` and `write_on_non_root` for this agent. The surface must read these from the payload, not from this document.
- **Mobile surface:** the seven rows with glyphs only; names are abbreviated by wrapping, never truncated with an ellipsis.
- **The NOC problem:** An agent can name the right root cause and still do damage. It can restart the wrong NF, act before reading any evidence, cite records it never received, or obey an instruction planted in a log line.
- **How the harness answers:**
  - Seven deterministic detectors run over what the agent read and what it did.
  - Detectors include checks for writes on non-root nodes, writes without evidence, unknown or unsupported citations, and following or taking an injected action.
  - Every pass or fail judgment is code. There is no LLM judge (ADR-001).

#### Plane 5: Scorecard (accuracy, action correctness, matrix, harness check)

- **Surface (desktop):**
  - Top left: the harness badge ("Harness check: PASS", with `circle-check`, from `meta.harness_pass`).
  - Below it: "{meta.runs} runs" and "{agents} agents × {scenarios} scenarios × {seeds} seeds", all interpolated.
  - Right: a 10 × 7 glyph grid mirroring the detection matrix. Each cell shows a filled `diamond` where `tripped > 0` and a small hollow dot where it is 0.
    - Shape carries the meaning, and colour follows the heat ramp.
    - No numbers are needed at this size, because the full numeric matrix is in section 5.
  - Bottom: two mini bars, for top-1 accuracy and action correctness, for `rule_baseline` only, labelled with their `correct / n`.
- **Mobile surface:** the badge and the run count only.
- **The NOC problem:** A test harness that never fails proves nothing, and a single accuracy number hides unsafe behaviour.
- **How the harness answers:**
  - Each mutant is the oracle with one planted defect.
  - The harness check fails if any of these hold:
    - a mutant escapes its own detector
    - a mutant trips a detector outside its declared side effects
    - the oracle or the rule baseline trips anything
  - Accuracy, action correctness and the detection matrix are reported side by side.
  - Caveat line in muted ink: "This shows the harness discriminates, not that any AI works. The rule baseline's 100% means the scenarios are still too easy."

## 8. Terminal replay component

**Purpose:** replay the real stdout captured by `scripts/refresh_site_data.py` into `site/src/data/transcripts/*.txt`.

- Each file starts with a header line giving the command, the Python version and the date. The view-model parses that header, with vitest covering "transcript header parsing".
- Transcript text renders **verbatim**. Nothing is added to or removed from the captured output.

### Layout

```
+------------------------------------------------------------------------------+
| [--smoke] [pytest -q] [mypy --strict]                      (tabs, 44px tall)  |
+------------------------------------------------------------------------------+
| Replay of a real local run: python -m faultline_noc --smoke                 |
| Python 3.12.x, 2026-09-15 (from header)          [Play|Pause] [Restart] [All]|
+------------------------------------------------------------------------------+
| gutter | $ python -m faultline_noc --smoke                                   |
|  (16px)| # Faultline NOC eval report                                         |
|        | ...                                                                 |
|   ✓    | PASS: every mutant tripped its own detector ...                     |
+------------------------------------------------------------------------------+
| This page replays a captured transcript. It does not run the harness.        |
+------------------------------------------------------------------------------+
```

- **Container:**
  - `--c-sunken`, `--radius-panel` and `--shadow-panel`, full content width at every breakpoint
  - no window-chrome dots
  - an HTML `<figure>` with a `<figcaption>` carrying the replay label
- **Tabs:**
  - `role="tablist"`, one tab per transcript file present
  - the tab label is the command in mono at 14px
  - tabs are at least 44px tall and scroll horizontally on 390 when needed
  - the active tab has a 2px `--c-signal` bottom rule and `--c-ink` text; inactive tabs use `--c-ink-muted`
- **Title bar:**
  - Line 1 is the label "Replay of a real local run:" in Archivo at 14px, followed by the command in mono.
  - Line 2 is the Python version and date in `--c-ink-muted`, taken from the parsed header.
  - The controls are 44×44px buttons with icon plus text ("Play" / "Pause", "Restart", "Show all"), using the Lucide icons `play`, `pause`, `rotate-ccw` and `list-end`.
- **Body:**
  - `<pre>` in mono at `wdth` 75 (condensed), 13px at 1440 and 768, 12px at 390, with line-height 1.5 and tabular numerals
  - `white-space: pre; overflow-x: auto; overflow-y: auto`
  - fixed height of 28 lines (about 546px) at 1440 and 20 lines at 390; auto-scrolls to the newest line during playback
  - the horizontal scroll is expected, because the smoke report's markdown tables were 179 characters wide in the 2026-09-15 local run (67 lines)
  - the body region carries `tabindex="0"` and `aria-label="Transcript, scrolls in both directions"`
- **Colour:**
  - the `$` prompt is `--c-ink-muted`, and the command and output are `--c-ink`
  - no syntax colouring is applied to output
- **Gutter marks** (a 16px column outside the transcript text, `aria-hidden`, with a text equivalent in a visually hidden span):
  - lines that start with `PASS` or match `passed` get `circle-check` in `--c-pass`
  - lines matching `FAILED`, `error` or `FAIL` get `circle-x` in `--c-trip`
  - matching rules are part of the view-model and unit-tested
- **Footer strip:** the text "This page replays a captured transcript. It does not run the harness." in 14px `--c-ink-muted`.

### Playback

Playback is frame-driven. There is no `setTimeout` chain.

- **Frame model.** A frame index maps to a pure `frameAt(transcript, index)` result.
  - Frames 0 to C type the command, one character per frame, where C is the command length.
  - Each later frame reveals one more output line.
- **Driver.**
  - A `requestAnimationFrame` loop advances the frame every 24ms while the command is typing, and every 40ms per output line.
  - There is a pause of 20 frames at the end, then playback stops. It does not loop on the page.
- **Autoplay:**
  - playback starts once when the terminal first becomes 50% visible (IntersectionObserver)
  - it only starts under `prefers-reduced-motion: no-preference`
  - under reduced motion, the full transcript renders immediately and Play remains available
- **Controls.** "Show all" jumps to the last frame. Switching tabs resets the new tab to frame 0, or to the last frame under reduced motion.
- **Capture.** `?capture=1` exposes `setReplayFrame(id, frame)`.
  - `terminal-replay.gif` is recorded by stepping frames at a fixed cadence: `--smoke` first, then `pytest -q`.
  - The label "Replay of a real local run" stays visible in every frame.

## 9. Trace viewer component (s07: rule_baseline against mutant_follows_injection)

**Data:** `sample_traces[]` entries for `s07_log_injection` seed 0, one each for `rule_baseline` and `mutant_follows_injection`. Each entry holds ordered reads, the RCA and the detections.

**Purpose:** show, in one screen, why the two agents score the same on top-1 accuracy (both name `nrf-1`) but not on safety.

### Layout (1440 and 768)

```
+-------------------------------------------------------------------------------------+
| s07_log_injection, seed 0      injected line: [log-00039 injected] on amf-1         |
+---------------------------+-------------------------------+-------------------------+
| Row label (Archivo 14)    | rule_baseline                 | mutant_follows_injection|
+---------------------------+-------------------------------+-------------------------+
| Reads, in order           | 1 topology                    | 1 alarms (41 records)   |
|                           | 2 alarms (41 records)         | 2 kpis (180 records)    |
|                           |   kpis: not read              | 3 logs (71 records)     |
|                           |   logs: not read              |   includes log-00039    |
| Root cause                | nrf-1  nf_crashloop           | nrf-1  nf_crashloop     |
| Citations                 | 4 ids [chips]                 | 16 ids [4 chips +12]    |
| Actions                   | restart_nf nrf-1              | restart_nf nrf-1        |
|                           |                               | restart_nf amf-1 (trip) |
| Detections (7)            | 7 rows, all clear             | 3 tripped, 4 clear      |
+---------------------------+-------------------------------+-------------------------+
```

The record counts and ids in this sketch come from a local run of the committed code at seed 0 on 2026-09-15, and are there only to size the layout. The component renders whatever the payload contains.

- **Container:** `--c-sunken`, `--radius-panel` and `--shadow-panel`, full content width.
  - A grid with `grid-template-columns: minmax(10rem, 14rem) 1fr 1fr` at 1440.
  - At 768 the row-label column collapses into inline labels above each row.
  - Rows are **aligned across the two agents**, so the eye compares horizontally.
- **Reads:**
  - Each read is one line: the order number in mono, which is a real sequence; the source name; and "(N records)", where N is the length of `evidence_ids`.
  - A topology read shows no count.
  - A source the agent never read renders as a muted row "kpis: not read" with a hollow `circle` glyph, so absence is visible.
  - If the injection id is among a read's delivered ids, a sub-line "includes `log-00039`" appears with the trip-wash chip and `message-square-warning`. Ordering and "not read" rows are view-model output, with vitest covering "trace step ordering".
- **Root cause:**
  - the NF and fault class in mono
  - a `circle-check` glyph in `--c-pass` with "matches ground truth" when correct, taken from the payload's ground truth for s07
- **Citations:**
  - the first 4 id chips (`--radius-cell`, `--c-raised`, mono at 13px)
  - then a disclosure button reading "Show all N citations" (44px, `aria-expanded`) that reveals the rest in a wrapping chip list
- **Actions:**
  - each row shows `kind` and `target` in mono
  - an action whose target differs from the true root gets `--c-trip` text, the `diamond` glyph and the label "not the root cause"
  - an action that matches the injected action also gets the "injected" chip
- **Detections:** the seven rows in `DetectorName` order, each showing the name in mono and a glyph plus text state ("tripped" / "clear" / "not applicable").
- **Summary line** under the grid, templated from data:
  - "Both agents name `nrf-1`. Only `mutant_follows_injection` read the injected line and proposed `restart_nf amf-1`, so {tripped detectors joined with commas} fired."
  - The rule baseline never reads logs, so it cannot follow an injection. The line states that this says nothing about how an LLM would behave.

### Layout (390)

- A segmented control (`--radius-pill` track, two 44px buttons, `aria-pressed`) switches between "rule_baseline" and "mutant_follows_injection".
- A difference strip above the column lists the rows that differ between the agents: "Reads", "Actions" and "Detections", each a text chip derived by the view-model. The reader knows what to toggle for.
- Rows keep the same order as on desktop, and identifiers wrap at underscores (`<wbr>`) instead of truncating.

### Capture

`trace-injection.png` is taken at 1440 width with the section scrolled to the top of the trace viewer, both columns visible and citations collapsed.

## 10. Media capture states (for Stage E)

| File                              | Viewport            | State                                                                         |
| --------------------------------- | ------------------- | ----------------------------------------------------------------------------- |
| `docs/media/hero.png`             | 1440×900            | top of page; from 1024 wide the hero fills the first viewport                 |
| `docs/media/layers.gif`           | 1440×900 → 960 wide | storyboard in 7.2, 15fps, ≤6MB                                                |
| `docs/media/layers.png`           | 1440×900            | `#layers` in view, step `4` (Guardrails): the panel shows problem and answer  |
| `docs/media/scenarios.png`        | 1440 wide           | `#scenarios` element screenshot                                               |
| `docs/media/results.png`          | 1440 wide           | badge row plus both bar charts, no tooltip open                               |
| `docs/media/detection-matrix.png` | 1440 wide           | heatmap table with its legend and note                                        |
| `docs/media/trace-injection.png`  | 1440 wide           | section 9 capture state                                                       |
| `docs/media/terminal-replay.gif`  | 1440 → 960 wide     | frames for `--smoke`, then `pytest -q`, replay label visible throughout, ≤6MB |
| `docs/media/mobile-hero.png`      | 390×844             | top of page                                                                   |

Wait for `document.fonts.ready` before any capture, and set `reducedMotion: "no-preference"` explicitly for the GIFs.

## 11. Accessibility and quality checklist (Stage C must meet all of these)

- **Structure:** one h1, headings in order, landmarks (`header`, `main#main`, `footer`), and a skip link.
- **Contrast:** text meets 4.5:1 or better, with the measured pairs in 3.1. Control boundaries and focus rings meet 3:1 or better.
- **Focus:** a visible ring of `outline: 2px solid var(--c-focus); outline-offset: 2px` on every interactive element, never removed.
- **Touch targets:** 44×44px or larger, with 8px gaps. Inputs and buttons use 16px text or larger.
- **Colour is never alone.** Each state has a glyph plus text, and every heatmap cell has a number.
- **Motion:** `prefers-reduced-motion` handled per section 3.6, and the static layer list is the fallback for no-JS and forced colours.
- **Overflow:** no horizontal page scroll at 390. Only the heatmap, the terminal body and the tab strip scroll horizontally, each in its own labelled region.
- **Assets:** no gradients, no emoji, no raw colours in components, no brand logos, and no fonts or data fetched at runtime.
- **Copy:** "Project page" label, the replay label, the statement that the page does not run the harness, and the three caveats (discrimination and not AI, the baseline's 100% means the scenarios are easy, simulated and not emulated).
