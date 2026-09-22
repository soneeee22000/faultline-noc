# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and entries are grouped by conventional-commit type.

## [Unreleased]

### Features

- **export:** `faultline_noc/export.py` builds a schema-versioned, timestamp-free JSON payload (run metadata, accuracy, action correctness, detection matrix, scenarios and sample traces), so the same seeds give byte-identical output.
- **cli:** `--json PATH` writes that payload alongside the unchanged markdown report.
- **runner:** `run_traced` keeps the ordered evidence-session trace next to each run result; `run_one` delegates to it.
- **scripts:** `scripts/refresh_site_data.py` regenerates `site/src/data/results.json` and captures real `--smoke`, `pytest` and `mypy --strict` output as transcripts with a command, Python version and date header.
- **site:** static project page under `site/` that reads the committed results and transcripts at build time and does not run the harness.
- **router:** new `faultline_noc/router/` package and `python -m faultline_noc.router --smoke | --all [--json PATH]`. It covers pydantic route plans where clarification is an outcome rather than an agent, a 52-item authored challenge set in `scenarios/router/challenge.yaml`, a keyword baseline that gates every network write and ignores instructions in quoted material, four one-defect mutant routers, per-item detectors (`misroute`, `missing_handoff_context`, `unsafe_write`, `missed_clarification`) and set-level metrics (route accuracy with a Wilson interval, macro-F1 by specialist, clarification precision and recall, handoff completeness and precision, unsafe-write gate recall over granted writes, injection resistance, per-step write-grant recall, Brier and ECE). `unsafe_write` compares writes by step position. The harness check fails if a mutant is missing or escapes its detector, if the baseline's gate recall is below 1.0, or if an injection probe (the baseline's plan plus one confirmed write, on each injection item) does not trip `unsafe_write`. The challenge loader rejects duplicate YAML keys, and `--challenge PATH` is recorded in the exported command and `meta.challenge_set`. The RCA CLI output is unchanged byte for byte.
- **scripts:** `refresh_site_data.py` also writes `site/src/data/router_results.json`.

### Documentation

- README rewritten for the public repository: business context, five-layer explainer, architecture diagram, headline results and media.
- Full agent, detector and side-effect tables moved to `docs/HARNESS.md`; full result tables and "How to read these numbers" moved to `docs/RESULTS.md`, regenerated from a fresh `--all` run.
- Added `docs/WHY.md`, `CHANGELOG.md` and an MIT `LICENSE`.
- Added `docs/ROUTER.md` (contract, detectors, metric definitions, why calibration is set-level, challenge-set caveats and every documented baseline miss) and `docs/adr/002-router-eval.md`, plus a README section.

### CI

- The Python job writes `results.json` from a fresh `--all` run and fails if it differs from the committed file.
- The Python job runs the router smoke run and `--all`, and fails if a fresh `router_results.json` differs from the committed file.
- `scripts/` is covered by `mypy --strict` and by the function-length and nesting-depth checks in `tests/test_code_standards.py`.

## [0.1.0] - 2026-09-15

### Features

- Seeded 5G SA core fault simulator and deterministic RCA evaluation harness (`a86eb8b`).
- Detectors `injected_action_taken`, `write_on_non_root` and `citation_unsupported`; every detector now has a mutant, with implied side effects declared in `MUTANT_TARGETS` (`82e96c1`).
- Mutants for following an injection, taking an injected action unread, uncited writes, bystander restarts and unsupported citations; the unseen-evidence mutant cites a real log id (`82e96c1`).
- Action correctness reported separately from top-1 accuracy; each scenario and seed is simulated once (`82e96c1`).

### Bug Fixes

- The rule baseline ignores the non-service-affecting `NTP_OFFSET_HIGH` alarm, so router noise no longer shadows NFs; the default `--all` seed count is 200 and baseline accuracy is pinned over 200 seeds per scenario (`82e96c1`).
- Agent factories split so evaluated agents take no arguments and ground truth reaches only an allowlist of the oracle and mutants (`82e96c1`).
- Corrected earlier baseline accuracy claims that were based on 20 seeds (`82e96c1`).

### CI

- The smoke run covers every scenario at seed 0; CI adds `ruff format --check`, the `--all` run and SHA-pinned actions; `.gitattributes` added (`82e96c1`).

### Refactoring

- Named alarm burst constants; documented the flap and N11 model simplifications (`82e96c1`).

[Unreleased]: https://github.com/soneeee22000/faultline-noc/compare/82e96c1...HEAD
[0.1.0]: https://github.com/soneeee22000/faultline-noc/commit/82e96c1
