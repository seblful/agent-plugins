# Seblful Coding Assistant Workflows

A curated collection of workflows for Claude Code, Codex, and OpenCode, grouped by **what they act on**: code in one language, any codebase, Obsidian notes, the conversation itself, and project work across repositories. Claude Code and Codex install it as a plugin marketplace; OpenCode uses the skill directories directly.

> **⚠️ Important:** Make sure you trust a plugin before installing, updating, or using it. Anthropic does not control what MCP servers, files, or other software are included in plugins and cannot verify that they will work as intended or that they won't change. See each plugin's source for more information.

## Structure

Five plugins, grouped by their target:

- **`/plugins/languages`** — acts on code in one language: Python and TypeScript practice, testing included, plus reproducible Jupyter notebooks — each the language layer over `code`'s language-agnostic skills
- **`/plugins/code`** — acts on any codebase, in any language: review, bug diagnosis, refactoring, architectural deepening, and keeping a project in sync with the template it came from
- **`/plugins/obsidian-vault`** — acts on your notes: maintenance routines for Obsidian vaults
- **`/plugins/lenses`** — acts on you and the conversation: code maps, terse mode, plan grilling, and a teaching workspace
- **`/plugins/meta`** — acts across all your projects: capturing bugs and ideas to a central GitHub backlog

## Installation

### Claude Code

Add this marketplace to Claude Code:

```
/plugin marketplace add seblful/agent-plugins
```

Then install plugins individually:

```
/plugin install languages@agent-plugins
/plugin install code@agent-plugins
/plugin install obsidian-vault@agent-plugins
/plugin install lenses@agent-plugins
/plugin install meta@agent-plugins
```

Or browse them in `/plugin > Discover`.

### Codex

Codex reads the same marketplace. Add it, then install plugins individually:

```
codex plugin marketplace add seblful/agent-plugins
codex plugin add languages@agent-plugins
codex plugin add code@agent-plugins
codex plugin add obsidian-vault@agent-plugins
codex plugin add lenses@agent-plugins
codex plugin add meta@agent-plugins
```

Pull new versions with `codex plugin marketplace upgrade`. The Claude subagents in `agents/` are not loaded; the skills they point to are.

### OpenCode

Every skill lives in `plugins/<plugin>/skills/<skill>/` and is a standard Agent Skill. Copy a plugin's skill directories into `.agents/skills/` in your project. Put them in `~/.agents/skills/` instead to make them available across your projects. For example, to add `code-sweep` to one project, the result should be:

```text
your-project/.agents/skills/code-sweep/SKILL.md
```

Copy whole skill directories, and copy a plugin's skills together: a workflow reads its sibling reference skill (`code-sweep` reads `code-smells`; every `vault-*` skill reads `vault-conventions`). There is no marketplace, so re-copy to update. The layout is documented in [OpenCode's skills docs](https://opencode.ai/docs/skills); if a skill does not appear, restart OpenCode and check that `SKILL.md` is directly inside a named skill directory.

Ask your assistant to use a workflow by its name, for example “use `code-sweep` on `src/`.” Skills can also be selected automatically when a request matches their descriptions. Claude Code exposes plugin skills as namespaced slash commands, such as `/code:code-sweep`. Some workflows require external tools named in their instructions, such as `gh`, Copier, or the Obsidian CLI. `refactor-interfaces` produces a local HTML report when the host cannot publish an Artifact.

## Plugins

### languages

Each language skill is the layer over `code-smells` and `codebase-design`: how their principles are spelled in that language, the traps easy to miss in it, how to test it, and what is not a finding. The named stack is the greenfield default only — a project's own choices outrank it.

- **python-code** (skill) — Python: principles mapped to types, dataclasses, pydantic, `with`, and structured async; Python-only traps; pytest practice; on the uv/ruff/ty stack.
- **typescript-code** (skill) — TypeScript: strict compiler baseline, discriminated unions, `unknown` parsed at the boundary, handled promises; TypeScript-only traps; Vitest practice.
- **python-notebooks** (skill) — Reproducible Jupyter notebooks: Restart & Run All as the contract, hidden-state discipline, uv-managed kernels, promotion of stable code to modules, jupytext pairing for version control, and restraint in figures and prose.

### code

- **code-reviewer** (skill; Claude agent) — Senior code reviewer that evaluates diffs across correctness, readability, architecture, security, and performance, with severity-labeled line-level suggestions.
- **diagnosing-bugs** (skill) — A feedback-loop-first discipline for hard bugs and performance regressions: build a tight red-capable repro, minimise it, generate falsifiable hypotheses, instrument, fix with a regression test, then clean up.
The codebase routines are split by **what they change**, each pairing a workflow skill with the reference skill that defines its vocabulary. One rule separates the first two — *would the fix change what a caller must know?* No → `code-sweep`. Yes → `refactor-interfaces`. The third changes no code at all:

|  | Reference skill | Workflow skill |
| --- | --- | --- |
| **Implementations** — inside a body, callers unaffected | `code-smells` | `code-sweep` |
| **Interfaces & seams** — the shape callers see | `codebase-design` | `refactor-interfaces` |
| **Docs** — the markdown a human reads | `writing-docs` | `docs-sweep` |

- **code-smells** (skill) — Catalog of implementation-level smells across three lenses (correctness & robustness, bad practices & idiom, duplication/dead weight/complexity), each with its fix and — equally important — the false positives to suppress.
- **code-sweep** (skill) — Codebase-wide sweep against the `code-smells` catalog, every finding verified by hand and listed as a defect list tiered by severity and evidenced by before/after code — then applied in attributable batches against a baseline verification signal, behaviour changes never mixed with pure refactors, only on your approval.
- **codebase-design** (skill) — Shared vocabulary for designing deep modules: module, interface, depth, seam, adapter, leverage, locality, plus the deepening patterns.
- **docs-sweep** (skill) — Condense every markdown doc a human reads against `writing-docs`: each doc gets one verdict — keep, tighten, split, merge, or delete — presented as a plan with lines now → expected, then applied one doc at a time on your approval, moving facts rather than losing them and fixing every link that moved.
- **refactor-interfaces** (skill) — Surface deepening opportunities and reduce shallow modules, presented as a diagram-led HTML report of up to five candidates. Pick the ones you want — the pick is the only approval — and each is designed, implemented in a shared worktree, verified against the project's own gates, and cherry-picked onto your branch — one commit per candidate, no pause between them, never pushed.
- **writing-docs** (skill) — Five laws for short, focused docs (one reader and one question, every sentence changes what the reader does, say what the code cannot, one home per fact, what survives is true), a table of what to cut, when to split, merge, or delete a doc, how to shape what stays — and what never to cut.

Alongside the pair, one workflow changes the codebase's *baseline* rather than its code:

- **update-from-template** (skill) — Pull the latest [Copier](https://copier.readthedocs.io/) template changes into a project, in any language. Requires a way to run Copier (`uvx --with jinja2-time copier`, `pipx run copier`, or a global install) and a git repo with a clean tree. Previews the template diff and takes a baseline from the project's *own* gates — discovered, not assumed — then branches, runs `copier update`, and owns what Copier could not decide: every conflict marker and `.rej` hunk resolved by intent under one rule — *the project wins on content, the template wins on shape* — with the resolution table keyed by what each file does (manifest, lockfile, hook config, assistant instructions, source skeleton) rather than what it is called. Ambiguities are surfaced rather than guessed. Adopts a template retroactively in a project with no answers file, by rendering a baseline to scratch and merging it in.

### obsidian-vault

> Requires a **running Obsidian** instance, the **`obsidian` CLI** ([`kepano/obsidian-skills`](https://github.com/kepano/obsidian-skills)), and **Python 3.12+** for the deterministic scripts (stdlib only). See the [plugin README](plugins/obsidian-vault/README.md).

- **vault-daily-format** (skill) — Normalize today's daily report (frontmatter, atomic tasks, titled links).
- **vault-inbox-ingest** (skill) — Empty the Inbox: merge each raw capture into the right note (or create one), relocate its images, wire into a MOC, delete the consumed capture.
- **vault-weekly-harvest** (skill) — Extract project-relevant knowledge from weekly reports into project notes, marking each report harvested.
- **vault-weekly-report** (skill) — Synthesize this week's daily reports grouped by project and archive the dailies.
- **vault-note-create** (skill) — Author a new source-of-truth reference note from a subject: plan scope and table of contents, then write a deep, modern note on approval.
- **vault-note-rewrite** (skill) — Refactor and expand fragmented notes into a source-of-truth reference note: audit and plan, then rewrite on approval.
- **vault-moc-create** (skill) — Build or restructure a Map of Content (MOC) for a domain; the canonical hub-building routine the other skills defer to.
- **vault-accuracy-review** (skill) — Verify every claim in every note (excluding Logs and the archive) and stamp reviewed dates.
- **vault-structural-scan** (skill) — Fix broken wikilinks, misplaced files, frontmatter errors, stale MOCs, plus dead weight (stubs, orphans, duplicates, empty notes).
- **vault-wikilink-sprint** (skill) — Add inline wikilinks between conceptually related notes, starting at hub notes.
- **vault-cleanup** (skill; Claude agent) — Mechanical file hygiene: attachment renames, markdown-to-wikilink conversion, orphan attachments, empty folders.
- **vault-conventions** (reference skill) — The conventions, authoring standard, and deterministic scripts every routine above reads.

### lenses

- **zoom-out** (skill) — Map the surrounding modules and callers when unfamiliar with an area.
- **caveman** (skill) — Ultra-compressed terse communication mode (~75% token reduction).
- **grill-me** (skill) — Stress-test a plan through relentless one-question-at-a-time interview.
- **teach** (skill) — Stateful, multi-session teaching workspace: grounds every lesson in a mission, gathers high-trust resources, and builds storage strength through beautiful interactive HTML lessons, glossaries, and learning records. Its workspace file formats live in [`references/`](plugins/lenses/skills/teach/references).

### meta

> Requires the **`gh` CLI**, authenticated (`gh auth status`), and an **`ISSUES_REPO`** env var set to an `owner/name` backlog repo. `CLAUDE_ISSUES_REPO` remains supported for existing Claude Code setups. There is no default.

- **issue** (skill) — Capture a bug, feature, enhancement, task, or idea from a session as a GitHub issue in your central backlog repo. Takes what to capture as an argument, or falls back to what the session just landed on. Classifies the item, checks for duplicates, uses only existing labels, and always drafts and confirms before filing — never files silently.

## Plugin Structure

The plugins follow the standard Claude Code plugin layout, and every skill directory is also a portable Agent Skill. Claude agents point to skills; a skill reaches only its own directory or a sibling skill:

```
plugins/
└── plugin-name/
    ├── .claude-plugin/
    │   └── plugin.json      # Plugin metadata (required)
    ├── skills/              # Agent Skills: workflows and reference skills
    │   └── <skill-name>/
    │       ├── SKILL.md
    │       ├── references/  # Files only this skill reads (optional)
    │       └── scripts/     # Helpers this skill runs (optional)
    └── agents/              # Claude subagents pointing at a skill (optional)
        └── <agent>.md
```

## Contributing

Open an issue or PR if you'd like to suggest a skill, fix a bug, or improve a description.

## License

MIT — see [LICENSE](LICENSE).

## Documentation

For more information on developing Claude Code plugins, see the [official documentation](https://code.claude.com/docs/en/plugins).
