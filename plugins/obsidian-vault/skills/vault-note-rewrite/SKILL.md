---
name: vault-note-rewrite
description: "Rewrite informal or fragmented notes into a durable source-of-truth reference note in an Obsidian vault — audit and plan first, then on approval restructure, correct, and expand. Use when the user asks to rewrite, refactor, restructure, expand, or clean up the content of a specific note or pasted notes. Not for today's daily note (vault-daily-format), vault-wide structural fixes (vault-structural-scan), or file and link tidying (vault-cleanup)."
allowed-tools: Read, Glob, Grep, WebSearch, WebFetch
---

# Rewrite Into Reference Note

Refactor, correct, and expand fragmented notes into the vault's authoritative reference on the subject: audit and plan before touching anything, get approval, then rewrite. The authoring standard — audience, voice, technical standards, diagrams, document shape, and the two-step workflow — lives in [AUTHORING.md](../vault-conventions/AUTHORING.md); vault mechanics and the deterministic scripts live in [CONVENTIONS.md](../vault-conventions/CONVENTIONS.md). Read both before planning.

## Input

The note(s) to rewrite — a vault note name/path, or pasted text. Read the source in full (and any notes it links) before planning. Never change the source's language (CONVENTIONS → Language and substance).

## Step 0 — Safety preflight

Run the preflight in [CONVENTIONS → Before changing anything](../vault-conventions/CONVENTIONS.md#before-changing-anything).

## Step 1 — Audit, research, and plan

Resolve the audience and domain (AUTHORING → Audience and domain), audit the source, verify its claims and your proposed corrections against real sources, and survey the graph (AUTHORING → Research and grounding, Connecting the note). Then produce the plan:

- **Audience** — who the rewritten note is for and its domain (AUTHORING → Audience and domain).
- **Proposed changes** — the key structural and thematic restructuring, each with its rationale.
- **Shape** — keep as one note, or split into a hub plus linked sub-notes if the source covers several note-worthy concepts (AUTHORING → Scoping).
- **Corrections** — inaccuracies, deprecated logic, and errors found in the source, each with its fix and the source confirming it.
- **Exclusions** — content to cut (irrelevant tangents, duplication), each with justification.
- **Technology / approach updates** — specific legacy libraries or methods to replace with modern standards (AUTHORING → Technical standards).
- **Connections** — existing notes to link out to, and the notes that should link back in (AUTHORING → Connecting the note).
- **Table of contents** — the full `##`/`###`/`####` outline of the rewritten note(s), following AUTHORING → Document shape.

Output only the plan, then ask: *"Do you approve this plan? Type 'Yes' to proceed with the rewrite."* Stop and wait.

## Step 2 — Rewrite (after approval)

Apply the approved plan and the AUTHORING standard. If the source is an existing vault note, rewrite it in place and bump `modified` per CONVENTIONS; if it's pasted text, create the note per CONVENTIONS → Creating notes. Preserve what already works — keep the source's language, and retain its images, embeds, and citations in their logical positions, re-formatted per CONVENTIONS → Links and Body formatting. Connect it per AUTHORING → Connecting the note, then verify before reporting (AUTHORING → Verify before done).

## Report

The note(s) rewritten (paths), the structural changes and corrections applied, content cut, technology updated, sources cited, and connections added.
