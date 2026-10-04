"""Plan (or apply) the self-healing year sweep on the Weekly/ folder.

Any weekly report whose `year` is earlier than the current ISO year is moved to
`Archive/Weekly/{year}/`, mirroring the live path. "Current" is the ISO year of
today, the same calendar `iso_week.py` stamps into `year`, so a W53 report
written on 1 January is not swept out the moment it is saved.

A report still marked `harvested: false` is **held**, never archived: archived
content is frozen and vault-weekly-harvest only reads Weekly/, so sweeping it
would lose its knowledge for good. Reports a plan by default; pass --apply to
perform the moves. This only moves files, it never edits their contents.

Weekly/ and Archive/ are located as siblings of the vault's daily-notes folder
(inside the vault even when daily notes live at the root) and matched
case-insensitively, so a vault that capitalizes them differently is swept into
its existing archive rather than a new one. A move whose destination already
exists is skipped and reported, never overwritten.

Usage:
    python year_sweep.py --vault PATH [--folder Weekly] [--apply]

Output (JSON to stdout):
    {applied, moves: [{from, to, year}], held: [{from, year, reason}],
     skipped?: [{from, to, year, reason}]}
"""

import argparse
import shutil
from pathlib import Path

from _vault import (
    NoteDecodeError,
    add_vault_arg,
    archive_dir,
    emit_json,
    load_note,
    require_vault_dir,
    resolve_subdir,
    today,
    weekly_dir,
)


def plan_sweep(
    weekly: Path, archive_base: Path, current_year: int
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """(moves, held): past-year reports to archive, and those held as unharvested."""
    moves: list[dict[str, object]] = []
    held: list[dict[str, object]] = []
    if not weekly.is_dir():
        return moves, held
    for md in sorted(weekly.glob("*.md")):
        try:
            fm = load_note(md).frontmatter
        except NoteDecodeError:
            continue
        try:
            year = int(str(fm.get("year")))
        except ValueError:
            continue
        if year >= current_year:
            continue
        if fm.get("harvested") is False:
            held.append({"from": str(md), "year": year, "reason": "not harvested"})
            continue
        dest = archive_base / weekly.name / str(year) / md.name
        moves.append({"from": str(md), "to": str(dest), "year": year})
    return moves, held


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
            shutil.move(str(move["from"]), dest)
        except OSError as exc:
            skipped.append({**move, "reason": str(exc)})
    return skipped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_vault_arg(parser)
    parser.add_argument(
        "--folder",
        help="Weekly folder, vault-relative (default: the sibling of the daily folder)",
    )
    parser.add_argument("--apply", action="store_true", help="Perform the moves")
    args = parser.parse_args()

    vault = require_vault_dir(args.vault)
    weekly = resolve_subdir(vault, args.folder) if args.folder else weekly_dir(vault)
    moves, held = plan_sweep(weekly, archive_dir(vault), today().isocalendar().year)

    result: dict[str, object] = {"applied": args.apply, "moves": moves, "held": held}
    if args.apply:
        skipped = apply_moves(moves)
        if skipped:
            result["skipped"] = skipped
    emit_json(result)


if __name__ == "__main__":
    main()
