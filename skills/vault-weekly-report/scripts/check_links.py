"""Find broken wikilinks/embeds and (optionally) orphan notes across a vault.

Deterministic backing for vault-structural-scan and the authoring verify step.
A link is broken when its target note name doesn't match any note's filename.
An orphan has neither incoming nor outgoing wikilinks. Archive/ is excluded from
editing scope but still counts as a valid link target.

To avoid false positives on real vaults, a wikilink target is matched by its
basename against the note index, so path-qualified links (`[[../Area/Note]]`,
`[[folder/Note]]` — as Obsidian's relative link format writes them) resolve;
links to non-note files (`[[image.png]]`, `[[data.base]]`) are treated as file
links, not broken notes; and wikilinks inside code spans/fences (documentation
examples) are ignored.

Usage:
    python check_links.py --vault PATH [--orphans]

Output (JSON to stdout):
    {"broken": [{"file", "link", "target", "embed"}], "orphans": ["file", ...]}
"""

import argparse
import re

from _vault import (EMBED_RE, WIKILINK_RE, add_vault_arg, emit_json, iter_notes,
                    link_target, note_index, require_vault_dir, scan_exclude)

_CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")


def _strip_code(text: str) -> str:
    """Drop fenced and inline code so example wikilinks in code aren't counted."""
    return _INLINE_CODE_RE.sub("", _CODE_FENCE_RE.sub("", text))


def _note_key(target: str) -> str:
    """The note-index key for a wikilink target: its basename without a `.md` suffix."""
    base = target.rsplit("/", 1)[-1]
    return (base[:-3] if base.lower().endswith(".md") else base).lower()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_vault_arg(parser)
    parser.add_argument("--orphans", action="store_true", help="Also report orphans")
    args = parser.parse_args()

    vault = require_vault_dir(args.vault)
    index = note_index(vault, include_archive=True)
    notes = iter_notes(vault, include_archive=False, exclude=scan_exclude(vault))

    broken: list[dict[str, object]] = []
    linked_from: set[str] = set()  # notes that are link targets (have incoming)
    has_outgoing: set[str] = set()

    for note in notes:
        text = _strip_code(note.text)
        embeds = set(EMBED_RE.findall(text))
        for raw in WIKILINK_RE.findall(text):
            target = link_target(raw)
            if not target:
                continue
            is_embed = raw in embeds
            if not is_embed:
                has_outgoing.add(note.stem.lower())
            base = target.rsplit("/", 1)[-1]
            key = _note_key(target)
            if key in index:
                linked_from.add(key)
            elif not is_embed and "." not in base:
                # A bare name with no matching note is broken. Targets with a
                # dot are file links (image/base/etc.), not note links — skip.
                broken.append(
                    {
                        "file": str(note.path),
                        "link": raw,
                        "target": target,
                        "embed": is_embed,
                    }
                )

    result: dict[str, object] = {"broken": broken}
    if args.orphans:
        orphans = [
            str(n.path)
            for n in notes
            if n.stem.lower() not in linked_from
            and n.stem.lower() not in has_outgoing
        ]
        result["orphans"] = orphans
    emit_json(result)


if __name__ == "__main__":
    main()
