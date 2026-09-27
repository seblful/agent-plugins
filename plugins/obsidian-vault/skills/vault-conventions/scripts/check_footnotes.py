"""Check footnote integrity: every `[^n]` reference has a definition and vice versa.

Deterministic backing for AUTHORING -> Verify before done. Run on a single note
after authoring, or across the vault to audit knowledge notes.

Usage:
    python check_footnotes.py --file PATH
    python check_footnotes.py --vault PATH

Output (JSON to stdout):
    {"issues": [{"file", "undefined": [...], "unreferenced": [...]}]}
"""

import argparse
from pathlib import Path

from _vault import (FOOTNOTE_DEF_RE, FOOTNOTE_REF_RE, Note, emit_json,
                    iter_notes, load_note, require_vault_dir, scan_exclude)


def check_note(note: Note) -> dict[str, list[str]] | None:
    defs = set(FOOTNOTE_DEF_RE.findall(note.text))
    # Drop definition lines before scanning for references, so `[^n]:` doesn't
    # count as its own reference.
    body_without_defs = FOOTNOTE_DEF_RE.sub("", note.text)
    refs = set(FOOTNOTE_REF_RE.findall(body_without_defs))
    undefined = sorted(refs - defs)
    unreferenced = sorted(defs - refs)
    if undefined or unreferenced:
        return {"undefined": undefined, "unreferenced": unreferenced}
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Single note path")
    group.add_argument("--vault", help="Vault root to scan")
    args = parser.parse_args()

    if args.file:
        notes = [load_note(Path(args.file))]
    else:
        vault = require_vault_dir(args.vault)
        notes = iter_notes(vault, exclude=scan_exclude(vault))
    issues: list[dict[str, object]] = []
    for note in notes:
        result = check_note(note)
        if result:
            issues.append({"file": str(note.path), **result})
    emit_json({"issues": issues})


if __name__ == "__main__":
    main()
