"""Universal, parameterized vault file-cleaner: one command, composable operations.

Pick any combination of operations; they always run in a safe fixed order
(rename -> dedupe -> relink -> collocate -> links -> attachments -> prune)
regardless of flag order, and emit a single JSON report keyed by operation.
Every mutating operation **plans by default and changes nothing until --apply**.
Archive/ is frozen and skipped unless --include-archive is given.

Operations (choose one or more, or --all):
    --rename        Rename image attachments to `YYYY-MM-DD-<unix-ms>.<ext>` and
                    rewrite every resolvable link/embed to them.
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
                    (external URLs left alone).
    --attachments   Report orphan (unreferenced) and broken (missing-target)
                    image attachments. Report-only — never deletes.
    --prune         Remove empty folders, cascading bottom-up.
    --all           Every operation above except --collocate.

Modifiers:
    --vault PATH        Vault root (default: cwd).
    --apply             Perform changes (default: plan/report only).
    --include-archive   Also process notes/files under any Archive/ folder.
    --ext e1,e2         Extra attachment extensions for --rename / --attachments.
    --keep n1,n2        Folder names --prune must never remove, even if empty.
    --config-dir DIR    Obsidian config dir for --collocate (default: .obsidian).
    --layout SPEC       Override --collocate layout: root | same-folder |
                        central:NAME | per-note:NAME (default: read app.json).

Usage:
    python vault_clean.py --vault PATH --all
    python vault_clean.py --vault PATH --all --apply
    python vault_clean.py --vault PATH --rename --links --apply
    python vault_clean.py --vault PATH --collocate           # layout from app.json
    python vault_clean.py --vault PATH --collocate --layout per-note:attachments

Output (JSON to stdout): {"vault", "applied", "operations", <op>: {...}, ...}
"""
from __future__ import annotations

import argparse
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

import obsidian_config
from _vault import (emit_json, image_basename_index, is_ignored,
                    iter_attachment_paths, iter_markdown_paths, iter_notes,
                    link_target, require_vault_dir, resolve_attachment,
                    under_archive)

# ---------------------------------------------------------------------------
# Shared constants and helpers
# ---------------------------------------------------------------------------

DEFAULT_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".avif"}

IMG_RE = re.compile(r"^IMG-(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(\d{0,3})(?:-\d+)?$")
TARGET_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{13}(?:-\d+)?$")
# Rewriting (rename): capture the pieces so links keep their prefix/alias/#subpath.
RENAME_WIKI_RE = re.compile(r"(!?)\[\[([^\[\]#|]+)((?:#[^\[\]|]*)?)((?:\|[^\[\]]*)?)\]\]")
RENAME_MD_RE = re.compile(r"(!?\[[^\]]*\]\()([^)\s]+)(\))")
# Conversion (links): capture bang, label, target for md -> wiki.
CONV_MD_RE = re.compile(r"(!?)\[([^\]]*)\]\(<?([^)\s>]+)>?\)")
# Reference detection (attachments): find link/embed targets.
REF_WIKI_RE = re.compile(r"(!?)\[\[([^\[\]|]+)(?:\|[^\[\]]*)?\]\]")
REF_MD_RE = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)\)")
URL_RE = re.compile(r"^([a-z][a-z0-9+.-]*:|//|#)", re.IGNORECASE)


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


# ---------------------------------------------------------------------------
# Operation: rename image attachments + rewrite links
# ---------------------------------------------------------------------------

def _timestamp_for(path: Path) -> tuple[str, int]:
    """Return (YYYY-MM-DD, unix_ms): from an IMG-... name if present, else mtime."""
    m = IMG_RE.match(path.stem)
    if m:
        y, mo, d, h, mi, s, ms = m.groups()
        ms_val = int((ms or "0").ljust(3, "0"))
        dt = datetime(int(y), int(mo), int(d), int(h), int(mi), int(s),
                      ms_val * 1000, tzinfo=timezone.utc)
    else:
        dt = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d"), int(dt.timestamp() * 1000)


def _plan_renames(images: list[Path], root: Path, ext: set[str]) -> dict[Path, Path]:
    """physical file -> new physical path, with per-directory collision handling."""
    rename_set = set(images)
    used: dict[Path, set[str]] = {}
    for p in iter_attachment_paths(root, ext, include_archive=True):
        if p not in rename_set:
            used.setdefault(p.parent, set()).add(p.name)

    mapping: dict[Path, Path] = {}
    for img in images:
        date, ms = _timestamp_for(img)
        suffix = img.suffix.lower()
        taken = used.setdefault(img.parent, set())
        name = f"{date}-{ms}{suffix}"
        n = 0
        while name in taken:
            n += 1
            name = f"{date}-{ms}-{n}{suffix}"
        taken.add(name)
        mapping[img.resolve()] = (img.parent / name).resolve()
    return mapping


def op_rename(root: Path, apply: bool, include_archive: bool, ext: set[str]) -> dict:
    images = []
    for p in iter_attachment_paths(root, ext, include_archive=include_archive):
        if TARGET_RE.match(p.stem):  # already renamed
            continue
        images.append(p)

    mapping = _plan_renames(images, root, ext)
    basename_idx = image_basename_index(root, ext)
    unresolved: list[dict[str, str]] = []
    edits: list[tuple[Path, str, int]] = []

    for note in iter_markdown_paths(root, include_archive=include_archive):
        text = note.read_text(encoding="utf-8", errors="replace")
        changes = 0

        def new_name_for(target: str) -> str | None:
            if Path(target).suffix.lower() not in ext:
                return None
            resolved = None
            for cand in ((note.parent / target), (root / target)):
                if cand.exists() and cand.suffix.lower() in ext:
                    resolved = cand.resolve()
                    break
            if resolved is None:
                hits = basename_idx.get(Path(target).name, [])
                if len(hits) == 1:
                    resolved = hits[0]
            if resolved is None:
                unresolved.append({"note": rel(note, root), "target": target})
                return None
            return mapping[resolved].name if resolved in mapping else None

        def wl_repl(match: re.Match) -> str:
            nonlocal changes
            bang, target, sub, alias = match.groups()
            new_name = new_name_for(target.strip())
            if new_name is None:
                return match.group(0)
            prefix = target.rsplit("/", 1)[0] + "/" if "/" in target else ""
            changes += 1
            return f"{bang}[[{prefix}{new_name}{sub}{alias}]]"

        def md_repl(match: re.Match) -> str:
            nonlocal changes
            head, target, tail = match.groups()
            new_name = new_name_for(target.strip())
            if new_name is None:
                return match.group(0)
            prefix = target.rsplit("/", 1)[0] + "/" if "/" in target else ""
            changes += 1
            return f"{head}{prefix}{new_name}{tail}"

        new_text = RENAME_WIKI_RE.sub(wl_repl, text)
        new_text = RENAME_MD_RE.sub(md_repl, new_text)
        if changes:
            edits.append((note, new_text, changes))

    if apply:
        for note, new_text, _ in edits:  # links first (old -> new), then files
            note.write_text(new_text, encoding="utf-8")
        for src, dst in mapping.items():
            src.rename(dst)

    return {
        "renames": [{"from": rel(src, root), "to": dst.name}
                    for src, dst in sorted(mapping.items())],
        "notes_updated": len(edits),
        "link_rewrites": sum(c for _, _, c in edits),
        "unresolved": unresolved,
    }


# ---------------------------------------------------------------------------
# Shared: rewrite image link/embed targets in every note
# ---------------------------------------------------------------------------

def _rewrite_image_targets(root: Path, include_archive: bool, ext: set[str],
                           new_target_for) -> list[tuple[Path, str, int]]:
    """Rewrite image link/embed targets via a callback; return edits (unapplied).

    `new_target_for(note_path, target_str)` returns the replacement target (the
    full text that goes between `[[`…`]]` or inside `(…)`), or None to leave it.
    Only image-extension targets are offered. Returns [(note, new_text, count)].
    """
    edits: list[tuple[Path, str, int]] = []
    for note in iter_markdown_paths(root, include_archive=include_archive):
        text = note.read_text(encoding="utf-8", errors="replace")
        count = 0

        def wl_repl(match: re.Match) -> str:
            nonlocal count
            bang, target, sub, alias = match.groups()
            if Path(target.strip()).suffix.lower() not in ext:
                return match.group(0)
            nt = new_target_for(note, target.strip())
            if nt is None:
                return match.group(0)
            count += 1
            return f"{bang}[[{nt}{sub}{alias}]]"

        def md_repl(match: re.Match) -> str:
            nonlocal count
            head, target, tail = match.groups()
            if Path(target.strip()).suffix.lower() not in ext:
                return match.group(0)
            nt = new_target_for(note, target.strip())
            if nt is None:
                return match.group(0)
            count += 1
            return f"{head}{nt}{tail}"

        new_text = RENAME_WIKI_RE.sub(wl_repl, text)
        new_text = RENAME_MD_RE.sub(md_repl, new_text)
        if count:
            edits.append((note, new_text, count))
    return edits


# ---------------------------------------------------------------------------
# Operation: collapse byte-identical attachments (dedupe)
# ---------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def op_dedupe(root: Path, apply: bool, include_archive: bool, ext: set[str]) -> dict:
    files = list(iter_attachment_paths(root, ext, include_archive=include_archive))
    basename_idx = image_basename_index(root, ext)

    by_hash: dict[str, list[Path]] = {}
    for f in files:
        by_hash.setdefault(_sha256(f), []).append(f)

    def canon_key(p: Path):
        r = p.relative_to(root)
        return (0 if TARGET_RE.match(p.stem) else 1, len(r.parts), r.as_posix())

    canon_target: dict[Path, str] = {}  # duplicate resolved path -> canonical target
    groups: list[dict[str, object]] = []
    for paths in by_hash.values():
        if len(paths) < 2:
            continue
        canon = min(paths, key=canon_key)
        unique = len(basename_idx.get(canon.name, [])) == 1
        target = canon.name if unique else canon.relative_to(root).as_posix()
        dups = [p for p in paths if p != canon]
        for d in dups:
            canon_target[d.resolve()] = target
        groups.append({"canonical": rel(canon, root),
                       "duplicates": sorted(rel(d, root) for d in dups)})

    def new_target_for(note: Path, target: str) -> str | None:
        resolved = resolve_attachment(target, note.parent, root, basename_idx, ext)
        if resolved is not None and resolved in canon_target:
            return canon_target[resolved]
        return None

    edits = _rewrite_image_targets(root, include_archive, ext, new_target_for)
    if apply:
        for note, new_text, _ in edits:
            note.write_text(new_text, encoding="utf-8")  # copies left on disk, flagged

    return {"groups": groups, "embeds_rewritten": sum(c for _, _, c in edits)}


# ---------------------------------------------------------------------------
# Operation: repair broken image embeds by unique basename (relink)
# ---------------------------------------------------------------------------

def op_relink(root: Path, apply: bool, include_archive: bool, ext: set[str]) -> dict:
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

    def new_target_for(note: Path, target: str) -> str | None:
        literal = unquote(target)
        if Path(literal).suffix.lower() not in ext:
            return None
        # Bare basenames (no folder) are Obsidian's own to resolve — leave them;
        # a truly-missing bare embed is check_attachments' broken report, not ours.
        comps = tuple(c for c in literal.split("/") if c not in ("", "."))
        if len(comps) < 2:
            return None
        # A pathed target resolves if it exists relative to the note or vault root,
        # or its path components are a suffix of some real file's path.
        if (note.parent / literal).exists() or (root / literal).exists():
            return None
        if suffix_match(comps):
            return None
        # Broken path — repairable only when the basename is unambiguous.
        hits = basename_idx.get(Path(literal).name, [])
        if len(hits) == 1:
            name = hits[0].name
            relinked.append({"note": rel(note, root), "from": target, "to": name})
            return name
        unresolved.append({"note": rel(note, root), "target": target})
        return None

    edits = _rewrite_image_targets(root, include_archive, ext, new_target_for)
    if apply:
        for note, new_text, _ in edits:
            note.write_text(new_text, encoding="utf-8")

    return {"relinked": relinked, "unresolved": unresolved}


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
        if p.suffix.lower() == ".md":
            notes.setdefault(p.stem.lower(), []).append(p)
        else:
            files.setdefault(p.name.lower(), []).append(p)
    return notes, files


def _resolve_for_wikilink(target: str, note_dir: Path, root: Path,
                          notes: dict[str, list[Path]],
                          files: dict[str, list[Path]]):
    """Resolve a markdown target to (wikitarget, display) or None."""
    path_part, _, anchor = target.partition("#")
    path_part = unquote(path_part.strip())
    if not path_part:
        return None
    anchor = ("#" + anchor) if anchor else ""
    suffix = Path(path_part).suffix.lower()
    resolved: Path | None = None

    if suffix in ("", ".md"):
        candidate_rel = path_part if suffix == ".md" else path_part + ".md"
        for cand in (note_dir / candidate_rel, root / candidate_rel):
            if cand.exists() and cand.suffix.lower() == ".md":
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


def op_links(root: Path, apply: bool, include_archive: bool) -> dict:
    notes, files = _link_indexes(root)
    converted: list[dict[str, object]] = []
    unresolved: list[dict[str, str]] = []

    for note in iter_markdown_paths(root, include_archive=include_archive):
        text = note.read_text(encoding="utf-8", errors="replace")
        count = 0

        def repl(match: re.Match) -> str:
            nonlocal count
            bang, label, target = match.groups()
            if URL_RE.match(target):
                return match.group(0)
            res = _resolve_for_wikilink(target, note.parent, root, notes, files)
            if res is None:
                unresolved.append({"note": rel(note, root), "target": target})
                return match.group(0)
            wikitarget, display = res
            count += 1
            if label and label != display and label != wikitarget:
                return f"{bang}[[{wikitarget}|{label}]]"
            return f"{bang}[[{wikitarget}]]"

        new_text = CONV_MD_RE.sub(repl, text)
        if count:
            converted.append({"note": rel(note, root), "count": count})
            if apply:
                note.write_text(new_text, encoding="utf-8")

    return {"converted": converted, "unresolved": unresolved}


# ---------------------------------------------------------------------------
# Operation: report orphan and broken image attachments (report-only)
# ---------------------------------------------------------------------------

def _iter_image_targets(text: str, ext: set[str]) -> list[str]:
    """Every image link/embed target in a note's text (wiki and markdown)."""
    out: list[str] = []
    for _bang, raw in REF_WIKI_RE.findall(text):
        if Path(link_target(raw)).suffix.lower() in ext:
            out.append(raw)
    for raw in REF_MD_RE.findall(text):
        if URL_RE.match(raw):
            continue
        if Path(unquote(link_target(raw)).strip()).suffix.lower() in ext:
            out.append(raw)
    return out


def op_attachments(root: Path, ext: set[str]) -> dict:
    files = list(iter_attachment_paths(root, ext, include_archive=True))
    basename_idx = image_basename_index(root, ext)

    referenced: set[Path] = set()
    broken: list[dict[str, str]] = []

    for note in iter_notes(root, include_archive=True):
        note_archived = under_archive(note.path, root)
        for raw in _iter_image_targets(note.text, ext):
            hit = resolve_attachment(raw, note.path.parent, root, basename_idx, ext)
            if hit is not None:
                referenced.add(hit)
            elif not note_archived:
                broken.append({"note": rel(note.path, root),
                               "target": link_target(raw).strip()})

    orphans = sorted(rel(f, root) for f in files
                     if f.resolve() not in referenced and not under_archive(f, root))
    seen = set()
    broken_unique = []
    for b in broken:
        key = (b["note"], b["target"])
        if key not in seen:
            seen.add(key)
            broken_unique.append(b)
    return {"orphans": orphans, "broken": broken_unique}


# ---------------------------------------------------------------------------
# Operation: co-locate attachments to the vault's configured location
# ---------------------------------------------------------------------------

def op_collocate(root: Path, apply: bool, include_archive: bool, ext: set[str],
                 config_dir: str, layout_override: str) -> dict:
    layout = (obsidian_config.parse_layout(layout_override) if layout_override
              else obsidian_config.attachment_layout(root, config_dir))

    files = list(iter_attachment_paths(root, ext, include_archive=include_archive))
    basename_idx = image_basename_index(root, ext)

    # Which note(s) reference each attachment (ownership decides where it belongs).
    owners: dict[Path, set[Path]] = {}
    for note in iter_notes(root, include_archive=include_archive):
        for raw in _iter_image_targets(note.text, ext):
            hit = resolve_attachment(raw, note.path.parent, root, basename_idx, ext)
            if hit is not None:
                owners.setdefault(hit, set()).add(note.path)

    moved: list[dict[str, str]] = []
    shared: list[dict[str, object]] = []
    conflicts: list[dict[str, str]] = []
    orphans = already = 0
    move_map: dict[Path, Path] = {}
    new_target: dict[Path, str] = {}

    for f in sorted(files):
        f_res = f.resolve()
        notes = owners.get(f_res, set())
        if not notes:
            orphans += 1  # no owning note — leave it (check --attachments lists these)
            continue
        if len(notes) > 1:
            shared.append({"attachment": rel(f, root),
                           "notes": sorted(rel(n, root) for n in notes)})
            continue
        note = next(iter(notes))
        dest = (layout.dest_dir(note, root) / f.name).resolve()
        if dest == f_res:
            already += 1
            continue
        if dest.exists():  # a different file already holds that name — never overwrite
            conflicts.append({"attachment": rel(f, root), "dest": rel(dest, root)})
            continue
        move_map[f_res] = dest
        unique = len(basename_idx.get(f.name, [])) == 1
        new_target[f_res] = f.name if unique else dest.relative_to(root).as_posix()
        moved.append({"from": rel(f, root), "to": rel(dest, root),
                      "note": rel(note, root)})

    def new_target_for(note_path: Path, target: str) -> str | None:
        hit = resolve_attachment(target, note_path.parent, root, basename_idx, ext)
        return new_target.get(hit) if hit is not None else None

    edits = _rewrite_image_targets(root, include_archive, ext, new_target_for)
    if apply:
        for note_path, new_text, _ in edits:  # rewrite links first, then move files
            note_path.write_text(new_text, encoding="utf-8")
        for src, dest in move_map.items():
            dest.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dest)

    return {
        "layout": {"kind": layout.kind, "folder": layout.folder,
                   "source": layout.source, "raw": layout.raw},
        "moved": moved,
        "already_placed": already,
        "shared": shared,
        "conflicts": conflicts,
        "orphans": orphans,
        "embeds_rewritten": sum(c for _, _, c in edits),
    }


# ---------------------------------------------------------------------------
# Operation: prune empty folders, cascading
# ---------------------------------------------------------------------------

def _prunable_dirs(root: Path, include_archive: bool, keep: set[str]) -> list[Path]:
    dirs = []
    for p in root.rglob("*"):
        if not p.is_dir() or p == root or is_ignored(p, root):
            continue
        if not include_archive and under_archive(p, root):
            continue
        if p.name in keep:
            continue
        dirs.append(p)
    return sorted(dirs, key=lambda d: len(d.parts), reverse=True)


def op_prune(root: Path, apply: bool, include_archive: bool, keep: set[str]) -> dict:
    removed: set[Path] = set()
    order: list[Path] = []
    changed = True
    while changed:
        changed = False
        for d in _prunable_dirs(root, include_archive, keep):
            if d in removed:
                continue
            if not [c for c in d.iterdir() if c not in removed]:
                removed.add(d)
                order.append(d)
                changed = True

    if apply:
        for d in order:  # deepest-first, so rmdir never hits a non-empty dir
            try:
                d.rmdir()
            except OSError:
                pass
    return {"removed": [rel(d, root) for d in order]}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--vault", default=".", help="Vault root (default: cwd)")
    parser.add_argument("--all", action="store_true", help="Run every operation")
    parser.add_argument("--rename", action="store_true", help="Rename image attachments")
    parser.add_argument("--dedupe", action="store_true",
                        help="Collapse byte-identical attachments, repoint embeds")
    parser.add_argument("--relink", action="store_true",
                        help="Repair broken image embeds by unique basename")
    parser.add_argument("--collocate", action="store_true",
                        help="Move attachments to the vault's configured location "
                             "(opt-in; not part of --all)")
    parser.add_argument("--links", action="store_true", help="Convert md links to wikilinks")
    parser.add_argument("--attachments", action="store_true",
                        help="Report orphan/broken attachments")
    parser.add_argument("--prune", action="store_true", help="Prune empty folders")
    parser.add_argument("--apply", action="store_true",
                        help="Perform changes (default: plan/report only)")
    parser.add_argument("--include-archive", action="store_true",
                        help="Also process Archive/")
    parser.add_argument("--ext", default="",
                        help="Extra comma-separated attachment extensions")
    parser.add_argument("--keep", default="",
                        help="Comma-separated folder names --prune must never remove")
    parser.add_argument("--config-dir", default=obsidian_config.DEFAULT_CONFIG_DIR,
                        help="Obsidian config dir for --collocate (default: .obsidian)")
    parser.add_argument("--layout", default="",
                        help="Override --collocate layout: root | same-folder "
                             "| central:NAME | per-note:NAME (default: read app.json)")
    args = parser.parse_args()

    # --collocate relocates files, so it is opt-in and deliberately NOT in --all.
    do_rename = args.all or args.rename
    do_dedupe = args.all or args.dedupe
    do_relink = args.all or args.relink
    do_collocate = args.collocate
    do_links = args.all or args.links
    do_attach = args.all or args.attachments
    do_prune = args.all or args.prune
    if not (do_rename or do_dedupe or do_relink or do_collocate
            or do_links or do_attach or do_prune):
        parser.error("choose at least one operation (--rename / --dedupe / --relink "
                     "/ --collocate / --links / --attachments / --prune / --all)")

    root = require_vault_dir(args.vault)

    ext = set(DEFAULT_EXT)
    ext.update("." + e.strip().lstrip(".").lower()
               for e in args.ext.split(",") if e.strip())
    keep = {n.strip() for n in args.keep.split(",") if n.strip()}

    operations: list[str] = []
    result: dict[str, object] = {"vault": str(root), "applied": args.apply}

    # Fixed safe order regardless of flag order: names settle before the rest reads them.
    if do_rename:
        operations.append("rename")
        result["rename"] = op_rename(root, args.apply, args.include_archive, ext)
    if do_dedupe:
        operations.append("dedupe")
        result["dedupe"] = op_dedupe(root, args.apply, args.include_archive, ext)
    if do_relink:
        operations.append("relink")
        result["relink"] = op_relink(root, args.apply, args.include_archive, ext)
    if do_collocate:
        operations.append("collocate")
        result["collocate"] = op_collocate(root, args.apply, args.include_archive,
                                            ext, args.config_dir, args.layout)
    if do_links:
        operations.append("links")
        result["links"] = op_links(root, args.apply, args.include_archive)
    if do_attach:
        operations.append("attachments")
        result["attachments"] = op_attachments(root, ext)
    if do_prune:
        operations.append("prune")
        result["prune"] = op_prune(root, args.apply, args.include_archive, keep)

    result["operations"] = operations
    emit_json(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
