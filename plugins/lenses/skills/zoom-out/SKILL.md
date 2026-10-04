---
name: zoom-out
description: "Step up one layer of abstraction from the current code and produce a map of the relevant modules and their callers, named in the project's own domain vocabulary. Use when the user is unfamiliar with an area and asks for the big picture, where something fits, or what calls it. Not for redesigning interfaces (codebase-design) or writing an architecture doc."
argument-hint: "[file, symbol, or directory to zoom out from — omit to use the one in focus]"
allowed-tools: Read, Glob, Grep, Agent
---

Map the area around one piece of code so the user can navigate it. Read only — change nothing.

## 1. Pick the target

`the user's request`, if given, names the file, symbol, or directory. Otherwise use the code the session is focused on, and name what you picked in the first line. Nothing in focus → ask.

## 2. Bound the map

- **One layer up** — the module that owns the target and its sibling modules at that level.
- **One hop of callers** — direct callers of the target's entry points; no transitive call graph.
- An area too big for one screen → map the top level and list the rest under **Not covered**.

## 3. Name it the project's way

Take the vocabulary from what the project already has — a `CONTEXT.md`, `CLAUDE.md`, an architecture doc or ADRs if they exist; otherwise from the code itself: module and type names, the domain nouns that recur across the area. **Never invent a glossary the project doesn't use.**

## 4. Output

| Module | Its job, in one line | Entry points | Called from |
| --- | --- | --- | --- |
| `path/` | … | `path:line` | `path:line` |

Then one line on how data or control flows through the area, and **Not covered** for whatever the bound cut off.

**Every `path:line` is one you opened, not one you guessed.**
