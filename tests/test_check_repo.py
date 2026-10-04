import json
import subprocess
from pathlib import Path

import check_repo
import pytest

GOOD_DESC = "Does a thing. Use when the user asks for it. Not for other things."


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def skill_md(name: str, description: str = GOOD_DESC, body: str = "") -> str:
    return f'---\nname: {name}\ndescription: "{description}"\n---\n\n{body}\n'


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    plugin = {"name": "demo", "version": "0.1.0", "description": "Demo plugin."}
    marketplace = {
        "name": "m",
        "version": "1.0.0",
        "plugins": [
            {"name": "demo", "description": "Demo plugin.", "source": "./plugins/demo"}
        ],
    }
    write(tmp_path / ".claude-plugin/marketplace.json", json.dumps(marketplace))
    write(tmp_path / "plugins/demo/.claude-plugin/plugin.json", json.dumps(plugin))
    write(
        tmp_path / "plugins/demo/skills/alpha/SKILL.md",
        skill_md("alpha", body="[b](../beta/SKILL.md)"),
    )
    write(tmp_path / "plugins/demo/skills/beta/SKILL.md", skill_md("beta"))
    write(tmp_path / "plugins/demo/agents/alpha.md", skill_md("alpha"))
    write(tmp_path / "README.md", "- **alpha** (skill)\n- **beta** (skill)\n")
    write(tmp_path / "AGENTS.md", "# rules\n")
    return tmp_path


def test_clean_repo_passes(repo: Path) -> None:
    assert check_repo.main(["--root", str(repo)]) == 0


def test_description_drift_is_reported(repo: Path) -> None:
    path = repo / "plugins/demo/.claude-plugin/plugin.json"
    path.write_text(
        json.dumps({"name": "demo", "version": "0.1.0", "description": "Changed."})
    )
    assert any("description differs" in e for e in check_repo.check_manifests(repo))


def test_description_without_triggers_is_reported(repo: Path) -> None:
    write(repo / "plugins/demo/skills/beta/SKILL.md", skill_md("beta", "Does a thing."))
    errors = check_repo.check_components(repo)
    assert "plugins/demo/skills/beta/SKILL.md: description lacks 'Use when'" in errors
    assert "plugins/demo/skills/beta/SKILL.md: description lacks 'Not for'" in errors


def test_name_mismatch_and_missing_readme_bullet(repo: Path) -> None:
    write(repo / "plugins/demo/skills/gamma/SKILL.md", skill_md("other"))
    errors = check_repo.check_components(repo)
    assert any("name 'other' != 'gamma'" in e for e in errors)
    assert any("no **gamma** bullet" in e for e in errors)


def test_skill_escaping_its_plugin_is_reported(repo: Path) -> None:
    write(
        repo / "plugins/demo/skills/beta/SKILL.md",
        skill_md("beta", body="Read ../../x.md"),
    )
    assert any("sibling directory" in e for e in check_repo.check_components(repo))


def test_broken_link_is_reported_and_placeholders_skipped(repo: Path) -> None:
    write(
        repo / "plugins/demo/skills/beta/SKILL.md",
        skill_md(
            "beta",
            body="[x](missing.md) [y](<path>) [z](https://a.b) `[c](code)`\n```\n[d](fence)\n```",
        ),
    )
    assert check_repo.check_links(repo) == [
        "plugins/demo/skills/beta/SKILL.md: broken link missing.md"
    ]


def test_unquoted_frontmatter_and_escaped_quotes(tmp_path: Path) -> None:
    path = tmp_path / "x.md"
    path.write_text(
        '---\nname: x\ndescription: "say \\"hi\\""\ntools: Read\n---\n',
        encoding="utf-8",
    )
    assert check_repo.read_frontmatter(path) == {
        "name": "x",
        "description": 'say "hi"',
        "tools": "Read",
    }


def test_file_without_frontmatter(tmp_path: Path) -> None:
    path = tmp_path / "x.md"
    path.write_text("# no frontmatter\n", encoding="utf-8")
    assert check_repo.read_frontmatter(path) == {}


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def test_versions_must_bump_with_changes(repo: Path) -> None:
    git(repo, "init", "-q")
    git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
    git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base")
    write(repo / "plugins/demo/skills/beta/SKILL.md", skill_md("beta", body="changed"))
    errors = check_repo.check_versions(repo, "HEAD")
    assert errors == [
        "demo: changed since HEAD but version is still 0.1.0",
        "marketplace: plugins changed since HEAD but version is still 1.0.0",
    ]
    write(
        repo / "plugins/demo/.claude-plugin/plugin.json",
        json.dumps({"name": "demo", "version": "0.1.1", "description": "Demo plugin."}),
    )
    marketplace = json.loads((repo / ".claude-plugin/marketplace.json").read_text())
    marketplace["version"] = "1.0.1"
    write(repo / ".claude-plugin/marketplace.json", json.dumps(marketplace))
    assert check_repo.check_versions(repo, "HEAD") == []
