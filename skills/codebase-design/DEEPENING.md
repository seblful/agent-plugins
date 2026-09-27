# Deepening

How to deepen a cluster of shallow modules safely, given its dependencies. Uses the vocabulary in [SKILL.md](SKILL.md).

## Dependency categories

Classify a candidate's dependencies first — **the category decides how the deepened module is tested across its seam.**

| Category | What it is | How to deepen and test |
| --- | --- | --- |
| **In-process** | pure computation, in-memory state, no I/O | Always deepenable. Merge the modules and test through the new interface directly — no adapter. |
| **Local-substitutable** | has a local stand-in: an embedded or in-memory version of the database, an in-memory filesystem | Deepenable if the stand-in exists. Tests run against it; the seam stays internal, with no port at the external interface. |
| **Remote but owned** | your own services across a network | Ports and adapters: define a **port** at the seam, keep the logic in one deep module, inject the transport as an **adapter** — a network adapter in production, an in-memory one in tests. |
| **True external** | third-party services you don't control | Inject the dependency as a port; tests supply a **mock** adapter. |

## Seam discipline

- **One adapter is a hypothetical seam; two is a real one.** Add a port only when at least two adapters are justified — typically production and test. One adapter is just indirection.
- **Keep internal seams internal.** Don't expose them through the interface because tests use them.

## Testing: replace, don't layer

- **Tests move to the deepened interface.** Once they exist there, the old unit tests on the shallow modules are waste — delete them.
- **Assert observable outcomes**, never internal state.
- **Tests survive internal refactors.** A test that changes when the implementation changes is testing past the interface.
