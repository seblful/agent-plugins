---
name: vault-structural-scan
description: "Audit a whole Obsidian vault's note content for structural problems and dead weight — broken wikilinks, frontmatter errors, heading structure, misplaced files, stale MOCs, stubs, orphan notes, duplicates, empty notes — then fix what you approve. Use when the user asks to scan, audit, health-check, or tidy the vault's notes. Not for files and link syntax — attachments, markdown-to-wikilink, empty folders (vault-cleanup) — nor rewriting one note (vault-note-rewrite)."
allowed-tools: Read, Glob, Grep
---

# Structural Scan

Catch structural problems and dead weight that accumulated since the last scan and fix them while they're still recent. Every note should be self-consistent, locatable, connected, and worth keeping — either it holds knowledge worth having or it's a useful navigation point. Scope: the whole vault except `Archive/` (frozen) and template folders (placeholders, not notes). The canonical schema, link rules, heading rules, MOC detection, folder/archive model, and deterministic scripts live in [CONVENTIONS.md](../vault-conventions/CONVENTIONS.md); this skill validates notes *against* them.

This skill owns the **editorial health of note content**. Mechanical, file-level hygiene — renaming attachments to convention, converting markdown links to wikilinks, orphan/broken *attachments*, empty *folders* — belongs to `vault-cleanup`; flag such issues here rather than fixing them. **Never delete a note** — flag deletion candidates for the user.

## Phase 0 — Safety preflight

Run the preflight in [CONVENTIONS → Before changing anything](../vault-conventions/CONVENTIONS.md#before-changing-anything).

## Phase 1 — Gather the deterministic signal

Run the scripts (CONVENTIONS → Deterministic checks) and use their JSON as the worklist; apply judgment to every flag:

- `python "<vault-conventions>/scripts/validate_frontmatter.py" --vault VAULT` — schema violations.
- `python "<vault-conventions>/scripts/check_links.py" --vault VAULT --orphans` — broken wikilinks, embeds, and heading links, plus orphan notes.

**Output:** the raw worklist.

## Phase 2 — Audit

Work through every check below and record each finding with its proposed fix — or "flag" when the fix needs the user. Change nothing yet.

### Frontmatter

From `validate_frontmatter.py`, plus your own read where the script can't judge intent. Validate against the note schema in CONVENTIONS → Frontmatter (general/reviewed/daily/weekly/project/archived):

- Missing or empty required fields → fill them. Fill a missing `created` from the file's first commit or creation date (CONVENTIONS → Frontmatter); **never overwrite an existing `created`**.
- Dates not in `YYYY-MM-DD` → reformat, keeping the date.
- Link-valued fields as wikilinks (single-string for one value, YAML list for many), `tags` a lowercase kebab-case list (nested `a/b` is valid), reserved keys (`aliases`, `cssclasses`, `tags`) preserved.

### Heading structure

Enforce CONVENTIONS → Headings: no body H1 (demote stray `#` to `##` or drop it if it just repeats the filename), top-level sections start at `##`, no skipped levels.

### Broken links

From `check_links.py`:

- `[[wikilinks]]` resolving to nothing (note renamed/moved) — fix if the target is obvious from context; flag if ambiguous.
- `[[Note#Heading]]` links whose heading is gone — fix if the heading was clearly renamed; otherwise flag.
- Embeds pointing to deleted or moved attachments — flag, and point at `vault-cleanup` (`--relink`) for the mechanical repair.

### Misplaced files

Learn the vault's folder structure and what each folder holds; flag notes that clearly don't match their folder's purpose, naming the folder they belong in. Don't move them in this skill.

### Dead weight

Find notes that are neither knowledge worth having nor useful navigation points.

- **Stubs** (`#stub` or near-empty) — propose completing them, or a concrete plan plus the `#stub` tag; flag if pointless.
- **Orphans** (from `--orphans`: no incoming or outgoing links) — propose a `[[wikilink]]` from a related note or MOC; flag if the note has no place.
- **Duplicates** (same topic, different notes) — propose consolidating into the canonical note and cross-linking with one marked primary; flag the redundant copy.
- **Empty notes** (title only) — propose content, or flag.

### Stale MOCs

Treat MOCs (detected by role — CONVENTIONS → MOCs) as structural assertions about the vault:

- Entries pointing to renamed/moved/deleted notes — fix if the new target is obvious, flag if ambiguous.
- Notes that clearly belong to a MOC's domain (same folder, tag cluster, topic) but are missing from it — add them under the appropriate section.
- Empty MOC sections or duplicate entries — clean up.

Deciding what a MOC *should* cover, restructuring its sections, or creating a new MOC is editorial work for `vault-moc-create` — flag the need; don't build it here.

**Output:** the findings — fixes proposed (file → change), flags (file → reason), and deletion candidates (file → reason).

## Phase 3 — Stop and ask

Present the findings and ask: *"Apply these fixes? Reply 'Yes', or name the ones to apply."* Change nothing until the user answers.

## Phase 4 — Apply and verify

Apply exactly the approved fixes, and bump `modified` on every note whose content you changed (CONVENTIONS → Frontmatter). Re-run both scripts and fix any breakage the edits introduced.

## Report

Files fixed (with what changed); files flagged for review (with reason); broken links resolved vs. flagged; dead weight completed, connected, or consolidated; every deletion candidate (with reason).

## Judgment

- A note with a few lines of real, accurate content is not a stub or a deletion candidate — short is fine, empty is not.
- Don't restructure or delete notes that are merely different in style — only fix what's genuinely wrong.
- When merging duplicates, keep the version that's more accurate, complete, or better formatted — not necessarily the older one.
- For MOCs: only mechanical upkeep (broken entries, obviously-missing notes). If a MOC's structure or scope seems wrong, flag it — don't redesign it.

**Not a finding:**

- standalone task lists, plan notes, and log notes with no links — fine as orphans; isolated concept or reference notes are the problem;
- an existing `created` that disagrees with the file's dates — `created` is never overwritten;
- a `modified` that differs from the file's modification time (CONVENTIONS → Frontmatter);
- anything inside `Archive/` or a template folder.
