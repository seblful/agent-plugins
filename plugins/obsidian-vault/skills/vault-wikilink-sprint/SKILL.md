---
name: vault-wikilink-sprint
description: "Propose, then on approval add, inline prose wikilinks between conceptually related notes across an Obsidian vault, starting with the most isolated hub notes — prose links only. Use when the user asks to connect, interlink, or add wikilinks across the vault, or to fix isolated notes. Not for See Also sections or MOC curation (vault-moc-create, vault-structural-scan), broken links (vault-structural-scan), or markdown-to-wikilink conversion (vault-cleanup)."
allowed-tools: Read, Glob, Grep
---

# Wikilink Connectivity Sprint

Systematically build **inline prose wikilinks** between notes that are conceptually related but currently isolated. Success is whether navigating from a concept to its prerequisites, applications, and related ideas becomes natural — not the raw count of links added. Scope: the whole vault except `Archive/` — archived notes are frozen, so never add links inside them (CONVENTIONS → Folder roles and the archive model) — and template folders. Link mechanics and the deterministic scripts live in [CONVENTIONS.md](../vault-conventions/CONVENTIONS.md).

**Out of scope:** curating MOCs, index notes, or "See Also" sections. MOC freshness (broken entries, missing notes) belongs to `vault-structural-scan`. This skill only touches links inside a note's prose.

## Principles for good linking

- Links appear **inline in prose** where the concept is naturally mentioned.
- Only link when the connection is genuinely useful for navigation or understanding — never add links the prose doesn't motivate.
- **Bidirectionality matters:** if A links to B, check whether B should link back.
- Prefer the specific note (`[[Gradient Descent]]`) over a broad folder-level note when the specific concept is what's meant.

## Phase 0 — Safety preflight

Run the preflight in [CONVENTIONS → Before changing anything](../vault-conventions/CONVENTIONS.md#before-changing-anything).

## Phase 1 — Prioritize

Start from the under-connected notes the data points at: `python "<vault-conventions>/scripts/check_links.py" --vault VAULT --orphans` (CONVENTIONS → Deterministic checks) lists notes with no incoming or outgoing links — the most isolated candidates. Then scan for **hub notes** — conceptually central notes that many others depend on, but that currently have few links. These unlock the most connectivity per edit. Good candidates: core concept notes a domain builds on; tool/framework notes many others reference; notes frequently named in prose but not yet linked. MOCs are not hubs for this purpose — they're indexes, and their entries are listings, not prose mentions.

**Output:** the ordered hub list, most isolated first.

## Phase 2 — Propose links

For each hub, in order:

1. Read the hub note; identify every mentioned concept that has its own note in the vault.
2. Resolve exact filenames (CONVENTIONS → Links — never guess, never link a note that doesn't exist).
3. Record each link: the note, the phrase that becomes the link, and the target.
4. Check bidirectionality — record a natural link back where it's missing.

**Output:** the proposed links, grouped by note.

## Phase 3 — Stop and ask

Present the proposals and ask: *"Add these links? Reply 'Yes', or name the notes to link."* Change nothing until the user answers.

## Phase 4 — Apply and verify

Add the approved links inline, changing no other wording, and bump `modified` on each note you edited (CONVENTIONS → Frontmatter). Then re-run `check_links.py --vault VAULT` and fix any broken link you introduced.

## Report

Hubs processed; links added per note; back-links added; proposals the user declined.

**Not a finding:** an orphan that is a standalone task list, plan, or log note — it needs no links; a concept mentioned only in a heading, a code block, or a quotation — don't link there.
