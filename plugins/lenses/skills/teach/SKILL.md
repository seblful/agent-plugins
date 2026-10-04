---
name: teach
description: "Run a stateful, multi-session teaching workspace — ground every lesson in a mission, gather high-trust resources, and build storage strength through interactive HTML lessons, a glossary, and learning records. Use when the user wants an ongoing course on a topic: \"teach me X over time\", \"start a learning workspace\", or continuing one. Not for one-off explanations, code walkthroughs (zoom-out), or a single question answered in chat."
argument-hint: "[what you want to learn — omit to continue the workspace's existing mission]"
allowed-tools: Read, Glob, Grep, WebSearch, WebFetch
---

# Teach

`the user's request`, if given, is the topic or the specific thing to learn this session. If it is empty, continue the workspace's existing mission.

The user intends to learn the topic over multiple sessions. The state of their learning lives in files in a **teaching workspace** directory, and every session follows the phases below.

## Workspace

| Path | Holds | Format |
| --- | --- | --- |
| `MISSION.md` | the _reason_ the user is learning this; grounds every lesson | [MISSION-FORMAT.md](references/MISSION-FORMAT.md) |
| `RESOURCES.md` | the curated high-trust sources lessons draw from | [RESOURCES-FORMAT.md](references/RESOURCES-FORMAT.md) |
| `GLOSSARY.md` | the workspace's canonical terms; every lesson uses them | [GLOSSARY-FORMAT.md](references/GLOSSARY-FORMAT.md) |
| `learning-records/NNNN-slug.md` | what the user has demonstrably learned; drives what to teach next | [LEARNING-RECORD-FORMAT.md](references/LEARNING-RECORD-FORMAT.md) |
| `lessons/NNNN-slug.html` | one self-contained lesson each — the primary unit of teaching | [Lessons](#lessons) |
| `reference/*.html` | cheat sheets, syntax, algorithms, poses — the compressed essence of lessons, printable | [Reference documents](#reference-documents) |
| `assets/*` | components shared across lessons: stylesheet, quiz widgets, simulators | [Assets](#assets) |
| `NOTES.md` | the user's teaching preferences and your working notes | free-form |

`NNNN` numbers are sequential: scan the directory for the highest and add one. Create a directory only when its first file is written.

## Session phases

### 0. Locate the workspace

A workspace is a directory with a `MISSION.md`. If the current directory has one, use it. If it does not, and the directory is a git repository or is not empty, **ask the user for a workspace path before writing anything** — a course scattered through a code project pollutes it. Otherwise, the empty current directory becomes the workspace.

Output: the workspace path, stated.

### 1. Load state

Read `MISSION.md`, `NOTES.md`, `GLOSSARY.md`, the learning records, and the list of `assets/` and `lessons/`.

Output: one line on where the user stands.

### 2. Mission check

If `MISSION.md` is missing or vague, interview the user on _why_ they want to learn this before anything else, then write it. Without a mission, lessons are too abstract and there is no way to judge what comes next. If the user's goal has shifted, confirm with them, update `MISSION.md`, and write a learning record for the shift.

Output: a mission you can trace the next lesson to.

### 3. Resources

Until `RESOURCES.md` is well populated, finding high-quality, high-trust sources is the main job. **Never trust your parametric knowledge** — draw claims from these sources and cite them.

Output: `RESOURCES.md` updated with anything new this session needs.

### 4. Pick the lesson

The user's request names it, or pick from their **zone of proximal development**: the most mission-relevant thing just beyond what the learning records show they know — challenged "just enough".

Output: the lesson's one tangible win, in one sentence.

### 5. Write the lesson

Build it from `assets/` (see [Lessons](#lessons)), save it to `lessons/NNNN-slug.html`, and add or update any reference document it earns. Then open it for the user:

| Shell | Command |
| --- | --- |
| Git Bash (Windows) | `start lessons/NNNN-slug.html` |
| PowerShell | `Start-Process lessons/NNNN-slug.html` |
| macOS | `open lessons/NNNN-slug.html` |
| Linux | `xdg-open lessons/NNNN-slug.html` |

Output: the lesson file, opened.

### 6. Record

As the user works through it and asks questions, write a learning record **only on evidence** of understanding, disclosed prior knowledge, a corrected misconception, or a mission shift — never for mere coverage. Promote a term to `GLOSSARY.md` once the user uses it correctly. Note new teaching preferences in `NOTES.md`.

Output: the files changed, listed.

## Philosophy

To learn at a deep level, the user needs three things:

- **Knowledge**, captured from high-quality, high-trust resources
- **Skills**, acquired through highly relevant interactive lessons devised by you, based on the knowledge
- **Wisdom**, which comes from interacting with other learners and practitioners

Some topics lean on knowledge (theoretical physics), others on skills (yoga).

**Build storage strength, not fluency.** Fluency — in-the-moment retrieval — gives an illusory sense of mastery; storage strength — long-term retention — is the goal. Design for desirable difficulty: retrieval practice (recall from memory), spacing (practice distributed over time), and interleaving (mixing related topics — skills practice only).

## Lessons

- **Short, completable quickly, one tangible win**, tied to the mission. Working memory is small; stay within it.
- **Beautiful** — clean typography and layout, since the user returns to review. Think Tufte.
- **Knowledge first, only what the skill needs, then practice.** For acquiring knowledge, difficulty is the enemy — it eats working memory. For skills, difficulty is the tool — effortful retrieval builds storage strength.
- **A feedback loop for every practice** — interactive quizzes and light in-browser tasks, or guided real-world steps (yoga poses). Feedback as immediate and automatic as possible.
- **Quiz answers give no clues** — every option the same number of words, and characters where possible.
- **Citations throughout** — link the sources behind every claim, and recommend one primary source to read or watch: the best one you found.
- **Linked** — anchors to other lessons and reference documents.
- **A reminder to ask follow-up questions** — you are their teacher for anything unclear.

## Assets

**Reuse is the default.** Before authoring a lesson, read `assets/` and build from the components already there. When a lesson needs something a second lesson could reuse, write it as a component in `assets/` and link it — never inline code a future lesson would duplicate. A shared stylesheet is the first component every workspace earns, so the lessons read as one course rather than a pile of one-offs.

## Reference documents

Lessons are rarely revisited; reference documents are. Each is the compressed essence of one or more lessons, designed for quick lookup and printing: syntax and snippets for programming, algorithms and flowcharts for processes, poses and sequences for yoga, routines for fitness. The glossary is the exception — it lives at the workspace root as `GLOSSARY.md`, and every lesson adheres to it.

## Wisdom

Wisdom comes from testing skills outside the learning environment. When a question needs it, attempt an answer, then point the user to a **community** — a forum, a subreddit, a real-world class (budget permitting), or a local group — with a high reputation. If the user does not want to join one, respect it and note it in `RESOURCES.md`.
