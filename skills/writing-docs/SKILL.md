---
name: writing-docs
description: "How to make documentation short, focused, and worth reading — what to cut, when to split, merge, or delete a doc, how to shape what stays, and what never to cut. Use when writing, editing, or condensing any README, guide, or other markdown doc in a codebase, when /docs-sweep runs, or when the user asks whether a doc is too long or any good. Not for docstrings and in-code comments (code-smells) or agent-facing instructions like CLAUDE.md and AGENTS.md."
license: MIT
---

Resolve `<skill-dir>` to the absolute directory containing this SKILL.md before running any command that uses it. Use the tools available in this assistant; if a named tool or subagent feature is unavailable, complete the same work directly.

# Writing Docs

**A doc earns every line or loses it.** Readers skim, stop early, and trust the first answer they find. Every extra sentence delays that answer and is one more thing that can go out of date.

Scope: markdown a human reads — whatever docs the project has. No doc is mandatory and none has a required shape. Out of scope: docstrings and comments (`code-smells`), agent-facing instructions, generated output (change its source).

## Laws

1. **One reader, one question.** Name who arrives and what they came for before writing a line. A doc serving two readers or answering two questions is two docs.
2. **Every sentence must change what the reader does.** If deleting it changes nothing for them, delete it.
3. **Say what the code cannot.** Why it is this way, when to use it, what to avoid. Never mirror what the repo already states — signatures, defaults, file trees, flag lists. The copy drifts; the original does not.
4. **One home per fact.** Explain a thing once; link to it everywhere else.
5. **What survives must be true.** Check each command, path, and name you keep against the repo. A line you cannot confirm is flagged, never polished.

## Cut

| Cut | Looks like | Instead |
| --- | --- | --- |
| Filler | "This document describes…", "It is important to note", "simply", "just" | Delete the sentence |
| Restated code | parameter tables, file trees, option lists copied from the source | Link to the source; keep only the why |
| Duplication | the same explanation in two docs | One home, one link |
| The obvious | explaining tools every reader of this doc already uses | Write for the reader named in law 1 |
| Narrative | history, the design journey, "how we got here" inside a how-to | One line of rationale, or move it to a design note |
| Ceremony | a table of contents on a short doc, badges, an "Overview" repeating the title | Delete |
| Dead sections | stubs, "coming soon", TODOs nobody will do | Delete — version control has it |
| Hedging | "may", "might", "could possibly" where the answer is known | State it |
| Speculation | plans and ideas written as if they were docs | Delete, or a labelled roadmap |

## Split, merge, delete

| Do | When |
| --- | --- |
| **Split** | two readers or two questions share one doc; a section most readers skip stands in the way of the rest |
| **Merge** | two docs answer the same question; a doc too thin to stand alone |
| **Delete** | it answers a question nobody asks, or only restates the code |

**Each doc a split produces must pass the laws on its own** — its own reader, its own opening question, links both ways. Every split, merge, and move updates every link to what moved; a dead link costs the reader more than the bloat did.

## Shape what stays

- **Answer first.** The command or conclusion goes above background, badges, and context.
- **Reader's order.** What they do first comes first — not what is architecturally primary.
- **Structure over prose.** Steps as numbered lists, comparisons as tables, choices as one bold rule. Prose only for reasoning.
- **Example over explanation.** One runnable example beats a paragraph describing it.
- **Short sentences, concrete nouns.** One name per concept — the project's own.
- **Headings name the task or question** — never "Details", "Misc", "Notes".
- **Prerequisites at the step that needs them**, not in a preamble.

## Do not cut

A cut that loses what a reader needs is worse than the bloat it removed.

- **Explicitness on a dangerous or irreversible step** — the full command, the exact warning.
- **Exact commands and error messages** — readers copy and search for them.
- **Reference depth** — a doc that is looked up, not read through, is long by nature. Length alone is never the problem.
- **The entry point's first screen** — it persuades a stranger to try the project.
- **A command repeated at the entry point** so the reader need not go looking. Repeating an *explanation* is duplication.
- **Examples that look alike but cover different cases.**
- **The project's conventions** — heading style, voice, layout, file names. Match them; your preference is churn.
- **Changelogs and history files** — repetitive by format.

## Writing a new doc

1. **Name the reader and their question** → the opening sentence.
2. **Write the shortest answer that works**, in the reader's order.
3. **Verify** every command, path, and name against the repo.
4. **Cut.** Re-read as the reader; most first drafts lose a third.
