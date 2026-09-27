---
name: vault-note-create
description: "Author a new durable source-of-truth reference note on a subject — plan the scope and table of contents first, then on approval write a deep, modern note into the vault. Use when the user asks to create or write a reference, concept, or knowledge note on a topic."
allowed-tools: Bash, Read, Edit, Write, Glob, Grep, WebSearch, WebFetch
---

# Create Reference Note

Turn a subject into the vault's authoritative reference note on it: plan before writing, get approval, then author a deep note its intended reader can rely on. The authoring standard — audience, voice, technical standards, diagrams, document shape, and the two-step workflow — lives in [AUTHORING.md](../../AUTHORING.md); vault mechanics and the deterministic scripts live in [CONVENTIONS.md](../../CONVENTIONS.md). Read both before planning.

## Input

The subject to document, plus any context the user gives (audience, desired depth, angle, constraints). If no subject is given, or it's too broad to scope into one note, ask before planning.

## Step 1 — Research and plan

First check whether the vault already covers the subject (search per CONVENTIONS → Accessing the vault). If a note already exists, the user likely wants `vault-note-rewrite` instead — say so and stop. Otherwise resolve the audience and domain, ground the subject, and survey the graph (AUTHORING → Audience and domain, Research and grounding, Connecting the note), then produce the plan:

- **Audience** — who the note is for and the domain it sits in (AUTHORING → Audience and domain). This governs every choice below.
- **Scope** — the boundaries of the note: which aspects of the subject it covers.
- **Shape** — one note, or a hub plus linked sub-notes (AUTHORING → Scoping).
- **Key concepts** — the core theoretical and practical ideas it must explain.
- **Exclusions** — adjacent topics deliberately left out to keep the note focused, and where each belongs instead.
- **Technology / approach stack** — the specific modern libraries, frameworks, or methods the examples will assume (AUTHORING → Technical standards).
- **Connections** — existing notes this one will link out to, and the notes that should link back in (AUTHORING → Connecting the note).
- **Table of contents** — the full `##`/`###`/`####` outline, following AUTHORING → Document shape.

Output only the plan, then ask: *"Do you approve this plan? Type 'Yes' to proceed with the note creation."* Stop and wait.

## Step 2 — Write the note (after approval)

Write the note(s) into the right folder following the approved table of contents and the AUTHORING standard throughout — grounded and cited, depth over breadth, modern and timeless, diagrams where they clarify structure. If the approved shape is a cluster, build its hub with `vault-moc-create`. Connect it per CONVENTIONS → Creating notes and AUTHORING → Connecting the note (frontmatter, footnote citations, links out, and links in from related notes). Then verify before reporting (AUTHORING → Verify before done).

## Report

The note(s) created (paths), the sections written, sources cited, and how it was connected (links out, links in, MOC).
