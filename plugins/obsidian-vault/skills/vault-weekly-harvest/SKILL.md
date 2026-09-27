---
name: vault-weekly-harvest
description: "Extract project-relevant knowledge from unprocessed weekly reports and merge it into the right project notes — no back-links, no archiving, just clean knowledge transfer."
allowed-tools: Bash, Read, Edit, Write, Glob, Grep
---

# Weekly Harvest

Read weekly reports that haven't been harvested, lift the project-relevant knowledge out of them, write it into the appropriate project notes, then mark each report processed. Do not add wikilinks back to the source reports. Do not archive or move anything except the year sweep at the end. Folder layout, frontmatter, link, language, note-creation, date, and script rules live in [CONVENTIONS.md](../../CONVENTIONS.md).

## Steps

### 1. Find unprocessed weekly reports

In the `Weekly/` folder (CONVENTIONS → Folder roles), a `W{nn}.md` report is **unprocessed** if its frontmatter lacks `harvested: true`. Read all unprocessed reports before writing anything.

### 2. Map the vault's project structure

Scan to find where project notes live; build a list of known projects and their note paths so you know where to write.

### 3. For each report, identify extractable knowledge

Extract only items with lasting value — skip routine entries.

| Category | Where it goes |
|---|---|
| Decisions about how to build/implement something | Project note — Decisions or Architecture section |
| Technical findings (API quirks, tool behavior, config tricks) | Project note — Notes / Technical Details section |
| Lessons learned, patterns worth remembering | Project note — Lessons Learned section |
| Scope changes, requirement clarifications | Project note — Requirements or Scope section |
| Open questions or risks to track | Project note — Risks / Open Questions section |
| Tasks discovered mid-work | Project note — Backlog or Next Steps section |

### 4. Write to project notes

1. Find the right project note; if none exists for a referenced project, create a minimal one (CONVENTIONS → Creating notes).
2. Write each item into the section it belongs to per CONVENTIONS → Merging knowledge into a note (standalone fact, no reference to the source report, source's language, no duplication).
3. Don't add wikilinks back to the weekly report.

### 5. Mark each report processed

After harvesting a report, set `harvested: true` in its frontmatter so it isn't processed again.

### 6. Year sweep

After step 5, run the year sweep on `Weekly/`: `python "$CLAUDE_PLUGIN_ROOT/scripts/year_sweep.py" --vault VAULT --apply` (CONVENTIONS → Deterministic checks, Folder roles and the archive model). Everything swept is already `harvested: true`.

### 7. Report

List every piece of knowledge extracted, the source report it came from (for your own audit trail in chat), and the destination project note.

## Judgment

- Minor entries (routine tasks, check-ins) don't need extraction.
- A finding appearing across multiple reports gets one consolidated entry.
- Prefer adding to an existing section over creating a new one.
- If content could belong to several projects, write it to the primary one and mention the overlap inline.
