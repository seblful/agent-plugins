"""Build standalone Agent Skills from the Claude marketplace's canonical skills.

The committed top-level skills/ directory is the portable distribution. This
script is for maintainers; users install the generated skills with their agent's
skill manager or a standard Agent Skills installer.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGINS = ROOT / "plugins"
OUTPUT = ROOT / "skills"
MARKER = ".generated-by-build-skills"
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
EXTRA_REFERENCES = {
    "code-sweep": "code-smells",
    "docs-sweep": "writing-docs",
    "refactor-interfaces": "codebase-design",
}


def parse_skill(path: Path) -> tuple[str, str, str]:
    content = path.read_text(encoding="utf-8")
    match = FRONTMATTER.match(content)
    if not match:
        raise ValueError(f"Missing frontmatter: {path}")
    fields = dict(line.split(":", 1) for line in match.group(1).splitlines() if ":" in line)
    name = fields.get("name", "").strip().strip('"\'')
    raw_description = fields.get("description", "").strip()
    description = json.loads(raw_description) if raw_description.startswith('"') else raw_description.strip("'")
    if name != path.parent.name or not description:
        raise ValueError(f"Invalid name or description: {path}")
    return name, description, content[match.end():].lstrip("\n")


def adapt(body: str, plugin: str, name: str) -> str:
    body = body.replace("`the user's request`", "the user's request")
    body = body.replace("$CLAUDE_PLUGIN_ROOT", "<skill-dir>")
    body = body.replace("Claude Code session", "coding assistant session")
    body = body.replace("(if `<skill-dir>` is unset, use this plugin folder's real path)", "")
    if plugin == "obsidian-vault":
        body = body.replace("../../CONVENTIONS.md", "references/CONVENTIONS.md")
        body = body.replace("../../AUTHORING.md", "references/AUTHORING.md")
    if name == "teach":
        body = body.replace("../../teach/", "references/")
    if name == "refactor-interfaces":
        body = body.replace(
            "the `REPORT-TEMPLATE.html` from the `codebase-design` skill (in Claude Code, `<skill-dir>/skills/codebase-design/REPORT-TEMPLATE.html`)",
            "`<skill-dir>/references/codebase-design/REPORT-TEMPLATE.html`",
        )
    return body


def copy_resources(plugin: Path, name: str, destination: Path) -> None:
    if plugin.name == "obsidian-vault":
        references = destination / "references"
        references.mkdir()
        for filename in ("CONVENTIONS.md", "AUTHORING.md"):
            body = (plugin / filename).read_text(encoding="utf-8")
            (references / filename).write_text(adapt(body, plugin.name, name), encoding="utf-8")
        shutil.copytree(plugin / "scripts", destination / "scripts", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    if name == "teach":
        shutil.copytree(plugin / "teach", destination / "references")
    if name in EXTRA_REFERENCES:
        reference = EXTRA_REFERENCES[name]
        shutil.copytree(plugin / "skills" / reference, destination / "references" / reference)
    if name in ("code-sweep", "docs-sweep", "refactor-interfaces"):
        reference = EXTRA_REFERENCES[name]
        (destination / "SKILL.md").write_text(
            (destination / "SKILL.md").read_text(encoding="utf-8").replace(
                "\n# ",
                f"\nRead [the {reference} reference](references/{reference}/SKILL.md) when applying this workflow.\n\n# ",
                1,
            ),
            encoding="utf-8",
        )


def build() -> int:
    sources = sorted(PLUGINS.glob("*/skills/*/SKILL.md"))
    if not sources:
        raise ValueError("No source skills found")
    names = [parse_skill(path)[0] for path in sources]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate skill names")
    OUTPUT.mkdir(exist_ok=True)
    for stale in OUTPUT.iterdir():
        if stale.is_dir() and stale.name not in names and (stale / MARKER).exists():
            if stale.resolve().parent != OUTPUT.resolve():
                raise ValueError(f"Unsafe output path: {stale}")
            shutil.rmtree(stale)
    for source in sources:
        name, description, body = parse_skill(source)
        destination = OUTPUT / name
        if destination.exists():
            if not (destination / MARKER).exists():
                raise FileExistsError(f"Refusing to replace unowned skill: {destination}")
            if destination.resolve().parent != OUTPUT.resolve():
                raise ValueError(f"Unsafe output path: {destination}")
            shutil.rmtree(destination)
        shutil.copytree(source.parent, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        prefix = (
            "Resolve `<skill-dir>` to the absolute directory containing this SKILL.md before "
            "running any command that uses it. Use the tools available in this assistant; "
            "if a named tool or subagent feature is unavailable, complete the same work directly.\n\n"
        )
        frontmatter = f"---\nname: {name}\ndescription: {json.dumps(description, ensure_ascii=False)}\nlicense: MIT\n---\n\n"
        (destination / "SKILL.md").write_text(frontmatter + prefix + adapt(body, source.parents[2].name, name), encoding="utf-8")
        copy_resources(source.parents[2], name, destination)
        (destination / MARKER).write_text("Generated by scripts/build_skills.py\n", encoding="utf-8")
    return len(sources)


if __name__ == "__main__":
    print(f"Built {build()} standalone skills in {OUTPUT}")
