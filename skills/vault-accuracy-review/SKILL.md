---
name: vault-accuracy-review
description: "Review all notes outside the work-log folder for factual accuracy — verify every claim in every note, correct errors in-place, and stamp each reviewed note with a reviewed date property."
license: MIT
---

Resolve `<skill-dir>` to the absolute directory containing this SKILL.md before running any command that uses it. Use the tools available in this assistant; if a named tool or subagent feature is unavailable, complete the same work directly.

# Factual Accuracy Review

Read every note in scope and verify its content is factually correct. Fix errors in-place, then stamp each note so it isn't needlessly re-reviewed next session. Frontmatter, link, language, date, and script rules live in [CONVENTIONS.md](references/CONVENTIONS.md).

**Scope:** every note in the vault **except** Logs and the archive:

- **Logs** — daily and weekly reports (CONVENTIONS → Folder roles). They're records of what happened, not knowledge to fact-check.
- **`Archive/`** — archived notes are frozen (CONVENTIONS → archive model); never read-stamp or rewrite them.

Everything else is in scope.

## What to verify

Check *every* factual claim in each note, not a subset. Verify against real sources — prefer authoritative primary documentation, a documentation MCP such as context7 when the session has one, otherwise web search and fetch. Never confirm a claim from memory alone.

- Definitions and explanations — accurate?
- Descriptions of how something works — still correct?
- Version numbers, API signatures, configuration options — still valid?
- Code snippets — do they work with current versions?
- Comparisons and rankings — still accurate?
- Named examples, references, citations — do they point to real, correct things?
- Any other concrete assertion the note makes.

## After verifying each note

- Correct any errors or outdated information in-place. When a correction references another vault note, link it as a `[[wikilink]]` (resolve the exact filename; use `[[Note#Section]]` for a specific section) per CONVENTIONS → Links.
- Add or update a `reviewed` frontmatter property set to today's date (CONVENTIONS → Today's date, `YYYY-MM-DD`). Even a fully-correct note gets its `reviewed` bumped — the verification itself has value.

## Prioritization

If the vault is too large for one pass, do notes with no `reviewed` property first, then those whose `reviewed` date is oldest.

## Final pass

Run `check_footnotes.py --vault VAULT` and `check_links.py --vault VAULT` (CONVENTIONS → Deterministic checks) and fix any footnote or wikilink breakage your corrections introduced.

## Report

Total notes reviewed; notes corrected.
