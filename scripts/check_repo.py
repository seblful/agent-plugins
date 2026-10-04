"""Check the repo rules in AGENTS.md that no runtime validator enforces."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

LINK_RE = re.compile(r"\]\(([^)\s]+)\)")
CODE_RE = re.compile(r"```.*?```|`[^`\n]*`", re.DOTALL)
SKIP_LINK_PREFIXES = ("http://", "https://", "mailto:", "#")
REQUIRED_PHRASES = ("Use when", "Not for")


def read_frontmatter(path: Path) -> dict[str, str]:
    """Return the flat `key: value` pairs of a markdown file's frontmatter."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, sep, value = line.partition(":")
        if not sep or line.startswith((" ", "\t", "-")):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1].replace('\\"', '"')
        fields[key.strip()] = value
    return fields


def check_manifests(root: Path) -> list[str]:
    marketplace = json.loads(
        (root / ".claude-plugin/marketplace.json").read_text(encoding="utf-8")
    )
    errors = []
    for entry in marketplace["plugins"]:
        manifest_path = root / entry["source"] / ".claude-plugin/plugin.json"
        if not manifest_path.is_file():
            errors.append(f"{entry['name']}: missing {manifest_path}")
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("name") != entry["name"]:
            errors.append(
                f"{entry['name']}: plugin.json name is {manifest.get('name')!r}"
            )
        if manifest.get("description") != entry.get("description"):
            errors.append(
                f"{entry['name']}: description differs between plugin.json and marketplace.json"
            )
    return errors


def check_components(root: Path) -> list[str]:
    errors = []
    readme = (root / "README.md").read_text(encoding="utf-8")
    skills = sorted(root.glob("plugins/*/skills/*/SKILL.md"))
    agents = sorted(root.glob("plugins/*/agents/*.md"))
    for path in skills + agents:
        rel = path.relative_to(root).as_posix()
        expected = path.parent.name if path.name == "SKILL.md" else path.stem
        fields = read_frontmatter(path)
        if fields.get("name") != expected:
            errors.append(f"{rel}: name {fields.get('name')!r} != {expected!r}")
        description = fields.get("description", "")
        for phrase in REQUIRED_PHRASES:
            if phrase not in description:
                errors.append(f"{rel}: description lacks {phrase!r}")
        if f"**{expected}**" not in readme:
            errors.append(f"{rel}: no **{expected}** bullet in README.md")
    for path in root.glob("plugins/*/skills/**/*.md"):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(root).as_posix()
        if "../../" in text or "CLAUDE_PLUGIN_ROOT" in text:
            errors.append(
                f"{rel}: skills may reach only their own or a sibling directory"
            )
    return errors


def check_links(root: Path) -> list[str]:
    errors = []
    docs = [root / "README.md", root / "AGENTS.md", *root.glob("plugins/**/*.md")]
    for path in docs:
        prose = CODE_RE.sub("", path.read_text(encoding="utf-8"))
        for target in LINK_RE.findall(prose):
            if target.startswith(SKIP_LINK_PREFIXES) or any(c in target for c in "<{$"):
                continue
            file_part = target.split("#", 1)[0]
            if file_part and not (path.parent / file_part).exists():
                errors.append(
                    f"{path.relative_to(root).as_posix()}: broken link {target}"
                )
    return errors


def git_show(root: Path, ref: str, rel: str) -> str | None:
    result = subprocess.run(
        ["git", "show", f"{ref}:{rel}"], cwd=root, capture_output=True, text=True
    )
    return result.stdout if result.returncode == 0 else None


def version_of(text: str | None) -> str | None:
    return json.loads(text)["version"] if text else None


def check_versions(root: Path, base: str) -> list[str]:
    """Every plugin changed since `base` bumps its own and the marketplace version."""
    changed = subprocess.run(
        ["git", "diff", "--name-only", base, "--", "plugins", ".claude-plugin"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    plugins = sorted({p.split("/")[1] for p in changed if p.startswith("plugins/")})
    errors = []
    for name in plugins:
        rel = f"plugins/{name}/.claude-plugin/plugin.json"
        current = root / rel
        if not current.is_file():
            continue
        old = version_of(git_show(root, base, rel))
        if old is not None and old == version_of(current.read_text(encoding="utf-8")):
            errors.append(f"{name}: changed since {base} but version is still {old}")
    if changed:
        rel = ".claude-plugin/marketplace.json"
        old = version_of(git_show(root, base, rel))
        new = version_of((root / rel).read_text(encoding="utf-8"))
        if old is not None and old == new:
            errors.append(
                f"marketplace: plugins changed since {base} but version is still {old}"
            )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--base", help="git ref to check version bumps against")
    args = parser.parse_args(argv)
    errors = (
        check_manifests(args.root)
        + check_components(args.root)
        + check_links(args.root)
    )
    if args.base:
        errors += check_versions(args.root, args.base)
    for error in errors:
        print(error, file=sys.stderr)
    print(f"{len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
