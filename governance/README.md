# STRling Engineering Governance

This directory contains durable engineering policy and the foundational
contracts used to govern architectural work. These artifacts govern engineering
work; they do not define STRling language syntax or semantics.

## Authority and invariants

-   [`ENGINEERING_CONSTITUTION.md`](ENGINEERING_CONSTITUTION.md) contains the
    permanent normative engineering rules.
-   [`product.md`](product.md) defines STRling's ratified product identity,
    authoring hierarchy, and host-language/target-engine distinction.
-   [`authority.md`](authority.md) defines precedence when project artifacts
    disagree.
-   [`architecture.md`](architecture.md) defines target architectural invariants
    and distinguishes them from the transitional repository state.
-   [`terminology.md`](terminology.md) defines stable vocabulary without
    prejudging canonical data-contract fields.
-   [`../spec/README.md`](../spec/README.md) classifies current specification
    material, while [`../spec/VERSIONING.md`](../spec/VERSIONING.md) defines
    independent semantic specification versioning.
-   [`certification-profiles.md`](certification-profiles.md) defines stable
    repository certification identities, aggregation, evidence ownership, and
    profile-evolution rules.

## Machine-readable contracts

-   `schemas/task-record.schema.json` defines declared change classes,
    deterministic diff scope, expected files, generated-output permissions,
    verification, completion, and readiness for contained engineering work.
-   `templates/task-record.yaml` is a validating starting point for a new record.
-   `generated-artifacts.json` inventories checked-in and material build-local
    generated families, their controlling contracts, actual generator inputs,
    producers, outputs, authority, determinism, and transition state. Its schema
    is `schemas/generated-artifact-registry.schema.json`.
-   `change-control.json` selects the active task and registries and maps
    machine-detectable paths to required change declarations. Its schema is
    `schemas/change-control.schema.json`.
-   `architecture-rules.json` distinguishes rules enforced now from
    transitional allowances and future rules. Its schema is
    `schemas/architecture-rules.schema.json`.
-   `public-surfaces.json` inventories binding APIs, package entrypoints, the
    root CLI, and stable structured contracts with an explicit deterministic
    extractor or bounded transition. Its schema is
    `schemas/public-surface-registry.schema.json`; compatibility and authority
    rules are documented in `public-contracts.md`.
-   `schemas/profile-certification-artifact.schema.json` defines the durable
    machine-readable evidence produced by canonical profile executions,
    including deterministic profile and operation evidence, aggregate status,
    execution metadata, and evidence fingerprints.
-   `schemas/waiver.schema.json` defines bounded exceptions with a stable ID,
    explicit rule and scope, rationale, and retirement condition.
-   `templates/waiver.yaml` is a validating starting point for an exception
    request.

Active architecture-migration records live in `docs/migration/records/`. The
ledger summarizes their completion and evidence; it MUST NOT duplicate or
reinterpret semantic specifications.

## Contained-task lifecycle

Every contained engineering task MUST:

1. establish allowed and forbidden scope before implementation;
2. define required verification before accepting implementation;
3. make the smallest coherent change that achieves the objective;
4. certify integration against the recorded baseline and declared contracts;
5. record completion evidence, preserved behavior, deferred work, and readiness
   for subsequent work; and
6. use meaningful commit subjects that describe the engineering change rather
   than a temporary campaign identifier.

A task record is the durable evidence for those steps. Version 1 records remain
valid historical evidence; every newly active task uses the stronger version 2
scope and change-declaration contract. Path expressions are repository-relative,
case-sensitive globs. Both sides of a rename and every deleted path remain in
scope.

A waiver authorizes only
its declared exception and scope; it does not alter the authority hierarchy or
become permanent debt by default. Related replacement work belongs in the
waiver's retirement section.

Generated output is never normative merely because it appears in the registry
or is checked in. The `authoritative_sources` field identifies the controlling
contract; `generator_inputs` records what the current producer actually reads.
A mismatch between those fields is explicit transition debt, not an elevation
of the implementation.

Public snapshots follow the same authority rule: a snapshot is reviewable
compatibility evidence, not a semantic specification. Detection of snapshot
drift and approval through a surface-specific task declaration remain separate.
