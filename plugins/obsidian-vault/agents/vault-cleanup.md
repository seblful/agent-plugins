---
name: vault-cleanup
description: "Maintains an Obsidian vault's files by its conventions — renames image attachments to the `YYYY-MM-DD-<unix-ms>` convention and rewrites their links, converts markdown links to wikilinks, finds orphan or broken attachments, prunes empty folders, and related file and link tidying, with the `vault_clean.py` cleaner and the `obsidian` CLI. Use when the user wants vault files, attachments, links, or folders cleaned, tidied, or normalized. Not for editorial problems in note content (vault-structural-scan)."
tools: Bash, Read, Edit, Write, Glob, Grep
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/vault-cleanup/SKILL.md` and follow it for this request.
