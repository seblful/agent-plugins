---
name: grill-me
description: "Interview the user one question at a time about a plan or design until reaching shared understanding, walking each branch of the decision tree."
argument-hint: "[the plan or design to grill — omit to use what the session just landed on]"
allowed-tools: Read, Glob, Grep
---

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

`the user's request`, if given, is the plan to grill. If it is empty, grill whatever plan or design the session just landed on — name what you picked before the first question.

Ask the questions one at a time.

If a question can be answered by exploring the codebase, explore the codebase instead.
