---
name: vault-weekly-report
description: "Create a weekly report note by synthesizing this week's daily reports — grouped by project, stored in a Weekly/ folder next to the daily reports, then archive the daily notes."
allowed-tools: Bash, Read, Edit, Write, Glob, Grep
---

# Weekly Report Creation

Read this week's daily reports, produce a weekly report grouped by project, store it in `Weekly/`, then archive the daily notes. Folder layout, the archive model, frontmatter, link, language, date, and script rules live in [CONVENTIONS.md](../../CONVENTIONS.md).

## Steps

### 1. Locate this week's daily reports

Get the week's bounds and label deterministically: `python "$CLAUDE_PLUGIN_ROOT/scripts/iso_week.py"` (CONVENTIONS → Deterministic checks) returns the ISO week label and every date Monday→today. Find the daily notes for those dates (CONVENTIONS → Folder roles). If fewer than two exist, tell the user and ask whether to proceed.

### 2. Read everything first

Read all daily reports before writing — build a full picture of which projects appear and what was done per project. Write the report in the **same language as the dailies** (CONVENTIONS → Language and substance); never translate.

### 3. Year sweep

Before writing, run the year sweep on `Weekly/`: `python "$CLAUDE_PLUGIN_ROOT/scripts/year_sweep.py" --vault VAULT --apply` (CONVENTIONS → Folder roles and the archive model).

### 4. Create the weekly report note

**Path:** `Weekly/W{nn}.md` (a sibling of the daily folder, created if needed) — use the `label` from `iso_week.py` (e.g. `W26.md`).

**Structure:**

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

**Grouping rules:**

- Use `year` and `week` from `iso_week.py` (`iso_year` and `iso_week`) for the frontmatter.
- One `##` section per project that appeared; the heading itself is the `[[wikilink]]` to the project note.
- Entries belonging to no specific project go under `## Cross-project / General`.
- Within each project use the four callouts above; omit any with no entries.
- Consolidate work that recurs across days into one entry; skip trivial/routine items.
- Accomplished — one bullet per outcome, not per task. Group anything serving the same goal; daily granularity belongs in the dailies.
- `harvested: false` marks the report eligible for `vault-weekly-harvest`, which flips it to `true` once processed.
- Under `## Sources`, link each daily note the report was built from by filename (`[[YYYY-MM-DD]]`).

### 5. Archive the daily notes and their attachments

Per CONVENTIONS → archive model: after the report is saved, for each included daily note, move the note to `Archive/Daily/{YYYY}/` and its attachments to `Archive/Daily/{YYYY}/attachments/`, creating folders as needed. Don't rewrite links inside archived notes — archived content is frozen.

Report which notes and attachments were moved and where.

## Judgment

- Prefer bullet points over prose.
- Do not invent or infer content beyond what the daily reports state.
- If a project note doesn't exist, still create the section using the name from the daily note.
