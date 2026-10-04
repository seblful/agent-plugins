---
name: code-sweep
description: "Sweep existing code for latent bugs, bad practices, and bad implementations, list verified findings ranked by severity, then apply only the fixes you approve. Use when the user asks to sweep, audit, or hunt for defects across a codebase or subtree. Not for one diff or PR (code-reviewer, /code-review), simplifying just-changed code (/simplify, code-simplifier), interface redesign (refactor-interfaces), or reviewing pending changes for security (/security-review)."
argument-hint: "[subtree to narrow the sweep to — omit to sweep the whole codebase]"
allowed-tools: Read, Glob, Grep, Agent, Skill, Bash(git status *), Bash(git log *), Bash(git ls-files *), Bash(git diff *)
---

# Code Sweep

Find what is wrong with code that already works, then fix it — **audit first, apply only on approval**.

Sweep the whole codebase. `the user's request` narrows it to a subtree; the process is the same.

## Scope: implementations, not interfaces

> **Would the fix change what a caller must know?**
> **No** → it belongs here. **Yes** → hand it to `/refactor-interfaces`.

Renaming a local, flattening nesting, fixing a swallowed error, and deleting dead code are in scope. Splitting a god object, removing a wrapper callers go through, and reshaping a signature move a seam — not here.

**Security hazards stay here, in their own tier** — injection, unsafe deserialization, hardcoded secret, unvalidated input. They live in existing code, which a diff review never re-reads, so report each in full (Phase 3).

When the sweep turns up one of these, **list it as a handoff and do not fix it**:

| Finding | Belongs to |
| --- | --- |
| Performance problem — work repeated per item, quadratic hot path, unbounded growth | the `diagnosing-bugs` skill (measure first) |
| Shallow module, wrong seam, interface redesign | `/refactor-interfaces` |
| Bloated, sprawling, or outdated **markdown** | `/docs-sweep` |

## Phase 0 — Bound the sweep and take a baseline

**Bound it.** List the source directories and the exclusions — vendored and generated code, migrations, lockfiles, fixtures, dependency and build output. Read the project's own conventions first — its assistant instructions, context docs, and decision records, where they exist: **a convention mistaken for a smell is the most expensive false positive.**

**Load the catalogs.** The `code-smells` skill, plus the language skill for each language in scope when it is installed — `python-code`, `typescript-code`. A language skill adds that language's traps and its own *Not a finding* list.

**Take a baseline.** Find the project's verification commands by role — **test, type-check, lint, build** — from its build config, task runner, and CI. Run each **before touching anything** and record whether it exists and whether it is green now. A red baseline is fine; you must know which failures you inherited. Every Phase 4 batch re-runs exactly these.

A missing signal or an untested file is **recorded risk, not a blocker** — carry it onto the finding as low confidence. Do not stall the sweep to write tests.

**Output:** scope, exclusions, and the baseline commands with their status.

## Phase 1 — Sweep with three lenses

Run three general-purpose subagents **in parallel**, one per `code-smells` lens:

1. **Correctness & robustness** — defects that misbehave now or will on plausible input, security hazards included.
2. **Bad practices & idiom** — code that works but misleads, or fights the language and stack.
3. **Duplication, dead weight & complexity** — code that should not exist, or costs too much to read.

**A subagent sees only its brief** — skills you loaded do not reach it. Put in each brief:

- the scope and exclusions from Phase 0, and the project conventions that bear on the lens;
- the lens's **Signals and its Not a finding list**, pasted verbatim from `code-smells`;
- the matching traps and *Not a finding* entries, pasted verbatim from each loaded language skill;
- for the correctness lens, the security hazards listed under Scope above.

Ask each to return per finding: `file:line`, the **quoted code**, the catalog signal, the **concrete consequence**, and every affected call site. **No style preferences, no "consider maybe", no finding it did not read the code for.**

**No subagents in this host** → run the three lenses yourself, one after another, against the same briefs.

Use the codebase's own domain vocabulary — "the order intake loop", not "the handler in file 3".

## Phase 2 — Verify every finding, then classify it

Agents over-report. **Verify yourself, not in a subagent.** Open the code for every candidate and keep it only if it passes the four tests in `code-smells` — **real, consequential, not already handled, not a lateral move** — and stays **in scope**: every interface intact, otherwise it is a handoff.

**Kind:** **Refactor** (same outputs, side effects, and errors for every input) or **Behaviour change** (a bug fix — state **old → new** behaviour). **Never let a behaviour change hide inside a refactor.**

**Severity:** `Security` (exploitable — injection, unsafe deserialization, a leaked secret, unvalidated input crossing a trust boundary), `High` (wrong results, data loss, silent failure), `Medium` (will bite on the next change, or misleads), `Low` (dead weight, noise).

## Phase 3 — List the findings, then stop

**A list in the conversation — no Artifact, no report file.** The code is the evidence. Detail scales with severity; number every finding in one sequence so the user can answer "do 3, 7, 12".

Open with two lines: scope swept / excluded, and the baseline strip — each command with its status, plus the untested-area count. Then the counts per tier.

**`Security`, then `High`** — one block each:

- **Title** — the fix, imperative: "Stop swallowing the parse error in the config loader" — with **kind** on the title line
- **Files** — `path:line`
- **Before / After** — real code, two fenced blocks, each under ~12 lines, trimmed to the changed region
- **Consequence** — one sentence; old → new semantics for a behaviour change. For `Security`: who can exploit it, with what input, and what they get
- **Blast radius** — call sites touched, and whether the baseline covers them

A `Security` fix applies like any other approved finding, always in a batch of its own. Where the fix needs a decision you cannot make — an auth model, a secret to rotate — say so instead of a Before / After.

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
5. **Follow the language** — the language skill loaded in Phase 0, or the surrounding code when there is none.

Where a batch has no verification coverage, say so as you apply it and read the callers harder.

## Phase 5 — Report

- [ ] Batches applied, with the verification result after each
- [ ] **Behaviour changes**, each as old → new
- [ ] Approved findings not applied, and why
- [ ] Files changed without verification coverage
- [ ] Follow-ups, and anything handed off

Do not commit unless asked.
