---
name: refactor-interfaces
description: "Scan a codebase for deepening opportunities — shallow modules, wrong seams, leaking interfaces — present them as a visual HTML report, then design and implement the ones you pick, one commit per candidate."
allowed-tools: Read, Glob, Grep, Bash, Agent, Edit, Write, Skill, Artifact
---

# Refactor Interfaces

Turn shallow modules into deep ones. **Load the `codebase-design` skill** and use its vocabulary exactly; name modules in the codebase's own domain terms.

**Scope test: would the fix change what a caller must know?** Yes → in scope. No → it belongs to `/code-sweep`; mention it in one line, never as a candidate.

## Phase 1 — Explore

Walk the codebase with `Explore` agents, following friction:

- one concept bouncing between many small modules
- shallow modules — interface nearly as complex as the implementation
- pure functions extracted for testability while the bugs hide in how they are called
- coupled modules leaking across their seams
- code untested, or hard to test through its current interface

Keep only suspects that pass the **deletion test**.

**Output:** up to five candidates, each with its files, dependency category ([DEEPENING.md](../codebase-design/DEEPENING.md)), and strength.

## Phase 2 — Report

Copy [`REPORT-TEMPLATE.html`](../codebase-design/REPORT-TEMPLATE.html) to the session scratchpad as `refactor-interfaces-audit.html`, title it `Interface Audit — <repo>`, and fill its slots by the rules in its header comment. **The template owns the look** — never restyle it, and load no design skill.

Each card: a title naming the deepening, a strength badge, a dependency tag (`in-process`, `local-substitutable`, `ports & adapters`, `mock`), files, a before/after diagram, a one-sentence problem, a one-sentence solution, and wins of six words or fewer in glossary terms — never "cleaner".

**The diagrams carry the weight** — if one needs a paragraph, redraw it. Candidates differ in graph shape, never styling: `module`, `deep` (what the after collapses into), `faded` (now internal), `leak` (reached past its seam). No other diagram kinds.

Publish it as an Artifact with `icon` `report` and a one-sentence description naming the repo and candidate count; if you cannot, give the local path. Then ask once, proposing no interfaces yet: "Which of these should I implement? (e.g. `1, 3`) — your pick is the go-ahead; I design and implement them without asking again."

## Phase 3 — Design

**The pick is the approval** — never ask the user to confirm a design. For each chosen candidate, in implementation order (one that reshapes a module another touches goes first), post one block:

- **Interface** — entry points, parameters, invariants, error modes
- **Behind the seam** — what stops being a caller's problem
- **Callers** — what changes at each call site
- **Tests** — which move to the new interface, which are deleted

One design per candidate — the strongest, not a menu.

**Output:** the designs, posted as a record the user can interrupt; start Phase 4 in the same turn.

## Phase 4 — Implement

**This workflow commits** — an exception to the house default: each candidate is one reviewable, revertable commit. Implement in the main session, not subagents, through the list without pausing between candidates.

**Setup.** Require a clean tree (`git status --porcelain` empty), else stop and ask. The current branch is the target. Create one worktree for the run — `git worktree add --detach <path> HEAD` with `<path>` in the scratchpad — install there if needed, and record the baseline of the project's test, type-check, lint, and build commands. Match `git log --oneline -10` for commit style.

**Per candidate, in the worktree:** implement the design and update every caller, with no shim; move tests to the new interface by [replace, don't layer](../codebase-design/DEEPENING.md); re-run the baseline and fix any red the change caused; stage by path — deletions included, never `git add -A` — and commit with the card's problem, solution, and verification result in the body; `git cherry-pick <sha>` onto the target branch; report one line with the candidate and its hash.

**Stop and ask only when** a red the change caused will not go green (leave it uncommitted in the worktree), a cherry-pick conflicts (`git cherry-pick --abort` — never resolve by guessing), or a design does not fit the code.

**Finish:** `git worktree remove <path>`, then report every hash in order and the final verification result. Never push, amend, or squash.
