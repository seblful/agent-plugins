"""Validate note frontmatter against the conventions in CONVENTIONS.md.

Deterministic backing for vault-structural-scan and vault-daily-format. Reports
schema violations per note; it flags, it does not fix — the calling routine
applies fixes against the vault so the live index stays correct. Archive/ is
skipped (archived frontmatter is frozen).

Note type (general/daily/weekly) is resolved from the vault's own daily-note
format via `_vault.vocabulary`, so a vault using a non-default daily filename is
still classified correctly. The date- and link-valued field sets default to the
CONVENTIONS schema but can be overridden for a vault with a different one.

Checks: required fields present per note type; dates ISO `YYYY-MM-DD[THH:MM:SS]`;
`tags` a lowercase kebab-case list; link-valued fields carry `[[wikilinks]]`.

Usage:
    python validate_frontmatter.py --vault PATH
        [--date-fields created,modified,reviewed] [--link-fields project,area,related]

Output (JSON to stdout): {"issues": [{"file", "type", "problem"}]}
"""

import argparse
from collections.abc import Iterable

from _vault import (ISO_DATE_RE, KEBAB_RE, Note, add_vault_arg, classify,
                    emit_json, iter_notes, require_vault_dir, scan_exclude,
                    vocabulary)

REQUIRED: dict[str, set[str]] = {
    "general": {"tags", "created", "modified"},
    "daily": {"tags", "created", "modified"},
    "weekly": {"year", "week", "tags", "harvested"},
}
DEFAULT_DATE_FIELDS = frozenset({"created", "modified", "reviewed"})
DEFAULT_LINK_FIELDS = frozenset({"project", "area", "related"})


def check_note(note: Note, note_type: str, date_fields: Iterable[str],
               link_fields: Iterable[str]) -> list[str]:
    if note_type == "archived":
        return []
    fm = note.frontmatter
    problems: list[str] = []

    for required in REQUIRED.get(note_type, REQUIRED["general"]):
        value = fm.get(required)
        if value is None or value == "" or value == []:
            problems.append(f"missing required field `{required}`")

    for field_name in date_fields:
        value = fm.get(field_name)
        if isinstance(value, str) and not ISO_DATE_RE.match(value):
            problems.append(f"`{field_name}` is not ISO date: {value!r}")

    tags = fm.get("tags")
    if isinstance(tags, list):
        bad = [t for t in tags if isinstance(t, str) and not KEBAB_RE.match(t)]
        if bad:
            problems.append(f"tags not lowercase-kebab: {bad}")
    elif isinstance(tags, str) and tags:
        problems.append("`tags` should be a YAML list")

    for field_name in link_fields:
        value = fm.get(field_name)
        values = value if isinstance(value, list) else [value] if value else []
        for v in values:
            if isinstance(v, str) and "[[" not in v:
                problems.append(f"`{field_name}` value not a wikilink: {v!r}")

    return problems


def _csv(raw: str) -> set[str]:
    return {item.strip() for item in raw.split(",") if item.strip()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_vault_arg(parser)
    parser.add_argument("--date-fields", default="",
                        help="Override date-valued fields (comma-separated)")
    parser.add_argument("--link-fields", default="",
                        help="Override wikilink-valued fields (comma-separated)")
    args = parser.parse_args()

    vault = require_vault_dir(args.vault)
    vocab = vocabulary(vault)
    date_fields = _csv(args.date_fields) or DEFAULT_DATE_FIELDS
    link_fields = _csv(args.link_fields) or DEFAULT_LINK_FIELDS

    issues: list[dict[str, str]] = []
    for note in iter_notes(vault, include_archive=False, vocab=vocab,
                           exclude=scan_exclude(vault)):
        note_type = classify(note.path, vault, vocab)
        for problem in check_note(note, note_type, date_fields, link_fields):
            issues.append({"file": str(note.path), "type": note_type, "problem": problem})
    emit_json({"issues": issues})


if __name__ == "__main__":
    main()
