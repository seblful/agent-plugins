---
name: vault-daily-format
description: "Format and normalize today's daily report — fix frontmatter, make tasks atomic, make completed items self-explanatory, and convert bare URLs to titled links. Never changes substance or language."
allowed-tools: Bash, Read, Edit, Write, Glob, Grep
---

# Daily Report Format

Clean up today's daily report so it reads well as a future reference — without changing what was actually written. Shared frontmatter, link, heading, date, and language rules live in [CONVENTIONS.md](../../CONVENTIONS.md); this skill adds only what's specific to daily reports.

## Steps

1. **Locate today's report.** Find `YYYY-MM-DD.md` matching today's date (CONVENTIONS → Today's date) in the vault's daily folder (CONVENTIONS → Folder roles). If none exists, tell the user and stop.

2. **Fix frontmatter.** Run `validate_frontmatter.py --vault VAULT` (CONVENTIONS → Deterministic checks) and apply its findings for today's note against the daily schema — link-valued fields as wikilinks, `tags` as a lowercase kebab-case list reflecting the note's actual content, dates matching the file's real ctime/mtime.

3. **Make planned tasks atomic.** Each item in the "planned" / "todo" section describes exactly one concrete action and uses Obsidian task syntax (`- [ ]` open, `- [x]` done). Split compound or vague items; keep the user's ordering.

4. **Make completed items self-explanatory.** Each item in the "done" / "completed" section must stand on its own six months from now — no assumed context, no pronouns with unclear referents.

5. **Make status unambiguous.** It must be clear which planned items were done and which came up during the day. Use the task markers consistently.

6. **Fix links and headings** per CONVENTIONS — bare URLs → titled links, vault references → wikilinks, no body H1.

## Hard constraints

- Do not change the meaning of anything written, and do not change the note's language (CONVENTIONS → Language and substance).
- Do not reorder items — the user's ordering is intentional.
- Do not add content that wasn't in the original.

## Report

The report formatted (path); what changed — frontmatter fixes, tasks made atomic, completed items clarified, links/headings normalized. If no report existed for today, say so.
