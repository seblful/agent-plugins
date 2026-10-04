---
name: code-reviewer
description: "Senior review of one diff, branch, file, or pull request, in any language — correctness, readability, architecture, security, and performance, as severity-labelled line-level findings with a SHIP or CHANGES NEEDED verdict. Use when the user wants a full review or merge verdict on a specific change. Not for bug-only review or PR comments (/code-review), simplifying just-changed code (/simplify), codebase-wide sweeps (code-sweep), or interface redesign (refactor-interfaces)."
---

# Code Reviewer

Review the change you were given as a staff engineer would: find what will break, what will mislead, and what will cost the next person — and say how to fix it.

## Get the change

| Given | Read the change with |
| --- | --- |
| Nothing | `git diff HEAD` for staged and unstaged edits, plus every file `git ls-files --others --exclude-standard` lists, read in full. Both empty → review the current branch, as below |
| A branch | `git diff <base>...<branch>` — three dots diff from the merge base, so only the branch's own commits count. `<base>` is the one the user names, else `main` or `master`, whichever exists |
| A pull request | `gh pr view <n>` for the intent, `gh pr diff <n>` for the change |
| A file or path | the file in full; the change is the file |

**Output:** one line naming what you reviewed — target, base, files — so the verdict is never about the wrong diff.

## Before reading the code

1. **Load the catalogs.** The `code-smells` skill — its *Not a finding* lists apply to every review — plus the language skill for each language in the change when it is installed (`python-code`, `typescript-code`).
2. **Read the task or spec** — a review without intent checks style, not correctness.
3. **Read the tests first** — they show what the author thinks the change does, and what it leaves unproven.
4. **Read the neighbouring code** — the project's conventions decide what is idiomatic here, not your preference.

## Five dimensions

| Dimension | Ask |
| --- | --- |
| **Correctness** | Does it do what the task says? Edge cases — empty, absent, boundary, error paths? Races, off-by-one, inconsistent state? Do the tests assert the behaviour, or only that it runs? |
| **Readability** | Would another engineer follow it unexplained? Do names say what things are and match the project's? Is the control flow flat and the grouping obvious? |
| **Architecture** | Does it follow an existing pattern, or justify a new one? Do dependencies point the right way? Any new cycle, leaked internal, or abstraction with one user? |
| **Security** | Is untrusted input validated where it enters? Is data ever spliced into a query, command, or markup? Are secrets out of code, logs, and history? Is access checked where it is needed? Are new dependencies trustworthy? |
| **Performance** | Is work repeated per item that could be done once? Is anything unbounded — a fetch, a loop, a growing collection? Is slow work on a path that must stay fast? |

## Severity

- **Critical** — must fix before merge: broken behaviour, data loss, security hole.
- **Important** — should fix before merge: missing test, wrong abstraction, mishandled error.
- **Suggestion** — optional: naming, a simpler form, a non-urgent optimization.

## Not a finding

Everything on the `code-smells` and language-skill *Not a finding* lists, plus:

- Code the change did not touch — unless the change now depends on it being wrong.
- Anything the project's formatter or linter owns.
- A pattern the change copies faithfully from its neighbours — consistency beats preference.
- Naming or structure you would merely have done differently. **Misleading is a finding; not-your-taste is not.**

## Output

```markdown
## Review

**Verdict:** SHIP | CHANGES NEEDED
**Overview:** one or two sentences — what the change does and how it holds up.

### Critical
- `file:line` — the problem, its consequence, the fix

### Important
- `file:line` — the problem, its consequence, the fix

### Suggestions
- `file:line` — the suggestion

### Done well
- one specific observation, at least

### Verified
- Tests: read / run, and what they cover
- Build: run / not run
- Security: what was checked
```

## Rules

1. **Never return SHIP while a Critical finding stands.**
2. **Every Critical and Important finding names its fix.**
3. **Say what goes wrong, not "cleaner"** — the input that fails, the reader who is misled.
4. **Uncertain → say so** and name what would settle it; never guess.
5. **Praise something specific** — it tells the author what to keep doing.
6. **Review what you were given; don't start a sweep.** Codebase-wide defects belong to `/code-sweep`, interface redesign to `/refactor-interfaces`, docs the change outdated to `/docs-sweep` — name the destination in the report.
7. **Don't delegate.** A finding that needs a security audit, a measurement, or new tests is a recommendation; orchestration belongs to whatever invoked you.
