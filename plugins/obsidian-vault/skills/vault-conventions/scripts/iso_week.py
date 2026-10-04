"""Compute the ISO-8601, Monday-anchored week for a date.

Replaces the hand-waved "moment.js gggg-[W]ww" in vault-weekly-report with a
deterministic answer: the week label, the ISO year, and every date Monday->target.

With --vault, also lists the *unreported* earlier weeks: daily notes still in the
daily folder dated before this week's Monday, grouped by ISO week. Daily notes
leave that folder only when a weekly report archives them, so any left behind
belong to a week that was skipped or only half-finished. Each week says whether
its `W{nn}.md` already exists (in Weekly/ or Archive/Weekly/{year}/) with that
`year`. Weekly/ and Archive/ are siblings of the daily folder and always inside
the vault (with daily notes at the vault root they are `<vault>/Weekly` and
`<vault>/Archive`); their vault-relative paths are reported too.

Usage:
    python iso_week.py [--date YYYY-MM-DD] [--vault PATH [--daily-dir DIR]]

Output (JSON to stdout):
    {"iso_year": 2026, "iso_week": 26, "label": "W26",
     "monday": "2026-06-22", "target": "2026-06-28",
     "dates": ["2026-06-22", ..., "2026-06-28"],
     "weekly_dir": "Weekly", "archive_dir": "Archive",      # only with --vault
     "unreported": [{"iso_year": 2026, "iso_week": 25, "label": "W25",
                     "notes": ["Daily/2026-06-15.md", ...],
                     "report_exists": false}]}   # only with --vault, oldest first
"""

import argparse
from datetime import date, timedelta
from pathlib import Path

import obsidian_config
from _vault import (
    MARKDOWN_SUFFIX,
    NoteDecodeError,
    archive_dir,
    daily_date,
    emit_json,
    load_note,
    require_vault_dir,
    today,
    vocabulary,
    weekly_dir,
)


def iso_week(target: date) -> dict[str, object]:
    iso_year, iso_week_num, iso_weekday = target.isocalendar()
    monday = target - timedelta(days=iso_weekday - 1)
    dates = [monday + timedelta(days=i) for i in range(iso_weekday)]
    return {
        "iso_year": iso_year,
        "iso_week": iso_week_num,
        "label": f"W{iso_week_num:02d}",
        "monday": monday.isoformat(),
        "target": target.isoformat(),
        "dates": [d.isoformat() for d in dates],
    }


def report_exists(weekly: Path, archive: Path, iso_year: int, label: str) -> bool:
    """True if `W{nn}.md` for this ISO year sits in Weekly/ or its archive year folder."""
    name = f"{label}{MARKDOWN_SUFFIX}"
    for cand in (weekly / name, archive / weekly.name / str(iso_year) / name):
        if not cand.is_file():
            continue
        try:
            year = load_note(cand).frontmatter.get("year")
        except NoteDecodeError:
            continue
        if str(year) == str(iso_year):
            return True
    return False


def unreported_weeks(
    vault: Path, daily_folder: str, monday: date
) -> list[dict[str, object]]:
    """Earlier ISO weeks whose daily notes are still in the daily folder, oldest first.

    `daily_folder` is vault-relative; "" means the vault root.
    """
    daily = vault / daily_folder.strip("/")
    if not daily.is_dir():
        raise SystemExit(f"error: daily folder not found: {daily}")
    weekly, archive = weekly_dir(vault, daily_folder), archive_dir(vault, daily_folder)
    daily_re = vocabulary(vault).daily_re
    weeks: dict[tuple[int, int], list[str]] = {}
    for md in sorted(daily.glob(f"*{MARKDOWN_SUFFIX}")):
        day = daily_date(md.stem, daily_re)
        if day is None or day >= monday:
            continue
        iso_year, iso_week_num, _ = day.isocalendar()
        weeks.setdefault((iso_year, iso_week_num), []).append(
            md.relative_to(vault).as_posix()
        )
    return [
        {
            "iso_year": iso_year,
            "iso_week": iso_week_num,
            "label": f"W{iso_week_num:02d}",
            "notes": notes,
            "report_exists": report_exists(
                weekly, archive, iso_year, f"W{iso_week_num:02d}"
            ),
        }
        for (iso_year, iso_week_num), notes in sorted(weeks.items())
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Target date YYYY-MM-DD (default: today)")
    parser.add_argument(
        "--vault", help="Vault root; also list unreported earlier weeks"
    )
    parser.add_argument(
        "--daily-dir",
        help="Daily folder, vault-relative (default: the vault's daily-notes folder)",
    )
    args = parser.parse_args()
    if args.daily_dir and not args.vault:
        parser.error("--daily-dir requires --vault")

    target = date.fromisoformat(args.date) if args.date else today()
    result = iso_week(target)
    if args.vault:
        vault = require_vault_dir(args.vault)
        folder = (
            args.daily_dir
            if args.daily_dir is not None
            else obsidian_config.daily_notes(vault).folder
        )
        result["weekly_dir"] = weekly_dir(vault, folder).relative_to(vault).as_posix()
        result["archive_dir"] = archive_dir(vault, folder).relative_to(vault).as_posix()
        result["unreported"] = unreported_weeks(
            vault, folder, date.fromisoformat(str(result["monday"]))
        )
    emit_json(result)


if __name__ == "__main__":
    main()
