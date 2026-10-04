"""check_links: the broken-link classifier and orphan detection."""

import check_links
from _vault import iter_notes


def broken(vault):
    notes = iter_notes(vault)
    index = check_links.build_link_index(vault)
    return {(b["target"], b["reason"]) for b in check_links.find_broken(notes, index)}


def test_dotted_note_names_are_notes_not_files(vault, write):
    write("Node.js.md", "")
    write("A.md", "[[Node.js]] [[Missing.Note]] [[Release v1.2]]")
    assert broken(vault) == {
        ("Missing.Note", "missing note"),
        ("Release v1.2", "missing note"),
    }


def test_broken_embeds_and_file_links_are_reported(vault, write):
    write("img/real.png", b"x")
    write("A.md", "![[real.png]] ![[nope.png]] [[doc.pdf]] ![[Missing Note]]")
    assert broken(vault) == {
        ("nope.png", "missing file"),
        ("doc.pdf", "missing file"),
        ("Missing Note", "missing note"),
    }


def test_unknown_suffix_resolves_against_files_too(vault, write):
    write("script.py", "print()")
    write("A.md", "[[script.py]]")
    assert broken(vault) == set()


def test_heading_and_block_links_are_checked(vault, write):
    write(
        "B.md",
        "## Setup & Install\ntext ^blk-1\n```\n## Not A Heading\n```\n### Deep\n",
    )
    write(
        "A.md",
        "[[B#Setup & Install]] [[B#setup  &  install]] [[B#Gone]] "
        "[[B#Setup & Install#Deep]] [[B#^blk-1]] [[B#^nope]] [[B#Not A Heading]] "
        "[[#Local]] [[#Missing Local]]\n## Local\n",
    )
    assert broken(vault) == {
        ("B#Gone", "missing heading"),
        ("B#^nope", "missing block"),
        ("B#Not A Heading", "missing heading"),
        ("#Missing Local", "missing heading"),
    }


def test_links_in_code_are_ignored_and_paths_resolve_by_basename(vault, write):
    write("Area/Note.md", "")
    write(
        "A.md", "`[[Gone]]`\n```\n[[Gone2]]\n```\n[[../Area/Note]] [[Area/Note.md|x]]"
    )
    assert broken(vault) == set()


def test_archived_notes_are_valid_targets_but_not_checked(vault, write):
    write("Archive/Old.md", "## H\n[[Broken In Archive]]")
    write("A.md", "[[Old#H]]")
    assert broken(vault) == set()


def test_main_reports_reason_orphans_and_unreadable(vault, write, run_main):
    write("A.md", "[[B]] [[Gone]]")
    write("B.md", "")
    write("Lonely.md", "")
    write("Bad.md", "Привет".encode("cp1251"))
    write("Templates/T.md", "[[{{title}}]]")
    (vault / ".obsidian/templates.json").write_text('{"folder": "Templates"}')
    code, data, _ = run_main(check_links, "--vault", str(vault), "--orphans")
    assert code == 0
    assert [(b["target"], b["reason"], b["embed"]) for b in data["broken"]] == [
        ("Gone", "missing note", False)
    ]
    assert [o.rsplit("\\", 1)[-1].rsplit("/", 1)[-1] for o in data["orphans"]] == [
        "Lonely.md"
    ]
    assert len(data["unreadable"]) == 1


def test_main_without_orphans_flag(vault, write, run_main):
    write("A.md", "")
    code, data, _ = run_main(check_links, "--vault", str(vault))
    assert code == 0
    assert data == {"broken": [], "unreadable": []}
