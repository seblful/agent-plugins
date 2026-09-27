"""Plan (or apply) the self-healing year sweep on the Weekly/ folder.

Any weekly report whose `year` is earlier than the current year is moved to
`Archive/Weekly/{year}/`, mirroring the live path. Reports a plan by default;
pass --apply to perform the moves. Archived content is frozen — this only moves
files, it never edits their contents.

The Weekly/ and Archive/ folders are matched case-insensitively, so a vault that
capitalizes them differently is swept into its existing archive rather than a new
one. A move whose destination already exists is skipped and reported, never
overwritten.

Usage:
    python year_sweep.py --vault PATH [--folder Weekly] [--apply]

Output (JSON to stdout): {applied, moves: [{from, to, year}], skipped?: [...]}
"""

import argparse
import shutil
from datetime import date
from pathlib import Path

from _vault import add_vault_arg, emit_json, load_note, require_vault_dir, resolve_subdir


def plan_sweep(weekly_dir: Path, archive_base: Path,
               current_year: int) -> list[dict[str, object]]:
    if not weekly_dir.is_dir():
        return []
    moves: list[dict[str, object]] = []
    for md in sorted(weekly_dir.glob("*.md")):
        note = load_note(md)
        raw_year = note.frontmatter.get("year")
        try:
            year = int(str(raw_year))
        except (TypeError, ValueError):
            continue
        if year < current_year:
            dest = archive_base / weekly_dir.name / str(year) / md.name
            moves.append({"from": str(md), "to": str(dest), "year": year})
    return moves


def apply_moves(moves: list[dict[str, object]]) -> list[dict[str, object]]:
    """Perform the moves; return any skipped because the destination existed."""
    skipped: list[dict[str, object]] = []
    for move in moves:
        dest = Path(str(move["to"]))
        if dest.exists():
            skipped.append({**move, "reason": "destination exists"})
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(move["from"], dest)
        except OSError as exc:
            skipped.append({**move, "reason": str(exc)})
    return skipped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_vault_arg(parser)
    parser.add_argument("--folder", default="Weekly", help="Weekly folder name")
    parser.add_argument("--apply", action="store_true", help="Perform the moves")
    args = parser.parse_args()

    vault = require_vault_dir(args.vault)
    weekly_dir = resolve_subdir(vault, args.folder)
    archive_base = resolve_subdir(vault, "Archive")
    moves = plan_sweep(weekly_dir, archive_base, date.today().year)

    result: dict[str, object] = {"applied": args.apply, "moves": moves}
    if args.apply:
        skipped = apply_moves(moves)
        if skipped:
            result["skipped"] = skipped
    emit_json(result)


if __name__ == "__main__":
    main()
