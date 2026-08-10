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

## Development

-   [`Contribution Guidelines`](guidelines.md)
-   [`Toolchains and Quality Commands`](toolchains.md)
-   [`Testing Philosophy & Workflow`](testing_workflow.md)
-   [`Test Design Standard`](testing_design.md)
-   [`Testing Setup`](testing_setup.md)
-   [`CI/CD Setup`](ci_cd_setup.md)
-   [`Releasing`](releasing.md)

## Current-state reminder

The regex-shaped source grammar, per-binding compilers, TypeScript-derived
fixtures, shallow AST/IR, target limitations, and binding-coupled tooling remain
transitional. Documentation about those paths describes compatibility workflow,
not the permanent source of semantic authority.
