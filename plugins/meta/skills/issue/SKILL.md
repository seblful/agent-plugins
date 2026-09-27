---
name: issue
description: "Capture a bug, feature, enhancement, task, or idea as a GitHub issue in the backlog repo set by the ISSUES_REPO or CLAUDE_ISSUES_REPO env var. Check duplicates and confirm the draft before filing."
argument-hint: "[what to capture — omit to use what just happened in this session]"
allowed-tools: Bash, Read, Write, Grep
---

# File Issue

Capture a **bug, feature request, enhancement, task, or idea** as a GitHub issue in a **backlog repo you configure**, so it is remembered instead of lost when the session ends. Nothing here is tied to a specific project — point it at any repo and reuse it for any current or future system or skill.

The user's request, if specific, is what to capture. Otherwise capture what the conversation was just about — the failure you observed, the idea the user floated — and name what you picked before drafting. If nothing in the session is capturable, ask rather than inventing an item.

**Core rule — draft, then confirm.** Filing or commenting is outward-facing. Always show the full draft and get an explicit "yes" before running `gh issue create` — including when you reached this command by offering it yourself. Never file silently.

## Prerequisites

`gh` must be installed and authenticated — verify with `gh auth status`. If not, tell the user and stop. Do not attempt to file through the web UI or any other channel.

## Where issues go — the backlog repo

The destination is the `ISSUES_REPO` environment variable, with `CLAUDE_ISSUES_REPO` accepted for existing Claude Code setups. **There is no default** — if both are unset or empty, ask the user to set one to an `owner/name`. Never fall back to any repo.

Resolve it **once** at the start and reuse that literal `owner/name` in every `gh` command (each Bash call is a fresh shell, so do not rely on a variable persisting):

```
gh repo view "${ISSUES_REPO:-$CLAUDE_ISSUES_REPO}" --json nameWithOwner -q .nameWithOwner
```

Use equivalent environment-variable syntax for the active shell. If both variables are empty, treat that as "not configured" and stop. Otherwise pass `--repo <that value>` to **every** `gh` command below, so the working directory never decides where the issue lands. If the repo is inaccessible, say so and stop.

## What gets captured

- **What the user points at** — whatever the user's request names, or the thing the conversation just landed on.
- **A misbehaving plugin or system** — a skill, command, agent, or hook that triggered when it should not, did the wrong thing, or failed, even while working in an unrelated project. This is the case most likely to evaporate unrecorded, so capture the failure while the evidence is still in the session: the exact error, the trigger, what you expected instead. If you noticed such a failure and the user has not asked yet, offer — *"Want me to file that as an issue?"* — and run this command on agreement.

## Steps

### 1. Resolve the backlog repo
Get `owner/name` from `ISSUES_REPO` or the `CLAUDE_ISSUES_REPO` fallback with the command above. If both are unset or empty, stop and ask the user to set one — there is no default. Otherwise confirm access.

### 2. Classify the item
Decide the type from context, asking only if genuinely unclear: **bug**, **feature**, **enhancement**, **task**, or **idea**. The type shapes the body template (step 6) and the label (step 5).

### 3. Gather the substance
Build it from what you actually observed or what the user described:
- **bug / failure** — what was attempted, the exact error, the command or `path:line`, expected vs. actual behavior.
- **feature / enhancement / idea** — the motivation (the problem it solves), the proposed behavior, and any alternatives considered.
- **task** — the concrete outcome wanted and any acceptance criteria.

**Do not invent** repro steps, stack traces, versions, or requirements you did not see. If something is unknown, omit it or mark it "unknown". A thin accurate issue beats a padded speculative one.

### 4. Check for duplicates
`gh issue list --repo <owner/name> --search "<key terms>" --state all --limit 10`. If a clear match exists, offer to comment on it (`gh issue comment <n> --repo <owner/name> --body-file <file>`) instead of opening a duplicate.

### 5. Pick labels (existing ones only)
`gh label list --repo <owner/name>`. Choose 0–2 that fit the type (e.g. `bug`, `enhancement`). **Never pass a label that is not in the list** — `gh issue create --label` errors on unknown labels. If none fit, use no label. If a new label is clearly warranted, ask before `gh label create`.

### 6. Draft
Title: one concise line naming the problem or change — not "error occurred". Include only sections you can actually fill.

**Bug / failure**
```
## Summary
<one or two sentences>

## Steps to reproduce
1. …

## Expected
…

## Actual
…

## Environment
<OS, tool / versions — only if known>

## Where it happened
<repo or directory the session was in, e.g. `owner/name` or the path — include when the backlog collects from multiple projects>

## References
- `path:line`
- <commands, links>
```

**Feature / enhancement / idea / task**
```
## Summary
<one or two sentences>

## Motivation
<the problem this solves>

## Proposed behavior
<what it should do>

## Alternatives considered
<optional>

## References
- <links, `path:line`>
```

End every body with:
```

---
Filed from a coding assistant session.
```

### 7. Confirm
Show the user the target repo, item type, title, labels, and full body. Wait for an explicit yes. Revise and re-show if they want changes.

### 8. Create
Write the body to a temp file first (avoids shell-quoting problems, especially in PowerShell), then:

```
gh issue create --repo <owner/name> --title "<title>" --label <label> --body-file <tmpfile>
```

Print the returned issue URL. If the user chose to comment on an existing issue instead, use `gh issue comment <n> --repo <owner/name> --body-file <tmpfile>`.
