"""Universal, parameterized vault file-cleaner: one command, composable operations.

Pick any combination of operations; they always run in a safe fixed order
(rename -> dedupe -> relink -> collocate -> links -> attachments -> prune)
regardless of flag order, and emit a single JSON report keyed by operation.
Every mutating operation **plans by default and changes nothing until --apply**.
Archive/ is frozen and skipped unless --include-archive is given.

Safety rules every mutating operation follows:
    * Notes are read as strict UTF-8 and written back byte-for-byte except for
      the edit: line endings (LF/CRLF) and a UTF-8 BOM are preserved. A note
      that is not valid UTF-8 is never rewritten; it is listed under
      `unreadable`.
    * File moves happen first, then note writes; if any step fails, every move
      and write already made is undone and the operation reports `error`
      (exit status 1). Links never end up pointing at a missing name.
    * --rename and --collocate never move a file that something they cannot
      rewrite still names: an unresolved link with that basename, an archived
      or undecodable note, HTML, a canvas text node. Such files are listed
      under `skipped` with the reason.

Operations (choose one or more, or --all):
    --rename        Rename image attachments to `YYYY-MM-DD-<unix-ms>.<ext>` and
                    rewrite every link/embed to them — wikilinks, markdown links
                    (percent-encoded, `<angle>` and titled targets) and canvas
                    file nodes. Camera names (`IMG-…`, `IMG_…`, `PXL_…`) are
                    read as local time; other files use their local mtime.
                    New names are unique across the whole vault.
    --dedupe        Collapse byte-identical image attachments to one canonical
                    file and repoint embeds to it; the redundant copies are
                    flagged (left on disk), never deleted.
    --relink        Repair broken image embeds whose target file is missing but
                    whose basename resolves uniquely to a moved attachment.
    --collocate     Move attachments to the vault's configured attachment folder
                    (read from .obsidian/app.json via obsidian_config), rewriting
                    embeds. Orphan and shared attachments are flagged, not moved.
                    OPT-IN: relocates files, so it is NOT included in --all.
    --links         Convert internal `[markdown](links)` to `[[wikilinks]]`
                    (external URLs and anything inside code left alone). Refused
                    when the vault is set to markdown links (`useMarkdownLinks`)
                    unless --force is given.
    --attachments   Report orphan (unreferenced) and broken (missing-target)
                    image attachments; canvas file nodes count as references.
                    Report-only — never deletes.
    --prune         Remove empty folders, cascading bottom-up. Never removes a
                    dot-folder (`.stfolder`, …) or a role folder: Inbox, Weekly,
                    Archive, the daily-notes folder, the central attachment
                    folder, and the template folders.
    --all           Every operation above except --collocate.

Modifiers:
    --vault PATH        Vault root (default: cwd).
    --apply             Perform changes (default: plan/report only).
    --include-archive   Also process notes/files under any Archive/ folder.
    --ext e1,e2         Extra attachment extensions for --rename / --attachments.
    --keep n1,n2        Folder names --prune must never remove, even if empty.
    --force             Run --links even though the vault uses markdown links.
    --config-dir DIR    Obsidian config dir (default: .obsidian).
    --layout SPEC       Override --collocate layout: root | same-folder |
                        central:NAME | per-note:NAME (default: read app.json).

Usage:
    python vault_clean.py --vault PATH --all
    python vault_clean.py --vault PATH --all --apply
    python vault_clean.py --vault PATH --rename --links --apply
    python vault_clean.py --vault PATH --collocate           # layout from app.json
    python vault_clean.py --vault PATH --collocate --layout per-note:attachments

Output (JSON to stdout):
    {"vault", "applied", "operations", "unreadable": [{"file", "reason"}],
     <op>: {...}, ...}; an op that failed and rolled back carries "error".
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import re
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, unquote

import obsidian_config
from _vault import (
    CANVAS_SUFFIX,
    DEFAULT_CONFIG_DIR,
    IMAGE_EXTS,
    INBOX_DIR_NAME,
    MARKDOWN_SUFFIX,
    NoteDecodeError,
    NoteText,
    archive_dir,
    emit_json,
    image_basename_index,
    is_ignored,
    iter_attachment_paths,
    iter_files,
    mask_code,
    read_note_text,
    require_vault_dir,
    resolve_image,
    under_archive,
    unreadable_entry,
    weekly_dir,
    write_note_text,
)

# ---------------------------------------------------------------------------
# Shared constants and helpers
# ---------------------------------------------------------------------------

DEFAULT_EXT = set(IMAGE_EXTS)
TEXT_SUFFIXES = (MARKDOWN_SUFFIX, CANVAS_SUFFIX)
# Files scanned for leftover mentions before a file is moved or renamed.
MENTION_SUFFIXES = (MARKDOWN_SUFFIX, CANVAS_SUFFIX, ".base")

CAMERA_RE = re.compile(
    r"^(?:IMG|PXL)[-_](\d{4})(\d{2})(\d{2})[-_]?(\d{2})(\d{2})(\d{2})(\d{0,3})(?:-\d+)?$"
)
TARGET_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{13}(?:-\d+)?$")
# Wikilink to a file: bang, target, #subpath, |alias.
WIKI_REF_RE = re.compile(r"(!?)\[\[([^\[\]#|]+)((?:#[^\[\]|]*)?)((?:\|[^\[\]]*)?)\]\]")
# Markdown link/embed: head `![alt](`, target (`<…>` or bare), tail (`"title")`).
MD_REF_RE = re.compile(
    r"(!?\[[^\]]*\]\()(<[^>\n]+>|[^)\s<>]+)((?:[ \t]+\"[^\"\n]*\")?\))"
)
# Conversion (links): bang, label, target, optional title.
CONV_MD_RE = re.compile(
    r"(!?)\[([^\]]*)\]\((<[^>\n]+>|[^)\s<>]+)(?:[ \t]+\"[^\"\n]*\")?\)"
)
CANVAS_FILE_RE = re.compile(r'("file"\s*:\s*)("(?:[^"\\]|\\.)*")')
URL_RE = re.compile(r"^([a-z][a-z0-9+.-]*:|//|#)", re.IGNORECASE)

# (note path, decoded target) -> replacement decoded target, or None to keep it.
Retarget = Callable[[Path, str], str | None]
# vault-relative canvas file path -> replacement path, or None to keep it.
CanvasRetarget = Callable[[str], str | None]


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _read(path: Path, root: Path, unreadable: list[dict[str, str]]) -> NoteText | None:
    """A note's text, or None (recorded in `unreadable`) if it is not UTF-8."""
    try:
        return read_note_text(path)
    except NoteDecodeError as exc:
        unreadable.append(unreadable_entry(exc, root))
        return None


def _split_md_target(raw: str) -> tuple[str, str, bool]:
    """(decoded path, '#anchor' or '', angle-bracketed?) of a markdown link target."""
    angle = raw.startswith("<") and raw.endswith(">")
    inner = raw[1:-1] if angle else raw
    path, hashmark, anchor = inner.partition("#")
    return unquote(path), hashmark + anchor, angle


def _encode_md_target(path: str, anchor: str, angle: bool, encoded: bool) -> str:
    if angle:
        return f"<{path}{anchor}>"
    if encoded or any(c in path for c in " ()<>"):
        path = quote(path, safe="/")
    return path + anchor


def _image_targets(text: str, ext: set[str]) -> list[str]:
    """Every decoded image link/embed target in a note (wiki and markdown)."""
    out = [
        m.group(2).strip()
        for m in WIKI_REF_RE.finditer(text)
        if Path(m.group(2).strip()).suffix.lower() in ext
    ]
    for m in MD_REF_RE.finditer(text):
        path, _, _ = _split_md_target(m.group(2))
        if (
            not URL_RE.match(m.group(2).strip("<>"))
            and Path(path).suffix.lower() in ext
        ):
            out.append(path)
    return out


def _canvas_files(text: str) -> list[str]:
    """The vault-relative paths of a canvas's file nodes."""
    out: list[str] = []
    for m in CANVAS_FILE_RE.finditer(text):
        try:
            value = json.loads(m.group(2))
        except ValueError:
            continue
        if isinstance(value, str):
            out.append(value)
    return out


def _rewrite_text(
    text: str, note: Path, ext: set[str], retarget: Retarget
) -> tuple[str, int]:
    """Rewrite image link/embed targets via `retarget`; return (new text, count)."""
    count = 0

    def wiki(m: re.Match[str]) -> str:
        nonlocal count
        bang, target, sub, alias = m.groups()
        decoded = target.strip()
        if Path(decoded).suffix.lower() not in ext:
            return m.group(0)
        new = retarget(note, decoded)
        if new is None or new == decoded:
            return m.group(0)
        count += 1
        return f"{bang}[[{new}{sub}{alias}]]"

    def markdown(m: re.Match[str]) -> str:
        nonlocal count
        head, raw, tail = m.groups()
        if URL_RE.match(raw.strip("<>")):
            return m.group(0)
        decoded, anchor, angle = _split_md_target(raw)
        if Path(decoded).suffix.lower() not in ext:
            return m.group(0)
        new = retarget(note, decoded)
        if new is None or new == decoded:
            return m.group(0)
        count += 1
        encoded = "%" in raw
        return f"{head}{_encode_md_target(new, anchor, angle, encoded)}{tail}"

    text = WIKI_REF_RE.sub(wiki, text)
    return MD_REF_RE.sub(markdown, text), count


def _rewrite_canvas(text: str, retarget: CanvasRetarget) -> tuple[str, int]:
    """Rewrite canvas file-node paths in place, keeping the JSON's own formatting."""
    count = 0

    def repl(m: re.Match[str]) -> str:
        nonlocal count
        try:
            value = json.loads(m.group(2))
        except ValueError:
            return m.group(0)
        new = retarget(value) if isinstance(value, str) else None
        if new is None or new == value:
            return m.group(0)
        count += 1
        return m.group(1) + json.dumps(new, ensure_ascii=False)

    return CANVAS_FILE_RE.sub(repl, text), count


@dataclass
class _Edit:
    path: Path
    original: str
    new: str
    bom: bool
    count: int


def _plan_edits(
    root: Path,
    include_archive: bool,
    ext: set[str],
    retarget: Retarget,
    canvas_retarget: CanvasRetarget | None,
    unreadable: list[dict[str, str]],
) -> list[_Edit]:
    """The note and canvas rewrites `retarget` implies (nothing written)."""
    edits: list[_Edit] = []
    suffixes = TEXT_SUFFIXES if canvas_retarget else (MARKDOWN_SUFFIX,)
    for path in iter_files(root, suffixes, include_archive=include_archive):
        content = _read(path, root, unreadable)
        if content is None:
            continue
        if path.suffix.lower() == CANVAS_SUFFIX and canvas_retarget is not None:
            new, count = _rewrite_canvas(content.text, canvas_retarget)
        else:
            new, count = _rewrite_text(content.text, path, ext, retarget)
        if count:
            edits.append(_Edit(path, content.text, new, content.bom, count))
    return edits


def _new_target(decoded: str, old: Path, new: Path, root: Path, unique: bool) -> str:
    """How a reference to `old` should name `new`, keeping the reference's style."""
    if "/" in decoded and old.parent == new.parent:
        return f"{decoded.rsplit('/', 1)[0]}/{new.name}"
    return new.name if unique else rel(new, root)


def _retargeters(
    root: Path,
    ext: set[str],
    basename_idx: dict[str, list[Path]],
    moves: dict[Path, Path],
    unresolved: list[dict[str, str]] | None = None,
) -> tuple[Retarget, CanvasRetarget]:
    """Retarget callbacks for references to files in `moves` (old -> new path)."""
    names_after = Counter(
        name.lower() for name, hits in basename_idx.items() for _ in hits
    )
    for old, new in moves.items():
        names_after[old.name.lower()] -= 1
        names_after[new.name.lower()] += 1

    def retarget(note: Path, decoded: str) -> str | None:
        resolved = resolve_image(decoded, note.parent, root, basename_idx, ext)
        if resolved is None:
            if unresolved is not None:
                unresolved.append({"note": rel(note, root), "target": decoded})
            return None
        new = moves.get(resolved)
        if new is None:
            return None
        return _new_target(
            decoded, resolved, new, root, names_after[new.name.lower()] == 1
        )

    def canvas(value: str) -> str | None:
        cand = root / value
        new = moves.get(cand.resolve()) if cand.is_file() else None
        return None if new is None else rel(new, root)

    return retarget, canvas


_WORD_BEFORE = rb"(?<![\w.-])"


def _mentions(data: bytes, name: str) -> bool:
    """True if `data` names `name` (plain or percent-encoded) as a whole filename."""
    low = data.lower()
    return any(
        re.search(_WORD_BEFORE + re.escape(form.lower().encode()), low)
        for form in {name, quote(name)}
    )


def _blocked_by_mentions(
    files: list[Path], names: dict[Path, str], root: Path, contents: dict[Path, bytes]
) -> dict[Path, str]:
    """Which entries of `names` (path -> basename) some file in `files` still names."""
    blocked: dict[Path, str] = {}
    for path in files:
        data = contents.get(path)
        if data is None:
            data = path.read_bytes()
        for src, name in names.items():
            if src not in blocked and _mentions(data, name):
                blocked[src] = f"still referenced after rewrite by {rel(path, root)}"
    return blocked


def _move(src: Path, dst: Path) -> None:
    """Move one file; never overwrites (a case-insensitive clash counts as existing)."""
    if dst.exists():
        raise FileExistsError(f"destination exists: {dst}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dst)


def _apply(moves: list[tuple[Path, Path]], edits: list[_Edit]) -> str | None:
    """Move files, then write notes; on any failure undo all of it. Returns the error."""
    moved: list[tuple[Path, Path]] = []
    touched: list[_Edit] = []
    try:
        for src, dst in moves:
            _move(src, dst)
            moved.append((src, dst))
        for edit in edits:
            touched.append(edit)
            write_note_text(edit.path, edit.new, bom=edit.bom)
    except OSError as exc:
        problems: list[str] = []
        for edit in reversed(touched):
            try:
                write_note_text(edit.path, edit.original, bom=edit.bom)
            except OSError as undo:
                problems.append(f"{edit.path}: {undo}")
        for src, dst in reversed(moved):
            try:
                dst.rename(src)
            except OSError as undo:
                problems.append(f"{dst}: {undo}")
        status = (
            "all changes rolled back"
            if not problems
            else "ROLLBACK INCOMPLETE: " + "; ".join(problems)
        )
        return f"{type(exc).__name__}: {exc} — {status}"
    return None


def _edit_report(edits: list[_Edit]) -> dict[str, int]:
    canvases = sum(1 for e in edits if e.path.suffix.lower() == CANVAS_SUFFIX)
    return {
        "notes_updated": len(edits) - canvases,
        "canvases_updated": canvases,
        "link_rewrites": sum(e.count for e in edits),
    }


# ---------------------------------------------------------------------------
# Operation: rename image attachments + rewrite links
# ---------------------------------------------------------------------------


def _timestamp_for(path: Path) -> tuple[str, int]:
    """Return (YYYY-MM-DD, unix_ms) on the local clock.

    A camera name (`IMG-20260714013000123`, `IMG_20260714_013000`, `PXL_…`) is
    the capture moment in local time; otherwise the file's modification time.
    """
    m = CAMERA_RE.match(path.stem)
    if m:
        y, mo, d, h, mi, s, ms = m.groups()
        try:
            moment = time.strptime(f"{y}{mo}{d}{h}{mi}{s}", "%Y%m%d%H%M%S")
        except ValueError:
            pass  # not a real date: fall back to mtime
        else:
            millis = int((ms or "0").ljust(3, "0"))
            return f"{y}-{mo}-{d}", int(time.mktime(moment)) * 1000 + millis
    unix_ms = round(path.stat().st_mtime_ns / 1_000_000)
    return time.strftime("%Y-%m-%d", time.localtime(unix_ms / 1000)), unix_ms


def _plan_renames(images: list[Path], root: Path) -> dict[Path, Path]:
    """physical file -> new physical path; new names are unique across the vault.

    Bare `![[name]]` embeds resolve by basename vault-wide, so a name is taken
    if any file anywhere holds it (case-insensitively, as on Windows/macOS).
    """
    taken = {p.name.lower() for p in root.rglob("*") if not is_ignored(p, root)}
    mapping: dict[Path, Path] = {}
    for img in images:
        day, ms = _timestamp_for(img)
        suffix = img.suffix.lower()
        name = f"{day}-{ms}{suffix}"
        n = 0
        while name.lower() in taken:
            n += 1
            name = f"{day}-{ms}-{n}{suffix}"
        taken.add(name.lower())
        mapping[img.resolve()] = (img.parent / name).resolve()
    return mapping


def op_rename(
    root: Path,
    apply: bool,
    include_archive: bool,
    ext: set[str],
    unreadable: list[dict[str, str]] | None = None,
) -> dict:
    root = root.resolve()
    images = [
        p
        for p in iter_attachment_paths(root, ext, include_archive=include_archive)
        if not TARGET_RE.match(p.stem)
    ]
    mapping = _plan_renames(images, root)
    basename_idx = image_basename_index(root, ext)
    mention_files = list(iter_files(root, MENTION_SUFFIXES, include_archive=True))
    skipped: dict[Path, str] = {}

    while True:  # block, re-plan without the blocked files, until nothing changes
        active = {src: dst for src, dst in mapping.items() if src not in skipped}
        unresolved: list[dict[str, str]] = []
        unread: list[dict[str, str]] = []
        retarget, canvas = _retargeters(root, ext, basename_idx, active, unresolved)
        edits = _plan_edits(root, include_archive, ext, retarget, canvas, unread)
        unresolved_names = {Path(u["target"]).name.lower() for u in unresolved}
        blocked = {
            src: "referenced by an unresolved link"
            for src in active
            if src.name.lower() in unresolved_names
        }
        after = {e.path: e.new.encode("utf-8") for e in edits}
        names = {src: src.name for src in active if src not in blocked}
        blocked |= _blocked_by_mentions(mention_files, names, root, after)
        if not blocked:
            break
        skipped |= blocked

    result: dict[str, object] = {
        "renames": [
            {"from": rel(src, root), "to": dst.name}
            for src, dst in sorted(active.items())
        ],
        "skipped": [
            {"file": rel(src, root), "reason": reason}
            for src, reason in sorted(skipped.items())
        ],
        **_edit_report(edits),
        "unresolved": unresolved,
    }
    if unreadable is not None:
        unreadable.extend(unread)
    if apply:
        error = _apply(sorted(active.items()), edits)
        if error:
            result["error"] = error
    return result


# ---------------------------------------------------------------------------
# Operation: collapse byte-identical attachments (dedupe)
# ---------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def op_dedupe(
    root: Path,
    apply: bool,
    include_archive: bool,
    ext: set[str],
    unreadable: list[dict[str, str]] | None = None,
) -> dict:
    root = root.resolve()
    files = list(iter_attachment_paths(root, ext, include_archive=include_archive))
    basename_idx = image_basename_index(root, ext)

    by_hash: dict[str, list[Path]] = {}
    for f in files:
        by_hash.setdefault(_sha256(f), []).append(f)

    def canon_key(p: Path) -> tuple[int, int, str]:
        r = p.relative_to(root)
        return (0 if TARGET_RE.match(p.stem) else 1, len(r.parts), r.as_posix())

    redirect: dict[Path, Path] = {}  # duplicate resolved path -> canonical path
    groups: list[dict[str, object]] = []
    for paths in by_hash.values():
        if len(paths) < 2:
            continue
        canon = min(paths, key=canon_key)
        dups = [p for p in paths if p != canon]
        for d in dups:
            redirect[d.resolve()] = canon.resolve()
        groups.append(
            {
                "canonical": rel(canon, root),
                "duplicates": sorted(rel(d, root) for d in dups),
            }
        )

    unread: list[dict[str, str]] = []
    retarget, canvas = _redirecting(redirect, root, ext, basename_idx)
    edits = _plan_edits(root, include_archive, ext, retarget, canvas, unread)
    result: dict[str, object] = {
        "groups": groups,
        "embeds_rewritten": sum(e.count for e in edits),
    }
    if unreadable is not None:
        unreadable.extend(unread)
    if apply:
        error = _apply([], edits)  # copies left on disk, flagged
        if error:
            result["error"] = error
    return result


def _redirecting(
    redirect: dict[Path, Path],
    root: Path,
    ext: set[str],
    basename_idx: dict[str, list[Path]],
) -> tuple[Retarget, CanvasRetarget]:
    """Retargeters that point references at a canonical copy (no file moves)."""

    def retarget(note: Path, decoded: str) -> str | None:
        resolved = resolve_image(decoded, note.parent, root, basename_idx, ext)
        canon = redirect.get(resolved) if resolved is not None else None
        if canon is None:
            return None
        unique = len(basename_idx.get(canon.name, [])) == 1
        return _new_target(decoded, resolved, canon, root, unique)

    def canvas(value: str) -> str | None:
        cand = root / value
        canon = redirect.get(cand.resolve()) if cand.is_file() else None
        return None if canon is None else rel(canon, root)

    return retarget, canvas


# ---------------------------------------------------------------------------
# Operation: repair broken image embeds by unique basename (relink)
# ---------------------------------------------------------------------------


def op_relink(
    root: Path,
    apply: bool,
    include_archive: bool,
    ext: set[str],
    unreadable: list[dict[str, str]] | None = None,
) -> dict:
    root = root.resolve()
    # Resolution targets: image files (excluding Archive unless asked) — indexed
    # by basename and by path-components, to mirror how Obsidian resolves a link.
    files = list(iter_attachment_paths(root, ext, include_archive=include_archive))
    basename_idx: dict[str, list[Path]] = {}
    rel_parts: list[tuple[str, ...]] = []
    for f in files:
        basename_idx.setdefault(f.name, []).append(f.resolve())
        rel_parts.append(f.relative_to(root).parts)

    def suffix_match(comps: tuple[str, ...]) -> bool:
        n = len(comps)
        return any(parts[-n:] == comps for parts in rel_parts if len(parts) >= n)

    relinked: list[dict[str, str]] = []
    unresolved: list[dict[str, str]] = []

    def retarget(note: Path, decoded: str) -> str | None:
        # Bare basenames (no folder) are Obsidian's own to resolve — leave them;
        # a truly-missing bare embed is --attachments' broken report, not ours.
        comps = tuple(c for c in decoded.split("/") if c not in ("", "."))
        if len(comps) < 2:
            return None
        # A pathed target resolves if it exists relative to the note or vault root,
        # or its path components are a suffix of some real file's path.
        if (note.parent / decoded).exists() or (root / decoded).exists():
            return None
        if suffix_match(comps):
            return None
        # Broken path — repairable only when the basename is unambiguous.
        hits = basename_idx.get(Path(decoded).name, [])
        if len(hits) == 1:
            relinked.append(
                {"note": rel(note, root), "from": decoded, "to": hits[0].name}
            )
            return hits[0].name
        unresolved.append({"note": rel(note, root), "target": decoded})
        return None

    unread: list[dict[str, str]] = []
    edits = _plan_edits(root, include_archive, ext, retarget, None, unread)
    result: dict[str, object] = {"relinked": relinked, "unresolved": unresolved}
    if unreadable is not None:
        unreadable.extend(unread)
    if apply:
        error = _apply([], edits)
        if error:
            result["error"] = error
    return result


# ---------------------------------------------------------------------------
# Operation: convert internal markdown links to wikilinks
# ---------------------------------------------------------------------------


def _link_indexes(root: Path) -> tuple[dict[str, list[Path]], dict[str, list[Path]]]:
    """(notes_by_stem, files_by_name), lowercased key -> Paths."""
    notes: dict[str, list[Path]] = {}
    files: dict[str, list[Path]] = {}
    for p in root.rglob("*"):
        if not p.is_file() or is_ignored(p, root):
            continue
        if p.suffix.lower() == MARKDOWN_SUFFIX:
            notes.setdefault(p.stem.lower(), []).append(p)
        else:
            files.setdefault(p.name.lower(), []).append(p)
    return notes, files


def _resolve_for_wikilink(
    target: str,
    note_dir: Path,
    root: Path,
    notes: dict[str, list[Path]],
    files: dict[str, list[Path]],
) -> tuple[str, str] | None:
    """Resolve a markdown target to (wikitarget, display) or None."""
    path_part, _, anchor = target.partition("#")
    path_part = unquote(path_part.strip())
    if not path_part:
        return None
    anchor = ("#" + anchor) if anchor else ""
    suffix = Path(path_part).suffix.lower()
    resolved: Path | None = None

    if suffix in ("", MARKDOWN_SUFFIX):
        candidate_rel = path_part if suffix == MARKDOWN_SUFFIX else path_part + ".md"
        for cand in (note_dir / candidate_rel, root / candidate_rel):
            if cand.is_file():
                resolved = cand.resolve()
                break
        if resolved is None:
            hits = notes.get(Path(path_part).stem.lower(), [])
            if len(hits) == 1:
                resolved = hits[0].resolve()
        if resolved is None:
            return None
        stem = resolved.stem
        unique = len(notes.get(stem.lower(), [])) == 1
        base = stem if unique else resolved.relative_to(root).with_suffix("").as_posix()
        return f"{base}{anchor}", stem

    for cand in (note_dir / path_part, root / path_part):
        if cand.is_file():
            resolved = cand.resolve()
            break
    if resolved is None:
        hits = files.get(Path(path_part).name.lower(), [])
        if len(hits) == 1:
            resolved = hits[0].resolve()
    if resolved is None:
        return None
    name = resolved.name
    unique = len(files.get(name.lower(), [])) == 1
    base = name if unique else resolved.relative_to(root).as_posix()
    return base, name


def _convert_links(
    text: str,
    note: Path,
    root: Path,
    indexes: tuple[dict[str, list[Path]], dict[str, list[Path]]],
    unresolved: list[dict[str, str]],
) -> tuple[str, int]:
    """Convert internal markdown links in prose (never inside code) to wikilinks."""
    pieces: list[str] = []
    last = count = 0
    for m in CONV_MD_RE.finditer(mask_code(text)):
        bang, label, raw = m.groups()
        target = raw[1:-1] if raw.startswith("<") else raw
        if URL_RE.match(target):
            continue
        res = _resolve_for_wikilink(target, note.parent, root, *indexes)
        if res is None:
            unresolved.append({"note": rel(note, root), "target": target})
            continue
        wikitarget, _display = res
        alias = f"|{label}" if label and label != wikitarget else ""
        pieces += [text[last : m.start()], f"{bang}[[{wikitarget}{alias}]]"]
        last = m.end()
        count += 1
    pieces.append(text[last:])
    return "".join(pieces), count


def op_links(
    root: Path,
    apply: bool,
    include_archive: bool,
    unreadable: list[dict[str, str]] | None = None,
) -> dict:
    root = root.resolve()
    indexes = _link_indexes(root)
    converted: list[dict[str, object]] = []
    unresolved: list[dict[str, str]] = []
    unread: list[dict[str, str]] = []
    edits: list[_Edit] = []

    for note in iter_files(root, (MARKDOWN_SUFFIX,), include_archive=include_archive):
        content = _read(note, root, unread)
        if content is None:
            continue
        new_text, count = _convert_links(content.text, note, root, indexes, unresolved)
        if count:
            converted.append({"note": rel(note, root), "count": count})
            edits.append(_Edit(note, content.text, new_text, content.bom, count))

    result: dict[str, object] = {"converted": converted, "unresolved": unresolved}
    if unreadable is not None:
        unreadable.extend(unread)
    if apply:
        error = _apply([], edits)
        if error:
            result["error"] = error
    return result


# ---------------------------------------------------------------------------
# Operation: report orphan and broken image attachments (report-only)
# ---------------------------------------------------------------------------


def op_attachments(
    root: Path, ext: set[str], unreadable: list[dict[str, str]] | None = None
) -> dict:
    root = root.resolve()
    files = list(iter_attachment_paths(root, ext, include_archive=True))
    basename_idx = image_basename_index(root, ext)
    unread: list[dict[str, str]] = []

    referenced: set[Path] = set()
    broken: list[dict[str, str]] = []
    for path in iter_files(root, TEXT_SUFFIXES, include_archive=True):
        content = _read(path, root, unread)
        if content is None:
            continue
        if path.suffix.lower() == CANVAS_SUFFIX:
            for value in _canvas_files(content.text):
                if (root / value).is_file():
                    referenced.add((root / value).resolve())
            continue
        note_archived = under_archive(path, root)
        for target in _image_targets(content.text, ext):
            hit = resolve_image(target, path.parent, root, basename_idx, ext)
            if hit is not None:
                referenced.add(hit)
            elif not note_archived:
                entry = {"note": rel(path, root), "target": target}
                if entry not in broken:
                    broken.append(entry)

    orphans = sorted(
        rel(f, root)
        for f in files
        if f.resolve() not in referenced and not under_archive(f, root)
    )
    if unreadable is not None:
        unreadable.extend(unread)
    return {"orphans": orphans, "broken": broken}


# ---------------------------------------------------------------------------
# Operation: co-locate attachments to the vault's configured location
# ---------------------------------------------------------------------------


def op_collocate(
    root: Path,
    apply: bool,
    include_archive: bool,
    ext: set[str],
    config_dir: str,
    layout_override: str,
    unreadable: list[dict[str, str]] | None = None,
) -> dict:
    root = root.resolve()
    layout = (
        obsidian_config.parse_layout(layout_override)
        if layout_override
        else obsidian_config.attachment_layout(root, config_dir)
    )
    files = list(iter_attachment_paths(root, ext, include_archive=include_archive))
    basename_idx = image_basename_index(root, ext)
    unread: list[dict[str, str]] = []

    # Which note(s) reference each attachment (ownership decides where it belongs).
    owners: dict[Path, set[Path]] = {}
    for note in iter_files(root, (MARKDOWN_SUFFIX,), include_archive=include_archive):
        content = _read(note, root, unread)
        if content is None:
            continue
        for target in _image_targets(content.text, ext):
            hit = resolve_image(target, note.parent, root, basename_idx, ext)
            if hit is not None:
                owners.setdefault(hit, set()).add(note)

    moved: list[dict[str, str]] = []
    shared: list[dict[str, object]] = []
    conflicts: list[dict[str, str]] = []
    orphans = already = 0
    moves: dict[Path, Path] = {}
    owner_of: dict[Path, Path] = {}
    planned: set[Path] = set()

    for f in sorted(files):
        f_res = f.resolve()
        notes = owners.get(f_res, set())
        if not notes:
            orphans += 1  # no owning note — leave it (--attachments lists these)
            continue
        if len(notes) > 1:
            shared.append(
                {
                    "attachment": rel(f, root),
                    "notes": sorted(rel(n, root) for n in notes),
                }
            )
            continue
        note = next(iter(notes))
        dest = (layout.dest_dir(note, root) / f.name).resolve()
        if dest == f_res:
            already += 1
            continue
        if dest.exists() or dest in planned:  # never overwrite, never collide
            conflicts.append({"attachment": rel(f, root), "dest": rel(dest, root)})
            continue
        planned.add(dest)
        moves[f_res] = dest
        owner_of[f_res] = note

    # A file named by something this run cannot rewrite (a frozen archived note,
    # an undecodable note) must stay where it is.
    frozen = [
        p
        for p in iter_files(root, MENTION_SUFFIXES, include_archive=True)
        if not include_archive and under_archive(p, root)
    ]
    frozen += [root / u["file"] for u in unread]
    skipped = _blocked_by_mentions(frozen, {s: s.name for s in moves}, root, {})
    for src in skipped:
        del moves[src]

    retarget, canvas = _retargeters(root, ext, basename_idx, moves)
    edits = _plan_edits(root, include_archive, ext, retarget, canvas, [])
    for src, dest in sorted(moves.items()):
        moved.append(
            {
                "from": rel(src, root),
                "to": rel(dest, root),
                "note": rel(owner_of[src], root),
            }
        )

    result: dict[str, object] = {
        "layout": {
            "kind": layout.kind,
            "folder": layout.folder,
            "source": layout.source,
            "raw": layout.raw,
        },
        "moved": moved,
        "skipped": [
            {"file": rel(src, root), "reason": reason}
            for src, reason in sorted(skipped.items())
        ],
        "already_placed": already,
        "shared": shared,
        "conflicts": conflicts,
        "orphans": orphans,
        "embeds_rewritten": sum(e.count for e in edits),
    }
    if unreadable is not None:
        unreadable.extend(unread)
    if apply:
        error = _apply(sorted(moves.items()), edits)
        if error:
            result["error"] = error
    return result


# ---------------------------------------------------------------------------
# Operation: prune empty folders, cascading
# ---------------------------------------------------------------------------


def _role_folders(root: Path, config_dir: str) -> set[str]:
    """Lowercased vault-relative folders the vault's routines rely on existing."""
    roles = {
        INBOX_DIR_NAME,
        rel(weekly_dir(root, config_dir=config_dir), root),
        rel(archive_dir(root, config_dir=config_dir), root),
        obsidian_config.daily_notes(root, config_dir).folder,
        *obsidian_config.template_folders(root, config_dir),
    }
    layout = obsidian_config.attachment_layout(root, config_dir)
    if layout.kind == "central" and layout.folder:
        roles.add(layout.folder)
    return {r.strip("/").lower() for r in roles if r.strip("/")}


def op_prune(
    root: Path,
    apply: bool,
    include_archive: bool,
    keep: set[str],
    config_dir: str = DEFAULT_CONFIG_DIR,
) -> dict:
    root = root.resolve()
    roles = _role_folders(root, config_dir)
    candidates: list[Path] = []
    protected: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_dir() or is_ignored(p, root):
            continue
        parts = p.relative_to(root).parts
        if any(part.startswith(".") for part in parts):
            continue  # dot-folders (.stfolder, plugin state) are never ours to remove
        if p.name in keep or rel(p, root).lower() in roles:
            protected.append(p)
            continue
        if not include_archive and under_archive(p, root):
            continue
        candidates.append(p)
    candidates.sort(key=lambda d: (-len(d.parts), d.as_posix()))

    removed: set[Path] = set()
    order: list[Path] = []
    changed = True
    while changed:
        changed = False
        for d in candidates:
            if d not in removed and all(c in removed for c in d.iterdir()):
                removed.add(d)
                order.append(d)
                changed = True

    if apply:
        for d in order:  # deepest-first, so rmdir never hits a non-empty dir
            with contextlib.suppress(OSError):  # raced: something appeared in it
                d.rmdir()
    return {
        "removed": [rel(d, root) for d in order],
        "protected": sorted(
            rel(d, root) for d in protected if all(c in removed for c in d.iterdir())
        ),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--vault", default=".", help="Vault root (default: cwd)")
    parser.add_argument("--all", action="store_true", help="Run every operation")
    parser.add_argument(
        "--rename", action="store_true", help="Rename image attachments"
    )
    parser.add_argument(
        "--dedupe",
        action="store_true",
        help="Collapse byte-identical attachments, repoint embeds",
    )
    parser.add_argument(
        "--relink",
        action="store_true",
        help="Repair broken image embeds by unique basename",
    )
    parser.add_argument(
        "--collocate",
        action="store_true",
        help="Move attachments to the vault's configured location "
        "(opt-in; not part of --all)",
    )
    parser.add_argument(
        "--links", action="store_true", help="Convert md links to wikilinks"
    )
    parser.add_argument(
        "--attachments",
        action="store_true",
        help="Report orphan/broken attachments",
    )
    parser.add_argument("--prune", action="store_true", help="Prune empty folders")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform changes (default: plan/report only)",
    )
    parser.add_argument(
        "--include-archive", action="store_true", help="Also process Archive/"
    )
    parser.add_argument(
        "--ext", default="", help="Extra comma-separated attachment extensions"
    )
    parser.add_argument(
        "--keep",
        default="",
        help="Comma-separated folder names --prune must never remove",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run --links even though the vault is set to markdown links",
    )
    parser.add_argument(
        "--config-dir",
        default=DEFAULT_CONFIG_DIR,
        help="Obsidian config dir (default: .obsidian)",
    )
    parser.add_argument(
        "--layout",
        default="",
        help="Override --collocate layout: root | same-folder "
        "| central:NAME | per-note:NAME (default: read app.json)",
    )
    args = parser.parse_args()

    # --collocate relocates files, so it is opt-in and deliberately NOT in --all.
    do_rename = args.all or args.rename
    do_dedupe = args.all or args.dedupe
    do_relink = args.all or args.relink
    do_collocate = args.collocate
    do_links = args.all or args.links
    do_attach = args.all or args.attachments
    do_prune = args.all or args.prune
    if not (
        do_rename
        or do_dedupe
        or do_relink
        or do_collocate
        or do_links
        or do_attach
        or do_prune
    ):
        parser.error(
            "choose at least one operation (--rename / --dedupe / --relink "
            "/ --collocate / --links / --attachments / --prune / --all)"
        )

    root = require_vault_dir(args.vault)
    if (
        do_links
        and not args.force
        and obsidian_config.link_format(root, args.config_dir).use_markdown_links
    ):
        raise SystemExit(
            "error: this vault is set to markdown links (useMarkdownLinks: true in "
            f"{args.config_dir}/app.json); --links would convert them against the "
            "vault's own setting. Drop --links (or --all), or pass --force."
        )

    ext = set(DEFAULT_EXT)
    ext.update(
        "." + e.strip().lstrip(".").lower() for e in args.ext.split(",") if e.strip()
    )
    keep = {n.strip() for n in args.keep.split(",") if n.strip()}

    operations: list[str] = []
    unreadable: list[dict[str, str]] = []
    result: dict[str, object] = {"vault": str(root), "applied": args.apply}

    # Fixed safe order regardless of flag order: names settle before the rest reads them.
    if do_rename:
        operations.append("rename")
        result["rename"] = op_rename(
            root, args.apply, args.include_archive, ext, unreadable
        )
    if do_dedupe:
        operations.append("dedupe")
        result["dedupe"] = op_dedupe(
            root, args.apply, args.include_archive, ext, unreadable
        )
    if do_relink:
        operations.append("relink")
        result["relink"] = op_relink(
            root, args.apply, args.include_archive, ext, unreadable
        )
    if do_collocate:
        operations.append("collocate")
        result["collocate"] = op_collocate(
            root,
            args.apply,
            args.include_archive,
            ext,
            args.config_dir,
            args.layout,
            unreadable,
        )
    if do_links:
        operations.append("links")
        result["links"] = op_links(root, args.apply, args.include_archive, unreadable)
    if do_attach:
        operations.append("attachments")
        result["attachments"] = op_attachments(root, ext, unreadable)
    if do_prune:
        operations.append("prune")
        result["prune"] = op_prune(
            root, args.apply, args.include_archive, keep, args.config_dir
        )

    result["operations"] = operations
    result["unreadable"] = list({u["file"]: u for u in unreadable}.values())
    emit_json(result)
    failed = any(
        isinstance(result[op], dict) and "error" in result[op] for op in operations
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
