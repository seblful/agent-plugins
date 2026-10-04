"""obsidian_config, validate_frontmatter, check_footnotes: their CLI contracts."""

import check_footnotes
import obsidian_config
import validate_frontmatter
from _vault import load_note

# -- obsidian_config ----------------------------------------------------------------


def test_config_missing_vault_fails_loudly(tmp_path, run_main):
    code, data, err = run_main(obsidian_config, "--vault", str(tmp_path / "nope"))
    assert code == 1
    assert data is None
    assert "vault root not found" in err


def test_config_warns_when_config_dir_is_missing(tmp_path, run_main):
    code, data, err = run_main(obsidian_config, "--vault", str(tmp_path))
    assert code == 0
    assert "warning" in err and ".obsidian" in err
    assert data["daily_notes"]["source"] == "fallback"


def test_config_reads_settings(vault, config, run_main):
    config(
        "app.json", {"attachmentFolderPath": "./assets", "newLinkFormat": "relative"}
    )
    config("daily-notes.json", {"folder": "/Daily/", "format": "YYYY.MM.DD"})
    config("plugins/templater-obsidian/data.json", {"templates_folder": "tpl"})
    config("templates.json", {"folder": "Tpl"})
    code, data, err = run_main(obsidian_config, "--vault", str(vault))
    assert code == 0
    assert err == ""
    assert data["attachment_layout"]["kind"] == "per-note"
    assert data["attachment_layout"]["folder"] == "assets"
    assert data["link_format"]["new_link_format"] == "relative"
    assert data["daily_notes"]["folder"] == "Daily"
    assert data["template_folders"] == ["Tpl"]


def test_attachment_layout_variants(vault, config):
    for raw, kind, folder in [
        ("/", "root", None),
        ("./", "same-folder", None),
        ("Files/", "central", "Files"),
        ("", "per-note", "attachments"),
    ]:
        config("app.json", {"attachmentFolderPath": raw})
        layout = obsidian_config.attachment_layout(vault)
        assert (layout.kind, layout.folder) == (kind, folder)


def test_parse_layout_and_dest_dir(vault):
    note = vault / "a" / "n.md"
    assert obsidian_config.parse_layout("root").dest_dir(note, vault) == vault
    assert (
        obsidian_config.parse_layout("same-folder").dest_dir(note, vault) == vault / "a"
    )
    assert (
        obsidian_config.parse_layout("central:F").dest_dir(note, vault) == vault / "F"
    )
    assert obsidian_config.parse_layout("per-note:att").dest_dir(note, vault) == (
        vault / "a" / "att"
    )
    try:
        obsidian_config.parse_layout("bogus")
    except ValueError as exc:
        assert "bad layout" in str(exc)
    else:
        raise AssertionError("bogus layout accepted")


def test_config_tolerates_corrupt_json(vault):
    (vault / ".obsidian/app.json").write_text("{not json", encoding="utf-8")
    assert obsidian_config.link_format(vault).source == "fallback"


# -- validate_frontmatter -------------------------------------------------------------


def run_validate(vault, run_main, *extra):
    code, data, _ = run_main(validate_frontmatter, "--vault", str(vault), *extra)
    assert code == 0
    return data


def test_validate_accepts_nested_tags_and_bom(vault, write, run_main):
    write(
        "A.md",
        "---\ntags:\n  - project/alpha\ncreated: 2026-01-01\nmodified: 2026-01-02\n---\n",
    )
    write(
        "B.md",
        b"\xef\xbb\xbf---\r\ntags: [ok]\r\ncreated: 2026-01-01\r\nmodified: 2026-01-01\r\n---\r\n",
    )
    assert run_validate(vault, run_main)["issues"] == []


def test_validate_flags_schema_problems_and_unreadable(vault, write, run_main):
    write("A.md", "---\ntags: Bad\ncreated: yesterday\nproject: Alpha\n---\n")
    write("Weekly/W01.md", "---\nyear: 2026\n---\n")
    write("Bad.md", "Привет".encode("cp1251"))
    write("Archive/Old.md", "no frontmatter at all")
    data = run_validate(vault, run_main)
    problems = {
        (i["file"].replace("\\", "/").rsplit("/", 1)[-1], i["problem"])
        for i in data["issues"]
    }
    assert ("A.md", "`tags` should be a YAML list") in problems
    assert ("A.md", "`created` is not ISO date: 'yesterday'") in problems
    assert ("A.md", "`project` value not a wikilink: 'Alpha'") in problems
    assert ("A.md", "missing required field `modified`") in problems
    assert ("W01.md", "missing required field `harvested`") in problems
    assert not any(f == "Old.md" for f, _ in problems)
    assert len(data["unreadable"]) == 1


def test_validate_field_overrides(vault, write, run_main):
    write(
        "A.md",
        "---\ntags: [x]\ncreated: 2026-01-01\nmodified: 2026-01-01\nwhen: soon\n---\n",
    )
    data = run_validate(vault, run_main, "--date-fields", "when", "--link-fields", "x")
    assert [i["problem"] for i in data["issues"]] == ["`when` is not ISO date: 'soon'"]


# -- check_footnotes -------------------------------------------------------------------


def test_footnotes_single_file(write):
    note = load_note(
        write("A.md", "Claim.[^1] Other.[^2]\n\n[^1]: https://a\n[^3]: https://c\n")
    )
    assert check_footnotes.check_note(note) == {
        "undefined": ["2"],
        "unreferenced": ["3"],
    }


def test_footnotes_ignore_code(write):
    note = load_note(write("A.md", "Fine.[^1]\n```\nx[^9]\n```\n\n[^1]: https://a\n"))
    assert check_footnotes.check_note(note) is None


def test_footnotes_cli_file_and_vault(vault, write, run_main):
    path = write("A.md", "Claim.[^1]\n")
    write("Bad.md", "Привет".encode("cp1251"))
    code, data, _ = run_main(check_footnotes, "--file", str(path))
    assert code == 0
    assert data["issues"][0]["undefined"] == ["1"]
    code, data, _ = run_main(check_footnotes, "--vault", str(vault))
    assert code == 0
    assert len(data["issues"]) == 1
    assert len(data["unreadable"]) == 1


def test_footnotes_cli_missing_file_fails_loudly(tmp_path, run_main):
    code, _, err = run_main(check_footnotes, "--file", str(tmp_path / "nope.md"))
    assert code == 1
    assert "not found" in err
