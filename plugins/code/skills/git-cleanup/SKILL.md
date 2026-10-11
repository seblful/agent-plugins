---
name: git-cleanup
description: "Clear out a git repository's leftover branches and worktrees — inventory merged, squash-merged, and gone-upstream branches, stale, missing, and orphaned worktrees (agent worktrees included), tier each as safe or at risk, then remove only what you approve, recording every deleted tip so it can be restored. Use when the user asks to clean up, prune, or tidy branches or worktrees, or a repo or folder of repos has piled up feature branches, agent worktrees, or .claude/worktrees folders. Not for stashes, tags, or rewriting history, nor for reviewing what a branch contains (code-reviewer)."
argument-hint: "[repo path, or a folder of repos — omit for the current repo; add 'remote' to also offer merged remote branches]"
allowed-tools: Read, Glob, Bash(git for-each-ref *), Bash(git worktree list *), Bash(git status *), Bash(git log *), Bash(git rev-parse *), Bash(git symbolic-ref *), Bash(git merge-base *), Bash(git cherry *), Bash(git rev-list *), Bash(git remote), Bash(gh pr list *)
---

# Git Cleanup

Remove the branches and worktrees a repository has outgrown — **inventory first, delete only on approval**.

`the user's request` names a repo path, a folder holding several repos, or nothing (the current repo). A folder that is not itself a repo → find the repos in it (`find <dir> -maxdepth 3 -name .git`) and run Phase 0 in each; Phase 2 then presents one plan grouped by repo.

**Scope: local branches, worktrees, and worktree folders.** Remote branches only when the request says `remote`. Stashes, tags, and history are out of scope — name any stray stash in the report and touch nothing.

## Phase 0 — Inventory

Run each step with `git -C <repo>`; never `cd` into a worktree that may be removed.

**1. Refresh.** `git fetch --prune <remote>` updates remote-tracking refs and marks deleted upstreams `[gone]`. It touches no local branch. Offline or no remote → skip, and say `[gone]` is stale.

**2. The default branch.** First that answers:

| Source | Command |
| --- | --- |
| remote HEAD, cached | `git symbolic-ref --short refs/remotes/<remote>/HEAD` |
| remote HEAD, live | `git ls-remote --symref <remote> HEAD` — the `ref: refs/heads/<name>` line |
| no remote | whichever of `main`, `master` exists |

None → ask. `<remote>` is `origin`, or the only name `git remote` prints.

**3. Protected** — never a candidate, never listed as one: the default branch; long-lived branches the repo itself names (`develop`, `dev`, `staging`, `production`, `release/*`, `hotfix/*`, and any branch in a CI workflow's `branches:` trigger); every branch with an open PR (`gh pr list --head <branch> --state open`, when `gh` is authenticated).

**4. Branches.**

```
git for-each-ref refs/heads --format='%(refname:short)|%(objectname:short)|%(upstream:short)|%(upstream:track)|%(worktreepath)|%(committerdate:short)'
git for-each-ref --merged=<default> refs/heads --format='%(refname:short)'
```

**Test against `<remote>/<default>`, not the local `<default>`, when the local one is behind it** — a stale local default makes merged work look unmerged. For each branch not merged, the squash check — it builds one unreferenced commit with the branch's whole diff and asks whether the default already has that patch:

```
git cherry <default> $(git commit-tree <branch>^{tree} -p $(git merge-base <default> <branch>) -m _)
```

`-` → squash- or rebase-merged. `+` → unmerged. The dangling commit is never referenced and `git gc` collects it.

**5. Worktrees.**

```
git worktree list --porcelain
```

Per linked worktree: its `branch` or `detached` HEAD, and the `locked` and `prunable` lines. For each one whose folder exists: `git -C <path> status --porcelain` (empty = clean). A detached HEAD: `git merge-base --is-ancestor <sha> <default>` (exit 0 = its commits are safe).

**6. Orphaned folders** — directories in a worktree home that git no longer knows: `.claude/worktrees/*`, `.worktrees/*`, and the parent of every registered linked worktree. A folder is orphaned when its path is not in the worktree list. Record its file count and newest modification time, and list its top level. **Git cannot tell you what in an orphaned folder is unsaved work** — the `.git` link is gone, so nothing is tracked, and only the listing speaks for it.

**Output:** per repo — the default branch, the protected set, and one row per branch, worktree, and orphaned folder with its facts.

## Phase 1 — Tier every item

**Branches**

| Class | Evidence | Delete with | Tier |
| --- | --- | --- | --- |
| **Merged** | in `--merged=<default>` | `git branch -d`; when `-d` refuses because the branch is ahead of its own upstream, `-D` — its commits are already in the default | safe |
| **Squash-merged** | squash check prints `-` | `git branch -D` — `-d` refuses these unless the branch's own upstream holds them | safe |
| **PR merged** | `gh pr list --head <branch> --state merged --json number,headRefOid` returns a PR **and** `headRefOid` equals the branch tip | `git branch -D` | safe |
| **Gone, unmerged** | `[gone]`, none of the above | `git branch -D` | at risk |
| **Unmerged** | everything else | — | kept |

A PR whose `headRefOid` differs from the tip means commits landed after the merge — that branch is **Gone, unmerged** or **Unmerged**, never safe.

**Worktrees**

| Class | Evidence | Remove with | Tier |
| --- | --- | --- | --- |
| **Missing** | `prunable` | `git worktree prune` | safe |
| **Finished** | clean, and its branch is safe above or its detached HEAD is an ancestor of the default | `git worktree remove <path>`, then the branch by its class | safe |
| **Dirty** | `status --porcelain` not empty | `git worktree remove --force <path>` | at risk |
| **Unfinished** | clean, but its branch is unmerged or its detached HEAD is not an ancestor | `git worktree remove <path>` — the commits stay on the branch; a detached HEAD's are lost | at risk |
| **Locked** | `locked` | `git worktree remove -f -f <path>` | kept |
| **Orphaned, empty** | orphaned folder, no files | delete the folder | safe |
| **Orphaned, with files** | orphaned folder with files | delete the folder | at risk |

**Not a finding:** a protected branch; the main worktree; the current branch of any worktree you are not proposing to remove; an unmerged branch with no upstream — that is work in progress, not debris, whatever its age; a locked worktree — someone locked it on purpose.

**Output:** every item with its class and tier.

## Phase 2 — Present the plan, then stop

Numbered, so the user can answer "1–6, 9":

1. **Safe** items first, grouped by repo: name, class, the one-line evidence (`merged`, `squash → -`, `PR #42 merged`, `prunable`), last commit date.
2. **At risk** items, each with what would be lost — `git log --oneline <default>..<branch>` for a branch, the `status --porcelain` lines for a dirty worktree, the top-level listing and newest file for an orphaned folder.
3. **Remote** branches, only when asked: `git for-each-ref --merged=<remote>/<default> refs/remotes/<remote> --format='%(refname:short)|%(authorname)|%(committerdate:short)'`, minus protected and `<remote>/HEAD`. **Deleting one deletes it for everyone** — show the author of each tip.
4. One **Kept** line: unmerged and locked items, so the user sees nothing was missed.

**Then stop and ask which numbers to apply.** "All safe" is an answer; an at-risk or remote item runs only when named by its number. Delete nothing before an answer.

## Phase 3 — Apply in this order

**Record every branch tip first** — `git rev-parse <branch>` for each approved branch, and the HEAD of each approved worktree. That SHA is the only undo.

| Step | Command | Why this position |
| --- | --- | --- |
| 1 | `git worktree prune` | a branch held by a missing worktree cannot be deleted until its entry is pruned |
| 2 | `git worktree remove <path>` per approved worktree; `--force` only for an approved **Dirty** one | git refuses to delete a branch checked out in a worktree |
| 3 | delete approved orphaned folders | they hold no git state, so order among themselves is free |
| 4 | `git branch -d`, or `-D` exactly where Phase 1's table says | after step 2 no worktree holds them |
| 5 | `git push <remote> --delete <branch>` per approved remote branch | last — the only outward-facing step |

**A failed step stops that item, never the run, and is never retried with force.** On Windows, `git worktree remove` can fail partway on a locked file and leave the folder behind with its `.git` link already gone — report it as a new **Orphaned, with files** item for the next run; do not escalate to `--force` on your own.

Never run `git gc`, `git reflog expire`, or `git prune` — they destroy the reflog and unreachable objects that make every deletion here recoverable.

Then re-run the Phase 0 branch and worktree listings.

## Phase 4 — Report

- [ ] Deleted, per repo — every branch with its recorded tip SHA, every worktree and folder removed
- [ ] Restore line — `git branch <name> <sha>` brings any deleted branch back while git still has its objects
- [ ] Approved items that failed, with the error, and anything left behind
- [ ] Kept — unmerged, locked, and at-risk items not approved
- [ ] Out of scope but noticed — stray stashes, a stale `<remote>/HEAD`

Do not commit anything; this routine changes refs and folders only.
