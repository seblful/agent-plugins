# Authoring Reference Notes

Shared spec for authoring durable **source-of-truth** reference notes. `vault-note-create` and `vault-note-rewrite` follow it end to end; other routines apply the relevant parts whenever they create or substantially expand a knowledge note — e.g. `vault-inbox-ingest` when it promotes a capture into one. Each authoring skill states its own job and its own plan; the standards they share live here once, so they can't drift apart.

Vault mechanics are **not** repeated here. Frontmatter schema, `[[wikilinks]]`, footnote citations, heading rules, math and variable-key formatting, image alt text, MOC wiring, note creation, the deterministic scripts, and CLI access all live in [CONVENTIONS.md](CONVENTIONS.md) — follow it. This file adds only what's specific to writing deep reference documents.

## What a reference note is

A reference note is the vault's single source of truth on its subject: a durable handbook entry, not a quick capture or a log. It favors conceptual depth, design rationale, and long-term maintainability over breadth or novelty. One subject per note (CONVENTIONS → Creating notes); when a subject is too large, narrow the scope rather than write shallow.

## Audience and domain

A reference note is written *for someone* in *some field*, and that choice sets its vocabulary, assumed background, and depth. **Establish the audience and domain before outlining — never assume a default field.** Resolve them in this order:

1. **Stated** — if the user names the audience or domain (e.g. "for a junior backend engineer", "for a clinician"), use it.
2. **Discovered** — otherwise infer it from the vault: the dominant subject matter of existing notes, their assumed reader, and their depth (CONVENTIONS → Discovering a vault's conventions). A vault of distributed-systems notes implies a systems engineer; a vault of case law implies a lawyer.
3. **Ask** — if neither is clear, ask the user who the note is for before planning. Don't guess a field.

Record the resolved audience as the first line of the plan, since it governs every later choice. The default reader is a **practitioner who must understand and apply the subject, not merely recognize it** — pitch to that level within whatever domain applies.

## Voice

- **Authoritative** — precise and definitive. State how something works and why it's built that way; don't hedge or editorialize.
- **Timeless** — no relative time references ("recently", "current state of the art", "new"). Write a standard that stays true. Name specific versions instead of "latest".
- **Depth over breadth** — explain the underlying model and the rationale, not just the surface mechanism. Never pad to feel comprehensive.

## Technical standards

These apply to any technical or engineering subject; for a non-technical domain, read "modern" as "current accepted practice in the field" and "code" as "worked example".

- **Modern by default** — examples and logic assume current standards in the domain. Treat legacy approaches as legacy: cover one only when the note is explicitly about a legacy system; otherwise upgrade it silently.
- **Rigorous bias** — prioritize correctness, robustness, and the trade-offs behind a recommendation; explain the design rationale, not just the mechanism.
- **Examples sparingly** — include a code snippet or worked example only when it's essential for clarity. Prefer high-level logic descriptions and diagrams. Any code that stays follows CONVENTIONS → Body formatting.

## Research and grounding

A source-of-truth note must be verifiable, not recalled from memory — a note full of plausible-but-wrong API signatures, dates, or figures is the exact failure `vault-accuracy-review` exists to catch. Before and while writing:

- **Verify every concrete claim against a real source** — version numbers, signatures, configuration options, benchmark figures, named references, dates. Prefer authoritative primary documentation; use a documentation MCP such as context7 when the session has one, otherwise web search and fetch.
- **Cite what you consulted.** Every external claim or definition gets a footnote pointing at the source actually used (CONVENTIONS → Links). Never cite a source you didn't read.
- **Don't invent citations or numbers.** If a fact can't be verified, state it as a general principle without a fabricated reference, or leave it out.

The bar: a note this skill produces should pass `vault-accuracy-review` unchanged.

## Diagrams

- Use **Mermaid** fenced blocks (` ```mermaid `) for architectures, pipelines, and flowcharts — they render in Obsidian.
- Keep each diagram valid and Obsidian-compatible: simple node text, and avoid syntax Obsidian's renderer rejects (e.g. unquoted parentheses or brackets in node labels — wrap such labels in quotes). One diagram per distinct structure; don't add decorative ones.

## Document shape

The body progresses **Concept → Architecture → Implementation → Operational Considerations**: what it is and why it exists, how it's structured, how it's built, then how it's run, scaled, and maintained. Adapt the four stages to the domain — for a non-engineering subject, read them as definition → structure → practice → consequences. Headings are descriptive and unnumbered, starting at `##` (CONVENTIONS → Headings).

## Scoping: one note or a cluster

A reference note holds one subject, but a subject can be larger than one note. Decide the shape before outlining:

- **One note** — a single coherent concept whose depth fits one readable note.
- **A cluster** — a domain whose sub-topics are each note-worthy. Plan a small set of linked sub-notes, one concept each, plus a hub that indexes them, rather than one sprawling note. The hub is a MOC — build it with `vault-moc-create` (CONVENTIONS → MOCs).

Bias toward depth over size: if a section of the outline is itself note-worthy, split it into its own note and link it rather than bury it.

## Connecting the note

The note joins the vault's graph, not just a folder. Go beyond the CONVENTIONS minimum (one incoming link or a MOC entry):

- **Survey related notes first.** Before writing, find the existing notes for the subject's prerequisites, applications, and sibling concepts.
- **Link out** from the prose to those notes where each concept is naturally mentioned (CONVENTIONS → Links).
- **Link in.** Add a natural inline link from the most relevant existing notes back to this one, so it's reachable from where readers already are.

Bidirectionality is the goal (the `vault-wikilink-sprint` principle), done at authoring time instead of as later cleanup.

## Interactive workflow

These skills **never** emit the final note in one shot. They gate on the user:

1. **Research and plan.** Resolve the audience and domain (Audience and domain), ground the subject (Research and grounding), and survey the graph (Connecting the note), then produce the plan your skill defines — audience, scope/audit fields, the one-note-or-cluster decision (Scoping), exclusions, tech choices, planned connections, and a full hierarchical `##`/`###`/`####` Table of Contents following the document shape above. Output only the plan.
2. **Stop and ask.** End the planning turn with the skill's approval question and generate nothing further until the user answers.
3. **Execute on approval.** Write the note(s) into the vault per CONVENTIONS (frontmatter, links, footnote citations, connections), following the approved Table of Contents.
4. **Verify before reporting** (Verify before done).

## Verify before done

Before reporting the note complete, check and fix:

- Footnote integrity — run `check_footnotes.py --file` on each note written; every `[^n]` reference has a matching definition and vice versa (CONVENTIONS → Deterministic checks).
- Every `[[wikilink]]` resolves to a real note — no accidental broken links (`check_links.py`, CONVENTIONS → Links).
- Each Mermaid block is valid and renders in Obsidian (Diagrams).
- Every concrete claim that needs a source has one (Research and grounding).
- Frontmatter, headings, and math match CONVENTIONS (`validate_frontmatter.py`).
