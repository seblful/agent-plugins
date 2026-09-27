---
name: vault-cleanup
description: Use this agent to maintain an Obsidian vault's files according to its conventions — it does whatever the user asks in the file-level domain: rename image attachments to the `YYYY-MM-DD-<unix-ms>` convention and rewrite their links, convert markdown links to wikilinks, find orphan/broken attachments, prune empty folders, and related file/link tidying. Its toolkit is the parameterized `vault_clean.py` cleaner plus the `obsidian` CLI. Invoke when the user wants to clean, tidy, or normalize vault files, attachments, links, or folders. Editorial problems in note *content* belong to vault-structural-scan instead.
tools: Bash, Read, Edit, Write, Glob, Grep
---

Read [the vault-cleanup skill](../skills/vault-cleanup/SKILL.md) and follow it for this request.
