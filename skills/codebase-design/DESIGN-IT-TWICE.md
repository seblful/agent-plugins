# Design It Twice

Explore alternative interfaces for a chosen deepening candidate with parallel subagents. **Your first design is unlikely to be the best** (Ousterhout). Uses the vocabulary in [SKILL.md](SKILL.md).

## 1. Frame the problem

Write the user a short problem statement for the candidate:

- the constraints any new interface must satisfy
- its dependencies and their category ([DEEPENING.md](DEEPENING.md))
- a rough sketch that makes the constraints concrete — an illustration, not a proposal

Show it, then go straight to step 2; the user reads while the subagents work.

## 2. Spawn subagents

Spawn **three or more in parallel**, each told to produce a **radically different** interface. Give each a separate technical brief — files, coupling, dependency category, what sits behind the seam — plus the glossary and the codebase's own domain terms, and one constraint:

| Agent | Constraint |
| --- | --- |
| 1 | Minimise the interface — one to three entry points, maximum leverage each |
| 2 | Maximise flexibility — many use cases, open to extension |
| 3 | Optimise for the most common caller — make the default case trivial |
| 4 *(if cross-seam dependencies exist)* | Design around ports and adapters |

Each returns:

1. **Interface** — entry points and parameters, plus invariants, ordering, error modes
2. **Usage** — how a caller uses it
3. **Hidden** — what the implementation keeps behind the seam
4. **Dependencies** — strategy and adapters
5. **Trade-offs** — where leverage is high, where it is thin

## 3. Compare and recommend

Present the designs one at a time, then compare them on **depth**, **locality**, and **seam placement**. **End with a recommendation** — the strongest design and why, or a hybrid if parts combine well. The user wants a strong read, not a menu.
