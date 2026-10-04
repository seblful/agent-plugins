---
name: vault-inbox-ingest
description: "Empty an Obsidian vault's Inbox — plan where each raw capture goes, then on approval merge it into the right note (or create one), move its images into the destination's attachments, wire it into a MOC, and trash the consumed capture. Use when the user asks to process, triage, file, or empty the inbox or new captures. Not for drafts the user is still writing, deep authoring of one note (vault-note-create / vault-note-rewrite), or weekly reports (vault-weekly-harvest)."
allowed-tools: Read, Glob, Grep
---

# Inbox Ingest

The inbox holds raw captures dropped in without a home. File each into the place it belongs and leave the inbox empty: read it, decide where its knowledge goes, get approval, merge it there, move its images, wire the result into a MOC, then trash the consumed capture. Frontmatter, link, MOC-detection, note-creation, and date rules live in [CONVENTIONS.md](../vault-conventions/CONVENTIONS.md). Filing is triage, not deep authoring: when a capture becomes or substantially grows a knowledge note, hold it to the [AUTHORING.md](../vault-conventions/AUTHORING.md) standard, and hand the heavy jobs off to `vault-note-create` / `vault-note-rewrite` rather than doing them inline.

**Process only the inbox.** Don't touch folders holding work the user is actively authoring (drafts, texts) — those are owned documents, not material to dissolve. If unsure whether a folder is an inbox or a drafts area, ask.

## Phase 0 — Safety preflight

Run the preflight in [CONVENTIONS → Before changing anything](../vault-conventions/CONVENTIONS.md#before-changing-anything).

## Phase 1 — Read

1. **Locate the inbox** (`Inbox/`, or this vault's clear equivalent) and list it. If empty, say so and stop.
2. **Read every capture first** — content, frontmatter, embedded images — so you can spot duplicates and group related ones.

## Phase 2 — Plan

**Decide each destination.** Map the vault's folders and search the topic before assuming no home exists.

- A note already covers it → **enrich that note in place**. If the capture calls for restructuring or substantially expanding that note, that's a rewrite — hand off to `vault-note-rewrite` instead of forcing it inline.
- Genuinely new concept with lasting value → **create a standalone note** in the right folder (CONVENTIONS → Creating notes), written to the AUTHORING standard for a knowledge note (audience, voice, shape, connection). If it deserves the full researched treatment, plan a solid note now and flag it for `vault-note-create` to deepen — don't half-write a reference note during triage.
- Duplicate → merge into the single destination; don't create twice.
- No lasting value → propose discarding it, with the reason.
- Can't place it confidently → leave it in the inbox and say why.

**Output:** a plan per capture — destination (enrich vs. new) and path; images to move, with their destination paths and any collision renames; MOC entry or incoming link to add, or a new MOC to build with `vault-moc-create`; proposed discards; captures left in place.

## Phase 3 — Stop and ask

Present the plan and ask: *"Apply this filing plan? Reply 'Yes', or name the captures to file."* Change nothing until the user answers.

## Phase 4 — Apply

For each approved capture, in order:

1. **Merge cleanly.** Write the knowledge into the destination per CONVENTIONS → Merging knowledge into a note (which bumps `modified`), in the authoritative, timeless voice of a reference note (AUTHORING → Voice). Use `[[wikilinks]]` for inline references (CONVENTIONS → Links).
2. **Move referenced images** into the destination's attachments folder (mirror the vault's convention) with `obsidian move path="Inbox/<image>" to="<destination folder>/"` (CONVENTIONS → Accessing the vault). **Never move onto an existing file** — on a name collision, pass a new name in the `to=` path. If the vault's `alwaysUpdateLinks` is off, update the embed yourself.
3. **Wire into a MOC.** New notes go under the right section of the relevant MOC (detected by role — CONVENTIONS → MOCs); if none fits but the domain clearly needs an index, build the one the approved plan named with `vault-moc-create`; otherwise add at least one incoming `[[wikilink]]` so the note isn't orphaned. Prefer bidirectional connection — link the new note out to related notes and add a link back in from the most relevant one (AUTHORING → Connecting the note). Enriched notes need this only if they were missing from their MOC.
4. **Trash the consumed capture** with `obsidian delete path="Inbox/<capture>.md"` — only after its content is merged, its images moved, and it's wired in. **Never pass `permanent`, and never delete an unplaced capture.**

## Phase 5 — Verify

Run `check_links.py --vault VAULT` (CONVENTIONS → Deterministic checks) and fix any broken wikilink or embed your merges and moves introduced.

## Report

Per capture: destination (enriched vs. new note) and path; images moved, with any renames; MOC entries added; anything discarded or left for review (with reason); final inbox state.

## Judgment

- Enrich an existing note over creating a near-duplicate — proliferation is the failure mode to avoid.
- A capture worth keeping but too thin to stand alone belongs *inside* a broader note, not as its own stub.
- When a capture could fit several notes, place it in the primary one and cross-link the rest inline.
- An unfiled capture is recoverable; a wrongly-merged-then-deleted one is not. When in doubt, leave it and ask.
