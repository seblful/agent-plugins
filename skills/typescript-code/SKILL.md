---
name: typescript-code
description: "The TypeScript layer for code that will outlive a quick script — how the general principles are spelled in TypeScript (compiler strictness, types that narrow, boundary parsing, errors, promises, tests) and the traps easy to miss in it. Use when writing, changing, or reviewing TypeScript modules, types, tsconfig, input parsing, async code, or tests. Not for language-agnostic defects (code-smells), interface and module shape (codebase-design), or framework-specific UI practice."
license: MIT
---

Resolve `<skill-dir>` to the absolute directory containing this SKILL.md before running any command that uses it. Use the tools available in this assistant; if a named tool or subagent feature is unavailable, complete the same work directly.

# TypeScript Code

How the principles of `code-smells` and `codebase-design` are written in TypeScript, plus the traps particular to it. What holds in every language lives there; this file holds only what is TypeScript.

**The project's existing choices outrank every default here** — its package manager, runtime, module system, libraries, and compiler settings. A codebase half one stack and half another is worse than either. Propose a migration; never perform one as a side effect.

Write this way without commentary; name a rule only when asked why, or when deviating from it. In existing code, fix what you are already changing and point out the rest.

## Stack — greenfield only

| Role | Default |
| --- | --- |
| Compiler | the `tsc --init` baseline — `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `verbatimModuleSyntax` — plus `noImplicitOverride`; `tsc --noEmit` as a CI gate |
| Lint | `typescript-eslint` with `strictTypeChecked` — the type-aware rules catch unhandled promises and unsafe `any` |
| Format | Prettier — owns style; never hand-enforce what it checks |
| Tests | Vitest, `fast-check` for properties |
| Input validation | a schema library that infers the static type — Zod |
| Modules | ESM only |

## Principles, in TypeScript

| Principle | TypeScript spelling |
| --- | --- |
| Absence is visible | `T \| undefined` in the type, `noUncheckedIndexedAccess` so an index can miss; narrow it, never `!` it away |
| Illegal states unrepresentable | a discriminated union on a literal tag, `switch`ed and closed by a `default` that assigns to `never` |
| Restricted values | a union of string literals or an `as const` object; a branded type for distinct ids |
| Parse at the boundary, trust inside | `unknown` at every input — `JSON.parse`, responses, env, messages — parsed once by a schema whose inferred type flows inward |
| Types tell the truth | `satisfies` to check a value without widening it; `@ts-expect-error` with a reason over `@ts-ignore`; no `as` or `any` to silence an error |
| Immutable by default | `readonly` fields and `readonly T[]` parameters; `toSorted`, `toReversed`, `with` over mutating a shared array |
| Scoped resources | `try/finally`, or `using` / `await using` where the runtime supports it |
| Errors keep their cause | `catch (e)` is `unknown` — narrow before use; `new Error(msg, { cause: e })`; throw `Error` subclasses, never strings |
| Promises are handled | every promise awaited, returned, or explicitly `void`ed; `Promise.all` for independent work, `allSettled` when partial failure is expected; `AbortSignal` to cancel |

## Traps

Code that reads correct and is not.

- **Async callback to `forEach`** — nothing awaits it; failures become unhandled rejections. `for…of` with `await`, or `Promise.all` over `map`.
- **Default `sort()`** — compares as strings (`[10, 9, 1]` → `[1, 10, 9]`) and mutates in place. Pass a comparator.
- **`Object.keys` and `Object.entries`** return `string`, not `keyof T` — an object can carry more keys than its type names. Narrow; don't cast.
- **Excess properties pass** — only a fresh object literal is checked for extra keys; any other value with extra fields satisfies the type, and a serializer sends them on. Pick the fields you mean.
- **Spread of an explicit `undefined`** — in `{ ...defaults, ...overrides }`, `key: undefined` erases the default. `exactOptionalPropertyTypes` makes the type say which is allowed.
- **Runtime-emitting syntax** — `enum`, `namespace`, and constructor parameter properties generate code, so type-stripping runtimes reject them. Literal unions or `as const`; `erasableSyntaxOnly` enforces it.
- **Unbound method** — `obj.method` passed as a callback loses `this`. Wrap it in an arrow function, or `bind`.
- **Every number is a float** — money in integer minor units or a decimal type, `bigint` past 2⁵³.
- **`Date` is mutable and local-time** — pass UTC instants or ISO strings; format only at the edge.

## Tests

Tests pin behaviour through the public interface; a refactor that keeps behaviour keeps them green.

- **One behaviour per test**, named for it, arrange–act–assert visibly apart. A long arrange is the code under test asking for fewer dependencies.
- **Named cases with `test.each`** — one table per behaviour, so a failure names its case.
- **Inject fakes before mocking modules.** `vi.mock` is hoisted above the imports, so anything its factory references comes from `vi.hoisted`. Reset mocks and timers between tests so order never matters.
- **Await async assertions** — `await expect(p).rejects.toThrow(…)`; the type-aware lint flags the floating promise when you forget.
- **Fake timers over real waits** — `vi.useFakeTimers`, never a `sleep` in a test.
- **`fast-check` for pure code** — parsers, serializers, anything with a round-trip.
- **Type tests for public generic types** — `expectTypeOf`; a type that widens to `any` passes every runtime test.

## Not a finding

- Anything `tsc` or the linter already reports — the gate says it.
- The project's own stack, module system, or compiler settings where they differ from the defaults above.
- `enum` in a project that compiles with `tsc` and already uses them.
- Inferred return types on non-exported functions — annotate what is exported.
- `interface` versus `type`, unless the project's lint picks one.
- `any` or `as` at an untyped third-party edge, contained and commented.
- A `!` directly after a check the compiler cannot follow, with a comment saying why.

**Make the compiler prove it — every cast is a claim nobody checks.**
