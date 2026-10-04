# AGENTS.md

A coding assistant workflow repository for Claude Code, Codex, and OpenCode. Plugins live in `plugins/<name>/`, each with its own `.claude-plugin/plugin.json`; the Claude marketplace manifest is `.claude-plugin/marketplace.json`. Every workflow is an Agent Skill in `plugins/<name>/skills/<skill>/SKILL.md` — the one and only copy. Claude Code and Codex load it through the marketplace — Codex reads `.claude-plugin/marketplace.json` and each `.claude-plugin/plugin.json` as they are, so add no Codex manifest; OpenCode users copy a plugin's `skills/*` directories into `.agents/skills/`. There is no build step and no generated tree: **never commit a second copy of a skill or of a file it reads.**

## What to write: skill or agent

| Kind | When | Lives in |
| --- | --- | --- |
| **skill** | canonical workflow or reference knowledge, usable across assistants | `plugins/<plugin>/skills/<name>/SKILL.md` |
| **agent** | Claude subagent entry point to a canonical skill | `plugins/<plugin>/agents/<name>.md` |

**Put workflow logic in a skill.** An agent must point to that skill without restating its procedure.

**A skill reaches only its own directory or a sibling skill's** (`../<sibling>/…`, relative to its `SKILL.md`). Both install layouts keep a plugin's skills side by side, so these paths work in every assistant; `../../` and `$CLAUDE_PLUGIN_ROOT` do not. A file several skills share becomes its own reference skill — `vault-conventions` holds the vault conventions, authoring standard, and scripts.

Process and reference are paired: `code-sweep` ↔ `code-smells`, `refactor-interfaces` ↔ `codebase-design`, `docs-sweep` ↔ `writing-docs`. The workflow loads its reference skill by name — never copy it in.

## Layout and frontmatter

- kebab-case directories; `SKILL.md` uppercase; a skill's name **is** its Claude slash name, namespaced by plugin.
- **Skill** — `name`, `description`, plus Claude-specific `allowed-tools`, `argument-hint`, and `disable-model-invocation: true` (for a workflow that commits or runs third-party code, so only the user starts it) only when needed; the body must work without them. **Agent** (Claude-only) — `name`, `description`, optional `tools`; its body is one line, ``Read `${CLAUDE_PLUGIN_ROOT}/skills/<name>/SKILL.md` and follow it`` — a relative link does not resolve from the user's project, and agents never run outside Claude, so the variable is safe there.
- **Quote every `description`.** An unquoted value containing `: ` fails YAML parsing, and Claude then loads the component with every field but its name silently dropped.
- The `description` is what makes a skill trigger. Write it as *when to use this*, name the triggers, and name what it is **not** for — it must contain the literal phrases `Use when` and `Not for`; CI checks.
- **`allowed-tools` pre-approves, it does not restrict.** Whatever it lists runs without a prompt for the turn that invokes the skill. Never list unscoped `Bash` in a skill that changes files, runs commands with side effects, or files anything — scope it to read-only commands (`Bash(git status *)`) or leave it out, so the mutating step still prompts.
- The `vault-conventions` skill holds `CONVENTIONS.md` and `AUTHORING.md` — read them before touching anything in `plugins/obsidian-vault/`.

## Voice

Match the files already here.

- **Imperative and dense.** No preamble, no "this document will". Cut every sentence that does not change what the reader does.
- **Phases, not narrative.** Numbered phases with a stated output each.
- **Tables and bold rules over paragraphs.** One memorable rule per section, bolded.
- **Say what goes wrong, not "cleaner".** Name the consequence.
- **Suppress false positives explicitly.** Any skill that finds problems must also say what is *not* a finding.
- **Audit before touching anything**, and **do not commit unless asked** — the house default for every workflow that changes files.

## Ground the shell commands you write

These files are full of literal shell invocations that have to work. Verify flags and behavior against the real docs (context7, the tool's `--help`, the actual repo) before writing them in — never from memory. Same for a template's or tool's own config: read it, don't assume it.

## Versioning

**Every change bumps two versions**, in the same commit: the touched plugin's `version` in `plugins/<name>/.claude-plugin/plugin.json`, and the marketplace `version` in `.claude-plugin/marketplace.json`. Never one without the other.

**Patch-bump both by default** — `0.5.1 → 0.5.2`, `0.13.0 → 0.13.1`. That includes adding a new skill or agent.

Larger bumps happen **only when the user asks**: minor for a new skill, command, or plugin, or a change in what an existing one does; major for a breaking rename or removal. The trigger is the request, not the size of the diff.

## Keeping descriptions in sync

Each plugin's description is written twice — `plugins/<name>/.claude-plugin/plugin.json` and that plugin's entry in `.claude-plugin/marketplace.json`. Change one, change the other. Adding or removing a skill or agent also means updating its bullet in `README.md`.

## Before you commit

Run every gate; CI runs the same ones.

```bash
uv run ruff check && uv run ruff format --check
uv run pytest
uv run python scripts/check_repo.py --base origin/main   # descriptions, links, README bullets, version bumps
claude plugin validate --strict . && for p in plugins/*/; do claude plugin validate --strict "$p"; done
```

**A script change ships with a test** in `tests/`, red before the fix and green after.
