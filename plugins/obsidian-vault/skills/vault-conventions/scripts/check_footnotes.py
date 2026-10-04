"""Check footnote integrity: every `[^n]` reference has a definition and vice versa.

Deterministic backing for AUTHORING -> Verify before done. Run on a single note
after authoring, or across the vault to audit knowledge notes. Footnote markers
inside code are ignored; notes that are not valid UTF-8 are skipped and listed
under `unreadable`.

Usage:
    python check_footnotes.py --file PATH
    python check_footnotes.py --vault PATH

Output (JSON to stdout):
    {"issues": [{"file", "undefined": [...], "unreferenced": [...]}],
     "unreadable": [{"file", "reason"}]}
"""

import argparse
from pathlib import Path

from _vault import (
    FOOTNOTE_DEF_RE,
    FOOTNOTE_REF_RE,
    Note,
    NoteDecodeError,
    emit_json,
    iter_notes,
    load_note,
    mask_code,
    require_vault_dir,
    scan_exclude,
    unreadable_entry,
)


def check_note(note: Note) -> dict[str, list[str]] | None:
    text = mask_code(note.text)
    defs = set(FOOTNOTE_DEF_RE.findall(text))
    # Drop definition lines before scanning for references, so `[^n]:` doesn't
    # count as its own reference.
    refs = set(FOOTNOTE_REF_RE.findall(FOOTNOTE_DEF_RE.sub("", text)))
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

    unreadable: list[dict[str, str]] = []
    if args.file:
        path = Path(args.file)
        if not path.is_file():
            raise SystemExit(f"error: note not found: {path.resolve()}")
        try:
            notes = [load_note(path)]
        except NoteDecodeError as exc:
            notes = []
            unreadable.append(unreadable_entry(exc))
    else:
        vault = require_vault_dir(args.vault)
        notes = iter_notes(vault, exclude=scan_exclude(vault), unreadable=unreadable)
    issues: list[dict[str, object]] = []
    for note in notes:
        result = check_note(note)
        if result:
            issues.append({"file": str(note.path), **result})
    emit_json({"issues": issues, "unreadable": unreadable})


if __name__ == "__main__":
    main()
