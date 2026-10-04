# obsidian-vault

Maintenance and authoring routines for [Obsidian](https://obsidian.md) vaults — formatting, knowledge harvesting into projects, weekly reports by project, structural scanning, accuracy review, wikilink connectivity, file cleanup, inbox ingestion, and authoring or rewriting source-of-truth reference notes.

Every routine defers to [`CONVENTIONS.md`](skills/vault-conventions/CONVENTIONS.md) for the shared schema, link rules, heading rules, MOC detection, the folder/archive model, and the deterministic [`scripts/`](skills/vault-conventions/scripts). The two authoring routines additionally share [`AUTHORING.md`](skills/vault-conventions/AUTHORING.md) for audience, voice, technical standards, diagrams, document shape, and the plan-then-write workflow. The routines validate and edit notes *against* those conventions — and discover the vault's own conventions first when they differ from the defaults.

Deterministic, repeatable checks — broken links, frontmatter schema, footnote integrity, the year sweep, the ISO week number, attachment hygiene — are handled by small stdlib-only Python scripts in [`scripts/`](skills/vault-conventions/scripts) rather than re-reasoned each run. The routines read each script's JSON and apply judgment and fixes through the CLI.

## Prerequisites

These routines run inside a **live Obsidian vault**, not a code repo, and reach it through the **`obsidian` CLI** — not an MCP server. Before using this plugin:

1. **Obsidian must be open** on the target vault while a routine runs (the CLI talks to the running app so the live index, daily-note config, and wikilink resolution stay correct).
2. **The `obsidian` CLI must be installed.** It ships as the `obsidian-cli` skill from [`kepano/obsidian-skills`](https://github.com/kepano/obsidian-skills). Run `obsidian help` to confirm it's available and to see the authoritative command list.
3. **Python 3.12+** must be on `PATH` for the deterministic [`scripts/`](skills/vault-conventions/scripts). They use the standard library only — nothing to `pip install`.

Moves, renames, and deletes go through `obsidian move`, `obsidian rename`, and `obsidian delete` (trash, never `permanent`), so Obsidian updates links when the vault's *Automatically update internal links* setting is on — never `mv` or `rm`. Every routine that changes files first runs a safety preflight (a clean git tree or a checkpoint commit; otherwise a backup), presents its plan, and waits for approval — see [CONVENTIONS → Before changing anything](skills/vault-conventions/CONVENTIONS.md#before-changing-anything).

## Routines

Every routine is a skill that can be requested by name. Claude Code also exposes plugin skills as namespaced slash commands. `vault-cleanup` additionally has a Claude agent entry point for delegation.

### Skills

- **vault-daily-format** — Normalize today's daily report: frontmatter, atomic tasks, self-explanatory completed items, titled links. Never changes substance or language.
- **vault-inbox-ingest** — Empty the Inbox: merge each raw capture into the right note (or create one), relocate its images, wire into a MOC, trash the consumed capture — all after you approve the plan.
- **vault-weekly-harvest** — Extract project-relevant knowledge from unprocessed weekly reports into project notes, marking each report harvested.
- **vault-weekly-report** — Synthesize this week's daily reports grouped by project, store in `Weekly/`, and archive the dailies.
- **vault-note-create** — Author a new source-of-truth reference note on a subject: plan scope and table of contents first, then on approval write a deep, modern engineering-handbook note.
- **vault-note-rewrite** — Refactor and expand informal or fragmented notes into a source-of-truth reference note: audit and plan first, then on approval rewrite.
- **vault-moc-create** — Build a Map of Content (MOC) for a domain — or restructure one — grouping its notes into sections of wikilinks. The canonical MOC routine the authoring and inbox skills defer to.

### Whole-vault audits

- **vault-accuracy-review** — Verify every claim in every knowledge note (excluding logs, the Inbox, templates, and the archive), correct what you approve, and stamp each with a `reviewed` date.
- **vault-structural-scan** — Fix broken wikilinks, misplaced files, frontmatter errors, stale MOCs, plus dead weight (stubs, orphans, duplicates, empty notes).
- **vault-wikilink-sprint** — Add inline prose wikilinks between conceptually related notes, starting at the most isolated hub notes.
- **vault-cleanup** — Mechanical file-level hygiene: rename image attachments to the naming convention and rewrite their links, convert stray markdown links to wikilinks, report orphan/broken attachments, and prune empty folders. The file-level counterpart to `vault-structural-scan`; it plans before every apply and flags deletions rather than making them.

### Agent

- **vault-cleanup** — Claude subagent entry point to the `vault-cleanup` skill.

## Scripts

The deterministic helpers in [`scripts/`](skills/vault-conventions/scripts) (stdlib-only Python, JSON output) back the routines' repeatable checks:

- **`iso_week.py`** — ISO-8601 Monday-anchored week label and the week's dates; with `--vault`, the earlier weeks whose daily notes were never reported.
- **`year_sweep.py`** — plan or `--apply` the Weekly→Archive year sweep by ISO year; reports still `harvested: false` are held back.
- **`check_links.py`** — broken wikilinks, embeds, and heading links, and `--orphans`.
- **`validate_frontmatter.py`** — schema violations per note.
- **`check_footnotes.py`** — footnote reference/definition mismatches.
- **`obsidian_config.py`** — central reader for the vault's own `.obsidian/*.json` settings (attachment location, link format, daily-notes folder/format). Routines read it instead of asking the user; importable, or run it to dump the resolved settings as JSON.
- **`vault_clean.py`** — the universal file-cleaner behind `vault-cleanup`; its operations and safeguards are documented in [the vault-cleanup skill](skills/vault-cleanup/SKILL.md).

They **report** (the routine decides and fixes); the mutating ones — `year_sweep` and `vault_clean` — plan by default and act on `--apply`. Invoke each by its path inside the installed `vault-conventions` skill directory, with `--vault` pointing at the vault, e.g. `python "<vault-conventions>/scripts/check_links.py" --vault /path/to/vault --orphans`.

## Conventions

See [`CONVENTIONS.md`](skills/vault-conventions/CONVENTIONS.md) for the full specification. In brief: per-type YAML frontmatter with ISO dates, `[[wikilinks]]` for internal references, no body H1, one concept per file, a daily/weekly/archive folder model with a self-healing year sweep, and a hard rule never to change a note's language or meaning.
