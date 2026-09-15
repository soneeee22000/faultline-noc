# ADR-001: Pass/fail judgments are deterministic code, never an LLM

- Status: Accepted
- Date: 2026-09-15

## Context

Faultline NOC scores RCA agents on a simulated 5G SA core. In this slice the judgments are:

- whether an RCA is correct;
- whether an agent cited evidence it never received;
- whether it wrote before gathering evidence;
- whether it blamed a symptom;
- whether it followed an instruction injected into a log line.

A later milestone adds a safety gate in front of write actions, such as `restart_nf`.

One option is to have an LLM act as the judge. It can read free text and grade nuance.

## Decision

Every judgment that gates a result is a pure function of three structured inputs:

- the agent's RCA, validated by pydantic;
- the ordered trace of reads and actions recorded by `EvidenceSession`;
- ground truth derived from what the fault injector actually did.

No LLM is called to decide pass or fail. The future write gate follows the same rule. It decides from structured state (approval token, dry-run diff, post-check result), not from a model's opinion.

## Reasons

1. **Reproducibility.** The same scenario and seed give byte-identical telemetry, so they give the same verdict. A judge model adds sampling variance and version drift that would hide real changes in agent quality.
2. **The judge must not share the agent's attack surface.** Scenario s07 puts an instruction in a log line. An LLM judge that reads the same telemetry can be steered by the same text. A set-membership check on evidence ids cannot.
3. **The harness can be tested.** Each mutant agent has one known defect, and CI asserts that the defect trips exactly its own detector. That discrimination test only means something when detectors are deterministic.
4. **Auditability.** A failed run points to a specific evidence id, trace position or action. An operator can check it by hand.
5. **Cost and speed.** The full matrix runs in seconds on a laptop with no API key. That keeps smoke-first iteration cheap.

## Consequences

- Detectors only see structured fields. The quality of free-text explanations is not graded.
- Scenarios need explicit labels. The simulator derives ground truth from the injected fault, and a test checks that it equals the label.
- Accuracy for mock agents proves the harness works, not that any AI works. Real-model accuracy has to come from recorded runs scored by this same code.
- A new failure mode needs a new detector and a mutant that exercises it, not a prompt change.

## Alternatives considered

- **LLM-as-judge for correctness and safety.** Rejected for gating, for reasons 1 and 2. It might later be used as a non-gating, clearly labelled signal for explanation quality.
- **Human review of every run.** Does not scale to scenarios × seeds × agents in CI. Kept for spot checks of recorded LLM runs.
