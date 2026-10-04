---
name: vault-weekly-harvest
description: "Lift lasting project knowledge — decisions, technical findings, lessons, scope changes, risks — out of unharvested weekly reports in an Obsidian vault and, on approval, merge it into the right project notes and mark each report harvested. Use when the user asks to harvest, process, or extract knowledge from weekly reports. Not for writing the weekly report (vault-weekly-report) or filing Inbox captures (vault-inbox-ingest)."
allowed-tools: Read, Glob, Grep
---

# Weekly Harvest

Read weekly reports that haven't been harvested, lift the project-relevant knowledge out of them, write it into the appropriate project notes, then mark each report processed. Do not add wikilinks back to the source reports. Do not archive or move anything except the year sweep at the end. Folder layout, frontmatter, link, language, note-creation, date, and script rules live in [CONVENTIONS.md](../vault-conventions/CONVENTIONS.md).

## Phase 0 — Safety preflight

Run the preflight in [CONVENTIONS → Before changing anything](../vault-conventions/CONVENTIONS.md#before-changing-anything).

## Phase 1 — Find unprocessed weekly reports

In the `Weekly/` folder (CONVENTIONS → Folder roles), a `W{nn}.md` report is **unprocessed** if its frontmatter lacks `harvested: true`. Read all unprocessed reports before planning anything.

## Phase 2 — Map the vault's project structure

Find where project notes live; build a list of known projects and their note paths so you know where to write.

## Phase 3 — Plan the extraction

Extract only items with lasting value — skip routine entries.

| Category | Where it goes |
|---|---|
| Decisions about how to build/implement something | Project note — Decisions or Architecture section |
| Technical findings (API quirks, tool behavior, config tricks) | Project note — Notes / Technical Details section |
| Lessons learned, patterns worth remembering | Project note — Lessons Learned section |
| Scope changes, requirement clarifications | Project note — Requirements or Scope section |
| Open questions or risks to track | Project note — Risks / Open Questions section |
| Tasks discovered mid-work | Project note — Backlog or Next Steps section |

**Output:** every item to extract, its source report, and its destination note and section; project notes to create; reports to mark harvested.

## Phase 4 — Stop and ask

Present the plan and ask: *"Write these items and mark the reports harvested? Reply 'Yes', or name what to change."* Change nothing until the user answers.

## Phase 5 — Write to project notes

1. Find the right project note; if none exists for a referenced project, create a minimal one (CONVENTIONS → Creating notes).
2. Write each item into the section it belongs to per CONVENTIONS → Merging knowledge into a note (standalone fact, no reference to the source report, source's language, no duplication, `modified` bumped).
3. Don't add wikilinks back to the weekly report.

## Phase 6 — Mark each report processed

After harvesting a report, set `harvested: true` in its frontmatter so it isn't processed again.

## Phase 7 — Year sweep

Run the year sweep on `Weekly/`: `python "<vault-conventions>/scripts/year_sweep.py" --vault VAULT --apply` (CONVENTIONS → Deterministic checks, Folder roles and the archive model). Everything it sweeps is already `harvested: true`: the sweep holds back every report still `harvested: false` and lists it under `held`. A `held` report after Phase 6 is one you skipped — name it in the report.

## Report

Every piece of knowledge extracted, the source report it came from (for your own audit trail in chat), and the destination project note; reports archived and held by the sweep.

## Judgment

- Minor entries (routine tasks, check-ins) don't need extraction.
- A finding appearing across multiple reports gets one consolidated entry.
- Prefer adding to an existing section over creating a new one.
- If content could belong to several projects, write it to the primary one and mention the overlap inline.
