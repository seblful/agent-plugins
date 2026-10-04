---
name: python-code
description: "The Python layer for code that will outlive a quick script — how the general principles are spelled in Python (types, data modeling, boundaries, errors, resources, async, tests) and the traps easy to miss in it. Use when writing, changing, or reviewing Python modules, classes, type annotations, data models, configuration or input parsing, CLIs, or pytest tests. Not for notebooks (python-notebooks), language-agnostic defects (code-smells), or interface and module shape (codebase-design)."
---

# Python Code

How the principles of `code-smells` and `codebase-design` are written in Python, plus the traps particular to it. What holds in every language lives there; this file holds only what is Python. Both ship in the `code` plugin; if they are not available, say so rather than treating this file as the whole review.

**The project's existing choices outrank every default here** — its package manager, libraries, layout, and `requires-python`. A codebase half one stack and half another is worse than either. Propose a migration; never perform one as a side effect.

Write this way without commentary; name a rule only when asked why, or when deviating from it. In existing code, fix what you are already changing and point out the rest.

## Stack — greenfield only

| Role | Default |
| --- | --- |
| Environments and dependencies | `uv`, every dependency declared in `pyproject.toml` |
| Lint and format | `ruff` — owns style; never hand-enforce what it checks |
| Type check | `ty`, every rule at error — `[tool.ty.rules]` `all = "error"` in `pyproject.toml` (ty has no "strict" switch) — as a CI gate |
| Tests | `pytest`, `hypothesis` for properties |
| Input validation, settings | `pydantic`, `pydantic-settings` |
| Logging | `structlog` — events named in `snake_case` past tense, context as fields |
| CLI | `typer` |
| HTTP | `httpx` — `Client`, or `AsyncClient` inside `async def`, one per process lifetime, closed by `with` / `async with` |
| Layout | `src/<package>/` with `py.typed`; tests outside the package |

## Principles, in Python

| Principle | Python spelling |
| --- | --- |
| Absence is visible | `T \| None` in the signature; a `-> T` function never has a branch returning `None` |
| Illegal states unrepresentable | a union of frozen dataclasses, dispatched with `match` and closed with `assert_never` |
| Restricted values | `Literal` for one-off, `Enum` when shared, `NewType` for distinct ids |
| Parse at the boundary, trust inside | a pydantic model at every input — file, network, env, CLI; plain dataclasses downstream |
| Invariants in one place | a class with private fields validated in `__init__`; a dataclass only when fields are independent |
| Structural over nominal | `Protocol` for new abstractions; `ABC` only when enforced inheritance is the point |
| Idiomatic interfaces | dunder protocols (`__iter__`, `__enter__`, `__len__`) where callers would reach for them |
| Act, then handle | EAFP — `try` the operation instead of checking first; `exists()` then `open()` races |
| Scoped resources | `with`, and `@contextmanager` for anything you acquire and release |
| Errors keep their cause | narrow `except`, `raise … from e`, one project-rooted exception hierarchy |
| Structured concurrency | `asyncio.TaskGroup` over bare `gather`; CPU-bound work in a process pool; `asyncio.run` only at entry points |
| Paths are values | `pathlib.Path`, never string joins |

## Traps

Code that reads correct and is not.

- **Shared default** — a mutable default argument, or a dataclass field defaulting to a container, is one object shared by every call. Default to `None`, or `field(default_factory=…)`.
- **Shallow freeze** — `frozen=True` blocks rebinding, not mutating a list inside; deep immutability needs `tuple` and `frozenset`.
- **Late-binding closure** — a lambda built in a loop sees the variable's last value. Bind it as a default argument or with `functools.partial`.
- **`assert` as validation** — stripped under `python -O`. Raise.
- **Naive time** — `datetime.utcnow()` is naive and deprecated; `datetime.now(timezone.utc)`.
- **Blocking the loop** — sync I/O, `time.sleep`, or a sync HTTP client (`requests`, `httpx.Client`) inside `async def`.
- **HTTP client per call** — `httpx.get(…)` or a fresh `Client` per request builds and tears down a connection pool every time: no keep-alive, a new TLS handshake per call. One client, passed in, closed once.
- **`__eq__` without `__hash__`** — defining equality makes instances unhashable.
- **`@cache` on a method** — keeps every `self` alive for the life of the process.
- **Decorator without `functools.wraps`** — loses the wrapped function's name, docstring, and signature.
- **Mixed pydantic generations** — `.dict()`, `@validator`, `class Config` are v1; v2 is `model_dump`, `@field_validator`, `model_config`. Match the installed major.
- **Spellings the floor has outgrown** — `Optional`, `Union`, `List[…]` once `X | None` and `list[…]` are available; `TypeVar` boilerplate once 3.12 allows `def f[T](…)`.

## Tests

Tests pin behaviour through the public interface; a refactor that keeps behaviour keeps them green.

- **One behaviour per test**, named for it, arrange–act–assert visibly apart. A long arrange is the code under test asking for fewer dependencies.
- **Fixtures** at the narrowest scope that stays fast, `yield` for teardown, built-ins (`tmp_path`, `monkeypatch`, `caplog`, `capsys`) before hand-rolled ones.
- **Parametrize with `ids`** so a failure names its case; parametrize a fixture to run one suite against every implementation.
- **Mock only the seams you own.** Patch where the name is looked up, with `autospec=True` so drift fails; wrap a third-party client in an adapter and fake that. Never mock the unit under test.
- **Awaited mocks assert with `assert_awaited_*`** — `assert_called_*` passes even when the `await` is missing.
- **`hypothesis` for pure code** — parsers, serializers, anything with a round-trip.
- **Expected errors via `pytest.raises(…, match=…)`**, never a `try/except` in the test.
- **Markers declared under `--strict-markers`**; slow and integration tests behind them so the default run stays fast.

## Before calling it done

Run the project's own gate if it has one (CI workflow, pre-commit, task runner); on the default stack:

```bash
uv run ruff check && uv run ruff format --check && uv run ty check && uv run pytest
```

Done means every command exits 0. A failure you did not cause is reported, not hidden.

## Not a finding

- Anything `ruff` or the type checker already reports — the gate says it.
- The project's own stack, layout, or spellings where they differ from the defaults above.
- Spellings the project's `requires-python` still needs.
- Missing annotations in tests, scripts, or notebooks the project leaves untyped.
- `Any` or `cast` at an untyped third-party edge, contained and commented.
- A dataclass with public fields that nothing constrains.

**Write the obvious version; let the types and the tests be the safety net.**
