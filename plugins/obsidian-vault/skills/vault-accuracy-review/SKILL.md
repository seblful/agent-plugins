---
name: vault-accuracy-review
description: "Fact-check knowledge notes across an Obsidian vault against real sources — verify every claim, propose corrections with citations, then on approval correct them in place and stamp each note's reviewed date. Use when the user asks to fact-check, verify, or review the vault's notes for accuracy or outdated information. Not for logs, the Inbox, templates, or the archive; not for structure or links (vault-structural-scan) or restructuring one note (vault-note-rewrite)."
allowed-tools: Read, Glob, Grep, WebSearch, WebFetch
---

# Factual Accuracy Review

Read every note in scope and verify its content is factually correct. Propose corrections, apply the approved ones in place, then stamp each note so it isn't needlessly re-reviewed next session. Frontmatter, link, language, date, and script rules live in [CONVENTIONS.md](../vault-conventions/CONVENTIONS.md).

**Scope:** every note in the vault **except**:

- **Logs** — daily and weekly reports (CONVENTIONS → Folder roles). They're records of what happened, not knowledge to fact-check.
- **The Inbox** — raw captures waiting for `vault-inbox-ingest`; they are fact-checked when they land in a knowledge note.
- **Template folders** — from `obsidian_config.py` (`template_folders`); their placeholders are not claims.
- **`Archive/`** — frozen (CONVENTIONS → Folder roles and the archive model); never stamp or rewrite archived notes.

## Phase 0 — Safety preflight

Run the preflight in [CONVENTIONS → Before changing anything](../vault-conventions/CONVENTIONS.md#before-changing-anything).

## Phase 1 — Select the batch

If the vault is too large for one pass, take notes with no `reviewed` property first, then those whose `reviewed` date is oldest. **Output:** the list of notes in this batch.

## Phase 2 — Verify

Check *every* factual claim in each note, not a subset. Verify against real sources — prefer authoritative primary documentation, a documentation MCP such as context7 when the session has one, otherwise web search and fetch. **Never confirm a claim from memory alone** — a memory-confirmed claim is exactly the plausible-but-wrong fact this review exists to catch.

- Definitions and explanations — accurate?
- Descriptions of how something works — still correct?
- Version numbers, API signatures, configuration options — still valid?
- Code snippets — do they work with current versions?
- Comparisons and rankings — still accurate?
- Named examples, references, citations — do they point to real, correct things?
- Any other concrete assertion the note makes.

**Output:** per note — each error or outdated claim, its correction, and the source confirming it; or "verified, no changes".

**Not a finding:** a claim you could not verify either way — report it as unverified rather than "correcting" it; style or structure you'd write differently.

## Phase 3 — Stop and ask

Present the findings and ask: *"Apply these corrections and stamp the reviewed notes? Reply 'Yes', or name the notes to apply."* Change nothing until the user answers.

## Phase 4 — Apply

For each approved note:

- Correct the errors in place. When a correction references another vault note, link it as a `[[wikilink]]` (resolve the exact filename; use `[[Note#Section]]` for a specific section) per CONVENTIONS → Links; cite the source per CONVENTIONS → Links (footnotes).
- Bump `modified` to today on every note you corrected (CONVENTIONS → Frontmatter).
- Set `reviewed` to today (CONVENTIONS → Today's date, `YYYY-MM-DD`). A fully-correct note gets its `reviewed` bumped too — the verification itself has value — but not its `modified`.

## Phase 5 — Verify

Run `check_footnotes.py --vault VAULT` and `check_links.py --vault VAULT` (CONVENTIONS → Deterministic checks) and fix any footnote or wikilink breakage your corrections introduced.

## Report

Notes reviewed; notes corrected (with each correction and its source); claims left unverified; notes deferred to the next batch.
