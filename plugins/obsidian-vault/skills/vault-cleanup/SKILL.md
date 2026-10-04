---
name: vault-cleanup
description: "File-level hygiene for an Obsidian vault via vault_clean.py and the obsidian CLI: rename image attachments to YYYY-MM-DD-<unix-ms>, convert markdown links to wikilinks, dedupe, relink, or collocate attachments, report orphan and broken attachments, prune empty folders. Use when the user asks to clean, tidy, or normalize vault files, attachments, link syntax, or folders. Not for note content (frontmatter, broken wikilinks, orphan notes, dead weight, MOCs) — that is vault-structural-scan."
allowed-tools: Read, Glob, Grep
---

# Vault Cleanup

Keep a vault's **files and link syntax** in line with its conventions. Do what the user asks in this domain — choose the operations and parameters that satisfy the request, not a fixed pipeline — and never invent work they didn't ask for. Attachment naming (→ Attachments), link rules (→ Links), the folder/archive model, and the rule never to change a note's meaning or language live in [CONVENTIONS.md](../vault-conventions/CONVENTIONS.md); read it first, and **discover the vault's own conventions before applying any default** (→ Discovering a vault's conventions).

**Scope:** attachment names, link syntax, dead attachments, empty folders, and one-off file or link fixes the user names. The editorial health of note *content* — frontmatter, note orphans, broken *wikilinks*, dead weight, MOCs — belongs to `vault-structural-scan` and the authoring skills: point the user there, and flag such issues you notice in passing.

## Toolkit

- **`vault_clean.py`** — the one parameterized cleaner: `python "<vault-conventions>/scripts/vault_clean.py" --vault VAULT [ops] [modifiers]` (CONVENTIONS → Deterministic checks explains `<vault-conventions>`). Run it with `--help` for the authoritative flag list.
- **`obsidian_config.py`** — the vault's attachment location, link format, and daily-notes settings; read them here instead of asking the user. `--collocate` and `--links` already use it.
- **The `obsidian` CLI** — `read`, `search`, `backlinks` to understand what a request refers to; `move` / `rename` / `delete` for any one-off file operation `vault_clean.py` doesn't cover (CONVENTIONS → Accessing the vault). **Never `mv` or `rm`** — a filesystem move breaks every inbound link.

### `vault_clean.py` operations

Select any combination. They always run in one fixed order — rename → dedupe → relink → collocate → links → attachments → prune — so names settle before later operations read them, and they emit one JSON report keyed by operation. **Mutating operations plan by default and change nothing until `--apply`.**

| Operation flag | Does | Mutating? |
|---|---|---|
| `--rename` | Rename image attachments to `YYYY-MM-DD-<unix-ms>.<ext>` and rewrite links. Skips and reports any file with a reference it cannot resolve — renaming it would break the link it can't see. | yes (`--apply`) |
| `--dedupe` | Collapse byte-identical attachments to one canonical file and repoint embeds; redundant copies are flagged and left on disk, never deleted | yes (`--apply`) |
| `--relink` | Repair broken image embeds whose stale path resolves uniquely by basename to a moved file | yes (`--apply`) |
| `--collocate` | Move attachments to the vault's configured attachment folder (via `obsidian_config`), rewriting embeds; orphan and shared attachments are flagged, not moved. **Opt-in — not in `--all`.** | yes (`--apply`) |
| `--links` | Convert internal `[md](links)` to `[[wikilinks]]`; external URLs and links inside code are untouched. **Refuses when the vault is set to markdown links** (`useMarkdownLinks`) unless `--force` — converting would fight the vault's own convention. | yes (`--apply`) |
| `--attachments` | Report orphan (unreferenced) and broken (missing-target) attachments | no (report-only) |
| `--prune` | Remove empty folders, cascading bottom-up. Never removes a dot-folder or the Inbox, Weekly, Archive, daily, attachment, or template folders, even when empty. | yes (`--apply`) |
| `--all` | Every operation above **except `--collocate`** | — |

Shared modifiers: `--include-archive` (default: `Archive/` frozen), `--ext e1,e2` (extra attachment extensions for `--rename`/`--attachments`), `--keep n1,n2` (further folder names `--prune` must never remove), `--config-dir DIR` and `--layout SPEC` (for `--collocate`; layout defaults to the vault's `app.json`). Files that are not valid UTF-8 are skipped and reported; rewritten files keep their line endings.

## Workflow

### Phase 0 — Safety preflight

Run the preflight in [CONVENTIONS → Before changing anything](../vault-conventions/CONVENTIONS.md#before-changing-anything). Skip it only when the request is report-only (`--attachments` alone).

### Phase 1 — Map the request

Translate the request into operations and modifiers — no more. "Tidy the attachments" → `--rename --attachments`; "convert my markdown links" → `--links`; "clean everything" → `--all`; "include the archive" → add `--include-archive`. If the target vault or the scope is unclear, ask. **Output:** the command line you will run.

### Phase 2 — Plan

Run the selected operations without `--apply` and read the JSON. Plan any one-off fix the user named (rename one file, move an attachment into a note's `attachments/`, fix a single link) as the exact `obsidian` command. **Output:** counts per operation; every file to be renamed, moved, or removed; links to be rewritten; everything skipped or refused, with its reason.

### Phase 3 — Stop and ask

Present the plan and ask: *"Apply these changes? Reply 'Yes', or name the operations to apply."* Change nothing until the user answers. If the plan looks wrong in kind or scale — hundreds of unresolved links, renames touching files you expected to be frozen, folders you'd want to keep — say so and recommend against applying.

### Phase 4 — Apply

Re-run with `--apply` for exactly the approved operations, then run the approved one-off `obsidian` commands. **Output:** the apply report.

### Phase 5 — Judge the report-only findings

For each orphan or broken attachment, apply the rules below and give its path with a recommendation.

### Phase 6 — Report

What ran, what changed (counts), what was flagged, and what was skipped or refused.

## Rules

1. **Do only what the user asked** — don't run `--all` when they asked to rename attachments.
2. **Never delete a file on your own initiative** — flag orphan attachments with their paths and let the user decide. If they ask you to delete one, use `obsidian delete` (trash), never `permanent`.
3. **Never touch the archive** unless the user explicitly asks (`--include-archive`).
4. **Change file names and link syntax only — never a note's meaning or language** (CONVENTIONS → Language and substance).
5. Fix an unresolved or broken link only when the intended target is unambiguous; otherwise flag it, don't guess.

**Not a finding:**

- an orphan attachment that is deliberately staged, or used only by a canvas or base — check those before recommending removal;
- `--links` refusing on a vault set to markdown links — that is the vault's convention working; add `--force` only if the user asks to switch the vault to wikilinks;
- files `--rename` skipped for unresolved references, and files skipped as not valid UTF-8 — report them; never force the rename or re-encode the file.
