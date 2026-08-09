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
