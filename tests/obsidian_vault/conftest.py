"""Fixture-vault builders shared by the obsidian-vault script tests."""

import json
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

SCRIPTS = (
    Path(__file__).resolve().parents[2]
    / "plugins/obsidian-vault/skills/vault-conventions/scripts"
)
if str(SCRIPTS) not in sys.path:  # pythonpath in pyproject covers uv runs
    sys.path.insert(0, str(SCRIPTS))

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16

WriteFn = Callable[[str, str | bytes], Path]


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    root = tmp_path / "vault"
    (root / ".obsidian").mkdir(parents=True)
    return root


@pytest.fixture
def write(vault: Path) -> WriteFn:
    """write(rel, content) -> path; str content is written as UTF-8 bytes verbatim."""

    def _write(rel: str, content: str | bytes = "") -> Path:
        path = vault / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(
            content.encode("utf-8") if isinstance(content, str) else content
        )
        return path

    return _write


@pytest.fixture
def config(vault: Path) -> Callable[[str, dict], None]:
    def _config(name: str, data: dict) -> None:
        path = vault / ".obsidian" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")

    return _config


@pytest.fixture
def run_main(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    """run_main(module, *argv) -> (exit_code, parsed_json_or_None, stderr)."""

    def _run(module, *argv: str):
        monkeypatch.setattr(sys, "argv", [module.__name__, *argv])
        code = 0
        try:
            rc = module.main()
            code = rc or 0
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
            if isinstance(exc.code, str):
                print(exc.code, file=sys.stderr)
        out, err = capsys.readouterr()
        data = json.loads(out) if out.strip() else None
        return code, data, err

    return _run
