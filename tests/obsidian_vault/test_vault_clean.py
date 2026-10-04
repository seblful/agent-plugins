"""vault_clean: every operation, run against fixture vaults."""

import json
import os
import time
from pathlib import Path

import pytest
import vault_clean

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16

EXT = set(vault_clean.DEFAULT_EXT)


def rename(vault, apply=True, include_archive=False):
    return vault_clean.op_rename(vault, apply, include_archive, EXT)


def names(vault, folder=""):
    return sorted(p.name for p in (vault / folder).iterdir() if p.is_file())


def png(tag: str) -> bytes:
    return PNG + tag.encode()


# -- rename: timestamps and names ------------------------------------------------


def test_timestamp_for_camera_name_is_local_time(tmp_path):
    path = tmp_path / "IMG-20260714013000123.png"
    path.write_bytes(PNG)
    day, ms = vault_clean._timestamp_for(path)
    assert day == "2026-07-14"
    assert ms == int(time.mktime((2026, 7, 14, 1, 30, 0, 0, 0, -1))) * 1000 + 123


def test_timestamp_for_underscore_camera_name(tmp_path):
    path = tmp_path / "IMG_20260714_013000.jpg"
    path.write_bytes(PNG)
    day, ms = vault_clean._timestamp_for(path)
    assert day == "2026-07-14"
    assert ms == int(time.mktime((2026, 7, 14, 1, 30, 0, 0, 0, -1))) * 1000


def test_timestamp_for_other_names_uses_local_mtime(tmp_path):
    path = tmp_path / "shot.png"
    path.write_bytes(PNG)
    os.utime(path, (1784035374.192, 1784035374.192))
    day, ms = vault_clean._timestamp_for(path)
    assert day == time.strftime("%Y-%m-%d", time.localtime(1784035374.192))
    assert ms == 1784035374192


def test_plan_renames_is_unique_across_the_whole_vault(vault, write):
    a = write("F1/IMG-20260714013000123.png", png("1"))
    b = write("F2/IMG-20260714013000123.png", png("2"))
    day, ms = vault_clean._timestamp_for(a)
    write(f"F3/{day}-{ms}-1.png", png("3"))  # an existing file already holds -1
    mapping = vault_clean._plan_renames([a, b], vault)
    new = sorted(p.name for p in mapping.values())
    assert new == [f"{day}-{ms}-2.png", f"{day}-{ms}.png"]
    assert mapping[a.resolve()].parent == a.parent.resolve()


# -- rename: link rewriting -------------------------------------------------------


def test_rename_rewrites_encoded_angle_titled_wiki_and_canvas_refs(vault, write):
    write("Notes/my img.png", PNG)
    write(
        "Notes/A.md",
        '![a](my%20img.png) ![b](<my img.png>) ![c](my%20img.png "t") '
        "![[my img.png|200]] ![[Notes/my img.png]]\n",
    )
    write(
        "Board.canvas",
        json.dumps(
            {"nodes": [{"id": "1", "type": "file", "file": "Notes/my img.png"}]}
        ),
    )
    result = rename(vault)
    assert "error" not in result
    assert result["skipped"] == []
    (new,) = [n for n in names(vault, "Notes") if n.endswith(".png")]
    assert new != "my img.png"
    text = (vault / "Notes/A.md").read_text(encoding="utf-8")
    assert text == (
        f'![a]({new}) ![b](<{new}>) ![c]({new} "t") ![[{new}|200]] ![[Notes/{new}]]\n'
    )
    canvas = json.loads((vault / "Board.canvas").read_text(encoding="utf-8"))
    assert canvas["nodes"][0]["file"] == f"Notes/{new}"
    assert result["notes_updated"] == 1
    assert result["canvases_updated"] == 1
    assert result["link_rewrites"] == 6


def test_rename_plan_changes_nothing(vault, write):
    write("x.png", PNG)
    note = write("A.md", "![[x.png]]")
    result = rename(vault, apply=False)
    assert len(result["renames"]) == 1
    assert names(vault) == ["A.md", "x.png"]
    assert note.read_text(encoding="utf-8") == "![[x.png]]"


def test_rename_skips_already_converted_files(vault, write):
    write("2026-07-14-1784035374192.png", PNG)
    assert rename(vault)["renames"] == []


def test_rename_blocks_file_named_by_an_unresolved_link(vault, write):
    write("A/pic.png", png("a"))
    write("B/pic.png", png("b"))
    write("N.md", "![[pic.png]]")  # ambiguous: two files share the basename
    result = rename(vault)
    assert result["renames"] == []
    assert {s["file"] for s in result["skipped"]} == {"A/pic.png", "B/pic.png"}
    assert all("unresolved" in s["reason"] for s in result["skipped"])
    assert names(vault, "A") == ["pic.png"]
    assert (vault / "N.md").read_text(encoding="utf-8") == "![[pic.png]]"


@pytest.mark.parametrize(
    ("rel", "content"),
    [
        ("Page.md", '<img src="pic.png">'),
        (
            "Board.canvas",
            json.dumps({"nodes": [{"type": "text", "text": "![[pic.png]]"}]}),
        ),
        ("Archive/Old.md", "![[pic.png]]"),  # frozen: cannot be rewritten
        ("Bad.md", "Привет ![[pic.png]]".encode("cp1251")),  # undecodable
    ],
)
def test_rename_blocks_file_still_mentioned_after_rewrite(vault, write, rel, content):
    write("pic.png", PNG)
    write("N.md", "![[pic.png]]")
    write(rel, content)
    result = rename(vault)
    assert result["renames"] == []
    assert [s["file"] for s in result["skipped"]] == ["pic.png"]
    assert (vault / "N.md").read_text(encoding="utf-8") == "![[pic.png]]"
    assert (vault / "pic.png").exists()


def test_rename_preserves_crlf_and_bom(vault, write):
    write("x.png", PNG)
    note = write("A.md", b"\xef\xbb\xbf---\r\ntags: [a]\r\n---\r\n![[x.png]]\r\n")
    rename(vault)
    raw = note.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf---\r\n")
    assert raw.count(b"\r\n") == 4
    assert b"x.png" not in raw


def test_rename_rolls_back_when_a_move_fails(vault, write, monkeypatch):
    write("a.png", png("a"))
    write("b.png", png("b"))
    note = write("A.md", "![[a.png]] ![[b.png]]")
    real_move = vault_clean._move
    calls = []

    def flaky(src: Path, dst: Path) -> None:
        calls.append(src)
        if len(calls) == 2:
            raise OSError("locked by another process")
        real_move(src, dst)

    monkeypatch.setattr(vault_clean, "_move", flaky)
    result = rename(vault)
    assert "locked" in result["error"]
    assert names(vault) == ["A.md", "a.png", "b.png"]
    assert note.read_text(encoding="utf-8") == "![[a.png]] ![[b.png]]"


def test_rename_rolls_back_when_a_note_write_fails(vault, write, monkeypatch):
    write("a.png", PNG)
    n1 = write("A.md", "![[a.png]]")
    n2 = write("B.md", "![[a.png]]")
    real_write = vault_clean.write_note_text
    calls = []

    def flaky(path, text, *, bom=False):
        calls.append(path)
        if len(calls) == 2:
            raise OSError("disk full")
        real_write(path, text, bom=bom)

    monkeypatch.setattr(vault_clean, "write_note_text", flaky)
    result = rename(vault)
    assert "disk full" in result["error"]
    assert names(vault) == ["A.md", "B.md", "a.png"]
    assert n1.read_text(encoding="utf-8") == "![[a.png]]"
    assert n2.read_text(encoding="utf-8") == "![[a.png]]"


def test_rename_refuses_existing_destination(vault, write, monkeypatch):
    src = write("a.png", PNG)
    write("A.md", "![[a.png]]")
    mapping = vault_clean._plan_renames([src], vault)
    dst = next(iter(mapping.values()))
    monkeypatch.setattr(vault_clean, "_plan_renames", lambda images, root: mapping)
    dst.write_bytes(b"other")  # appears between planning and applying
    result = rename(vault)
    assert "exists" in result["error"]
    assert dst.read_bytes() == b"other"
    assert src.exists()


# -- dedupe / relink / collocate ---------------------------------------------------


def test_dedupe_repoints_embeds_and_keeps_copies(vault, write):
    write("2026-01-01-1767225600000.png", PNG)
    write("sub/copy.png", PNG)
    note = write("N.md", "![[sub/copy.png]] ![x](sub/copy.png)")
    result = vault_clean.op_dedupe(vault, True, False, EXT)
    assert result["groups"] == [
        {"canonical": "2026-01-01-1767225600000.png", "duplicates": ["sub/copy.png"]}
    ]
    assert result["embeds_rewritten"] == 2
    assert note.read_text(encoding="utf-8") == (
        "![[2026-01-01-1767225600000.png]] ![x](2026-01-01-1767225600000.png)"
    )
    assert (vault / "sub/copy.png").exists()


def test_relink_repairs_stale_path_by_unique_basename(vault, write):
    write("new/place/x.png", PNG)
    write("y.png", png("y1"))
    write("other/y.png", png("y2"))
    note = write("N.md", "![[old/x.png]] ![[old/y.png]] ![[x.png]] ![[place/x.png]]")
    result = vault_clean.op_relink(vault, True, False, EXT)
    assert result["relinked"] == [{"note": "N.md", "from": "old/x.png", "to": "x.png"}]
    assert result["unresolved"] == [{"note": "N.md", "target": "old/y.png"}]
    assert note.read_text(encoding="utf-8") == (
        "![[x.png]] ![[old/y.png]] ![[x.png]] ![[place/x.png]]"
    )


def test_collocate_moves_to_per_note_folder_and_updates_canvas(vault, write, config):
    config("app.json", {"attachmentFolderPath": "./attachments"})
    write("loose.png", PNG)
    write("Notes/N.md", "![[loose.png]]")
    write("shared.png", png("s"))
    write("Notes/M.md", "![[shared.png]]")
    write("Other.md", "![[shared.png]]")
    write("orphan.png", png("o"))
    write(
        "B.canvas",
        json.dumps({"nodes": [{"type": "file", "file": "loose.png"}]}),
    )
    result = vault_clean.op_collocate(vault, True, False, EXT, ".obsidian", "")
    assert result["moved"] == [
        {"from": "loose.png", "to": "Notes/attachments/loose.png", "note": "Notes/N.md"}
    ]
    assert result["shared"][0]["attachment"] == "shared.png"
    assert result["orphans"] == 1
    assert (vault / "Notes/attachments/loose.png").exists()
    assert (vault / "Notes/N.md").read_text(encoding="utf-8") == "![[loose.png]]"
    canvas = json.loads((vault / "B.canvas").read_text(encoding="utf-8"))
    assert canvas["nodes"][0]["file"] == "Notes/attachments/loose.png"


def test_collocate_blocks_move_referenced_from_frozen_archive(vault, write):
    write("x.png", PNG)
    write("Notes/N.md", "![[x.png]]")
    write("Archive/Old.md", "![[x.png]]")
    result = vault_clean.op_collocate(
        vault, True, False, EXT, ".obsidian", "central:Files"
    )
    assert result["moved"] == []
    assert [s["file"] for s in result["skipped"]] == ["x.png"]
    assert (vault / "x.png").exists()


def test_collocate_conflict_and_already_placed(vault, write):
    write("Files/x.png", png("other"))
    write("x.png", PNG)
    write("N.md", "![[x.png]] ![[Files/x.png]]")
    write("Files/y.png", png("y"))
    write("M.md", "![[y.png]]")
    result = vault_clean.op_collocate(
        vault, False, False, EXT, ".obsidian", "central:Files"
    )
    assert result["conflicts"] == [{"attachment": "x.png", "dest": "Files/x.png"}]
    assert result["already_placed"] == 2
    assert result["layout"]["kind"] == "central"


# -- links ---------------------------------------------------------------------------


def test_links_converts_prose_but_not_code(vault, write):
    write("B.md", "")
    write("img/p q.png", PNG)
    note = write(
        "A.md",
        'See [B](B.md) and [the b](B.md#Sec) and ![](<img/p q.png> "t").\r\n'
        "```\r\nexample [B](B.md)\r\n```\r\n`[B](B.md)` [ext](https://x.y) [gone](Gone.md)\r\n",
    )
    result = vault_clean.op_links(vault, True, False)
    assert result["converted"] == [{"note": "A.md", "count": 3}]
    assert result["unresolved"] == [{"note": "A.md", "target": "Gone.md"}]
    assert note.read_bytes().decode() == (
        "See [[B]] and [[B#Sec|the b]] and ![[p q.png]].\r\n"
        "```\r\nexample [B](B.md)\r\n```\r\n`[B](B.md)` [ext](https://x.y) [gone](Gone.md)\r\n"
    )


def test_links_uses_path_when_basename_is_ambiguous(vault, write):
    write("a/Dup.md", "")
    write("b/Dup.md", "")
    note = write("N.md", "[Dup](a/Dup.md)")
    vault_clean.op_links(vault, True, False)
    assert note.read_text(encoding="utf-8") == "[[a/Dup|Dup]]"


def test_main_refuses_links_when_vault_uses_markdown_links(
    vault, write, config, run_main
):
    config("app.json", {"useMarkdownLinks": True})
    write("B.md", "")
    note = write("A.md", "[B](B.md)")
    code, data, err = run_main(vault_clean, "--vault", str(vault), "--links", "--apply")
    assert code != 0
    assert data is None
    assert "useMarkdownLinks" in err
    assert note.read_text(encoding="utf-8") == "[B](B.md)"
    code, data, _ = run_main(
        vault_clean, "--vault", str(vault), "--links", "--apply", "--force"
    )
    assert code == 0
    assert note.read_text(encoding="utf-8") == "[[B]]"


# -- attachments -----------------------------------------------------------------------


def test_attachments_counts_canvas_references(vault, write):
    write("used.png", PNG)
    write("canvas-only.png", png("c"))
    write("orphan.png", png("o"))
    write("N.md", "![[used.png]] ![[missing.png]]")
    write(
        "B.canvas", json.dumps({"nodes": [{"type": "file", "file": "canvas-only.png"}]})
    )
    result = vault_clean.op_attachments(vault, EXT)
    assert result["orphans"] == ["orphan.png"]
    assert result["broken"] == [{"note": "N.md", "target": "missing.png"}]


# -- prune -------------------------------------------------------------------------------


def test_prune_protects_dot_and_role_folders(vault, config):
    config("daily-notes.json", {"folder": "Journal"})
    config("app.json", {"attachmentFolderPath": "Files"})
    config("templates.json", {"folder": "Templates"})
    for d in [
        ".stfolder",
        "Inbox",
        "Weekly",
        "Archive",
        "Journal",
        "Files",
        "Templates",
        "Keep Me",
        "skeleton/a/b",
        "skeleton/c",
    ]:
        (vault / d).mkdir(parents=True)
    result = vault_clean.op_prune(vault, True, False, {"Keep Me"})
    assert result["removed"] == ["skeleton/a/b", "skeleton/a", "skeleton/c", "skeleton"]
    assert result["protected"] == [
        "Archive",
        "Files",
        "Inbox",
        "Journal",
        "Keep Me",
        "Templates",
        "Weekly",
    ]
    assert (vault / ".stfolder").is_dir()
    assert not (vault / "skeleton").exists()


def test_prune_plan_only_and_archive_frozen(vault):
    (vault / "Archive/2025/empty").mkdir(parents=True)
    (vault / "x/empty").mkdir(parents=True)
    result = vault_clean.op_prune(vault, False, False, set())
    assert result["removed"] == ["x/empty", "x"]
    assert (vault / "x/empty").is_dir()
    result = vault_clean.op_prune(vault, False, True, set())
    assert "Archive/2025/empty" in result["removed"]


# -- CLI ------------------------------------------------------------------------------------


def test_main_requires_an_operation(vault, run_main):
    code, _, _ = run_main(vault_clean, "--vault", str(vault))
    assert code == 2


def test_main_all_plan_reports_every_operation_and_unreadable(vault, write, run_main):
    write("x.png", PNG)
    write("A.md", "![[x.png]]")
    write("Bad.md", "Привет".encode("cp1251"))
    code, data, _ = run_main(
        vault_clean, "--vault", str(vault), "--all", "--ext", "tiff"
    )
    assert code == 0
    assert data["operations"] == [
        "rename",
        "dedupe",
        "relink",
        "links",
        "attachments",
        "prune",
    ]
    assert data["applied"] is False
    assert [u["file"] for u in data["unreadable"]] == ["Bad.md"]


def test_main_exits_nonzero_when_an_apply_rolls_back(
    vault, write, run_main, monkeypatch
):
    write("x.png", PNG)
    write("A.md", "![[x.png]]")

    def boom(src, dst):
        raise OSError("locked")

    monkeypatch.setattr(vault_clean, "_move", boom)
    code, data, _ = run_main(vault_clean, "--vault", str(vault), "--rename", "--apply")
    assert code == 1
    assert "locked" in data["rename"]["error"]


# -- edge paths ------------------------------------------------------------------------------


def test_attachments_reads_markdown_refs_and_skips_urls(vault, write):
    write("two words.png", PNG)
    write(
        "N.md",
        "![a](two%20words.png) ![b](https://e.x/remote.png) ![c](<gone one.png>)",
    )
    result = vault_clean.op_attachments(vault, EXT)
    assert result["orphans"] == []
    assert result["broken"] == [{"note": "N.md", "target": "gone one.png"}]


def test_timestamp_for_impossible_camera_date_falls_back_to_mtime(tmp_path):
    path = tmp_path / "IMG-20261345990000.png"  # month 13: not a real moment
    path.write_bytes(PNG)
    os.utime(path, (1784035374.0, 1784035374.0))
    assert vault_clean._timestamp_for(path)[1] == 1784035374000


def test_dedupe_repoints_canvas_file_nodes(vault, write):
    write("a.png", PNG)
    write("b/a-copy.png", PNG)
    write("N.md", "")
    board = write(
        "B.canvas",
        json.dumps({"nodes": [{"type": "file", "file": "b/a-copy.png"}, {"file": 3}]}),
    )
    vault_clean.op_dedupe(vault, True, False, EXT)
    nodes = json.loads(board.read_text(encoding="utf-8"))["nodes"]
    assert nodes[0]["file"] == "a.png"
    assert nodes[1]["file"] == 3


def test_links_resolves_by_unique_basename_for_notes_and_files(vault, write):
    write("deep/Topic.md", "")
    write("files/doc.pdf", b"%PDF")
    note = write("N.md", "[t](elsewhere/Topic.md) [d](doc.pdf) [e]() [h](#local)")
    result = vault_clean.op_links(vault, True, False)
    assert result["converted"] == [{"note": "N.md", "count": 2}]
    assert (
        note.read_text(encoding="utf-8")
        == "[[Topic|t]] [[doc.pdf|d]] [e]() [h](#local)"
    )


def test_collocate_leaves_files_named_by_undecodable_notes(vault, write):
    write("x.png", PNG)
    write("Notes/N.md", "![[x.png]]")
    write("Notes/Bad.md", "Привет ![[x.png]]".encode("cp1251"))
    unreadable: list[dict[str, str]] = []
    result = vault_clean.op_collocate(
        vault, True, False, EXT, ".obsidian", "same-folder", unreadable
    )
    assert result["moved"] == []
    assert [s["file"] for s in result["skipped"]] == ["x.png"]
    assert unreadable == [{"file": "Notes/Bad.md", "reason": unreadable[0]["reason"]}]
    assert (vault / "x.png").exists()


def test_rename_ignores_non_image_and_external_refs(vault, write):
    write("x.png", PNG)
    note = write(
        "N.md", "[[Other Note]] ![r](https://e.x/remote.png) [p](paper.pdf) ![[x.png]]"
    )
    result = rename(vault)
    new = result["renames"][0]["to"]
    assert note.read_text(encoding="utf-8") == (
        f"[[Other Note]] ![r](https://e.x/remote.png) [p](paper.pdf) ![[{new}]]"
    )
