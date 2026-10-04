"""Find broken wikilinks/embeds and (optionally) orphan notes across a vault.

Deterministic backing for vault-structural-scan and the authoring verify step.
Archive/ is excluded from the scan but still counts as a valid link target;
configured template folders are not scanned. A wikilink is broken when:

* **missing note** — no note has the target's basename. A target is a *file*
  only when its suffix is a known attachment extension, so `[[Node.js]]` and
  `[[Release v1.2]]` are notes; an unknown suffix still resolves to a real file
  of that name (`[[script.py]]`).
* **missing file** — an attachment link or embed (`![[img.png]]`, `[[doc.pdf]]`)
  whose basename matches no file in the vault.
* **missing heading** — `[[Note#Heading]]` (or `[[#Heading]]` in the same note)
  where the target note has no such heading; for `#A#B` the last part counts.
  Headings compare case- and whitespace-insensitively.
* **missing block** — `[[Note#^id]]` where no line in the target ends in `^id`.

Path-qualified targets (`[[../Area/Note]]`) match by basename, as Obsidian's
relative link format writes them. Links inside code spans and fences are
ignored. An orphan has neither incoming nor outgoing wikilinks.

Usage:
    python check_links.py --vault PATH [--orphans]

Output (JSON to stdout):
    {"broken": [{"file", "link", "target", "embed", "reason"}],
     "orphans": ["file", ...],                       # only with --orphans
     "unreadable": [{"file", "reason"}]}
"""

import argparse
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from _vault import (
    ATTACHMENT_EXTS,
    MARKDOWN_SUFFIX,
    WIKILINK_RE,
    Note,
    NoteDecodeError,
    add_vault_arg,
    emit_json,
    is_ignored,
    iter_notes,
    mask_code,
    read_note_text,
    require_vault_dir,
    scan_exclude,
)

_HEADING_RE = re.compile(
    r"^ {0,3}#{1,6}[ \t]+(.+?)(?:[ \t]+#+)?[ \t]*\r?$", re.MULTILINE
)
_BLOCK_ID_RE = re.compile(r"(?:^|\s)\^([A-Za-z0-9-]+)[ \t]*\r?$", re.MULTILINE)
# Characters Obsidian cannot keep in a heading link; it writes them as spaces.
_HEADING_PUNCT_RE = re.compile(r"[#|^:%\[\]\\]")


def _norm_heading(text: str) -> str:
    return " ".join(_HEADING_PUNCT_RE.sub(" ", text).lower().split())


@dataclass
class LinkIndex:
    """Every resolvable link target in the vault (Archive included)."""

    notes: dict[str, list[Path]]  # lowercased note stem -> note paths
    files: set[str]  # lowercased basenames of every non-markdown file
    _anchors: dict[Path, tuple[set[str], set[str]]] = field(default_factory=dict)

    def anchors(self, path: Path) -> tuple[set[str], set[str]]:
        """(normalized headings, block ids) of a note; cached, empty if unreadable."""
        if path not in self._anchors:
            try:
                text = mask_code(read_note_text(path).text)
            except (NoteDecodeError, OSError):
                text = ""
            self._anchors[path] = (
                {_norm_heading(m) for m in _HEADING_RE.findall(text)},
                set(_BLOCK_ID_RE.findall(text)),
            )
        return self._anchors[path]


def build_link_index(vault: Path) -> LinkIndex:
    notes: dict[str, list[Path]] = {}
    files: set[str] = set()
    for p in sorted(vault.rglob("*")):
        if not p.is_file() or is_ignored(p, vault):
            continue
        if p.suffix.lower() == MARKDOWN_SUFFIX:
            notes.setdefault(p.stem.lower(), []).append(p)
        else:
            files.add(p.name.lower())
    return LinkIndex(notes=notes, files=files)


@dataclass(frozen=True)
class _Link:
    raw: str  # everything between [[ and ]]
    embed: bool
    target: str  # path part, before any #subpath; "" for a same-note link
    subpath: str  # after the first #, "" if none


def _links(note: Note) -> Iterator[_Link]:
    text = mask_code(note.text)
    for m in WIKILINK_RE.finditer(text):
        raw = m.group(1)
        target, _, subpath = raw.split("|", 1)[0].partition("#")
        embed = m.start() > 0 and text[m.start() - 1] == "!"
        yield _Link(raw, embed, target.strip(), subpath.strip())


def _resolve(link: _Link, note: Note, index: LinkIndex) -> tuple[list[Path], str]:
    """(target note paths, problem): paths empty for file links; problem "" if ok."""
    if not link.target:
        return [note.path], ""
    base = link.target.replace("\\", "/").rsplit("/", 1)[-1]
    suffix = Path(base).suffix.lower()
    if suffix in ATTACHMENT_EXTS:
        return [], "" if base.lower() in index.files else "missing file"
    name = base[: -len(MARKDOWN_SUFFIX)] if suffix == MARKDOWN_SUFFIX else base
    paths = index.notes.get(name.lower(), [])
    if not paths and base.lower() not in index.files:
        return [], "missing note"
    return paths, ""


def _subpath_problem(subpath: str, paths: list[Path], index: LinkIndex) -> str:
    if not subpath or not paths:
        return ""
    if subpath.startswith("^"):
        block = subpath[1:]
        found = any(block in index.anchors(p)[1] for p in paths)
        return "" if found else "missing block"
    heading = _norm_heading(subpath.rsplit("#", 1)[-1])
    found = any(heading in index.anchors(p)[0] for p in paths)
    return "" if found else "missing heading"


def find_broken(notes: list[Note], index: LinkIndex) -> list[dict[str, object]]:
    """Every broken wikilink/embed in `notes`, with the reason it is broken."""
    broken: list[dict[str, object]] = []
    for note in notes:
        for link in _links(note):
            if not link.target and not link.subpath:
                continue
            paths, problem = _resolve(link, note, index)
            problem = problem or _subpath_problem(link.subpath, paths, index)
            if problem:
                broken.append(
                    {
                        "file": str(note.path),
                        "link": link.raw,
                        "target": link.raw.split("|", 1)[0].strip(),
                        "embed": link.embed,
                        "reason": problem,
                    }
                )
    return broken


def find_orphans(notes: list[Note], index: LinkIndex) -> list[str]:
    """Notes with neither an incoming link (from a scanned note) nor an outgoing one."""
    linked: set[Path] = set()
    has_outgoing: set[Path] = set()
    for note in notes:
        for link in _links(note):
            if not link.target:
                continue
            if not link.embed:
                has_outgoing.add(note.path)
            paths, _ = _resolve(link, note, index)
            linked.update(p for p in paths if p != note.path)
    return [
        str(n.path)
        for n in notes
        if n.path not in linked and n.path not in has_outgoing
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_vault_arg(parser)
    parser.add_argument("--orphans", action="store_true", help="Also report orphans")
    args = parser.parse_args()

    vault = require_vault_dir(args.vault)
    index = build_link_index(vault)
    unreadable: list[dict[str, str]] = []
    notes = iter_notes(
        vault, include_archive=False, exclude=scan_exclude(vault), unreadable=unreadable
    )

    result: dict[str, object] = {"broken": find_broken(notes, index)}
    if args.orphans:
        result["orphans"] = find_orphans(notes, index)
    result["unreadable"] = unreadable
    emit_json(result)


if __name__ == "__main__":
    main()
