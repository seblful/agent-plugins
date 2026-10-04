---
name: vault-weekly-report
description: "Write this week's report in an Obsidian vault from its daily notes — catch up any unreported earlier week, draft the report grouped by project, then on approval save it to Weekly/, archive the dailies, and run the year sweep. Use when the user asks for a weekly report, weekly summary, or week review. Not for formatting one daily note (vault-daily-format) or moving weekly knowledge into project notes (vault-weekly-harvest)."
allowed-tools: Read, Glob, Grep
---

# Weekly Report Creation

Read this week's daily reports — and any earlier week still unreported — draft a weekly report grouped by project, and on approval store it in `Weekly/` and archive the daily notes. Folder layout, the archive model, frontmatter, link, language, date, and script rules live in [CONVENTIONS.md](../vault-conventions/CONVENTIONS.md).

## Phase 0 — Safety preflight

Run the preflight in [CONVENTIONS → Before changing anything](../vault-conventions/CONVENTIONS.md#before-changing-anything).

## Phase 1 — Locate this week's daily reports, and any week left behind

Get the week's bounds and label deterministically: `python "<vault-conventions>/scripts/iso_week.py" --vault VAULT --daily-dir DAILY` (CONVENTIONS → Deterministic checks), where `DAILY` is the vault-relative daily folder (CONVENTIONS → Folder roles; omit `--daily-dir` to use the vault's configured daily-notes folder). It returns the ISO week label, every date Monday→today, and `unreported` — earlier weeks whose daily notes are still in the daily folder.

**Never skip a week silently.** Daily notes leave the daily folder only when their week's report archives them, so every `unreported` entry is a week that was missed. List each one to the user, oldest first, before the current week, and offer:

- `report_exists: false` → build that week's report: run Phases 2–5 for it, with its `label`, `iso_year`, and `iso_week`, from exactly its `notes`.
- `report_exists: true` → the report was written but its dailies were never archived. Don't rebuild it; check the report's `## Sources`, and offer Phase 5's archive step for those notes.

Then find the current week's daily notes for the returned `dates`. If fewer than two exist, tell the user and ask whether to proceed.

## Phase 2 — Read everything

Read all daily reports before drafting — build a full picture of which projects appear and what was done per project. Write the report in the **same language as the dailies** (CONVENTIONS → Language and substance); never translate.

## Phase 3 — Draft and plan

**Draft** the report at `Weekly/W{nn}.md` (a sibling of the daily folder) using the `label` from `iso_week.py` (e.g. `W26.md`):

```markdown
---
year: {YYYY}
week: {nn}
tags:
  - weekly-report
harvested: false
---

## [[Project Name]]

> [!success] Accomplished
> - …

> [!note] Decisions
> - …

> [!warning] Problems
> - …

> [!todo] Carry-over
> - …

---

## [[Another Project]]

…

---

## Cross-project / General

### Notes and observations

- …

## Sources

- [[YYYY-MM-DD]]
- [[YYYY-MM-DD]]
```

Grouping rules:

- Use `year` and `week` from `iso_week.py` (`iso_year` and `iso_week`) for the frontmatter.
- One `##` section per project that appeared; the heading itself is the `[[wikilink]]` to the project note.
- Entries belonging to no specific project go under `## Cross-project / General`.
- Within each project use the four callouts above; omit any with no entries.
- Consolidate work that recurs across days into one entry; skip trivial/routine items.
- Accomplished — one bullet per outcome, not per task. Group anything serving the same goal; daily granularity belongs in the dailies.
- `harvested: false` marks the report eligible for `vault-weekly-harvest`, which flips it to `true` once processed.
- Under `## Sources`, link each daily note the report was built from by filename (`[[YYYY-MM-DD]]`).

**Plan the moves:** each daily note and its attachments with their archive destinations (CONVENTIONS → Folder roles and the archive model — `Archive/Daily/{YYYY}/` and `Archive/Daily/{YYYY}/attachments/`), and the year-sweep plan from `python "<vault-conventions>/scripts/year_sweep.py" --vault VAULT` (no `--apply`), including any `held` reports.

**Output:** the drafted report and the move plan.

## Phase 4 — Stop and ask

Present the draft and the plan and ask: *"Save this report and archive these notes? Reply 'Yes', or say what to change."* Change nothing until the user answers.

## Phase 5 — Apply

1. **Year sweep:** `python "<vault-conventions>/scripts/year_sweep.py" --vault VAULT --apply`. Reports it lists as `held` are still `harvested: false` — they stay in `Weekly/` until `vault-weekly-harvest` processes them.
2. **Save the report** to `Weekly/W{nn}.md`, creating `Weekly/` if needed.
3. **Archive the daily notes and their attachments** with `obsidian move` (CONVENTIONS → Accessing the vault), creating the archive folders first. Don't edit anything inside archived notes — archived content is frozen.

## Report

The report saved (path); which notes and attachments moved, and where; any reports the sweep archived or held.

## Judgment

- Prefer bullet points over prose.
- Do not invent or infer content beyond what the daily reports state.
- If a project note doesn't exist, still create the section using the name from the daily note.
