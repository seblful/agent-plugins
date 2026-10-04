---
name: update-from-template
description: "Pull the latest Copier template changes into a project — preview the template diff, run copier update, resolve conflict markers and .rej hunks by intent, and prove the result with the project's own gates. Use when the user asks to update, re-sync, or adopt a Copier template, or mentions .copier-answers.yml. Not for CLAUDE.md upkeep (claude-md-management) or dependency upgrades with no template involved."
argument-hint: "[template ref to move to — e.g. v0.7.7 or HEAD; omit for the latest tag]"
allowed-tools: Read, Grep, Glob, Bash(git status *), Bash(git log *), Bash(git diff *), Bash(git ls-remote *), Bash(git rev-parse *)
disable-model-invocation: true
---

# Update From Template

Bring a project back in line with the [Copier](https://copier.readthedocs.io/) template it was generated from. `copier update` does the mechanical three-way merge and stops at the first thing it cannot decide; **this command owns everything after that** — the conflict markers, the `.rej` hunks, and the gates that prove the result still works.

`the user's request`, if given, is the template ref to move to (`v0.7.7`, `HEAD`). Omit it for the latest tag, which is what Copier picks by default.

**Nothing here is tied to one template, one language, or one toolchain.** The template URL comes from the project's own answers file, so this works on any Copier subproject; the gates come from the project's own build config; the conflict table is keyed by what a file *does*, not what it is called. Where a worked example is needed it uses a Python/`uv` project, because that is the stack with the most moving parts — read it as an illustration of the rule above it, never as the rule itself.

## Prerequisites

- **A way to run Copier.** `uvx --with jinja2-time copier` needs nothing installed globally and is what every command below uses; `pipx run copier` or a global install work the same way. This is only how Copier itself is launched — it says nothing about what language the *project* is written in. Whichever you use, include the template's own Jinja extensions: `jinja2-time` is not optional for a template that stamps the current year into a LICENSE, and a template declaring others fails the same way.
- **A git repo with a clean working tree.** Copier refuses to update a dirty destination, and without a clean state there is no abort point.
- Run everything from the project root. `<scratch>` below is a directory outside the project — the session scratchpad if the host has one, else one from `mktemp -d`.

## Phase 0 — Find the link, preview, then stop

**The link.** Look for the answers file at the project root: `.copier-answers.yml`, or `.copier-answers.*.yml` when the project tracks more than one template. Two keys matter:

| Key | What it is |
| --- | --- |
| `_src_path` | the template — a `gh:owner/name` or `gl:owner/name` shorthand, any git URL, or a local path |
| `_commit` | the template version the project last synced to — a tag, or a `git describe` string such as `v0.7.6-3-g1a2b3c4`; git resolves either as is |

**Not `.copier-answers.yml`** → pass `-a <answers file>` (`--answers-file`) to every `copier update` below; Copier reads only the default name otherwise.

No answers file → **the project predates the template.** Go to Phase 5. Do not hand-write an answers file to force `copier update` — Copier's own docs say never to edit that file by hand, and the merge it produces is against a rendering the project never matched.

**The URL.** Expand a shorthand for git: `gh:owner/name` → `https://github.com/owner/name.git`, `gl:owner/name` → `https://gitlab.com/owner/name.git`. A git URL or local path is used as is.

**The target.** `the user's request` names it, or take the newest release tag:

```
git ls-remote --tags --refs --sort=-v:refname <url>
```

The first tag without a pre-release suffix (`-rc1`, `a1`, `.dev0`) is the target — Copier skips pre-releases by default too. If `_commit` already equals the target, say so and stop.

**The preview.** A partial clone — full history, file contents fetched only when a diff needs them; a shallow clone would lack `_commit`:

```
git clone --quiet --filter=blob:none --no-checkout <url> <scratch>/template
git -C <scratch>/template log --oneline <_commit>..<target>
git -C <scratch>/template diff --name-status <_commit> <target>
```

Group the files by what they touch — dependencies, tooling config, package source, tests, assistant instructions — and list the commit subjects.

**Then stop and ask whether to update to `<target>`.** Run nothing below before a yes — this is the user's chance to say "not now".

**The baseline.** After the go-ahead, run the project's gates before the update, and record each as green or red. **Discover them; do not assume a stack.** Read the project's build config and its assistant instructions (`CLAUDE.md` / `AGENTS.md`), and take the commands they actually name. Five roles matter, in this order — skip any the project doesn't have:

| Gate | Where to find the command |
| --- | --- |
| Install / sync dependencies | the package manager the lockfile implies |
| Lint | the lint config at the project root |
| Type-check | the type-checker config, if the language has one |
| Test | the test runner's config or the CI workflow |
| Pre-commit / hooks | `.pre-commit-config.yaml` or the repo's hook runner |

A Python project on a `uv` stack, for example, resolves them to `uv sync`, `uv run ruff check .`, `uv run ty check src/ tests/`, `uv run pytest -v`, `uv run pre-commit run --all-files`. A Node project resolves the same five roles to its own commands. **Write down whatever you resolved — Phase 3 re-runs exactly these.**

**A red baseline is not a blocker — it is the control.** Without it you will blame the template for a failure the project already had.

## Phase 1 — Branch, then update

```
git switch -c chore/template-update-<target>
git rev-parse HEAD          # record it — this is your abort point
```

Then:

```
uvx --with jinja2-time copier update --trust --defaults --skip-tasks --conflict inline --vcs-ref=<target>
```

| Flag | Why |
| --- | --- |
| `--trust` | the template runs Jinja extensions and migrations; Copier refuses without it |
| `--defaults` | reuse every stored answer and take the template's default for questions added since — the non-interactive form |
| `--skip-tasks` | the template's `_tasks` — formatters and linters such as `ruff format .`, `mdformat .` — cannot parse a file with conflict markers. Skip them here; Phase 3 runs them |
| `--conflict inline` | git-style markers in place, both sides visible where the code is. `--conflict rej` instead collects rejected hunks in `.rej` files and leaves each file syntactically valid — switch to it if the markers are too tangled to work in |
| `--vcs-ref=<target>` | always — the exact ref the preview showed. Without it Copier picks its own newest tag by PEP 440, which may not be what the user approved |
| `-a <answers file>` | only when the answers file is not `.copier-answers.yml` |
| `--data key=value` | change a stored answer in the same run — a new runtime version, a different license. No interactive session needed |

**Record the skipped tasks now:** `git -C <scratch>/template show <target>:copier.yml` (or `copier.yaml`), and note every `_tasks` entry, rendered with the project's answers.

**Abort** at any point: `git reset --hard <recorded sha>` then `git clean -fd`.

## Phase 2 — Resolve what Copier could not

Find every one:

```
grep -rln "^<<<<<<<" . --exclude-dir=.git
find . -name "*.rej" -not -path "./.git/*"
```

**The rule: the project wins on content, the template wins on shape.** The template owns how the project is built — rule sets, tool tables, module skeletons, hook versions. The project owns what it actually is — its dependencies, its prose, its settings fields, its commands, its tests. A hunk that mixes both gets merged, never resolved by picking a side wholesale.

Two corollaries:

- **Lists union, they do not choose.** Dependencies, ruff `select`, pre-commit repos, gitignore lines, env keys — take both sides.
- **Deliberate divergence is the trap.** A pinned older dependency, a disabled lint rule, a rewritten `settings.py`: where the template now changes exactly the thing the project changed on purpose, do not silently adopt the template. Check `git log -- <file>` for why, and ask if the answer is not there.

Resolve by the **role** a file plays, not its name — every ecosystem has all of these under different spellings:

| Role | Example | How it resolves |
| --- | --- | --- |
| Package manifest | `pyproject.toml`, `package.json`, `Cargo.toml` | Union. Keep every real dependency the project added and its own identity (name, description, version, scripts); take the template's tool-config tables whole. |
| Lockfile | `uv.lock`, `package-lock.json` | Neither side. Delete the conflict and regenerate it with the manager in Phase 3. |
| Hook / CI config | `.pre-commit-config.yaml`, `.github/workflows/*` | Union of hooks and jobs; take the template's version bumps. |
| Assistant instructions | `CLAUDE.md`, `AGENTS.md` | Template sections describe the stack — take them. Project sections describe *this* project — keep them intact. Never let a template default overwrite a real instruction. |
| Wired-in source skeleton | the settings, logging, and entry-point modules | Take the template's new shape, then re-apply the project's own config fields, processors and commands on top. These grow project-specific code fastest. |
| Test scaffolding | `conftest.py`, test setup files | Take the template's fixtures and helpers; keep every project test. |
| Ignore / env / version pins | `.gitignore`, `.env*`, `.python-version`, `.nvmrc` | Union. Never drop a project-specific ignore or env key, and never let a template placeholder overwrite a real local value. |
| README | `README.md` | The project's, always. Take only genuinely new template sections — a new command, a new gate. |
| Answers file | `.copier-answers.yml` | Copier's, untouched. It records the new `_commit`; that file *is* the update. |

Anything genuinely ambiguous goes to the user with **both candidate resolutions named** — not a guess, and not a silent choice.

When you are done, delete every `.rej` file you applied and re-run both searches until they come back empty. **A left-behind marker is a broken project**, not a stray comment.

## Phase 3 — Verify

Run the `_tasks` you recorded in Phase 1, in their order (e.g. `uv run ruff format .`, `uv run mdformat .`), regenerate any lockfile you deleted in Phase 2, then re-run the Phase 0 gates in order.

- **Red where the baseline was green → the update caused it.** Fix it.
- **Red where the baseline was red → inherited.** Confirm you did not make it worse, and do not fold an unrelated pre-existing fix into this change.
- **A new lint or type error from a rule the template just added is a real finding.** Fix the code. Do not disable the rule to reach green unless the user says so.

Iterate until the gates match or beat the baseline.

## Phase 4 — Report

- **Version** — `_commit` → target, with the template's commit subjects.
- **What the template changed**, grouped: dependencies, tooling config, package source, tests, assistant instructions.
- **Conflicts resolved** — one line each: file, what the template wanted, what the project wanted, what you did.
- **Surfaced, not resolved** — every ambiguity left to the user, with both candidates.
- **Answers newly defaulted** — any question the template added that `--defaults` answered on the user's behalf, so they can override it with `--data`.
- **Gates** — baseline vs. now.

Do not commit unless asked. The branch and the abort SHA stay as they are.

## Phase 5 — Adoption: a project with no answers file

A project that predates the template has no common ancestor, so **`copier update` has nothing to merge against.** Build the ancestor instead of faking it:

**0. Get the template.** With no answers file there is nothing to read it from — **ask the user which template to adopt** and do not guess one.

**1. Infer the answers.** Read the template's `copier.yml` for the questions it actually asks, then answer each from what the project already is. Every template's question set differs; the pattern is always *find the fact in the repo, don't ask the user to retype it*:

| Question about | Read it from |
| --- | --- |
| Project / package name | the manifest's name field, and the real source directory |
| Description, author, version | the manifest's metadata |
| License | the `LICENSE` file, or none |
| Language / runtime version | the version pin file, else the manifest's requires-field |
| Which assistant | which instruction file exists — `CLAUDE.md`, `AGENTS.md`, an editor's ignore file |
| Optional features | whether the artifacts they generate are already present |

Show the filled table and **confirm before generating**: a wrong package name renders the whole template into the wrong path.

**2. Render a baseline into a scratch directory**, never over the project:

```
uvx --with jinja2-time copier copy --trust --defaults --vcs-ref=<target> --data-file <scratch>/answers.yml <template> <scratch>/baseline
```

`<target>` is resolved as in Phase 0.

The template's `_tasks` run in there — typically a `git init`, a dependency install, a format pass. Harmless, but it takes a minute.

**3. Merge the baseline into the project** file by file, under the Phase 2 rule. Files the project lacks get added; files it has get merged; nothing is overwritten wholesale.

**4. Take `.copier-answers.yml` from `<scratch>/baseline`** — it already records the correct `_src_path` and `_commit`. From here the project is an ordinary Copier subproject and Phases 0–4 work on it.

**5. Verify and report** as in Phases 3–4, and say plainly which template files were adopted and which were skipped as inapplicable.
