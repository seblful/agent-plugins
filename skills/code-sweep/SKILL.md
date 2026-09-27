---
name: code-sweep
description: "Sweep a codebase for bad practices, latent bugs, and bad implementations, list the findings ranked by severity, then apply only the fixes you approve."
license: MIT
---

Resolve `<skill-dir>` to the absolute directory containing this SKILL.md before running any command that uses it. Use the tools available in this assistant; if a named tool or subagent feature is unavailable, complete the same work directly.

Read [the code-smells reference](references/code-smells/SKILL.md) when applying this workflow.

# Code Sweep

Find what is wrong with code that already works, then fix it — **audit first, apply only on approval**.

Sweep the whole codebase. the user's request narrows it to a subtree; the process is the same.

## Scope: implementations, not interfaces

> **Would the fix change what a caller must know?**
> **No** → it belongs here. **Yes** → hand it to `/refactor-interfaces`.

Renaming a local, flattening nesting, fixing a swallowed error, and deleting dead code are in scope. Splitting a god object, removing a wrapper callers go through, and reshaping a signature move a seam — not here.

When the sweep turns up one of these, **list it as a handoff and do not fix it**:

| Finding | Belongs to |
| --- | --- |
| Security hazard — injection, unsafe deserialization, hardcoded secret, unvalidated input | `/security-review` |
| Performance problem — work repeated per item, quadratic hot path, unbounded growth | the `diagnosing-bugs` skill (measure first) |
| Shallow module, wrong seam, interface redesign | `/refactor-interfaces` |
| Bloated, sprawling, or outdated **markdown** | `/docs-sweep` |

## Phase 0 — Bound the sweep and take a baseline

**Bound it.** List the source directories and the exclusions — vendored and generated code, migrations, lockfiles, fixtures, dependency and build output. Read the project's own conventions first — its assistant instructions, context docs, and decision records, where they exist: **a convention mistaken for a smell is the most expensive false positive.**

**Take a baseline.** Find the project's verification commands by role — **test, type-check, lint, build** — from its build config, task runner, and CI. Run each **before touching anything** and record whether it exists and whether it is green now. A red baseline is fine; you must know which failures you inherited. Every Phase 4 batch re-runs exactly these.

A missing signal or an untested file is **recorded risk, not a blocker** — carry it onto the finding as low confidence. Do not stall the sweep to write tests.

**Output:** scope, exclusions, and the baseline commands with their status.

## Phase 1 — Sweep with three lenses

Load the `code-smells` skill — it defines each lens's signals **and the false positives to suppress**. Run three `Explore` agents **in parallel**, one per lens:

1. **Correctness & robustness** — defects that misbehave now or will on plausible input.
2. **Bad practices & idiom** — code that works but misleads, or fights the language and stack.
3. **Duplication, dead weight & complexity** — code that should not exist, or costs too much to read.

Brief each to return per finding: `file:line`, the **quoted code**, the catalog signal, the **concrete consequence**, and every affected call site. **No style preferences, no "consider maybe", no finding it did not read the code for.**

Use the codebase's own domain vocabulary — "the order intake loop", not "the handler in file 3".

## Phase 2 — Verify every finding, then classify it

Agents over-report. **Verify yourself, not in a subagent.** Open the code for every candidate; keep it only if all hold:

- [ ] **Real** — you read the code and the smell is there.
- [ ] **Consequential** — you can name what goes wrong: an input that misbehaves, a change that will break, a reader who will be misled.
- [ ] **Not already handled** — a missing absence check is not a finding when every caller guarantees presence.
- [ ] **Not a lateral move** — if you would accept a reviewer reverting it, drop it.
- [ ] **In scope** — every interface stays intact; otherwise it is a handoff.

**Kind:** **Refactor** (same outputs, side effects, and errors for every input) or **Behaviour change** (a bug fix — state **old → new** behaviour). **Never let a behaviour change hide inside a refactor.**

**Severity:** `High` (wrong results, data loss, silent failure), `Medium` (will bite on the next change, or misleads), `Low` (dead weight, noise).

## Phase 3 — List the findings, then stop

**A list in the conversation — no Artifact, no report file.** The code is the evidence. Detail scales with severity; number every finding in one sequence so the user can answer "do 3, 7, 12".

Open with two lines: scope swept / excluded, and the baseline strip — each command with its status, plus the untested-area count. Then the counts per tier.

**`High`** — one block each:

- **Title** — the fix, imperative: "Stop swallowing the parse error in the config loader" — with **kind** on the title line
- **Files** — `path:line`
- **Before / After** — real code, two fenced blocks, each under ~12 lines, trimmed to the changed region
- **Consequence** — one sentence; old → new semantics for a behaviour change
- **Blast radius** — call sites touched, and whether the baseline covers them

**`Medium`** — one line each: number, title, kind, `path:line`, smell → consequence.

**`Low`** — a table: number, `path:line`, the fix in a few words.

Close with the **recommended batch** — which to take first, in one sentence, biased toward high severity with tight blast radius — and the **handoffs**.

Never write "cleaner" or "easier to maintain" — say what changes. Past ~10 `Low` findings, state the count instead of padding the table.

**Then stop and ask which findings to apply.** Edit nothing before an answer.

## Phase 4 — Apply in batches

Small coherent batches, lowest risk first. Re-run the baseline after each.

1. **Never mix a refactor and a behaviour change in one batch** — a red signal must be attributable.
2. **Red after a batch → revert it and diagnose.** If it was red at baseline, confirm you did not make it worse.
3. **Update every call site.** No compatibility shim unless asked — a shim is a new shallow module.
4. **One finding, one fix.** Anything new goes in the report as a follow-up.
5. **Follow the language.** Load a skill for the batch's language or stack if one is available; otherwise match the surrounding code.

Where a batch has no verification coverage, say so as you apply it and read the callers harder.

## Phase 5 — Report

- [ ] Batches applied, with the verification result after each
- [ ] **Behaviour changes**, each as old → new
- [ ] Approved findings not applied, and why
- [ ] Files changed without verification coverage
- [ ] Follow-ups, and anything handed off

Do not commit unless asked.
