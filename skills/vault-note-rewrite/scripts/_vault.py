"""Shared helpers for the obsidian-vault deterministic scripts.

Standard library only — these run against a user's live vault folder on any
machine with Python 3.12+, with no third-party dependencies to install.

Three groups of helpers, each behind a banner below:

* **scanning** — ignore-aware walks over notes and attachments, plus the
  attachment resolver the cleaner and link checks share. One definition of
  "which files count" (skip `.git`/`.obsidian`/`.trash`, and `Archive/` unless
  asked) instead of a copy per script.
* **vocabulary** — how a note is classified (daily / weekly / archived /
  general), discovered from the vault's own Obsidian config where possible so
  classification tracks the vault rather than a hardcoded guess.
* **cli** — the argparse/JSON boilerplate every script's `main()` repeats,
  including a guard that turns a mistyped `--vault` into a loud error instead of
  a misleading empty report.

The frontmatter parser here is intentionally tolerant: it recognizes the simple
`key: value` and YAML-list shapes these vaults use, and is meant to *flag* issues
for a human or the calling routine to resolve, not to be a full YAML engine.
"""

import argparse
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
EMBED_RE = re.compile(r"!\[\[([^\]]+)\]\]")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2})?$")
DAILY_NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
WEEKLY_NAME_RE = re.compile(r"^W\d{1,2}$")
KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
FOOTNOTE_DEF_RE = re.compile(r"^\[\^([^\]]+)\]:", re.MULTILINE)
FOOTNOTE_REF_RE = re.compile(r"(?<!^)\[\^([^\]]+)\]")

DEFAULT_CONFIG_DIR = ".obsidian"
MARKDOWN_SUFFIX = ".md"
# Directories never scanned or mutated (matched case-insensitively per segment).
IGNORE_DIRS = frozenset({".git", ".obsidian", ".trash"})
# Vault-convention folder names, matched case-insensitively so a vault whose
# archive is `archive/` (not `Archive/`) is still recognized as the archive.
ARCHIVE_DIR_NAME = "archive"
WEEKLY_DIR_NAME = "weekly"


@dataclass
class Note:
    """A markdown note: its path, raw text, parsed frontmatter, and body."""

    path: Path
    text: str
    frontmatter: dict[str, object] = field(default_factory=dict)
    body: str = ""

    @property
    def stem(self) -> str:
        return self.path.stem


def parse_frontmatter(text: str) -> tuple[dict[str, object], str]:
    """Split a `---`-fenced YAML frontmatter block from the body.

    Returns (frontmatter_dict, body). Values are str, list[str], or bool.
    Tolerant by design — unknown shapes are kept as raw strings.
    """
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
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
            fm.setdefault(current_key, [])
            if isinstance(fm[current_key], list):
                fm[current_key].append(list_item.group(1).strip())  # type: ignore[union-attr]
            continue
        kv = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", raw)
        if kv:
            key, value = kv.group(1), kv.group(2).strip()
            current_key = key
            if value == "":
                fm[key] = []  # likely a YAML list that follows on later lines
            elif value.lower() in ("true", "false"):
                fm[key] = value.lower() == "true"
            elif value.startswith("[") and value.endswith("]"):
                inner = value[1:-1].strip()  # inline flow list: `tags: [a, b]`
                fm[key] = [item.strip().strip("\"'") for item in inner.split(",")
                           if item.strip()] if inner else []
            else:
                fm[key] = value.strip("\"'")
    body = "\n".join(lines[end + 1 :])
    return fm, body


def load_note(path: Path) -> Note:
    text = path.read_text(encoding="utf-8", errors="replace")
    fm, body = parse_frontmatter(text)
    return Note(path=path, text=text, frontmatter=fm, body=body)


# ---------------------------------------------------------------------------
# Vocabulary — how this vault names and files its notes
# ---------------------------------------------------------------------------

_DAILY_FORMAT_TOKENS = (
    ("YYYY", r"\d{4}"), ("YY", r"\d{2}"),
    ("MM", r"\d{2}"), ("M", r"\d{1,2}"),
    ("DD", r"\d{2}"), ("D", r"\d{1,2}"),
)


def _daily_name_regex(fmt: str) -> re.Pattern[str]:
    """Compile an Obsidian daily-note moment.js `format` into a filename regex.

    Only the date tokens a daily-note filename can carry are translated
    (YYYY/YY/MM/M/DD/D); moment `[literal]` brackets are dropped and every other
    character is matched literally. A format with sub-path segments
    (`YYYY/YYYY-MM-DD`) contributes only its basename to the name pattern.
    """
    name_fmt = fmt.replace("[", "").replace("]", "").rsplit("/", 1)[-1]
    pattern = ""
    i = 0
    while i < len(name_fmt):
        for token, rx in _DAILY_FORMAT_TOKENS:
            if name_fmt.startswith(token, i):
                pattern += rx
                i += len(token)
                break
        else:
            pattern += re.escape(name_fmt[i])
            i += 1
    return re.compile(f"^{pattern}$")


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


def under_archive(path: Path, root: Path, vocab: VaultVocabulary = DEFAULT_VOCAB) -> bool:
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

    return tuple(f.strip("/").lower()
                 for f in obsidian_config.template_folders(vault, config_dir))


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
        for child in vault.iterdir():
            if child.is_dir() and child.name.lower() == target:
                return child
    return vault / name


# ---------------------------------------------------------------------------
# Scanning — ignore-aware walks and the shared attachment resolver
# ---------------------------------------------------------------------------

def iter_markdown_paths(vault: Path, *, include_archive: bool = False,
                        vocab: VaultVocabulary = DEFAULT_VOCAB,
                        exclude: tuple[str, ...] = ()) -> Iterator[Path]:
    """Yield every markdown note under the vault, skipping ignored dirs (and Archive).

    `exclude` is vault-relative folder prefixes to also skip (e.g. template folders).
    """
    for md in sorted(vault.rglob(f"*{MARKDOWN_SUFFIX}")):
        if is_ignored(md, vault):
            continue
        if not include_archive and under_archive(md, vault, vocab):
            continue
        if is_under(md, vault, exclude):
            continue
        yield md


def iter_notes(vault: Path, *, include_archive: bool = False,
               vocab: VaultVocabulary = DEFAULT_VOCAB,
               exclude: tuple[str, ...] = ()) -> list[Note]:
    """Load every markdown note under the vault, skipping ignored dirs (and Archive)."""
    return [load_note(md) for md in
            iter_markdown_paths(vault, include_archive=include_archive,
                                vocab=vocab, exclude=exclude)]


def note_index(vault: Path, *, include_archive: bool = True,
               vocab: VaultVocabulary = DEFAULT_VOCAB) -> set[str]:
    """Set of resolvable wikilink targets: note stems (case-insensitive)."""
    return {md.stem.lower() for md in
            iter_markdown_paths(vault, include_archive=include_archive, vocab=vocab)}


def iter_attachment_paths(vault: Path, exts: set[str], *, include_archive: bool = False,
                          vocab: VaultVocabulary = DEFAULT_VOCAB) -> Iterator[Path]:
    """Yield every attachment file (suffix in `exts`), skipping ignored dirs (and Archive)."""
    for p in sorted(vault.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in exts:
            continue
        if is_ignored(p, vault):
            continue
        if not include_archive and under_archive(p, vault, vocab):
            continue
        yield p


def image_basename_index(vault: Path, exts: set[str], *, include_archive: bool = True,
                         vocab: VaultVocabulary = DEFAULT_VOCAB) -> dict[str, list[Path]]:
    """basename -> [resolved paths], for uniqueness checks and basename resolution.

    Indexes the whole vault (Archive included) by default, so a name counts as
    unique only when it is unique everywhere.
    """
    idx: dict[str, list[Path]] = {}
    for p in iter_attachment_paths(vault, exts, include_archive=include_archive, vocab=vocab):
        idx.setdefault(p.name, []).append(p.resolve())
    return idx


def link_target(raw: str) -> str:
    """Normalize a wikilink payload to its target note name.

    `Note#Section|Display` -> `Note`; strips alias and heading anchors.
    """
    return raw.split("|", 1)[0].split("#", 1)[0].strip()


def resolve_attachment(target: str, note_dir: Path, root: Path,
                       basename_idx: dict[str, list[Path]], exts: set[str]) -> Path | None:
    """Resolve a link/embed target to a real attachment file, or None.

    Tries `note_dir/target`, then `root/target`; failing that, a unique basename
    match. Only files whose suffix is in `exts` qualify. This mirrors how
    Obsidian resolves an attachment reference.
    """
    target = unquote(link_target(target).strip())
    if not target or Path(target).suffix.lower() not in exts:
        return None
    for cand in (note_dir / target, root / target):
        if cand.exists() and cand.suffix.lower() in exts:
            return cand.resolve()
    hits = basename_idx.get(Path(target).name, [])
    return hits[0] if len(hits) == 1 else None


# ---------------------------------------------------------------------------
# CLI plumbing — shared across every script's main()
# ---------------------------------------------------------------------------

def add_vault_arg(parser: argparse.ArgumentParser,
                  help: str = "Vault root (default: cwd)") -> None:
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
