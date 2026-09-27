---
name: vault-structural-scan
description: "Scan the whole vault for structural problems and dead weight — broken wikilinks, misplaced files, frontmatter errors, stale MOCs, plus stubs, orphans, duplicates, and empty notes — and fix them in-place."
license: MIT
---

Resolve `<skill-dir>` to the absolute directory containing this SKILL.md before running any command that uses it. Use the tools available in this assistant; if a named tool or subagent feature is unavailable, complete the same work directly.

# Structural Scan

Catch structural problems and dead weight that accumulated since the last scan and fix them while they're still recent. Every note should be self-consistent, locatable, connected, and worth keeping — either it holds knowledge worth having or it's a useful navigation point. Fix what you safely can in-place; **never delete a note** — flag deletion candidates for the user. Scope: whole vault. The canonical schema, link rules, heading rules, MOC detection, folder/archive model, and deterministic scripts live in [CONVENTIONS.md](references/CONVENTIONS.md); this command validates notes *against* them.

This command owns the **editorial health of note content**. Mechanical, file-level hygiene — renaming attachments to convention, converting markdown links to wikilinks, orphan/broken *attachments*, empty *folders* — belongs to the `vault-cleanup` agent; flag such issues here rather than fixing them.

## Gather the deterministic signal first

Run the scripts (CONVENTIONS → Deterministic checks) and use their JSON as the worklist; apply judgment to every flag before acting:

- `python "<skill-dir>/scripts/validate_frontmatter.py" --vault VAULT` — schema violations.
- `python "<skill-dir>/scripts/check_links.py" --vault VAULT --orphans` — broken wikilinks and orphan notes.

The scripts find candidates mechanically; deciding what to do with each is the work below.

## What to check

### Frontmatter

From `validate_frontmatter.py`, plus your own read where the script can't judge intent. Validate against the note schema in CONVENTIONS → Frontmatter (general/reviewed/daily/weekly/project/archived). Then:

- Fill missing or empty required fields.
- Ensure dates are `YYYY-MM-DD` and match the file's real ctime/mtime; correct mismatches.
- Ensure link-valued fields are wikilinks (single-string for one value, YAML list for many), `tags` is a lowercase kebab-case list, and reserved keys (`aliases`, `cssclasses`, `tags`) are preserved.
- Never rewrite frontmatter inside archived notes — they're frozen.

### Heading structure

Enforce CONVENTIONS → Headings: no body H1 (demote stray `#` to `##` or drop it if it just repeats the filename), top-level sections start at `##`, no skipped levels.

### Broken links

From `check_links.py`:

- `[[wikilinks]]` resolving to nothing (note renamed/moved) — fix if the target is obvious from context; flag if ambiguous.
- Heading links `[[Note#Heading]]` whose target heading is gone — flag for review.
- Image/file embeds pointing to deleted or moved attachments — flag for review.

### Misplaced files

- Understand the vault's folder structure and what each folder is meant to hold.
- Identify notes that clearly don't match their folder's purpose.
- Flag misplaced files for the user rather than moving them unilaterally.

### Dead weight

Find notes that are neither knowledge worth having nor useful navigation points. Resolve what you can in-place; flag the rest — **never delete anything**.

- **Stubs** (`#stub` or near-empty) — complete now, or leave a concrete plan and tag `#stub`; flag if pointless.
- **Orphans** (from `check_links.py --orphans`, no incoming or outgoing links) — connect via a `[[wikilink]]` from a related note or MOC; flag if it has no place. Standalone task/plan/log notes are fine as orphans (see Judgment).
- **Duplicates** (same topic, different notes) — consolidate into the canonical note, cross-link with one marked primary, flag the redundant copy.
- **Empty notes** (title only) — populate or flag.

### Stale MOCs

Treat MOCs (detected by role — CONVENTIONS → MOCs) as structural assertions about the vault, and check them like links:

- Entries pointing to renamed/moved/deleted notes — fix if the new target is obvious, flag if ambiguous.
- Notes that clearly belong to a MOC's domain (same folder, tag cluster, topic) but are missing from it — add them under the appropriate section.
- Empty MOC sections or duplicate entries — clean up.

Out of scope here: deciding what a MOC *should* cover, restructuring its sections, or creating new MOCs — that's editorial work for `vault-moc-create`, not structural validation. Flag the need; don't build it here.

## Report

- Files fixed (with what changed).
- Files flagged for human review (with reason).
- Broken links resolved vs. flagged.
- Dead weight: stubs completed/planned, orphans connected, duplicates consolidated/cross-linked, empty notes populated — and everything flagged as a deletion candidate (with reason).

## Judgment

- A note with a few lines of real, accurate content is not a stub or a deletion candidate — short is fine, empty is not.
- If a broken link's target is obvious from context, fix it; if ambiguous, flag rather than guess.
- Don't restructure or delete notes that are merely different in style — only fix what's genuinely wrong.
- When merging duplicates, keep the version that's more accurate, complete, or better formatted — not necessarily the older one.
- Standalone task lists, plan notes, and log notes are fine as orphans; isolated concept or reference notes are a problem.
- For MOCs: only mechanical upkeep (broken entries, obviously-missing notes). If a MOC's structure or scope seems wrong, flag it — don't redesign it.
