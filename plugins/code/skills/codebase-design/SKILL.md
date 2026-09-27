---
name: codebase-design
description: "Shared, language-agnostic vocabulary for designing deep modules — module, interface, depth, seam, adapter, leverage, locality — with the principles that go with it. Use when the user wants to design or improve a module's interface, find deepening opportunities, decide where a seam goes, make code more testable or easier to navigate, or when another skill needs the deep-module vocabulary. Not for defects inside a function body (code-smells)."
---

# Codebase Design

Design **deep modules**: a lot of behaviour behind a small interface, placed at a clean seam, testable through that interface. The payoff is leverage for callers, locality for maintainers, and testability for everyone.

## Glossary

**Use these terms exactly** — not "component", "service", "API", or "boundary". Consistent language is the point.

| Term | Means | Avoid |
| --- | --- | --- |
| **Module** | anything with an interface and an implementation, at any scale — function, type, package, a slice across tiers | unit, component, service |
| **Interface** | everything a caller must know to use the module correctly: the signature, plus invariants, ordering, error modes, required configuration, performance | API, signature — both name only the type-level surface |
| **Implementation** | the code inside a module | — |
| **Depth** | leverage at the interface: behaviour a caller or test gets per unit of interface learned. **Deep** — much behaviour, small interface. **Shallow** — interface nearly as complex as what it hides | — |
| **Seam** | a place where behaviour can change without editing that place — where an interface lives. Where to put it is its own decision | boundary |
| **Adapter** | a concrete thing that satisfies an interface at a seam. Names a role, not a size: a database-backed store is a small adapter over a large implementation, an in-memory fake the reverse | — |
| **Leverage** | what callers get from depth: more capability per unit learned, one implementation paying back across every call site and test | — |
| **Locality** | what maintainers get from depth: change, bugs, and knowledge concentrate in one place. Fix once, fixed everywhere | — |

## Principles

- **Depth is a property of the interface, not the implementation.** A deep module can be built from small, swappable parts — they just are not part of its interface. It can have **internal seams** for its own tests as well as the **external seam** at its interface.
- **The deletion test.** Imagine deleting the module. If complexity vanishes, it was a pass-through. If complexity reappears across its callers, it earned its keep.
- **The interface is the test surface.** Callers and tests cross the same seam. Needing to test *past* the interface means the module is the wrong shape.
- **One adapter is a hypothetical seam; two is a real one.** Introduce a seam only where something actually varies across it.
- **Shrink the interface.** Fewer entry points, simpler parameters, more hidden inside — every fact a caller must know is a cost paid at every call site.

## Designing for testability

1. **Accept dependencies, don't create them.** A function that constructs its own payment gateway cannot be tested without the real one; one that receives it can.
2. **Return results, don't produce side effects.** A function that returns a discount can be asserted on; one that mutates the cart must be inspected.
3. **Small surface.** Fewer entry points mean fewer tests; fewer parameters mean simpler setup.

## Rejected framings

- **Depth as implementation lines over interface lines** — rewards padding. Depth here is leverage.
- **Interface as a language keyword or a type's public methods** — too narrow; it includes every fact a caller must know.
- **"Boundary"** — overloaded with the bounded context. Say **seam** or **interface**.

## Going deeper

- [DEEPENING.md](DEEPENING.md) — deepening a cluster given its dependencies: dependency categories, seam discipline, replace-don't-layer testing.
- [REPORT-TEMPLATE.html](REPORT-TEMPLATE.html) — the page `/refactor-interfaces` fills in: fixed styling, fixed diagram vocabulary, one card per candidate. Fill its slots; never restyle it.
