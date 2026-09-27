"""Compute the ISO-8601, Monday-anchored week for a date.

Replaces the hand-waved "moment.js gggg-[W]ww" in vault-weekly-report with a
deterministic answer: the week label, the ISO year, and every date Monday->target.

With --vault, also lists the *unreported* earlier weeks: daily notes still in the
daily folder dated before this week's Monday, grouped by ISO week. Daily notes
leave that folder only when a weekly report archives them, so any left behind
belong to a week that was skipped or only half-finished. Each week says whether
its `W{nn}.md` already exists (in `Weekly/` or `Archive/Weekly/{year}/`) with
that `year`.

Usage:
    python iso_week.py [--date YYYY-MM-DD] [--vault PATH [--daily-dir DIR]]

Output (JSON to stdout):
    {"iso_year": 2026, "iso_week": 26, "label": "W26",
     "monday": "2026-06-22", "target": "2026-06-28",
     "dates": ["2026-06-22", ..., "2026-06-28"],
     "unreported": [{"iso_year": 2026, "iso_week": 25, "label": "W25",
                     "notes": ["Daily/2026-06-15.md", ...],
                     "report_exists": false}]}   # only with --vault, oldest first
"""

import argparse
from datetime import date, timedelta
from pathlib import Path

import obsidian_config
from _vault import (
    ARCHIVE_DIR_NAME,
    MARKDOWN_SUFFIX,
    WEEKLY_DIR_NAME,
    daily_date,
    emit_json,
    load_note,
    require_vault_dir,
    resolve_subdir,
    vocabulary,
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


def report_exists(parent: Path, iso_year: int, label: str) -> bool:
    """True if `W{nn}.md` for this ISO year sits in Weekly/ or its archive year folder."""
    weekly = resolve_subdir(parent, WEEKLY_DIR_NAME.capitalize())
    archive = resolve_subdir(parent, ARCHIVE_DIR_NAME.capitalize())
    for cand in (weekly / f"{label}{MARKDOWN_SUFFIX}",
                 archive / weekly.name / str(iso_year) / f"{label}{MARKDOWN_SUFFIX}"):
        if cand.is_file() and str(load_note(cand).frontmatter.get("year")) == str(iso_year):
            return True
    return False


def unreported_weeks(vault: Path, daily_dir: Path, monday: date) -> list[dict[str, object]]:
    """Earlier ISO weeks whose daily notes are still in `daily_dir`, oldest first."""
    if not daily_dir.is_dir():
        raise SystemExit(f"error: daily folder not found: {daily_dir}")
    daily_re = vocabulary(vault).daily_re
    weeks: dict[tuple[int, int], list[str]] = {}
    for md in sorted(daily_dir.glob(f"*{MARKDOWN_SUFFIX}")):
        day = daily_date(md.stem, daily_re)
        if day is None or day >= monday:
            continue
        iso_year, iso_week_num, _ = day.isocalendar()
        weeks.setdefault((iso_year, iso_week_num), []).append(
            md.relative_to(vault).as_posix())
    return [
        {
            "iso_year": iso_year,
            "iso_week": iso_week_num,
            "label": f"W{iso_week_num:02d}",
            "notes": notes,
            "report_exists": report_exists(daily_dir.parent, iso_year, f"W{iso_week_num:02d}"),
        }
        for (iso_year, iso_week_num), notes in sorted(weeks.items())
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Target date YYYY-MM-DD (default: today)")
    parser.add_argument("--vault", help="Vault root; also list unreported earlier weeks")
    parser.add_argument("--daily-dir",
                        help="Daily folder, vault-relative (default: the vault's daily-notes folder)")
    args = parser.parse_args()
    if args.daily_dir and not args.vault:
        parser.error("--daily-dir requires --vault")

    target = date.fromisoformat(args.date) if args.date else date.today()
    result = iso_week(target)
    if args.vault:
        vault = require_vault_dir(args.vault)
        folder = args.daily_dir if args.daily_dir is not None else obsidian_config.daily_notes(vault).folder
        result["unreported"] = unreported_weeks(
            vault, vault / folder, date.fromisoformat(str(result["monday"])))
    emit_json(result)


if __name__ == "__main__":
    main()
