"""_vault: text i/o, frontmatter parsing, daily-name vocabulary, code masking."""

import codecs
from datetime import date

import _vault
import pytest
from _vault import (
    KEBAB_RE,
    NoteDecodeError,
    _daily_name_regex,
    daily_date,
    iter_notes,
    load_note,
    mask_code,
    parse_frontmatter,
    read_note_text,
    write_note_text,
)

# -- text i/o -----------------------------------------------------------------


def test_read_strips_and_remembers_bom_and_keeps_crlf(write):
    path = write("a.md", codecs.BOM_UTF8 + b"---\r\ntags: [x]\r\n---\r\nbody\r\n")
    content = read_note_text(path)
    assert content.bom is True
    assert content.text == "---\r\ntags: [x]\r\n---\r\nbody\r\n"


def test_read_rejects_non_utf8(write):
    path = write("ru.md", "Привет".encode("cp1251"))
    with pytest.raises(NoteDecodeError) as exc:
        read_note_text(path)
    assert exc.value.path == path
    assert "UTF-8" in exc.value.reason


def test_write_round_trips_line_endings_and_bom(write):
    original = codecs.BOM_UTF8 + "a\r\nб\nc".encode()
    path = write("a.md", original)
    content = read_note_text(path)
    write_note_text(path, content.text, bom=content.bom)
    assert path.read_bytes() == original


def test_write_without_bom_keeps_lf(tmp_path):
    path = tmp_path / "n.md"
    write_note_text(path, "x\ny\n")
    assert path.read_bytes() == b"x\ny\n"


def test_iter_notes_skips_and_reports_undecodable(vault, write):
    write("ok.md", "fine")
    write("bad.md", "Привет".encode("cp1251"))
    unreadable: list[dict[str, str]] = []
    notes = iter_notes(vault, unreadable=unreadable)
    assert [n.stem for n in notes] == ["ok"]
    assert len(unreadable) == 1
    assert unreadable[0]["file"].endswith("bad.md")


def test_load_note_keeps_bom_flag(write):
    note = load_note(write("b.md", codecs.BOM_UTF8 + b"---\ntags: [a]\n---\n"))
    assert note.bom is True
    assert note.frontmatter == {"tags": ["a"]}


# -- frontmatter ---------------------------------------------------------------


def test_parse_frontmatter_block_and_flow_lists():
    fm, body = parse_frontmatter(
        "---\ntags:\n  - a\n  - \"b-c\"\naliases: [X, 'Y']\ndone: true\n"
        "created: 2026-01-01\n---\nbody line\n"
    )
    assert fm == {
        "tags": ["a", "b-c"],
        "aliases": ["X", "Y"],
        "done": True,
        "created": "2026-01-01",
    }
    assert body == "body line"


def test_parse_frontmatter_bom_and_crlf():
    fm, body = parse_frontmatter("﻿---\r\ntags:\r\n  - ok\r\nweek: 3\r\n---\r\nb\r\n")
    assert fm == {"tags": ["ok"], "week": "3"}
    assert body == "b"


def test_parse_frontmatter_link_value_is_not_a_flow_list():
    fm, _ = parse_frontmatter('---\nrelated: "[[Note]]"\nproject: [[P]]\n---\n')
    assert fm == {"related": "[[Note]]", "project": "[[P]]"}


@pytest.mark.parametrize(
    "text",
    ["no frontmatter", "---\nunterminated: yes\n", "", "--- \nnot: closed"],
)
def test_parse_frontmatter_absent_or_unterminated(text):
    fm, body = parse_frontmatter(text)
    assert fm == {}
    assert body == text


def test_parse_frontmatter_empty_flow_list_and_false():
    fm, _ = parse_frontmatter("---\ntags: []\nharvested: False\n---\n")
    assert fm == {"tags": [], "harvested": False}


@pytest.mark.parametrize("tag", ["deep-work", "area/deep-work", "a/b/c-1", "x2"])
def test_kebab_accepts_nested_tags(tag):
    assert KEBAB_RE.match(tag)


@pytest.mark.parametrize("tag", ["DeepWork", "a//b", "/a", "a/", "a_b", "-a"])
def test_kebab_rejects_bad_tags(tag):
    assert not KEBAB_RE.match(tag)


# -- daily-note vocabulary ------------------------------------------------------


@pytest.mark.parametrize(
    ("fmt", "stem", "expected"),
    [
        ("YYYY-MM-DD", "2026-07-14", date(2026, 7, 14)),
        ("YYYY.MM.DD", "2026.07.14", date(2026, 7, 14)),
        ("DD-MM-YY", "14-07-26", date(2026, 7, 14)),
        ("YYYY/YYYY-MM-DD", "2026-07-14", date(2026, 7, 14)),
        ("[Daily] YYYY-M-D", "Daily 2026-7-4", date(2026, 7, 4)),
        ("YYYY-MM-DD [(]MM[)]", "2026-07-14 (07)", date(2026, 7, 14)),
    ],
)
def test_daily_date_reads_configured_format(fmt, stem, expected):
    assert daily_date(stem, _daily_name_regex(fmt)) == expected


@pytest.mark.parametrize(
    ("fmt", "stem"),
    [
        ("YYYY-MM-DD", "2026-13-01"),  # matches the shape, not a real date
        ("YYYY-MM-DD", "2026.07.14"),
        ("YYYY.MM.DD", "2026x07x14"),  # dots are literal, not regex wildcards
        ("YYYY-MM-DD", "Project note"),
    ],
)
def test_daily_date_rejects_non_daily(fmt, stem):
    assert daily_date(stem, _daily_name_regex(fmt)) is None


def test_vocabulary_reads_daily_format(vault, config):
    config("daily-notes.json", {"format": "YYYY.MM.DD"})
    vocab = _vault.vocabulary(vault)
    assert vocab.daily_re.match("2026.01.02")
    assert not vocab.daily_re.match("2026-01-02")


# -- code masking ---------------------------------------------------------------


def test_mask_code_blanks_fences_and_inline_code_keeping_offsets():
    text = "a [x](y)\n```md\n[x](y)\n```\nb `[x](y)` c\n~~~\n[z](w)\n"
    masked = mask_code(text)
    assert len(masked) == len(text)
    assert masked.count("[x](y)") == 1
    assert masked.startswith("a [x](y)\n")
    assert "[z](w)" not in masked  # unclosed fence runs to the end
    assert masked.count("\n") == text.count("\n")


def test_mask_code_leaves_prose_without_code_untouched():
    text = "plain [[Link]] and [md](Note.md)\n"
    assert mask_code(text) == text
