---
name: python-notebooks
description: "Reproducible Jupyter notebooks — Restart & Run All as the contract, hidden-state discipline, declared dependencies, promotion to modules, restraint in figures, jupytext pairing. Use when creating, editing, running, reviewing, or cleaning up any .ipynb (EDA, experiments, reports, teaching), or when a notebook fails on rerun, has kernel or environment issues, or is converted to or from a script. Not for the modules a notebook imports (python-code) or explicitly throwaway scratch."
---

# Jupyter Notebooks

A notebook's value is its narrative; its danger is hidden state. One contract governs everything below:

**Restart kernel → Run All must succeed top-to-bottom and reproduce what the prose claims.**

A notebook that works only in a secret cell order is a broken build that renders green. Verify it headless before calling any notebook work done. The commands assume `uv`, this plugin's default; in a project on conda, poetry, or plain pip, keep its manager and translate — what matters is that dependencies live in a file, never in a cell. The tooling below is itself a dependency — declare it once, or every `uv run` here fails to spawn:

```bash
uv add --dev ipykernel nbclient jupytext nbmake   # kernel, `jupyter execute`, pairing, CI smoke run
```

```bash
uv run jupyter execute notebook.ipynb             # run, discard outputs
uv run jupyter execute --inplace notebook.ipynb   # run, keep outputs
```

## Notebook vs module

Notebooks are for work where the narrative is the product — exploration, analysis, experiments, reports, teaching. Logic that stabilizes or gets reused belongs in a module.

**The promotion loop:** explore → a function stabilizes → move it to `src/` with types and tests (`python-code`) → import it back. A helper copy-pasted into a second notebook is overdue. When importing local code, put `%load_ext autoreload` and `%autoreload 2` in the setup cell so module edits apply without a kernel restart.

A notebook run on a schedule is a script in costume — promote it. If the rendered document is the deliverable, parameterize it and run it with `papermill`.

## Structure

1. **Title cell** — the question this notebook answers, its inputs, what it produces.
2. **One setup cell** — every import, constant, seed, and path, so a missing dependency fails in seconds instead of at cell 40.
3. **Markdown headings** section the analysis in the data's order — load → inspect → clean → transform → analyze — with nothing used before it is introduced; within a section, derive before you display.
4. **One logical step per cell**, intermediate results named rather than chained into one uninspectable expression.
5. **Headings and plot titles name the topic or metric, never a finding** — "Cancel rate by market", not "Pittsburgh cancels 72%". A title that states a result dates the notebook to one run's data. Siblings share one naming convention.

**One notebook answers one question**; when a second moves in, split.

## Restraint

Every figure, series, and paragraph costs the reader something on the way to the conclusion. Fewer is the default.

- **Every figure carries a point.** Subplots only when the panels are one chart across a facet, or when the side-by-side comparison *is* the finding. A cut of the data shown because it exists never earns a figure; a section that takes five plots to land one point has not found it yet.
- **The plainest encoding that shows the effect** — a bar, a line, a scatter. An effect that needs dual axes or layered annotations to appear is better stated in a sentence.
- **Prose states the claim, next to its evidence, in a line or two** — "Cancels concentrate in the last 48 hours". The derivation is already in the code above it, and "now we plot the trend" narrates what the next cell shows.

## Hidden-state discipline

The kernel remembers everything ever executed; the file shows only what is there now.

- **Cells are idempotent.** `df = df[df.score > 0]` shrinks the data on every rerun; derive a new name.
- **No in-place mutation across cells** — `inplace=True` makes a cell's outcome depend on execution history.
- **Cell order is execution order**; reorder until top-to-bottom is the truth.
- **One name, one meaning** — reusing `df` for four tables makes every cell depend on scroll position.
- Deleted cells leave their variables alive; Restart & Run All is the only proof the file matches the state.

## Environment and data

| Concern | Do | Never |
| --- | --- | --- |
| Dependencies | `uv add <pkg>`, recorded in `pyproject.toml` | `!pip install` in a cell — works today, fails for the next person |
| Kernel | the project env: `uv run python -m ipykernel install --user --name <project>` | the system Python |
| Lint and format | `uv run ruff check --fix`, `uv run ruff format` — native `.ipynb` support | — |
| Randomness | every seed set in the setup cell | conclusions drawn from unseeded runs |
| Paths | `pathlib` from the project root, so a fresh clone runs | absolute user paths, cwd assumptions |
| Expensive fetches | one cell writes a cache file, analysis cells read it | refetching on every rerun |
| Secrets | env vars | literals — outputs capture whatever a cell prints, and get committed |

## Version control and CI

Committed outputs mean megabytes of base64 images, unreviewable diffs, and whatever data got printed. Pair every notebook with a `py:percent` script:

```bash
uv run jupytext --set-formats ipynb,py:percent notebook.ipynb   # pair once
uv run jupytext --sync notebook.ipynb                           # after edits
```

The paired `.py` is the reviewable source of truth in git; the `.ipynb` with its outputs stays local, gitignored. **A fresh clone or CI has only the `.py`** — rebuild the notebooks before running anything that needs one:

```bash
uv run jupytext --sync notebooks/*.py   # writes the missing .ipynb from each paired .py
```

Edit `.ipynb` files with notebook-aware tooling (in Claude Code, `NotebookEdit`), never as raw JSON — the format corrupts easily. Where no notebook tool exists (Codex, OpenCode), edit the paired `.py` instead and run `jupytext --sync` on it.

Notebooks that must stay green get a CI smoke run — rebuild first, or nbmake finds no `.ipynb`, collects nothing, and pytest exits 5:

```bash
uv run jupytext --sync notebooks/*.py && uv run pytest --nbmake notebooks/
```

It proves the narrative still executes; logic is tested after promotion, never inside a notebook.

## Not a finding

- An in-cell install in a notebook built for a hosted runtime that has no project environment.
- An import at its point of first use in a teaching notebook, where introducing the library is the lesson.
- Committed outputs on a notebook whose rendered form is the deliverable and that the project commits on purpose.
- A long notebook that still answers one question — length alone is no reason to split.
- A scratch notebook marked as throwaway.

**Before calling it done: restart, run all, top to bottom, clean.**
