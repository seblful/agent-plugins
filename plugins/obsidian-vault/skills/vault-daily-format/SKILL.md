---
name: vault-daily-format
description: "Format and normalize today's daily note in an Obsidian vault — frontmatter, atomic tasks, self-explanatory completed items, titled links — without changing its substance or language. Use when the user asks to format, tidy, or clean up today's daily note or daily report. Not for other notes (vault-note-rewrite), the weekly report (vault-weekly-report), or vault-wide checks (vault-structural-scan)."
allowed-tools: Read, Glob, Grep
---

# Daily Report Format

Clean up today's daily report so it reads well as a future reference — without changing what was actually written. Shared frontmatter, link, heading, date, and language rules live in [CONVENTIONS.md](../vault-conventions/CONVENTIONS.md); this skill adds only what's specific to daily reports.

## Hard constraints

- Do not change the meaning of anything written, and do not change the note's language (CONVENTIONS → Language and substance).
- Do not reorder items — the user's ordering is intentional.
- Do not add content that wasn't in the original.

## Phase 0 — Safety preflight

Run the preflight in [CONVENTIONS → Before changing anything](../vault-conventions/CONVENTIONS.md#before-changing-anything).

## Phase 1 — Locate today's report

Find `YYYY-MM-DD.md` matching today's date (CONVENTIONS → Today's date) in the vault's daily folder (CONVENTIONS → Folder roles). If none exists, tell the user and stop.

## Phase 2 — Plan the edits

1. **Frontmatter.** Run `validate_frontmatter.py --vault VAULT` (CONVENTIONS → Deterministic checks) and take its findings for today's note against the daily schema — link-valued fields as wikilinks, `tags` as a lowercase kebab-case list reflecting the note's actual content. Fill a missing `created` per CONVENTIONS → Frontmatter; **never overwrite an existing `created`**.
2. **Make planned tasks atomic.** Each item in the "planned" / "todo" section describes exactly one concrete action and uses Obsidian task syntax (`- [ ]` open, `- [x]` done). Split compound or vague items; keep the user's ordering.
3. **Make completed items self-explanatory.** Each item in the "done" / "completed" section must stand on its own six months from now — no assumed context, no pronouns with unclear referents.
4. **Make status unambiguous.** It must be clear which planned items were done and which came up during the day. Use the task markers consistently.
5. **Fix links and headings** per CONVENTIONS — bare URLs → titled links, vault references → wikilinks, no body H1.

**Output:** each proposed edit as before → after.

## Phase 3 — Stop and ask

Present the edits and ask: *"Apply these edits to today's note? Reply 'Yes', or name the ones to apply."* Change nothing until the user answers.

## Phase 4 — Apply

Apply the approved edits and set `modified` to today (CONVENTIONS → Frontmatter).

## Report

The report formatted (path); what changed — frontmatter fixes, tasks made atomic, completed items clarified, links/headings normalized. If no report existed for today, say so.
