# STRling AI Orchestration Matrix

STRling is a portable regex-intent compiler with multiple host-language bindings
and target-engine outputs. Load the bounded instruction set that matches the
task:

-   API and Simply design: `instructions/philosophy.instructions.md`
-   compiler/specification architecture: `instructions/architecture.instructions.md`
-   tests and compatibility evidence: `instructions/testing.instructions.md`
-   documentation and pedagogy: `instructions/documentation.instructions.md`
-   contributor workflow and diagnostics: `instructions/workflow.instructions.md`

Load every applicable file when work crosses those boundaries.

## Authority before implementation

Use this order when guidance conflicts:

1. ratified versioned specification;
2. expressly normative versioned contracts;
3. delegated specification-authored conformance cases;
4. ratified architecture decisions;
5. reference implementation;
6. implementation tests and compatibility evidence; and
7. explanatory documentation.

There is no ratified Semantic STRling specification version yet.
`spec/drafts/1.0/` is non-normative. Current TypeScript behavior and
`tests/spec/*.json` are transitional compatibility evidence, not semantic
authority.

Do not begin parser, grammar, AST/IR, backend, adapter, or Simply redesign from
the product-architecture documents alone. Those changes require contained,
contract-first work.

## Routing notes

Load architecture instructions for parser/compiler/emitter changes, canonical
contract work, target profiles, grammar/semantics classification, or host/target
boundary questions.

Load testing instructions for conformance, fixture regeneration, parity
failures, diagnostics compatibility, or certification.

Load philosophy instructions when evaluating semantic authoring, Simply naming,
raw-regex import, or target-output exposure.

## Quick reference

| Resource                           | Path                             |
| ---------------------------------- | -------------------------------- |
| Product definition                 | `governance/product.md`          |
| Architecture invariants            | `governance/architecture.md`     |
| Authority hierarchy                | `governance/authority.md`        |
| Canonical vocabulary               | `governance/terminology.md`      |
| Specification hub                  | `spec/README.md`                 |
| Specification versioning           | `spec/VERSIONING.md`             |
| 1.0 draft scope                    | `spec/drafts/1.0/README.md`      |
| Compatibility fixtures             | `tests/spec/*.json`              |
| Root quality entry point           | `./strling`                      |
| Operational package version source | `bindings/python/pyproject.toml` |

The operational package-version source has no semantic authority. Binding count
describes host-ecosystem coverage, not target-engine coverage.
