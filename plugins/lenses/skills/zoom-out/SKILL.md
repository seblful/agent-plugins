---
name: zoom-out
description: "Step up one layer of abstraction from the current code and produce a map of all relevant modules and callers, named in the project's own domain vocabulary."
allowed-tools: Read, Glob, Grep, Agent
---

I don't know this area of code well. Go up a layer of abstraction. Give me a map of all the relevant modules and callers.

Name things the way the project names them. Take the vocabulary from whatever the project actually has — a `CONTEXT.md`, `CLAUDE.md`, an architecture doc or ADRs if they exist; otherwise from the code itself: module and type names, the domain nouns that recur across the area. Never invent a glossary the project doesn't use.
