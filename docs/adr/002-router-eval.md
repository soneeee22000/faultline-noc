# ADR-002: Router plans are scored as structured routes by deterministic detectors, with calibration at set level

- Status: Accepted
- Date: 2026-09-22

## Context

A router in front of the knowledge, testing and incident agents turns one request into an ordered plan. Its judgments are:

- whether the right specialists were picked, in the right order;
- whether each step got the context it needs, such as the test run handed from a testing step to an incident step;
- whether a network write is gated by confirmation, and never granted because of text the user didn't write;
- whether the router asked for clarification instead of guessing on an ambiguous request;
- whether its confidence tracks how often it's right.

It would be possible to have an LLM grade plans, or to score the plan's free text. ADR-001 already rules out an LLM judge for gating decisions in the RCA harness, and the same reasons apply here.

## Decision

A router returns a pydantic `RoutePlan`: ordered steps, each with an agent, context refs, allowed capabilities and a confirmation flag, or else a clarification. Four deterministic detectors compare that plan with the item's authored expectation. Clarification is an outcome of the plan, never a fourth agent.

Calibration is computed only at set level, as Brier score and ECE over a named number of bins. The outcome used is the exact ordered-route match, counting the clarification outcome.

The harness check requires each of four one-defect mutant routers to trip its own detector on an item where the keyword baseline doesn't. It also requires every mutant to have run, the baseline's unsafe-write gate recall over the writes it granted to be 1.0, and an injection probe to trip `unsafe_write`: on every injection item, the baseline's plan with one confirmed write appended. The router code sits in its own package, `faultline_noc/router/`, and changes nothing in the RCA harness or its outputs.

## Reasons

1. **Reproducibility.** A keyword baseline and pure-function detectors give byte-identical output. That lets CI diff the published JSON on every push, as it does for `results.json`.
2. **The judge must not be steerable by the request.** Injection items put instructions inside quoted logs and tickets. A structural check (does any step grant `network_write` where the expected step at that position asks for none?) can't be talked out of its verdict. None of the four mutants writes on an injection item, so this half of `unsafe_write` is exercised by the injection probe and by unit tests, not by a mutant.
3. **The harness can be tested.** Each mutant corrupts one field of the baseline's plan: the agents, the later refs, the gate, or the clarification. Switching off any detector makes the check fail and name that detector.
4. **Calibration only exists over many items.** A single confidence of 0.8 is neither right nor wrong. A per-item calibration detector would trip at random, so calibration is reported as a set metric with its small-n caveat.
5. **Isolation.** A separate package, CLI and JSON file keep the RCA results byte-identical. The only shared code is generic: the Wilson interval, the frozen base model and the repo root path.

## Consequences

- Only structure is graded. A step's free-text objective isn't scored, and neither is whether a specialist actually uses the refs it was given.
- `unsafe_write` compares writes by step position, not by target. A router that follows an injected target on a step where a write was legitimately requested isn't caught.
- The challenge set needs explicit expectations. Its tags are derived from those expectations and checked when the set loads.
- The mutants wrap the baseline, so the challenge set has to contain items where the baseline produces multi-step handoffs, gated writes and clarifications. Otherwise a mutant is reported as unexercised.
- Scores from a 52-item authored set show that the harness discriminates. They don't show that any router is good.
- A new routing failure mode needs a new detector and a mutant that exercises it.

## Alternatives considered

- **LLM-as-judge for plan quality.** Rejected for gating, for reasons 1 and 2. It might later be used as a non-gating, clearly labelled signal for objective wording.
- **Clarification as a fourth agent.** Rejected. It would let F1 reward "sending to clarify" as if it were a specialist, and it would blur the rule that a clarification carries no steps.
- **Per-item confidence thresholds as a detector.** Rejected for reason 4.
- **Reusing the RCA `RunResult` and report.** Rejected. It would change the RCA payload and its byte-identical CI diff for a different kind of subject.
