"""Weekly/Archive location, the ISO week, unreported weeks, and the year sweep."""

from datetime import date

import iso_week
import pytest
import year_sweep
from _vault import archive_dir, weekly_dir

WEEKLY = (
    "---\nyear: {year}\nweek: {week}\ntags:\n  - weekly-report\nharvested: {h}\n---\n"
)


def weekly(year: int, week: int, harvested: bool = True) -> str:
    return WEEKLY.format(year=year, week=week, h=str(harvested).lower())


# -- folder location ----------------------------------------------------------


def test_weekly_and_archive_live_in_vault_when_dailies_are_at_root(vault):
    assert weekly_dir(vault) == vault / "Weekly"
    assert archive_dir(vault) == vault / "Archive"


def test_weekly_is_sibling_of_nested_daily_folder(vault, config):
    config("daily-notes.json", {"folder": "Journal/Daily"})
    assert weekly_dir(vault) == vault / "Journal" / "Weekly"
    assert archive_dir(vault) == vault / "Journal" / "Archive"


def test_existing_root_folder_is_reused_rather_than_forked(vault, config):
    config("daily-notes.json", {"folder": "Journal/Daily"})
    (vault / "weekly").mkdir()
    assert weekly_dir(vault) == vault / "weekly"


def test_daily_folder_override_and_case_insensitive_match(vault):
    (vault / "Logs" / "WEEKLY").mkdir(parents=True)
    assert weekly_dir(vault, daily_folder="Logs/Daily") == vault / "Logs" / "WEEKLY"


# -- iso week -------------------------------------------------------------------


def test_iso_week_across_the_year_boundary():
    result = iso_week.iso_week(date(2027, 1, 1))
    assert (result["iso_year"], result["iso_week"], result["label"]) == (
        2026,
        53,
        "W53",
    )
    assert result["monday"] == "2026-12-28"
    assert result["dates"][-1] == "2027-01-01"
    assert len(result["dates"]) == 5


def test_report_exists_checks_weekly_and_archive_by_year(vault, write):
    write("Weekly/W39.md", weekly(2026, 39))
    write("Archive/Weekly/2025/W39.md", weekly(2025, 39))
    weekly_path, archive_path = vault / "Weekly", vault / "Archive"
    assert iso_week.report_exists(weekly_path, archive_path, 2026, "W39")
    assert iso_week.report_exists(weekly_path, archive_path, 2025, "W39")
    assert not iso_week.report_exists(weekly_path, archive_path, 2024, "W39")
    assert not iso_week.report_exists(weekly_path, archive_path, 2026, "W40")


def test_unreported_weeks_with_root_daily_folder_finds_existing_report(vault, write):
    write("2026-09-21.md", "")  # W39
    write("2026-09-14.md", "")  # W38
    write("2026-09-28.md", "")  # current week, not "earlier"
    write("Weekly/W39.md", weekly(2026, 39))
    weeks = iso_week.unreported_weeks(vault, "", date(2026, 9, 28))
    assert [(w["label"], w["report_exists"]) for w in weeks] == [
        ("W38", False),
        ("W39", True),
    ]
    assert weeks[1]["notes"] == ["2026-09-21.md"]


def test_unreported_weeks_spanning_iso_year_boundary(vault, write):
    write("Daily/2026-12-31.md", "")  # ISO 2026-W53
    write("Daily/2025-12-29.md", "")  # ISO 2026-W01
    weeks = iso_week.unreported_weeks(vault, "Daily", date(2027, 1, 4))
    assert [(w["iso_year"], w["label"]) for w in weeks] == [
        (2026, "W01"),
        (2026, "W53"),
    ]


def test_unreported_weeks_missing_daily_folder_fails_loudly(vault):
    with pytest.raises(SystemExit):
        iso_week.unreported_weeks(vault, "Nope", date(2026, 1, 5))


def test_iso_week_main_reports_locations(vault, write, run_main):
    write("2026-09-21.md", "")
    write("Weekly/W39.md", weekly(2026, 39))
    code, data, _ = run_main(iso_week, "--date", "2026-10-04", "--vault", str(vault))
    assert code == 0
    assert data["label"] == "W40"
    assert data["weekly_dir"] == "Weekly"
    assert data["archive_dir"] == "Archive"
    assert data["unreported"][0]["report_exists"] is True


def test_iso_week_main_without_vault(run_main):
    code, data, _ = run_main(iso_week, "--date", "2026-06-28")
    assert code == 0
    assert data["label"] == "W26"
    assert "unreported" not in data


def test_iso_week_daily_dir_requires_vault(run_main):
    code, _, _ = run_main(iso_week, "--daily-dir", "Daily")
    assert code == 2


# -- year sweep -----------------------------------------------------------------


def test_plan_sweep_holds_unharvested_reports(vault, write):
    write("Weekly/W52.md", weekly(2025, 52, harvested=False))
    write("Weekly/W51.md", weekly(2025, 51, harvested=True))
    write("Weekly/W01.md", weekly(2026, 1, harvested=False))
    write("Weekly/notes.md", "no year here")
    moves, held = year_sweep.plan_sweep(vault / "Weekly", vault / "Archive", 2026)
    assert [m["to"] for m in moves] == [str(vault / "Archive/Weekly/2025/W51.md")]
    assert [(h["from"], h["reason"]) for h in held] == [
        (str(vault / "Weekly/W52.md"), "not harvested")
    ]


def test_plan_sweep_missing_folder_is_empty(vault):
    assert year_sweep.plan_sweep(vault / "Weekly", vault / "Archive", 2026) == ([], [])


def test_sweep_uses_iso_year_so_w53_written_on_new_years_day_stays(
    vault, write, run_main, monkeypatch
):
    write("Weekly/W53.md", weekly(2026, 53))
    monkeypatch.setattr(year_sweep, "today", lambda: date(2027, 1, 1))  # ISO 2026
    code, data, _ = run_main(year_sweep, "--vault", str(vault), "--apply")
    assert code == 0
    assert data["moves"] == []
    assert (vault / "Weekly/W53.md").exists()


def test_sweep_apply_moves_and_skips_existing_destination(
    vault, write, run_main, monkeypatch
):
    write("Weekly/W10.md", weekly(2025, 10))
    write("Weekly/W11.md", weekly(2025, 11))
    write("Archive/Weekly/2025/W11.md", "already archived")
    monkeypatch.setattr(year_sweep, "today", lambda: date(2026, 6, 1))
    code, data, _ = run_main(year_sweep, "--vault", str(vault), "--apply")
    assert code == 0
    assert (vault / "Archive/Weekly/2025/W10.md").exists()
    assert not (vault / "Weekly/W10.md").exists()
    assert [s["reason"] for s in data["skipped"]] == ["destination exists"]
    assert data["held"] == []


def test_sweep_plan_only_changes_nothing(vault, write, run_main, monkeypatch):
    write("Weekly/W10.md", weekly(2025, 10))
    monkeypatch.setattr(year_sweep, "today", lambda: date(2026, 6, 1))
    code, data, _ = run_main(year_sweep, "--vault", str(vault))
    assert code == 0
    assert data["applied"] is False
    assert len(data["moves"]) == 1
    assert (vault / "Weekly/W10.md").exists()


def test_sweep_follows_nested_daily_folder(vault, write, config, run_main, monkeypatch):
    config("daily-notes.json", {"folder": "Journal/Daily"})
    write("Journal/Weekly/W10.md", weekly(2025, 10))
    monkeypatch.setattr(year_sweep, "today", lambda: date(2026, 6, 1))
    code, _, _ = run_main(year_sweep, "--vault", str(vault), "--apply")
    assert code == 0
    assert (vault / "Journal/Archive/Weekly/2025/W10.md").exists()
