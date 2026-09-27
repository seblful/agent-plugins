---
name: refactor-interfaces
description: "Scan a codebase for deepening opportunities — shallow modules, wrong seams, leaking interfaces — present them as a visual HTML report, then design and implement the ones you pick, one commit per candidate."
license: MIT
---

Resolve `<skill-dir>` to the absolute directory containing this SKILL.md before running any command that uses it. Use the tools available in this assistant; if a named tool or subagent feature is unavailable, complete the same work directly.

Read [the codebase-design reference](references/codebase-design/SKILL.md) when applying this workflow.

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

**Output:** up to six candidates, each with its files, dependency category, and strength.

## Phase 2 — Publish the report

**The page design is decided.** Copy `<skill-dir>/references/codebase-design/REPORT-TEMPLATE.html` to the session scratchpad as `refactor-interfaces-audit.html` and fill its slots:

> **Fill slots, never restyle.** Don't touch `<style>`, add a class, a font, a colour, or a section. Add a candidate by duplicating the `<article class="candidate">` block whole.
> **One diagram form.** Every diagram is a mermaid `flowchart LR` in a before/after pair, carrying the template's `classDef` block unchanged — that block makes the legend true.
> **Fixed identity.** Title `Interface Audit — <repo>`, `favicon` 🧱, `icon` `report`, filename `refactor-interfaces-audit.html` — so a re-review lands on the same URL.

If the assistant can publish an Artifact, load `artifact-design` for its publishing contract and publish the HTML with the scratchpad path, `favicon`, `icon`, and a one-sentence description naming the repo and candidate count. Otherwise give the user the local HTML file path. **The template owns the look.**

### What fills the slots

Header: repo, date, candidate count. **Rank `Strong`, then `Worth exploring`, then `Speculative`**, numbered in that order. **Six candidates maximum** — a seventh means the cut is not sharp enough.

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

**Do not propose interfaces yet.** Ask: "Which of these would you like to explore?"

## Phase 3 — Design the chosen candidate

Walk the design with the user — constraints, dependencies, the shape of the deepened module, what sits behind the seam, which tests survive. Interview, sketch, or propose directly, whichever fits.

**To explore alternative interfaces**, use the design-it-twice pattern in the `codebase-design` skill.

**Output:** an agreed design — the new interface, what moves behind the seam, which callers and tests change. **Implement nothing until the user agrees.**

## Phase 4 — Implement and commit, one candidate at a time

**This command commits** — a deliberate exception to "do not commit unless asked": each candidate is one reviewable, revertable unit, so it lands as one commit the moment it is done.

Before the first candidate:

- **Clean tree.** `git status --porcelain` must print nothing. Otherwise stop and ask — a candidate's commit holds only its own change.
- **Baseline.** Find the verification commands by role — test, type-check, lint, build — and run them. Record each as green or red.
- **Commit style.** Read `git log --oneline -10` and match its subject convention.

Per candidate:

1. **Implement the agreed design.** Update every caller; no compatibility shim unless asked.
2. **Replace, don't layer.** Tests move to the new interface; delete the shallow-module tests they replace.
3. **Verify.** Re-run the baseline. Red where it was green → fix it. **Never commit a red the change caused** — if it will not go green, stop and report, uncommitted.
4. **Commit.** Stage the candidate's files by path — deletions included, never `git add -A` — and commit: the subject names the deepening in the log's style; the body carries the card's problem and solution and the verification result.
5. **Report and ask.** Give the commit hash, then ask which candidate is next — back to Phase 3 — or stop.

Never push, and never amend or squash an earlier candidate's commit.
