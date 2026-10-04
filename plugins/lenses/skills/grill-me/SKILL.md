---
name: grill-me
description: "Interview the user one question at a time about a plan or design until reaching shared understanding, walking each branch of the decision tree, and end with a decision table. Use when the user asks to be grilled, to stress-test a plan, or to poke holes in a design before building it. Not for reviewing code already written (code-reviewer) or open-ended brainstorming."
argument-hint: "[the plan or design to grill — omit to use what the session just landed on]"
allowed-tools: Read, Glob, Grep
---

Interview the user relentlessly about every aspect of this plan until you reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one.

`the user's request`, if given, is the plan to grill. If it is empty, grill whatever plan or design the session just landed on — name what you picked before the first question.

## 1. Interview

- **One question per message**, each with your recommended answer and the reason for it.
- **Explore before asking.** If the codebase can answer a question, read it instead of asking.
- **Ask only what changes the plan.** Skip trivia, settled choices, and anything the user already answered.

Output per turn: one question, one recommendation.

## 2. Stop

Stop when no open branch remains, or when the user says stop. Then output, once:

| # | Decision | Chosen answer | Why |
| --- | --- | --- | --- |

followed by **Open questions** — anything left unresolved, with who or what can resolve it. **The table is the deliverable; an interview that ends without it is lost.**
