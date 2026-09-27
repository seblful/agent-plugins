"""Compute the ISO-8601, Monday-anchored week for a date.

Replaces the hand-waved "moment.js gggg-[W]ww" in vault-weekly-report with a
deterministic answer: the week label, the ISO year, and every date Monday->target.

Usage:
    python iso_week.py [--date YYYY-MM-DD]

Output (JSON to stdout):
    {"iso_year": 2026, "iso_week": 26, "label": "W26",
     "monday": "2026-06-22", "target": "2026-06-28",
     "dates": ["2026-06-22", ..., "2026-06-28"]}
"""

import argparse
from datetime import date, timedelta

from _vault import emit_json


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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Target date YYYY-MM-DD (default: today)")
    args = parser.parse_args()
    target = date.fromisoformat(args.date) if args.date else date.today()
    emit_json(iso_week(target))


if __name__ == "__main__":
    main()
