---
name: vault-moc-create
description: "Build a Map of Content (MOC) — a navigational index note for a domain — or restructure an existing one, grouping the domain's notes into sections of wikilinks and wiring it into the vault. Use when the user asks to create, build, or reorganize a MOC, index, or map note, or when another routine needs a hub for a cluster of notes."
license: MIT
---

Resolve `<skill-dir>` to the absolute directory containing this SKILL.md before running any command that uses it. Use the tools available in this assistant; if a named tool or subagent feature is unavailable, complete the same work directly.

# Create a MOC

Build the navigational index for a domain: gather its notes, group them into a readable map, and wire the map into the vault so the domain is reachable. This is the canonical MOC-building routine — other routines defer here whenever they need a hub (e.g. `vault-note-create` for a cluster, `vault-inbox-ingest` when a domain has no index). What a MOC *is*, how it's detected by role, and its naming patterns live in [CONVENTIONS.md](references/CONVENTIONS.md) → MOCs, alongside the frontmatter, link, heading, and note-creation rules. This skill adds how to create and structure one.

## When to create one

- A domain has accumulated enough notes that navigating it needs an index, **or** an authoring routine is building a cluster and needs its hub.
- **Check for an existing MOC first.** Detect by role, not name alone (CONVENTIONS → MOCs). If one already covers the domain, enrich it instead of creating a duplicate.
- **Don't create premature MOCs.** A handful of notes that inline prose links already connect doesn't need one — a near-empty MOC is dead weight that `vault-structural-scan` flags. One MOC per domain.

## Steps

1. **Define the domain.** Settle what the MOC covers — its boundary. Too broad fragments into sub-MOCs; too narrow isn't worth an index.
2. **Gather members.** Search the vault for the domain's notes (CONVENTIONS → Accessing the vault). Link only notes that exist; resolve exact filenames (CONVENTIONS → Links) — never invent entries.
3. **Group into sections.** Organize members into `##` sections by subtopic, ordered foundational → advanced (or by the vault's existing MOC style). Each entry is a `[[wikilink]]`; add a short annotation only where the title isn't self-explanatory.
4. **Write the note.** Name and place it per the vault's MOC convention (CONVENTIONS → MOCs; mirror existing MOCs — `X MOC`, a `moc` tag, etc.). Frontmatter and headings per CONVENTIONS, a one-line intro stating what the map covers, then the sections.
5. **Connect it.** Link the new MOC from its parent/home MOC or index so it's reachable, and — for a cluster hub — add links from the member notes back to it (AUTHORING → Connecting the note). A MOC nothing links to is itself an orphan.
6. **Verify.** Run `check_links.py --vault VAULT` (CONVENTIONS → Deterministic checks) so every entry and back-link resolves.

## Boundary

Creating a MOC or restructuring what it covers is editorial — this skill's job. Routine upkeep of an existing MOC (fixing broken entries, adding obviously-missing notes) belongs to `vault-structural-scan`; deep authoring of the concept notes a MOC points at belongs to `vault-note-create` / `vault-note-rewrite`. This skill builds the index, not the notes inside it.

## Report

The MOC created or restructured (path), its sections and member links, and how it was connected (parent MOC, back-links from members).
