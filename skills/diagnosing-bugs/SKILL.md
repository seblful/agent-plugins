---
name: diagnosing-bugs
description: "Feedback-loop-first diagnosis for hard bugs and performance regressions, in any language or stack — build a red-capable repro, minimise it, test ranked falsifiable hypotheses, fix behind a regression test, clean up. Use when the user says \"diagnose\" or \"debug this\", or reports something broken, throwing, failing, flaky, or slow. Not for a sweep of code that works (/code-sweep)."
license: MIT
---

Resolve `<skill-dir>` to the absolute directory containing this SKILL.md before running any command that uses it. Use the tools available in this assistant; if a named tool or subagent feature is unavailable, complete the same work directly.

# Diagnosing Bugs

A discipline for hard bugs. Skip a phase only with a stated reason. Read the project's context docs and decision records for the area first, where they exist.

## Phase 1 — Build a feedback loop

**This is the skill.** With a tight pass/fail signal that goes red on *this* bug, you will find the cause — bisection, hypotheses, and instrumentation all just consume it. Without one, no amount of reading code will save you. **Spend disproportionate effort here.**

### Ways to build one, roughly in order

1. **Failing test** at whatever seam reaches the bug — unit, integration, end-to-end.
2. **Request script** against a running instance.
3. **CLI run** on a fixture input, diffed against a known-good output.
4. **UI automation script** that drives the interface and asserts on what it shows or logs.
5. **Replayed capture** — a real request, payload, or event log saved to disk and fed through the code path in isolation.
6. **Throwaway harness** — the smallest subset of the system (one component, stubbed dependencies) that reaches the bug in one call.
7. **Property or fuzz loop** — for "sometimes wrong", run many random inputs and catch the failure.
8. **Bisection harness** — the bug appeared between two known states (commit, dataset, version): automate "set up state, check" so bisection runs unattended.
9. **Differential loop** — the same input through old vs new version, or two configs, diffing outputs.
10. **Human in the loop** — last resort. If a person must act, drive them with `scripts/hitl-loop.template.sh` so the loop stays structured and their answers come back to you.

### Tighten it

Treat the loop as a product. **Faster** — cache setup, skip unrelated init, narrow scope. **Sharper** — assert the exact symptom, not "didn't crash". **Deterministic** — pin time, seed randomness, isolate the filesystem and network. A 30-second flaky loop is barely a loop; a 2-second deterministic one is a superpower.

**Non-deterministic bugs:** the goal is a **higher reproduction rate**, not a clean repro. Repeat the trigger, parallelise, add stress, narrow timing windows. A 50% flake is debuggable; 1% is not — keep raising it.

**No loop possible:** stop and say so. List what you tried, and ask for access to an environment that reproduces it, a captured artifact (logs, trace, dump, recording), or permission for temporary instrumentation. **Do not hypothesise without a loop.**

### Done when

You can name **one command** you have **already run** — paste it and its output — that is:

- [ ] **Red-capable** — drives the real bug path and asserts the **user's exact symptom**
- [ ] **Deterministic** — same verdict every run, or a pinned high rate for flaky bugs
- [ ] **Fast** — seconds, not minutes
- [ ] **Agent-runnable** — unattended; a human only through the HITL script

**Reading code to build a theory before this command exists is the exact failure this skill prevents.**

## Phase 2 — Reproduce and minimise

Run the loop and watch it go red. Confirm it shows **the failure the user described** — a nearby different failure means a wrong fix — that it reproduces reliably, and capture the exact symptom so the fix can be checked against it.

**Minimise:** cut inputs, callers, config, data, and steps **one at a time**, re-running after each. Done when **every remaining element is load-bearing** — removing any one turns it green. The minimal repro shrinks the hypothesis space and becomes the regression test.

## Phase 3 — Hypothesise

Write **3–5 ranked hypotheses** before testing any — one hypothesis anchors on the first plausible idea. Each must be **falsifiable**:

> "If X is the cause, then changing Y makes the bug disappear, and changing Z makes it worse."

No prediction → not a hypothesis. **Show the ranked list to the user** — they often re-rank it instantly or have ruled some out. Don't block on an answer.

## Phase 4 — Instrument

Each probe tests one prediction; **change one variable at a time.** Prefer a debugger or REPL over logs, and targeted logs at the boundaries that separate hypotheses over "log everything".

**Tag every debug log** with a unique prefix such as `[DEBUG-a4f2]` — cleanup becomes one search.

**Performance:** logs mislead. Take a baseline measurement with a timer, profiler, or query plan, then bisect. **Measure first, fix second.**

## Phase 5 — Fix and regression test

Write the regression test **before the fix**, at a **correct seam** — one where the test exercises the real bug pattern as it occurs at the call site. A seam too shallow to reproduce the triggering chain gives false confidence. **No correct seam is itself a finding** — record it.

With a seam: turn the minimal repro into a failing test → watch it fail → fix → watch it pass → re-run the Phase 1 loop on the original, un-minimised scenario.

## Phase 6 — Clean up and look back

- [ ] The original repro no longer reproduces
- [ ] The regression test passes, or the missing seam is recorded
- [ ] Every `[DEBUG-…]` line is removed
- [ ] Throwaway harnesses are deleted or clearly parked
- [ ] The confirmed hypothesis is stated in the commit or PR message

**Then ask what would have prevented it** — after the fix, when you know most. No good test seam, tangled callers, hidden coupling → `/refactor-interfaces`, with specifics. A defect pattern likely to recur — a swallowed error, an unguarded absence, a fix that missed a copy → `/code-sweep`, with the pattern to sweep for.
