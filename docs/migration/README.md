# Architecture Migration Records

This directory contains migration-control records and verification evidence for
the architectural initiative. It is not product documentation and MUST NOT
become a second source of STRling language semantics.

-   `ledger.md` is the concise index of completed work and verification evidence.
-   `records/` contains task records conforming to
    `governance/schemas/task-record.schema.json`.

Each contained task establishes scope and verification before implementation,
records checkpoint evidence and meaningful commits, and closes with behavior,
deferral, and next-task readiness statements. The ledger points to that evidence
without restating specifications or contracts.

Temporary sequencing metadata, when needed, belongs only in these records. It
MUST NOT leak into source code, comments, tests, ordinary documentation,
architecture terminology, generated output, release notes, or permanent commit
subjects.

## Completed product-architecture records

-   [Authoritative product and specification architecture](records/product-specification-architecture.yaml)
    records the ratified product identity, authoring and compiler responsibility
    model, specification authority and versioning policy, certification, and
    canonical-contract readiness.
-   [Product and specification contradiction inventory](product-specification-contradictions.md)
    classifies resolved authoritative conflicts and lower-authority transition
    debt without converting historical wording into product requirements.
-   The permanent product-facing entry points are
    [product identity](../../governance/product.md),
    [architecture](../../governance/architecture.md),
    [authority](../../governance/authority.md),
    [terminology](../../governance/terminology.md), and
    [specification versioning](../../spec/VERSIONING.md).
