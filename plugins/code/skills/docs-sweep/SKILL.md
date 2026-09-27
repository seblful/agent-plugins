---
name: docs-sweep
description: "Condense a project's documentation — cut what does not matter, split docs that do two jobs, merge or delete what does not earn its place, and tighten what stays. Plans every doc first, then applies only what you approve."
argument-hint: "[doc or subtree to narrow the sweep to — omit to sweep every doc in the project]"
allowed-tools: Read, Glob, Grep, Bash, Edit, Write, Agent, Skill
---

# Docs Sweep

Make a project's docs short, focused, and worth reading — **plan first, apply only on approval**.

Sweep every markdown doc a human reads. `the user's request` narrows it to a file or subtree; the process is the same.

**Scope: prose outside the code.** Docstrings and comments belong to `/code-sweep`. Leave agent-facing instructions alone. Never edit generated output — name the source that needs the change instead.

## Phase 0 — Inventory

Load the `writing-docs` skill. List the docs in scope with their line counts, excluding generated, vendored, and agent-facing files. Read a few neighbouring docs for the project's conventions: heading style, voice, where docs live and what they are called.

For each doc write one line: **its reader and the question it answers.** A doc you cannot write that line for is a split, a merge, or a delete.

**Output:** the inventory — doc, lines, reader, question.

## Phase 1 — Give each doc a verdict

Read every doc in full yourself. Past ~15 docs, fan out to `Explore` agents **by group of docs, never by concern** — duplication across docs is invisible to an agent that sees one file.

| Verdict | Means |
| --- | --- |
| **Keep** | already earns its lines |
| **Tighten** | cut and reshape — same doc, same question |
| **Split** | two readers or two questions — name each new doc and its question |
| **Merge** | fold into a named doc that answers the same question |
| **Delete** | answers nothing a reader asks, or only restates the code |

Split and Merge include tightening. **Name the cuts by section and by `writing-docs` category** — "reduce verbosity" is not a plan.

**Output:** a verdict and a cut list per doc.

## Phase 2 — Present the plan, then stop

One numbered item per doc that changes, entry point first, then by lines saved, so the user can answer "do 1, 3, 4":

- **Title** — imperative, names the doc: "Split `setup.md` into install and configuration"
- **Verdict**, and **lines now → expected**
- **Cut** — what goes, a few words each
- **Moves** — for a split or merge: new files, what lands where, links to update
- **Corrections** — any kept line whose meaning must change to match the repo, as old → new. Never bury one inside a rewrite.
- **Flagged** — kept lines you could not verify

Close with the Keep docs on one line and the total lines now → expected.

**Then stop and ask which items to apply.** Edit nothing before an answer.

## Phase 3 — Apply, one doc at a time

1. **Move, never lose.** Every fact a reader needs survives somewhere. A cut removes noise, never the only copy of something true.
2. **Fix every link** into and out of what was split, merged, moved, or deleted.
3. **Match the project's form**, not your preference — style-only churn hides the real change in the diff.
4. **Apply only what was approved.** New ideas go in the report as follow-ups.
5. **Never run a doc's commands to check them** — they can install, delete, or deploy. Read the repo instead. Never edit code from here.

## Phase 4 — Report

- [ ] Docs changed — verdict and lines before → after each, plus the total
- [ ] Files created, merged, or deleted, and links updated
- [ ] Corrections, as old → new
- [ ] Approved items not applied, and why
- [ ] Flagged lines still unverified
- [ ] Follow-ups, and anything handed to `/code-sweep`

Do not commit unless asked.
