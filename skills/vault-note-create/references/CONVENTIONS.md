# Vault Conventions

Shared reference for every `obsidian-vault` routine. Each routine states its own job; the rules that *all* of them obey live here, once, so they cannot drift apart. A routine that contradicts this file is wrong — fix the routine.

## Discovering a vault's conventions

These routines run inside a live Obsidian vault, not a code repo. Before applying any default below, learn what the vault actually does:

1. **Obsidian's own settings are authoritative for what they cover — read them, don't ask or guess.** The `obsidian_config.py` script resolves the vault's `.obsidian/*.json` into the settings routines keep needing: where new attachments go (`attachmentFolderPath`), whether internal links are wikilinks or markdown and in what path format (`useMarkdownLinks`, `newLinkFormat`), and the daily-notes folder and filename format. Run `python "<skill-dir>/scripts/obsidian_config.py" --vault VAULT` for the resolved JSON (or import it from a deterministic script). It is tolerant — a missing file or key yields the documented fallback — so it works on any vault. Prefer it over interrogating the user.
2. If the vault documents its own conventions (a `CLAUDE.md`, a `README`, a `System/`-style meta folder), that documentation wins over anything here.
3. Otherwise, infer conventions from existing notes — open a few representative notes and mirror their frontmatter shape, link style, and folder layout.
4. The structures below are the **defaults** to fall back on, and the shape these routines assume when they create or reorganize content.

When a vault's real convention and a default here disagree, follow the vault and do not "correct" it toward the default.

## Today's date

Anywhere a routine needs the current date, take it from the system clock — never assume or hardcode one. Dates written into the vault are always real and ISO-formatted (see Frontmatter).

## Accessing the vault

Reach the vault through the **`obsidian` CLI** (the `obsidian-cli` skill from `kepano/obsidian-skills`), not an MCP server — Obsidian must be open. Run `obsidian help` for the authoritative, always-current command list. Essentials:

- **Read / search:** `obsidian read file="Note"`, `obsidian search query="…" limit=N`, `obsidian backlinks file="Note"`, `obsidian daily:read`.
- **Create / edit:** `obsidian create name="Note" content="…"`, `obsidian append file="Note" content="…"`, `obsidian property:set name="key" value="…" file="Note"`, `obsidian daily:append content="…"`.
- **Target a file** with `file="Name"` (wikilink-style — no path or extension) or `path="folder/note.md"` (exact from vault root). Add the `silent` flag so edits don't pop notes open; lead with `vault="Name"` to pick a specific vault.
- **Structural moves and deletes** the CLI doesn't cover — archiving notes, relocating attachments, removing a consumed capture — operate on the vault folder directly with `Read`/`Edit`/`Write` and `Bash` (`mv`, `rm`).

Prefer the CLI for content operations so the live index, daily-note configuration, and wikilink resolution stay correct; drop to direct file edits only for what the CLI can't do.

## Deterministic checks: use the scripts

Whole-vault checks that are pure logic — broken links, frontmatter schema, footnote integrity, the year sweep, the ISO week number, attachment hygiene — are done by the scripts in `scripts/`, not re-derived by reasoning each run. They are stdlib-only Python 3.12+ and emit JSON. Most **report rather than fix**: the routine reads the JSON and applies fixes through the CLI so the live index stays correct. Those that perform filesystem operations the CLI can't (`year_sweep`, and the mutating operations of `vault_clean`) **plan by default and act only on `--apply`**.

The scripts fail loudly on a missing `--vault` path rather than reporting a misleading empty ("all clean") result, and adapt to the vault's own conventions where they can:

- the daily-note filename format is read from `obsidian_config`, so notes are classified by the vault's real daily format, not a hardcoded one;
- `Archive/` and `Weekly/` are matched case-insensitively, so a vault that capitalizes them differently is still handled (and swept into its existing archive, never a forked one);
- **template folders** (the core Templates plugin's `folder` and the Templater plugin's `templates_folder`) are discovered from config and skipped when scanning note *content* — their `{{date}}` / `<% tp… %>` placeholders are not real frontmatter or links;
- frontmatter parsing accepts inline flow-style lists (`tags: [a, b]`) as well as block lists;
- `check_links` matches a wikilink by its basename, so path-qualified and relative links (`[[../Area/Note]]`) resolve; links to non-note files (`[[image.png]]`, `[[data.base]]`) and wikilinks inside code are not reported as broken.

Invoke them from the plugin root, pointing `--vault` at the vault folder:

| Script | Purpose | Invocation |
|---|---|---|
| `iso_week.py` | ISO-8601 Monday-anchored week label and the week's dates | `python "<skill-dir>/scripts/iso_week.py" [--date YYYY-MM-DD]` |
| `year_sweep.py` | Plan (or `--apply`) the Weekly→Archive year sweep | `python "<skill-dir>/scripts/year_sweep.py" --vault VAULT [--apply]` |
| `check_links.py` | Broken wikilinks, and `--orphans` | `python "<skill-dir>/scripts/check_links.py" --vault VAULT [--orphans]` |
| `validate_frontmatter.py` | Schema violations per note | `python "<skill-dir>/scripts/validate_frontmatter.py" --vault VAULT` |
| `check_footnotes.py` | Footnote reference/definition mismatches | `python "<skill-dir>/scripts/check_footnotes.py" (--file NOTE \| --vault VAULT)` |
| `obsidian_config.py` | Resolve the vault's own settings from `.obsidian/*.json` (attachment location, link format, daily notes) | `python "<skill-dir>/scripts/obsidian_config.py" --vault VAULT` |
| `vault_clean.py` | Universal file-cleaner — one command, composable operations | `python "<skill-dir>/scripts/vault_clean.py" --vault VAULT [ops] [--apply]` |

`vault_clean.py` is the single tool behind all mechanical, file-level hygiene. Select any combination of operations (they always run in a safe fixed order and emit one JSON report keyed by operation); mutating ones plan by default and act only on `--apply`:

| Operation flag | Does | Mutating? |
|---|---|---|
| `--rename` | Rename image attachments to `YYYY-MM-DD-<unix-ms>.<ext>` and rewrite links | yes (`--apply`) |
| `--dedupe` | Collapse byte-identical attachments to one canonical file, repoint embeds; redundant copies flagged (left on disk), never deleted | yes (`--apply`) |
| `--relink` | Repair broken image embeds whose stale path resolves uniquely by basename to a moved file | yes (`--apply`) |
| `--collocate` | Move attachments to the vault's configured attachment folder (read via `obsidian_config`), rewriting embeds; orphan/shared attachments flagged, not moved. **Opt-in — not in `--all`.** | yes (`--apply`) |
| `--links` | Convert internal `[md](links)` to `[[wikilinks]]` (external URLs untouched) | yes (`--apply`) |
| `--attachments` | Report orphan (unreferenced) and broken (missing-target) attachments | no (report-only) |
| `--prune` | Remove empty folders, cascading bottom-up | yes (`--apply`) |
| `--all` | Every operation above **except `--collocate`** (run in fixed order) | — |

Shared modifiers: `--include-archive` (default: `Archive/` frozen), `--ext e1,e2` (extra attachment extensions for `--rename`/`--attachments`), `--keep n1,n2` (folder names `--prune` must never remove), `--config-dir DIR` and `--layout SPEC` (for `--collocate`; layout defaults to the vault's `app.json`). Run `python "<skill-dir>/scripts/vault_clean.py" --help` for the authoritative list.

`<skill-dir>` is the installed plugin directory; if it's unset, use the plugin folder's real path. The scripts are advisory — they flag candidates, and the routine applies judgment (a flagged orphan that's a standalone log is fine; see each routine's Judgment).

## Frontmatter

Every note carries YAML frontmatter. Schema by note type:

| Note type | Required | Notes |
|---|---|---|
| General / concept | `tags`, `created`, `modified` | |
| Reviewed (verified for accuracy) | adds `reviewed` | date `YYYY-MM-DD` |
| Daily (`YYYY-MM-DD.md`) | `tags`, `created`, `modified` | optional `project`, `area` as list-of-links |
| Weekly (`Weekly/W{nn}.md`) | `year`, `week`, `tags`, `harvested` | `harvested` boolean; `Weekly/` sits beside the daily folder |
| Project | `tags`, `created`, `modified` | optional `aliases` |
| Archived (`Archive/.../YYYY/...`) | unchanged — frozen | never rewrite archived frontmatter |

Rules:

- Dates are ISO `YYYY-MM-DD` (or `YYYY-MM-DDTHH:mm:ss` for datetime properties). Never relative dates inside frontmatter.
- `created` is set once and never changed. `modified` bumps whenever content changes. `reviewed` bumps only when a human or an accuracy routine has verified the note's claims.
- Date fields must match the file's real ctime/mtime; correct them when they don't.
- `tags` is a YAML list; tag names lowercase and kebab-case (`deep-work`, not `DeepWork`).
- Link-valued properties (`project`, `area`, `related`, …) are wikilinks, not plain text — single-string form for one value (`related: "[[Note]]"`), YAML list form for multiple.
- Preserve Obsidian's reserved keys (`aliases`, `cssclasses`, `tags`) if present; `aliases` and `cssclasses` are YAML lists. Never strip them.

## Links

- Internal references are `[[wikilinks]]`, never `[markdown](links)`. Use `[[Note|display text]]` for custom text and `[[Note#Section]]` to point at a heading. Stray `[markdown](links)` that resolve to a vault file are mechanically converted to wikilinks by `vault-cleanup` — external URLs are left alone (see below).
- **Resolve the exact filename before linking — never guess or approximate.** A wikilink to a note that doesn't exist yet is fine *only* when deliberately marking a planned note; an accidental misspelling is a broken link.
- **External URLs depend on note type:**
  - *Knowledge notes* (general/concept, reviewed, project) — move bare URLs to **footnotes**. Reference them with a superscript marker at the end of the sentence (`…as the docs explain.[^1]`) and put the definitions at the bottom of the note as `[^1]: https://…`, with no heading above them. Every reference must have a matching definition and vice versa (verify with `check_footnotes.py`). Markdown links already written as `[Title](https://…)` may stay inline.
  - *Logs* (daily, weekly) — bare URLs become titled inline links `[Title](https://…)`; don't footnote logs.
- Link inline, in prose, where a concept is naturally mentioned — not in a "See Also" dump. A short `See also:` footer is acceptable only on index/leaf notes.

## Headings

- No level-1 heading (`#`) in a note body — the filename is the title and Obsidian renders it as the page heading. Top-level sections start at `##`.
- Demote any stray `#` to `##`, or drop it if it merely repeats the filename.
- Don't skip levels (`##` → `####`); promote the deeper heading.

## Body formatting

- **Math.** Inline math and any math symbol mentioned in prose use `$…$`; display equations use `$$…$$` on their own lines. Never leave bare Unicode math symbols in text.
- **Variable keys.** When an equation needs its variables explained, start the block with `where:`, then list each variable on its own line as `- $variable$ - **name** explanation starting in lower case` — the symbol in inline math, a hyphen, the bold readable name, then the explanation.
- **Code.** Preserve fenced code blocks, their language tags, and their exact contents — never reformat code so it stops running or loses syntax.
- **Images.** Fold a caption into the embed's alt text (`![[image|descriptive alt]]`) and delete the standalone caption line; infer brief, descriptive alt text when none is given.

## Attachments

An attachment is any non-markdown file a note depends on — embedded via `![[file]]` / `![](path)`, referenced by `[[file]]` / `[text](file)`, or named in an image-valued property.

- **Naming.** Image attachments are named `YYYY-MM-DD-<unix-ms>.<ext>` — the capture date, then the Unix epoch in **milliseconds**, then the extension (e.g. `2026-07-14-1784035374192.png`). The name is note-independent, chronologically sortable, and collision-free. Derive the timestamp from an `IMG-YYYYMMDDHHmmssSSS` filename when the file has one (preserving each image's original moment); otherwise from the file's modification time. Within a single folder, a clash gets a `-1`, `-2`, … suffix. Files already in this form are left untouched, so renaming is safe to re-run.
- **Empty folders.** Directories left empty after files move — e.g. the nested skeleton an attachment plugin leaves behind when files return to a flat layout — carry no content and are pruned bottom-up (a parent emptied by pruning its children goes too). Never touch `.git`, `.obsidian`, or `.trash`.
- **Orphan attachments** — a file no note references — are candidates for removal, but like orphan notes they are **flagged, never deleted unilaterally**: a file may be deliberately staged.
- **Broken embeds** — an `![[…]]` / `![](…)` whose target file is missing — are flagged for review.
- Archived attachments are frozen with the rest of the archive: leave their names and locations untouched.

Renaming to the convention, pruning empty folders, converting stray markdown links, and reporting orphan/broken attachments are the mechanical, file-level job of the **`vault-cleanup`** agent, backed by the deterministic `vault_clean.py` tool. This is distinct from `vault-structural-scan`, which owns the *editorial* health of note **content** (frontmatter, note orphans, broken **wikilinks**, dead weight, MOCs).

## MOCs and index notes

A MOC (Map of Content) is any note that functions as a domain or folder index. Detect one by **role**, not just filename: a note is a MOC if it lists/links the notes of a domain. Common naming patterns — a name ending in ` MOC` (`Programming MOC.md`), or named `MOC.md` / `Index.md`, or carrying a `moc` tag — but treat the role as decisive.

Mechanical upkeep of MOCs (fixing broken entries, adding obviously-missing notes) belongs to `vault-structural-scan`. Creating a MOC or restructuring what it covers is editorial work — the job of `vault-moc-create`; other routines defer there when they need a hub, and `vault-structural-scan` flags the need rather than doing it unprompted.

## Folder roles and the archive model

- The **daily folder** holds `YYYY-MM-DD.md` notes (Obsidian Daily Notes default). It may be the vault root or a configured folder.
- **`Weekly/`** is a flat folder of `W{nn}.md` reports, a sibling of the daily folder. Being flat, it holds one year at a time without filename collisions.
- **`Archive/`** is a sibling of the daily and weekly folders. Archive paths **mirror** live paths and partition by year: a daily note archives to `Archive/Daily/{YYYY}/`, a weekly note to `Archive/Weekly/{YYYY}/`, using the year the note belongs to.
- **Year sweep (self-healing).** Whenever a routine touches `Weekly/`, run `year_sweep.py` to archive any report whose `year` is earlier than the current year. Because the sweep runs on every touch, a missed year boundary is cleaned up on the next invocation.
- Archived content is **frozen**: move it as-is, don't rewrite links or frontmatter inside it.
- Attachments (defined under Attachments above) move with the notes they belong to: when archiving, move a note's attachments into an `attachments/` subfolder of the same mirrored archive path.

## Language and substance

- **Never change the language of a note.** If content is written in another language (e.g. Russian work logs), keep it that language — never translate or rewrite it in English. When synthesizing one note from others, write the synthesis in the source notes' language.
- **Preserve meaning.** Format, clarify, link, and tidy — never silently change what the user wrote. This is load-bearing in work logs and daily reports.
- Don't reorder items the user wrote; their ordering is intentional.

## Merging knowledge into a note

Several routines lift knowledge out of a source (a capture, a report) and write it into a destination note. When they do:

- Write each piece as a **standalone fact** — strip all source-context ("note to self", timestamps, "this week", week numbers) so it reads as if it had always belonged to the destination note.
- Write it in the **source's language** (see Language and substance).
- **Don't duplicate** what the destination already says — merge into the existing statement, or skip it.
- Place it under the section it belongs to, adding the section if it doesn't exist.

## Creating notes

When a routine creates a note:

- Follow the schema above for that note type.
- Connect it: place it under the right section of the relevant MOC, or add at least one incoming `[[wikilink]]` from a related note so it isn't orphaned.
- No decorative dividers, auto-generated TOCs, "Last updated by …" footers, or emojis (unless the user already uses them).
- One concept per file. Don't create a near-duplicate of an existing note — enrich the existing one instead.
