# STRling Developer Documentation

## Start with authority

-   [`Product Architecture`](../governance/product.md) — authoritative product
    identity, authoring hierarchy, and host/target distinction.
-   [`Engineering Authority`](../governance/authority.md) — precedence among
    specifications, contracts, implementations, evidence, and documentation.
-   [`Architecture Invariants`](../governance/architecture.md) — permanent
    compiler, adapter, target, and tooling responsibilities.
-   [`Canonical Terminology`](../governance/terminology.md) — stable vocabulary
    for subsequent contract design.
-   [`Specification Hub`](../spec/README.md) and
    [`Versioning Policy`](../spec/VERSIONING.md) — current authority state,
    draft/ratified rules, and material classification.
-   [`Validation Guarantees`](../spec/stdlib/VALIDATION_GUARANTEES.md) and
    [`Compiler Boundaries`](../spec/stdlib/COMPILER_BOUNDARIES.md) — normative
    helper-claim levels, standards scope, and independence from safety,
    diagnostics, portability, and rewrites.

## Architecture and strategy

-   [`Architecture Guide`](architecture.md) — contributor-facing explanation of
    the ratified model.
-   [`Project Architecture & Strategy`](project_architecture_strategy.md) —
    contract-first delivery, reference compiler, adapter migration, tooling, and
    target expansion.
-   [`Formal Specification Links`](spec_links.md) — indexed current material
    with authority labels.
-   [`Migration Evidence`](migration/README.md) — frozen baseline, preservation,
    donor, contradiction, and readiness records.
-   [`Semantic Explanation Model`](migration/semantic-explanation-model.md) —
    canonical evidence boundary, structured entity taxonomy, uncertainty, and
    rendering rules for explanation model `1.0.0`.
-   [`Canonical CLI`](migration/canonical-cli-rebase.md) — command transport,
    versioned JSON envelopes, compatibility dispositions, exit semantics, and
    the rule that product commands reuse canonical compiler paths.
-   [`Canonical Interop Foundation`](migration/interop-foundation.md) — the
    versioned byte protocol, native C ABI, raw WebAssembly memory contract, and
    evidence plan for thin host adapters.
-   [`Rust, C, and C++ Adapter Migration`](migration/rust-c-cpp-adapter-migration.md) —
    the curated Rust facade, thin native C adapter, C++ RAII boundary, and
    compatibility-retirement rules.

## Development

-   [`Your First Semantic STRling Contribution`](tutorial/first_contribution.md)
    — flagship textual authoring, canonical requests, and focused verification.
-   [`Contribution Guidelines`](guidelines.md)
-   [`Toolchains and Quality Commands`](toolchains.md)
-   [`Testing Philosophy & Workflow`](testing_workflow.md)
-   [`Test Design Standard`](testing_design.md)
-   [`Testing Setup`](testing_setup.md)
-   [`CI/CD Setup`](ci_cd_setup.md)
-   [`Releasing`](releasing.md)

## Authoring hierarchy

Start with
[`Semantic STRling`](../spec/frontends/semantic/1.0/README.md) for textual
intent. Use the
[`Simply protocol`](../spec/frontends/simply/1.0/README.md) for programmatic
intent. Use
[`regex-compatible source`](../spec/frontends/legacy-regex/1.0/README.md) only
for import and compatibility work. Historical per-binding compilers and
TypeScript-derived fixtures remain transitional evidence, not semantic
authority.
