---
name: refactor-interfaces
description: "Scan a codebase for deepening opportunities — shallow modules, wrong seams, leaking interfaces — present them as a visual HTML report, then design and implement the ones you pick, one commit per candidate."
allowed-tools: Read, Glob, Grep, Bash, Agent, Edit, Write, Skill, Artifact
---

# Refactor Interfaces

Find architectural friction and propose **deepening opportunities** — refactors that turn shallow modules into deep ones, for testability and navigability.

## Scope: interfaces and seams, not implementations

> **Would the fix change what a caller must know?**
> **Yes** → it belongs here. **No** → hand it to `/code-sweep`.

Splitting a god object, deleting a wrapper callers go through, moving a seam, and reshaping a signature are in scope. A swallowed error, deep nesting, dead code, or a bad local name leaves the caller's view unchanged — close the report with one line pointing at `/code-sweep`; no cards, no fixes.

The outputs differ on purpose: `/code-sweep` lists defects evidenced by before/after **code** and ends in batched fixes; this workflow produces a **diagram-led HTML report** and ends in designed refactors, **one commit per candidate**.

**Load the `codebase-design` skill** and use its terms exactly — **module**, **interface**, **depth**, **seam**, **adapter**, **leverage**, **locality** — never "component", "service", "API", or "boundary". Name modules in the codebase's own domain terms — "the order intake module", not "the FooBarHandler".

## Phase 1 — Explore

Walk the codebase with `Explore` agents. Follow friction, not a checklist:

- Where does one concept take bouncing between many small modules?
- Which modules are **shallow** — interface nearly as complex as the implementation?
- Where were pure functions extracted for testability while the bugs hide in how they are called?
- Where do coupled modules leak across their seams?
- What is untested, or hard to test through its current interface?

Apply the **deletion test** to every suspect: does deleting it concentrate complexity, or just move it? "Concentrates" is the signal.

**Output:** up to five candidates, each with its files, dependency category, and strength.

## Phase 2 — Publish the report

**The page design is decided.** Copy [`REPORT-TEMPLATE.html`](../codebase-design/REPORT-TEMPLATE.html) from the sibling `codebase-design` skill to the session scratchpad as `refactor-interfaces-audit.html` and fill its slots:

> **Fill slots, never restyle.** Don't touch `<style>`, add a class, a font, a colour, or a section. Add a candidate by duplicating the `<article class="candidate">` block whole.
> **One diagram form.** Every diagram is a mermaid `flowchart LR` in a before/after pair, carrying the template's `classDef` block unchanged — that block makes the legend true.
> **Fixed identity.** Title `Interface Audit — <repo>`, `icon` `report`, filename `refactor-interfaces-audit.html` — so a re-review lands on the same URL.

**Publish it as an Artifact** — the filled file as it is, with `icon` `report` and a one-sentence description naming the repo and candidate count. The template *is* the predefined design: load no design skill and write no page of your own. **The template owns the look.** Only if the assistant cannot publish an Artifact, give the user the local HTML file path.

### What fills the slots

Header: repo, date, candidate count. **Rank `Strong`, then `Worth exploring`, then `Speculative`**, numbered in that order. **Five candidates maximum** — a sixth means the cut is not sharp enough.

Each card:

- **Title** — names the deepening: "Collapse the order intake pipeline"
- **Strength badge**, plus a dependency tag: `in-process`, `local-substitutable`, `ports & adapters`, `mock`
- **Files** — the modules involved
- **Before / After diagram** — the centrepiece
- **Problem** — one sentence
- **Solution** — one sentence
- **Wins** — bullets of six words or fewer, in glossary terms: "locality: bugs land in one module", "delete 4 shallow wrappers". Never "cleaner".

**The diagrams carry the weight.** If one needs a paragraph, redraw it. Candidates differ in **graph shape, never styling** — four node classes are the whole vocabulary:

| Class | Means |
| --- | --- |
| `:::module` | an ordinary module |
| `:::deep` | the deep module the "after" collapses into |
| `:::faded` | now internal — no longer a caller's problem |
| `:::leak` | a module callers reach past its seam to touch |

A dashed link (`-.->`) is a seam; leakage is a red link set with `linkStyle`. Keep the template's `theme: neutral` frontmatter — Mermaid takes its palette from its own theme. **No other diagram kinds** — sequence diagrams, hand-drawn SVG, layer stacks — each would make this report a different document from the last.

**Do not propose interfaces yet.** Ask once: "Which of these should I implement? (e.g. `1, 3`)"

## Phase 3 — Design every chosen candidate, approve once

**One message, one approval.** For every chosen candidate, in implementation order, give one block:

- **Interface** — the new entry points, parameters, invariants, and error modes
- **Behind the seam** — what moves inside and stops being a caller's problem
- **Callers** — what changes at each call site
- **Tests** — which move to the new interface, which are deleted

Propose one design per candidate — the strongest you see, not a menu of alternatives.

Order candidates so each builds on the last: one that reshapes a module another candidate touches goes first.

**Output:** the designs the user approved, in order, with any edits they asked for. **Implement nothing until the user approves.** A design the user rejects drops out; the rest proceed.

## Phase 4 — Implement and commit every approved candidate

**This command commits** — a deliberate exception to "do not commit unless asked": each candidate is one reviewable, revertable unit, so it lands as one commit the moment it is done.

**You implement, not subagents.** Subagents stop at Phase 1. Work in the main session through the approved list in order, without asking between candidates — the next starts only after the last is committed and picked onto the target branch.

Before the first candidate:

- **Clean tree.** `git status --porcelain` must print nothing. Otherwise stop and ask — a candidate's commit holds only its own change.
- **Target branch.** The branch checked out now; `git branch --show-current` names it. Every candidate lands there.
- **One worktree for the run.** `git worktree add --detach <path> HEAD`, with `<path>` outside the repo (the session scratchpad) so it never shows as untracked. It is a fresh checkout: run the project's install step there once if the baseline needs one. Work only inside it.
- **Baseline.** Find the verification commands by role — test, type-check, lint, build — and run them in the worktree. Record each as green or red.
- **Commit style.** Read `git log --oneline -10` and match its subject convention.

Per candidate, in the worktree:

1. **Implement the approved design.** Update every caller; no compatibility shim unless asked.
2. **Replace, don't layer.** Tests move to the new interface; delete the shallow-module tests they replace.
3. **Verify.** Re-run the baseline. Red where it was green → fix it. **Never commit a red the change caused** — if it will not go green, stop the run and report, leaving the change uncommitted in the worktree for the user to inspect.
4. **Commit.** Stage the candidate's files by path — deletions included, never `git add -A` — and commit: the subject names the deepening in the log's style; the body carries the card's problem and solution and the verification result.
5. **Cherry-pick onto the target branch.** In the main checkout, `git cherry-pick <sha>` with the hash from `git -C <path> rev-parse HEAD`. On a conflict, `git cherry-pick --abort` and stop the run and report — never resolve it by guessing.
6. **Say it landed** — one line: candidate, commit hash on the target branch — and go straight to the next.

**Stop the run only for** a red the change caused, a cherry-pick conflict, or a design that turns out not to fit the code — then ask. Anything else, keep going.

After the last candidate: `git worktree remove <path>`, then report every commit hash in order and the final verification result.

Each candidate is exactly one commit on the target branch. Never push, and never amend or squash an earlier candidate's commit.
