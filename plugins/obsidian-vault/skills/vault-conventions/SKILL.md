---
name: vault-conventions
description: "Shared conventions, authoring standard, and deterministic scripts for every vault-* routine — frontmatter schema, link and heading rules, MOC detection, the folder/archive model, and stdlib-only Python checks. Use when a vault-* skill points here, or when the user asks what the vault's rules are. Not for changing a vault: it is a reference, not a routine, and changes nothing."
---

# Vault Conventions

Reference skill; the `vault-*` routines read it before acting. Install it next to them — they reach its files as the sibling directory `../vault-conventions/`.

| File | Holds |
| --- | --- |
| [CONVENTIONS.md](CONVENTIONS.md) | Vault mechanics every routine obeys: discovering the vault's own conventions, the before-changing-anything gate, CLI access, frontmatter, links, headings, MOCs, folders and archive, and the script table. |
| [AUTHORING.md](AUTHORING.md) | The standard for deep reference notes: audience, voice, technical standards, diagrams, document shape, plan-then-write. |
| [scripts/](scripts) | Stdlib-only Python 3.12+ checks that emit JSON. Run as `python "<vault-conventions>/scripts/<name>.py"`, where `<vault-conventions>` is the real path of this directory — the sibling `../vault-conventions/` of every routine. |

**Answering a question about the rules:** read `CONVENTIONS.md` and cite the section.
