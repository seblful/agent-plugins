"""Shared helpers for the obsidian-vault deterministic scripts.

Standard library only — these run against a user's live vault folder on any
machine with Python 3.12+, with no third-party dependencies to install.

Four groups of helpers, each behind a banner below:

* **text i/o** — the one way every script reads and writes a note: strict UTF-8
  (an undecodable note is skipped and reported, never "repaired" with
  replacement characters), the BOM and the original line endings preserved on
  write-back.
* **vocabulary** — how a note is classified (daily / weekly / archived /
  general) and where the Weekly/ and Archive/ folders live, discovered from the
  vault's own Obsidian config where possible.
* **scanning** — ignore-aware walks over notes and attachments, plus the
  attachment resolver the cleaner and link checks share.
* **cli** — the argparse/JSON boilerplate every script's `main()` repeats,
  including a guard that turns a mistyped `--vault` into a loud error instead of
  a misleading empty report.

The frontmatter parser here is intentionally tolerant: it recognizes the simple
`key: value` and YAML-list shapes these vaults use, and is meant to *flag* issues
for a human or the calling routine to resolve, not to be a full YAML engine.
"""

import argparse
import codecs
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
EMBED_RE = re.compile(r"!\[\[([^\]]+)\]\]")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2})?$")
DAILY_NAME_RE = re.compile(r"^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})$")
WEEKLY_NAME_RE = re.compile(r"^W\d{1,2}$")
# Lowercase kebab-case segments; `/` separates Obsidian nested tags (`area/deep-work`).
KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*(/[a-z0-9]+(-[a-z0-9]+)*)*$")
FOOTNOTE_DEF_RE = re.compile(r"^\[\^([^\]]+)\]:", re.MULTILINE)
FOOTNOTE_REF_RE = re.compile(r"\[\^([^\]]+)\]")
_FENCE_OPEN_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})[^\n]*$", re.MULTILINE)
_INLINE_CODE_RE = re.compile(r"(`+)(?!`)(.+?)(?<!`)\1(?!`)", re.DOTALL)

DEFAULT_CONFIG_DIR = ".obsidian"
MARKDOWN_SUFFIX = ".md"
CANVAS_SUFFIX = ".canvas"
# Directories never scanned or mutated (matched case-insensitively per segment).
IGNORE_DIRS = frozenset({".git", ".obsidian", ".trash"})
# Vault-convention folder names, matched case-insensitively so a vault whose
# archive is `archive/` (not `Archive/`) is still recognized as the archive.
ARCHIVE_DIR_NAME = "archive"
WEEKLY_DIR_NAME = "weekly"
INBOX_DIR_NAME = "inbox"

IMAGE_EXTS = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".avif"}
)
# Suffixes that make a link target a file rather than a note. Anything else —
# `[[Node.js]]`, `[[Release v1.2]]` — names a note whose title contains a dot.
ATTACHMENT_EXTS = IMAGE_EXTS | frozenset(
    {
        ".mp3", ".wav", ".m4a", ".ogg", ".flac", ".3gp", ".webm",
        ".mp4", ".mov", ".mkv", ".ogv",
        ".pdf", ".canvas", ".base",
        ".csv", ".txt", ".json", ".zip", ".epub", ".html",
        ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    }
)  # fmt: skip


def today() -> date:
    """Today's date on the local clock (the date the user sees)."""
    return datetime.now(UTC).astimezone().date()


# ---------------------------------------------------------------------------
# Text i/o — strict UTF-8, BOM and line endings preserved
# ---------------------------------------------------------------------------


class NoteDecodeError(ValueError):
    """A note is not valid UTF-8: skip and report it, never rewrite it."""

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"{path}: {reason}")
        self.path = path
        self.reason = reason


@dataclass(frozen=True)
class NoteText:
    """A note's decoded text (BOM removed, line endings untouched)."""

    text: str
    bom: bool = False


def read_note_text(path: Path) -> NoteText:
    """Read a note as strict UTF-8; raise `NoteDecodeError` if it is not.

    The text keeps its original line endings (no newline translation), so
    writing it back with `write_note_text` changes only what the caller edited.
    """
    raw = path.read_bytes()
    bom = raw.startswith(codecs.BOM_UTF8)
    if bom:
        raw = raw[len(codecs.BOM_UTF8) :]
    try:
        return NoteText(raw.decode("utf-8"), bom)
    except UnicodeDecodeError as exc:
        raise NoteDecodeError(path, f"not valid UTF-8 ({exc.reason})") from exc


def write_note_text(path: Path, text: str, *, bom: bool = False) -> None:
    """Write text verbatim as UTF-8 — no newline translation, BOM restored."""
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(("﻿" if bom else "") + text)


def unreadable_entry(exc: NoteDecodeError, root: Path | None = None) -> dict[str, str]:
    """The JSON record for a skipped, undecodable note (vault-relative if `root`)."""
    if root is not None:
        try:
            return {"file": exc.path.relative_to(root).as_posix(), "reason": exc.reason}
        except ValueError:
            pass
    return {"file": str(exc.path), "reason": exc.reason}


@dataclass
class Note:
    """A markdown note: its path, raw text, parsed frontmatter, and body."""

    path: Path
    text: str
    frontmatter: dict[str, object] = field(default_factory=dict)
    body: str = ""
    bom: bool = False

    @property
    def stem(self) -> str:
        return self.path.stem


def _unquote_scalar(value: str) -> str:
    return value.strip().strip("\"'")


def parse_frontmatter(text: str) -> tuple[dict[str, object], str]:
    """Split a `---`-fenced YAML frontmatter block from the body.

    Returns (frontmatter_dict, body). Values are str, list[str], or bool.
    Tolerant by design — unknown shapes are kept as raw strings. A leading BOM
    and CRLF line endings are accepted.
    """
    lines = text.removeprefix("﻿").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return {}, text

    fm: dict[str, object] = {}
    current_key: str | None = None
    for raw in lines[1:end]:
        if not raw.strip():
            continue
        list_item = re.match(r"^\s*-\s+(.*)$", raw)
        if list_item and current_key is not None:
            items = fm.setdefault(current_key, [])
            if isinstance(items, list):
                items.append(_unquote_scalar(list_item.group(1)))
            continue
        kv = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", raw)
        if kv:
            key, value = kv.group(1), kv.group(2).strip()
            current_key = key
            if value == "":
                fm[key] = []  # likely a YAML list that follows on later lines
            elif value.lower() in ("true", "false"):
                fm[key] = value.lower() == "true"
            elif value.startswith("[") and value.endswith("]") and "[[" not in value:
                inner = value[1:-1]  # inline flow list: `tags: [a, b]`
                fm[key] = [
                    _unquote_scalar(item) for item in inner.split(",") if item.strip()
                ]
            else:
                fm[key] = _unquote_scalar(value)
    body = "\n".join(lines[end + 1 :])
    return fm, body


def load_note(path: Path) -> Note:
    """Read and parse a note; raises `NoteDecodeError` on non-UTF-8 bytes."""
    content = read_note_text(path)
    fm, body = parse_frontmatter(content.text)
    return Note(
        path=path, text=content.text, frontmatter=fm, body=body, bom=content.bom
    )


def mask_code(text: str) -> str:
    """`text` with fenced and inline code blanked out, same length and offsets.

    Lets a regex find links in prose only; a match's offsets index straight
    back into the original text. Newlines are kept so line structure survives.
    An unclosed fence runs to the end of the note, as in Obsidian.
    """
    chars = list(text)

    def blank(start: int, end: int) -> None:
        for i in range(start, end):
            if chars[i] not in "\r\n":
                chars[i] = " "

    fence = _FENCE_OPEN_RE.search(text)
    while fence:
        marker = fence.group(1)
        close = re.compile(
            rf"^ {{0,3}}{re.escape(marker[0])}{{{len(marker)},}}[ \t]*\r?$",
            re.MULTILINE,
        ).search(text, fence.end())
        end = close.end() if close else len(text)
        blank(fence.start(), end)
        fence = _FENCE_OPEN_RE.search(text, end)

    for m in _INLINE_CODE_RE.finditer("".join(chars)):
        if "\n\n" not in m.group(0):  # inline code never spans a paragraph break
            blank(m.start(), m.end())
    return "".join(chars)


# ---------------------------------------------------------------------------
# Vocabulary — how this vault names and files its notes
# ---------------------------------------------------------------------------

# Named groups let `daily_date` read the date back out of a matched filename.
_DAILY_FORMAT_TOKENS = (
    ("YYYY", r"(?P<year>\d{4})"),
    ("YY", r"(?P<yy>\d{2})"),
    ("MM", r"(?P<month>\d{2})"),
    ("M", r"(?P<month>\d{1,2})"),
    ("DD", r"(?P<day>\d{2})"),
    ("D", r"(?P<day>\d{1,2})"),
)


def _daily_name_regex(fmt: str) -> re.Pattern[str]:
    """Compile an Obsidian daily-note moment.js `format` into a filename regex.

    Only the date tokens a daily-note filename can carry are translated
    (YYYY/YY/MM/M/DD/D); text inside moment `[literal]` brackets and every other
    character is matched literally. A format with sub-path segments
    (`YYYY/YYYY-MM-DD`) contributes only its basename to the name pattern. A
    token that repeats (`MMMM`) is captured once; later copies match unnamed.
    """
    name_fmt = re.sub(r"\[[^\]]*\]", lambda m: m.group(0).replace("/", "\0"), fmt)
    name_fmt = name_fmt.rsplit("/", 1)[-1].replace("\0", "/")
    pattern = ""
    captured: set[str] = set()
    i = 0
    while i < len(name_fmt):
        if name_fmt[i] == "[":
            close = name_fmt.find("]", i + 1)
            if close != -1:
                pattern += re.escape(name_fmt[i + 1 : close])
                i = close + 1
                continue
        for token, rx in _DAILY_FORMAT_TOKENS:
            if name_fmt.startswith(token, i):
                group = rx[4 : rx.index(">")]
                body = rx[rx.index(">") + 1 :]
                pattern += rx if group not in captured else f"(?:{body}"
                captured.add(group)
                i += len(token)
                break
        else:
            pattern += re.escape(name_fmt[i])
            i += 1
    return re.compile(f"^{pattern}$")


def daily_date(stem: str, daily_re: re.Pattern[str]) -> date | None:
    """The date a daily-note filename encodes, or None if it is not a daily note."""
    m = daily_re.match(stem)
    if not m:
        return None
    groups = m.groupdict()
    year = groups.get("year") or (groups.get("yy") and f"20{groups['yy']}")
    try:
        return date(int(year), int(groups["month"]), int(groups["day"]))
    except (KeyError, TypeError, ValueError):
        return None


@dataclass(frozen=True)
class VaultVocabulary:
    """The naming rules used to classify notes. Defaults match CONVENTIONS.md."""

    daily_re: re.Pattern[str] = DAILY_NAME_RE
    weekly_re: re.Pattern[str] = WEEKLY_NAME_RE
    archive_name: str = ARCHIVE_DIR_NAME
    weekly_name: str = WEEKLY_DIR_NAME


DEFAULT_VOCAB = VaultVocabulary()


def vocabulary(vault: Path, config_dir: str = DEFAULT_CONFIG_DIR) -> VaultVocabulary:
    """Discover a vault's vocabulary, falling back to the CONVENTIONS defaults.

    The daily-note filename pattern is taken from the vault's own Obsidian
    `daily-notes.json` `format`, so a vault using e.g. `YYYY.MM.DD` is classified
    correctly instead of against the hardcoded `YYYY-MM-DD`.
    """
    import obsidian_config

    fmt = obsidian_config.daily_notes(vault, config_dir).format
    return VaultVocabulary(daily_re=_daily_name_regex(fmt))


def _rel_parts(path: Path, root: Path) -> set[str]:
    """Lowercased path segments of `path` relative to `root` (absolute if outside)."""
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    return {p.lower() for p in rel.parts}


def is_ignored(path: Path, root: Path) -> bool:
    """True if `path` lies under any never-touch directory (.git/.obsidian/.trash)."""
    return bool(IGNORE_DIRS & _rel_parts(path, root))


def under_archive(
    path: Path, root: Path, vocab: VaultVocabulary = DEFAULT_VOCAB
) -> bool:
    return vocab.archive_name in _rel_parts(path, root)


def is_under(path: Path, root: Path, prefixes: tuple[str, ...]) -> bool:
    """True if `path` sits within any vault-relative folder prefix (lowercased posix)."""
    if not prefixes:
        return False
    try:
        rel = path.relative_to(root).as_posix().lower()
    except ValueError:
        return False
    return any(rel == p or rel.startswith(f"{p}/") for p in prefixes)


def scan_exclude(vault: Path, config_dir: str = DEFAULT_CONFIG_DIR) -> tuple[str, ...]:
    """Vault-relative folder prefixes to skip when scanning note *content*.

    Currently the configured Obsidian template folders — their files are
    placeholders (`{{date}}`, `<% tp... %>`), not real notes to validate or
    link-check. Discovered from the vault's own config, so it adapts per vault.
    """
    import obsidian_config

    return tuple(
        f.strip("/").lower()
        for f in obsidian_config.template_folders(vault, config_dir)
    )


def classify(path: Path, root: Path, vocab: VaultVocabulary = DEFAULT_VOCAB) -> str:
    """Classify a note by path and filename: archived | daily | weekly | general."""
    parts = _rel_parts(path, root)
    if vocab.archive_name in parts:
        return "archived"
    if vocab.daily_re.match(path.stem):
        return "daily"
    if vocab.weekly_name in parts and vocab.weekly_re.match(path.stem):
        return "weekly"
    return "general"


def resolve_subdir(vault: Path, name: str) -> Path:
    """The existing immediate subdir matching `name` case-insensitively, else `vault/name`.

    Lets routines find the vault's real `Archive/` or `Weekly/` folder whatever
    its capitalization, and fall back to the canonical name when creating one.
    """
    target = name.lower()
    if vault.is_dir():
        for child in sorted(vault.iterdir()):
            if child.is_dir() and child.name.lower() == target:
                return child
    return vault / name


def _sibling_of_daily(
    vault: Path, name: str, daily_folder: str | None, config_dir: str
) -> Path:
    """`name` beside the daily folder — inside the vault even when dailies are at root.

    When the daily folder is nested but a vault-root folder of that name already
    exists, the existing one is reused rather than a second one forked.
    """
    import obsidian_config

    if daily_folder is None:
        daily_folder = obsidian_config.daily_notes(vault, config_dir).folder
    daily_folder = daily_folder.strip("/")
    parent = (vault / daily_folder).parent if daily_folder else vault
    sibling = resolve_subdir(parent, name)
    if parent != vault and not sibling.is_dir():
        at_root = resolve_subdir(vault, name)
        if at_root.is_dir():
            return at_root
    return sibling


def weekly_dir(
    vault: Path, daily_folder: str | None = None, config_dir: str = DEFAULT_CONFIG_DIR
) -> Path:
    """The Weekly/ folder: a sibling of the daily folder, always inside the vault.

    `daily_folder` (vault-relative) overrides the configured daily-notes folder.
    """
    return _sibling_of_daily(
        vault, WEEKLY_DIR_NAME.capitalize(), daily_folder, config_dir
    )


def archive_dir(
    vault: Path, daily_folder: str | None = None, config_dir: str = DEFAULT_CONFIG_DIR
) -> Path:
    """The Archive/ folder: a sibling of the daily and weekly folders, inside the vault."""
    return _sibling_of_daily(
        vault, ARCHIVE_DIR_NAME.capitalize(), daily_folder, config_dir
    )


# ---------------------------------------------------------------------------
# Scanning — ignore-aware walks and the shared attachment resolver
# ---------------------------------------------------------------------------


def iter_files(
    vault: Path,
    suffixes: set[str] | frozenset[str] | tuple[str, ...],
    *,
    include_archive: bool = False,
    vocab: VaultVocabulary = DEFAULT_VOCAB,
    exclude: tuple[str, ...] = (),
) -> Iterator[Path]:
    """Yield every file whose suffix is in `suffixes`, skipping ignored dirs (and Archive).

    `exclude` is vault-relative folder prefixes to also skip (e.g. template folders).
    """
    for p in sorted(vault.rglob("*")):
        if p.suffix.lower() not in suffixes or not p.is_file():
            continue
        if is_ignored(p, vault):
            continue
        if not include_archive and under_archive(p, vault, vocab):
            continue
        if is_under(p, vault, exclude):
            continue
        yield p


def iter_markdown_paths(
    vault: Path,
    *,
    include_archive: bool = False,
    vocab: VaultVocabulary = DEFAULT_VOCAB,
    exclude: tuple[str, ...] = (),
) -> Iterator[Path]:
    """Yield every markdown note under the vault, skipping ignored dirs (and Archive)."""
    return iter_files(
        vault,
        (MARKDOWN_SUFFIX,),
        include_archive=include_archive,
        vocab=vocab,
        exclude=exclude,
    )


def iter_notes(
    vault: Path,
    *,
    include_archive: bool = False,
    vocab: VaultVocabulary = DEFAULT_VOCAB,
    exclude: tuple[str, ...] = (),
    unreadable: list[dict[str, str]] | None = None,
) -> list[Note]:
    """Load every markdown note, skipping ignored dirs (and Archive).

    Notes that are not valid UTF-8 are skipped; each is recorded in
    `unreadable` (when given) so the caller can report it.
    """
    notes: list[Note] = []
    for md in iter_markdown_paths(
        vault, include_archive=include_archive, vocab=vocab, exclude=exclude
    ):
        try:
            notes.append(load_note(md))
        except NoteDecodeError as exc:
            if unreadable is not None:
                unreadable.append(unreadable_entry(exc))
    return notes


def note_index(
    vault: Path, *, include_archive: bool = True, vocab: VaultVocabulary = DEFAULT_VOCAB
) -> set[str]:
    """Set of resolvable wikilink targets: note stems (case-insensitive)."""
    return {
        md.stem.lower()
        for md in iter_markdown_paths(
            vault, include_archive=include_archive, vocab=vocab
        )
    }


def iter_attachment_paths(
    vault: Path,
    exts: set[str] | frozenset[str],
    *,
    include_archive: bool = False,
    vocab: VaultVocabulary = DEFAULT_VOCAB,
) -> Iterator[Path]:
    """Yield every attachment file (suffix in `exts`), skipping ignored dirs (and Archive)."""
    return iter_files(vault, exts, include_archive=include_archive, vocab=vocab)


def image_basename_index(
    vault: Path,
    exts: set[str] | frozenset[str],
    *,
    include_archive: bool = True,
    vocab: VaultVocabulary = DEFAULT_VOCAB,
) -> dict[str, list[Path]]:
    """basename -> [resolved paths], for uniqueness checks and basename resolution.

    Indexes the whole vault (Archive included) by default, so a name counts as
    unique only when it is unique everywhere.
    """
    idx: dict[str, list[Path]] = {}
    for p in iter_attachment_paths(
        vault, exts, include_archive=include_archive, vocab=vocab
    ):
        idx.setdefault(p.name, []).append(p.resolve())
    return idx


def link_target(raw: str) -> str:
    """Normalize a wikilink payload to its target note name.

    `Note#Section|Display` -> `Note`; strips alias and heading anchors.
    """
    return raw.split("|", 1)[0].split("#", 1)[0].strip()


def resolve_image(
    target: str,
    note_dir: Path,
    root: Path,
    basename_idx: dict[str, list[Path]],
    exts: set[str] | frozenset[str],
) -> Path | None:
    """Resolve an already-decoded target path to a real attachment file, or None.

    Tries `note_dir/target`, then `root/target`; failing that, a unique basename
    match. Only files whose suffix is in `exts` qualify. This mirrors how
    Obsidian resolves an attachment reference.
    """
    if not target or Path(target).suffix.lower() not in exts:
        return None
    for cand in (note_dir / target, root / target):
        if cand.is_file():
            return cand.resolve()
    hits = basename_idx.get(Path(target).name, [])
    return hits[0] if len(hits) == 1 else None


# ---------------------------------------------------------------------------
# CLI plumbing — shared across every script's main()
# ---------------------------------------------------------------------------


def add_vault_arg(
    parser: argparse.ArgumentParser, help: str = "Vault root (default: cwd)"
) -> None:
    parser.add_argument("--vault", default=".", help=help)


def require_vault_dir(vault: str | Path) -> Path:
    """Resolve `--vault` to an existing directory, or exit(1) with a message.

    Guards against a mistyped path silently scanning nothing and reporting a
    misleading empty ("all clean") result.
    """
    root = Path(vault).resolve()
    if not root.is_dir():
        raise SystemExit(f"error: vault root not found: {root}")
    return root


def emit_json(obj: object) -> None:
    print(json.dumps(obj, indent=2))
