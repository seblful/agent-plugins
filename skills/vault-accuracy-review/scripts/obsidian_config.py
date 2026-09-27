"""Central reader for an Obsidian vault's own settings (`.obsidian/*.json`).

These routines run against a live vault, so the vault's *configured* behaviour —
where attachments go, whether internal links are wikilinks or markdown, which
folder and filename format daily notes use — should come from Obsidian itself,
not from a question to the user or a hardcoded guess. This module reads the
relevant config files once and exposes them as typed values with documented
fallbacks, so every routine and script discovers the vault's conventions the
same way. Fewer questions, and correct for any vault.

Stdlib only, and tolerant: a missing file or key yields the documented default,
never an error — so it works even on a fresh vault that hasn't written configs.

Import:  from obsidian_config import attachment_layout, link_format, daily_notes
Run:     python obsidian_config.py --vault PATH [--config-dir .obsidian]
         -> dumps the resolved settings as JSON, for prose routines to consume.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_CONFIG_DIR = ".obsidian"


def _load(vault: Path, name: str, config_dir: str) -> dict:
    """Parse a `.obsidian/<name>` JSON file; {} if absent or unreadable."""
    p = vault / config_dir / name
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    except (ValueError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


# --- Attachments -----------------------------------------------------------

@dataclass
class AttachmentLayout:
    """Where new attachments live, from `app.json`'s `attachmentFolderPath`.

    kind:   root | central | same-folder | per-note
    folder: subfolder name for central/per-note; None otherwise
    source: app.json | override | fallback
    raw:    the raw setting value, if one was found
    """

    kind: str
    folder: str | None
    source: str
    raw: str | None

    def dest_dir(self, note_path: Path, vault: Path) -> Path:
        """The folder an attachment owned by `note_path` should live in."""
        if self.kind == "root":
            return vault
        if self.kind == "central":
            return vault / self.folder  # type: ignore[operator]
        if self.kind == "same-folder":
            return note_path.parent
        return note_path.parent / self.folder  # type: ignore[operator]  # per-note


def attachment_layout(vault: Path, config_dir: str = DEFAULT_CONFIG_DIR, *,
                      fallback: tuple[str, str | None] = ("per-note", "attachments")
                      ) -> AttachmentLayout:
    """Resolve the vault's attachment location. Maps `attachmentFolderPath`:

    `/` -> root | `./` -> same-folder | `./sub` -> per-note `sub`
    | a plain path -> central. Missing/empty -> the documented fallback.
    """
    raw = _load(vault, "app.json", config_dir).get("attachmentFolderPath")
    raw = raw if isinstance(raw, str) else None
    if raw is not None:
        v = raw.strip()
        if v == "/":
            return AttachmentLayout("root", None, "app.json", raw)
        if v.startswith("./"):
            sub = v[2:].strip("/")
            if sub:
                return AttachmentLayout("per-note", sub, "app.json", raw)
            return AttachmentLayout("same-folder", None, "app.json", raw)
        if v not in ("", "."):
            return AttachmentLayout("central", v.strip("/"), "app.json", raw)
    kind, folder = fallback
    return AttachmentLayout(kind, folder, "fallback", raw)


def parse_layout(spec: str) -> AttachmentLayout:
    """Parse a manual override: root | same-folder | central:NAME | per-note:NAME."""
    if spec in ("root", "same-folder"):
        return AttachmentLayout(spec, None, "override", None)
    kind, sep, name = spec.partition(":")
    if sep and kind in ("central", "per-note") and name:
        return AttachmentLayout(kind, name, "override", None)
    raise ValueError(
        f"bad layout {spec!r}: use root | same-folder | central:NAME | per-note:NAME")


# --- Links -----------------------------------------------------------------

@dataclass
class LinkFormat:
    use_markdown_links: bool  # app.json.useMarkdownLinks (default False = wikilinks)
    new_link_format: str      # shortest | relative | absolute
    source: str


def link_format(vault: Path, config_dir: str = DEFAULT_CONFIG_DIR) -> LinkFormat:
    """The vault's internal-link style, from `app.json`."""
    app = _load(vault, "app.json", config_dir)
    present = "useMarkdownLinks" in app or "newLinkFormat" in app
    return LinkFormat(
        use_markdown_links=bool(app.get("useMarkdownLinks", False)),
        new_link_format=str(app.get("newLinkFormat", "shortest")),
        source="app.json" if present else "fallback",
    )


# --- Daily notes -----------------------------------------------------------

@dataclass
class DailyNotes:
    folder: str          # "" = vault root
    format: str          # moment.js format; default YYYY-MM-DD
    template: str | None
    source: str


def daily_notes(vault: Path, config_dir: str = DEFAULT_CONFIG_DIR) -> DailyNotes:
    """The daily-notes folder and filename format, from `daily-notes.json`."""
    dn = _load(vault, "daily-notes.json", config_dir)
    return DailyNotes(
        folder=str(dn.get("folder", "")).strip("/"),
        format=str(dn.get("format") or "YYYY-MM-DD"),
        template=(dn.get("template") or None),
        source="daily-notes.json" if dn else "fallback",
    )


# --- Templates -------------------------------------------------------------

def template_folders(vault: Path, config_dir: str = DEFAULT_CONFIG_DIR) -> list[str]:
    """Configured template folders, from the core Templates and Templater plugins.

    Reads `templates.json` (`folder`) and, if present, the Templater community
    plugin's `plugins/templater-obsidian/data.json` (`templates_folder`). Returns
    the vault-relative folder paths (deduplicated), or [] if none are set. Their
    files are placeholders, not real notes, so content scans skip them.
    """
    folders: list[str] = []
    core = _load(vault, "templates.json", config_dir).get("folder")
    if isinstance(core, str) and core.strip("/"):
        folders.append(core.strip("/"))
    templater = _load(vault, "plugins/templater-obsidian/data.json",
                      config_dir).get("templates_folder")
    if isinstance(templater, str) and templater.strip("/"):
        folders.append(templater.strip("/"))
    seen: set[str] = set()
    out: list[str] = []
    for f in folders:
        if f.lower() not in seen:
            seen.add(f.lower())
            out.append(f)
    return out


def resolve_all(vault: Path, config_dir: str = DEFAULT_CONFIG_DIR) -> dict:
    """Everything above, resolved, as a plain dict (what the CLI prints)."""
    return {
        "vault": str(Path(vault).resolve()),
        "config_dir": config_dir,
        "attachment_layout": asdict(attachment_layout(vault, config_dir)),
        "link_format": asdict(link_format(vault, config_dir)),
        "daily_notes": asdict(daily_notes(vault, config_dir)),
        "template_folders": template_folders(vault, config_dir),
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Dump an Obsidian vault's resolved settings as JSON.")
    ap.add_argument("--vault", default=".", help="Vault root (default: cwd)")
    ap.add_argument("--config-dir", default=DEFAULT_CONFIG_DIR,
                    help="Obsidian config dir (default: .obsidian)")
    args = ap.parse_args()
    print(json.dumps(resolve_all(Path(args.vault), args.config_dir), indent=2))


if __name__ == "__main__":
    main()
