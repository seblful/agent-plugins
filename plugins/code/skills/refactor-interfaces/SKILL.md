---
name: refactor-interfaces
description: "Find deepening opportunities where code keeps changing — shallow modules, wrong seams, leaking interfaces — show them as a visual HTML report, then implement the ones you pick, one commit per candidate. Use when the user asks to improve a codebase's architecture or module shape, or to make code testable through its interfaces. Not for defects inside a body (code-sweep), simplifying just-changed code (/simplify, code-simplifier), or reviewing a diff (code-reviewer, /code-review)."
allowed-tools: Read, Glob, Grep, Agent, Write, Skill, Artifact, Bash(git status *), Bash(git log *), Bash(git ls-files *)
argument-hint: "[area to focus on]"
disable-model-invocation: true
---

# Refactor Interfaces

Turn shallow modules into deep ones. **Load the `codebase-design` skill** and use its vocabulary exactly; name modules in the codebase's own domain terms. Load the language skill for each language in scope when it is installed (`python-code`, `typescript-code`) — it says how an interface is spelled there.

**Scope test: would the fix change what a caller must know?** Yes → in scope. No → it belongs to `/code-sweep`; mention it in one line, never as a candidate.

## Phase 1 — Explore

**Look where code changes.** Deepening pays off in code that keeps changing. If the user named an area, take it. Otherwise rank hot spots from the repo root, over the source directories only, keeping files that still exist:

```
git log -n 200 --name-only --format= -- <source dirs> ':(exclude)*.json' ':(exclude)*.lock' | sort | uniq -c | sort -rn | while read -r n f; do [ -e "$f" ] && echo "$n $f"; done | head -20
```

Look there first; widen only if changes are scattered.

Walk that area following friction — with general-purpose subagents when the host has them, each briefed with the `codebase-design` glossary and the deletion test pasted in (skills you loaded do not reach them); otherwise yourself:

- one concept bouncing between many small modules
- shallow modules — interface nearly as complex as the implementation
- pure functions extracted for testability while the bugs hide in how they are called
- coupled modules leaking across their seams
- code untested, or hard to test through its current interface

Keep only suspects the **deletion test** flags: deleting the module makes complexity vanish (a pass-through), or the concept's complexity already sits scattered across callers that one deeper module would absorb. A module whose deletion would push complexity back into its callers has earned its keep — drop it.

**Output:** up to five candidates, each with its files, dependency category ([DEEPENING.md](../codebase-design/DEEPENING.md)), and strength.

## Phase 2 — Report

Copy [`REPORT-TEMPLATE.html`](../codebase-design/REPORT-TEMPLATE.html) to a scratch directory (the session scratchpad, else `mktemp -d`) as `refactor-interfaces-audit.html`, title it `Interface Audit — <repo>`, and fill its slots by the rules in its header comment. **The template owns the look** — never restyle it, and load no design skill.

Each card: a title naming the deepening, a strength badge, a dependency tag (`in-process`, `local-substitutable`, `ports & adapters`, `mock`), files, a before/after diagram, a one-sentence problem, a one-sentence solution, and wins of six words or fewer in glossary terms — never "cleaner".

**The diagrams carry the weight** — if one needs a paragraph, redraw it. Candidates differ in graph shape, never styling: `module`, `deep` (what the after collapses into), `faded` (now internal), `leak` (reached past its seam). No other diagram kinds.

Publish it as an Artifact with `icon` `report` and a one-sentence description naming the repo and candidate count; if you cannot, give the local path. Then ask once, proposing no interfaces: "Which of these should I implement? (e.g. `1, 3`) — your pick is the go-ahead; I implement them without asking again."

## Phase 3 — Implement

**The pick is the approval** — start implementing right after it, with no design step to confirm. **This workflow commits** — an exception to the house default: each candidate is one reviewable, revertable commit. Implement in the main session, not subagents, without pausing between candidates; a candidate that reshapes a module another touches goes first.

**Setup.** Require a clean tree (`git status --porcelain` empty), else stop and ask. The current branch is the target. Create one worktree for the run — `git worktree add --detach <path> HEAD` with `<path>` in that scratch directory — install there if needed, and record the baseline of the project's test, type-check, lint, and build commands. Match `git log --oneline -10` for commit style.

**Per candidate, in the worktree:** design the interface as you go — the deepest one the code allows, by `codebase-design` — and update every caller, with no shim; move tests to the new interface by [replace, don't layer](../codebase-design/DEEPENING.md); re-run the baseline and fix any red the change caused; stage by path — deletions included, never `git add -A` — and commit with the card's problem and solution, the new interface, and the verification result in the body; `git cherry-pick <sha>` onto the target branch; report one line with the candidate and its hash.

**Stop and ask only when** a red the change caused will not go green (leave it uncommitted in the worktree), a cherry-pick conflicts (`git cherry-pick --abort` — never resolve by guessing), or a candidate turns out not to fit the code.

**Finish:** `git worktree remove <path>`, then report every hash in order and the final verification result. Never push, amend, or squash.
