---
name: code-smells
description: "Language-agnostic catalog of implementation smells with their fixes and, equally important, the false positives to suppress — correctness and robustness defects, bad practices and non-idiomatic constructs, duplication, dead weight, and complexity. Use when /code-sweep runs, when reviewing code for defects or bad practice, or when the user asks what to look for in a file. Covers implementations only — interface, seam, and module-shape smells belong to codebase-design; markdown docs to writing-docs."
license: MIT
---

Resolve `<skill-dir>` to the absolute directory containing this SKILL.md before running any command that uses it. Use the tools available in this assistant; if a named tool or subagent feature is unavailable, complete the same work directly.

# Code Smells

Three lenses for finding what is wrong with code that already works. Each lists **signals** (what to look for, and the fix) and **not a finding** (what to suppress). The signals are named by what the code does, not by syntax — map each to the language in front of you.

**Scope: implementations.** Everything here is fixable without changing what any caller must know. A fix that alters an **interface** belongs to `codebase-design` and `/refactor-interfaces`. Comments and docstrings live with the code and are judged here; markdown belongs to `writing-docs`.

**The suppression lists matter as much as the signals.** A sweep that reports 200 nitpicks is ignored wholesale; the false-positive rate decides whether the next one is trusted.

A finding must be **real** (you read the code), **consequential** (you can name what goes wrong), **not already handled** (you checked the callers), and **not a lateral move** (clearly better, not differently shaped).

---

## 1. Correctness & robustness

Code that misbehaves now, or will on plausible input. **Highest severity** — fixes here usually change behaviour.

### Signals

**Errors**

- **Swallowed error** — an empty catch, or an error logged quietly and execution continuing as if nothing happened. → Handle, propagate, or narrow it and say *why* it is safe to ignore.
- **Over-broad catch** — a catch-all around a wide block, so unrelated failures and programming mistakes are absorbed by handling written for one expected error. → Narrow the type; shrink the guarded block to what actually fails.
- **Ambiguous failure value** — a null, `-1`, `false`, or empty collection signalling failure where the caller cannot tell it from a legitimate result. → Fail explicitly, or return a result type.
- **Lost cause** — re-throwing a new error without the original attached, or logging an error with no stack or context. → Chain the cause; log the error object, not its string.

**Absence and boundaries**

- **Unchecked absence** — using a value a real path can leave null or missing; looking up an optional key as if required; indexing a possibly empty collection. → Guard it, or make absence unrepresentable in the type.
- **Off-by-one** — the wrong comparison, a loop or slice bound that silently drops the first or last element. → Fix, and name the input that exposes it.
- **Ignored partial failure** — a loop that continues past failed items without recording them, so callers see success. → Collect and surface the failures.

**Resources and state**

- **Unreleased resource** — a file, connection, lock, or process acquired without the language's guaranteed-release construct, so an error leaks it. → Scoped acquisition.
- **Shared mutable state** — a default value, module-level container, or cached object created once and mutated across calls or requests. → Per-call or per-instance state; hand out copies or read-only views.
- **Mutation during iteration** — adding to or removing from a collection while iterating it. → Iterate a copy, or build a new collection.
- **Check-then-act race** — testing a condition (exists, unlocked, not taken) and acting on it as a separate step. → Act and handle the failure, or use an atomic operation.
- **Blocking in a non-blocking context** — synchronous I/O or sleep on an event loop, UI thread, or other path that must not stall. → The non-blocking equivalent, or move the work off that path.

**Silent divergence**

- **Comment contradicts the code** — a documented range, unit, return, or error that no longer matches. One of the two is a bug. → Find out which before changing either.
- **Dead branch** — a condition that cannot be true: subsumed by an earlier check, comparing incompatible types, testing what was just assigned. → Delete it, or fix the condition it was meant to be.

### Not a finding

- A missing absence check where **every caller** provably guarantees presence.
- A catch-all at a genuine top-level boundary — request handler, entry point, worker loop — that **logs with context and reports failure**. That is the correct pattern.
- Defensive validation in a public entry point that looks redundant from inside.
- Anything that depends on guessing what a dependency does — say so, or drop it.

---

## 2. Bad practices & idiom

Code that works but misleads, fights the language, or makes the next change harder. Behaviour-preserving.

### Signals

**Types and data shape**

- **Lying types** — a declared type, cast, or type-checker escape hatch that disagrees with what the value really is. A wrong type is worse than none. → Make it true; if the true type is ugly, that is a design signal.
- **Stringly-typed data** — states, kinds, and modes as raw strings compared across files; structure packed into a delimited string and re-split downstream. → An enum or a small type.
- **Primitive obsession** — values that belong together (amount and currency, a coordinate and its unit) threaded separately through many signatures; untyped maps passed between layers as implicit records. → One named type that validates once.
- **Boolean-flag parameter** — an unexplained `true` at the call site, or a flag switching between two mostly unrelated paths. → A named argument or enum at minimum; two functions when the paths barely overlap.
- **Illegal states representable** — optional fields where only some combinations are valid, enforced by scattered checks. → Restructure so the invalid combination cannot be built.

**Language and stack idiom**

- **Reinvented standard library** — hand-rolled grouping, retry, path handling, date parsing, or merging the language or framework already provides. → Use the provided one.
- **Unidiomatic iteration** — index bookkeeping where only the items are used; a manual accumulator where the language's collection operations read better. → The idiomatic form, only when genuinely clearer.
- **Ad-hoc output instead of logging** — printing to the console in library or service code; unstructured logs in a project that logs structurally. → The project's logger, the right level, context as fields.
- **String-built structured output** — queries, markup, serialized data, shell commands, or paths assembled by concatenation. → Parameterized queries, serializers, path APIs, argument lists. *(If injection-prone, also a security handoff.)*
- **Magic value** — an unexplained literal in a decision, especially repeated. → A named constant where the meaning lives. Obvious values need no name.
- **Configuration read mid-logic** — environment or global config reached deep inside a function, hiding a dependency and blocking tests. → Read at the edge, pass it in.

**Structure of the body**

- **Mixed levels of abstraction** — low-level detail and orchestration interleaved in one body. → Extract the low level behind a name.
- **Hidden mutation** — a function that mutates an argument and returns nothing, where its name promises a computation. → Return the result, or rename it.
- **Flag-then-act at a distance** — a variable set in one branch and acted on far below. → Act where the decision is made.

### Not a finding

- An established convention of **this** codebase you would have written differently — consistency beats preference. Check its instructions, decision records, and neighbouring files first.
- Idiom differences with no consequence, and anything the project's formatter or linter owns.
- Missing types in tests, scripts, or throwaway code, unless the project types those too.
- Naming you merely dislike. **Misleading is a finding; not-your-taste is not.**
- A literal inside a well-named function whose purpose explains it.

---

## 3. Duplication, dead weight & complexity

Code that should not exist, or costs too much to read. Behaviour-preserving, usually lower severity — **highest volume, so suppression discipline matters most.**

### Signals

**Dead weight** — before deleting, search the whole repo and check for dynamic references: reflection, string-keyed dispatch, entry points, plugin registries, template lookups.

- **Unused code** — a function, type, branch, or module with no callers; a parameter nobody passes and the body ignores; code after an unconditional return.
- **Commented-out code** — delete it; version control has it.
- **Stale TODO** — referencing shipped work, a resolved condition, or someone long gone. Resolve or delete.
- **Unused imports, variables, assignments** — including a value overwritten before any read. *(Skip if the linter enforces it.)*
- **Vestigial abstraction** — an option nothing sets, a branch for a removed mode, a helper forwarding its arguments unchanged. Deleting a wrapper callers go through changes an interface → `/refactor-interfaces`.

**Duplication** — only the *same decision* expressed twice.

- **Clone** — the same logic in several places, especially where copies have drifted (one fixed, others not — the drift is the consequence). → One place.
- **Parallel lists** — adding a case means editing several lists, switches, or maps that must stay in sync. → One source of truth.
- **Duplicated knowledge** — the same pattern, threshold, format, or default repeated in otherwise different code. → A shared constant.

**Complexity**

- **Long function** — many distinct responsibilities, not many lines. → Extract named steps.
- **Deep nesting** — three or more levels, happy path innermost. → Guard clauses, early return.
- **Long parameter list** — many positional parameters of the same type, easy to transpose. → Group what travels together. *(Changes the signature → possibly `/refactor-interfaces`.)*
- **Feature envy** — reaching deep into another object's internals to compute what it should compute itself. → Move the behaviour to the data.
- **Misleading name** — a getter that writes, a validator that mutates, a plural holding one item, a wrong unit. → Rename **and update every call site**.
- **Temporal coupling** — calls that must happen in a fixed order with nothing enforcing it. → One call, or make the wrong order impossible.

### Not a finding

- **Coincidental similarity** — blocks that look alike but encode decisions that will diverge. Merging them is the classic bad refactor.
- **Duplication across a deliberate seam** — a test fixture mirroring production shape, a transfer object mirroring a model, a vendored copy pinned on purpose.
- Two or three lines repeated twice, where extraction costs a name and a jump.
- A long function that is one linear sequence — a parser, a state machine, a config assembler. **Length alone is not a finding.**
- Nesting in a hot loop where flattening changes performance — measure first.
- Verbosity that is **explicitness** and reads correctly at the point of use.
- A god object or grab-bag utilities module — real, but splitting it moves seams → `/refactor-interfaces`.
