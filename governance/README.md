# STRling Engineering Governance

This directory contains durable engineering policy and the foundational
contracts used to govern architectural work. These artifacts govern engineering
work; they do not define STRling language syntax or semantics.

## Authority and invariants

- [`ENGINEERING_CONSTITUTION.md`](ENGINEERING_CONSTITUTION.md) contains the
  permanent normative engineering rules.
- [`authority.md`](authority.md) defines precedence when project artifacts
  disagree.
- [`architecture.md`](architecture.md) defines target architectural invariants
  and distinguishes them from the transitional repository state.

## Records and waivers

- `schemas/task-record.schema.json` defines the scope, verification, checkpoint,
  completion, commit, behavior, deferral, and readiness fields for contained
  engineering work.
- `templates/task-record.yaml` is a validating starting point for a new record.
- `schemas/waiver.schema.json` defines bounded exceptions with a stable ID,
  explicit rule and scope, rationale, and retirement condition.
- `templates/waiver.yaml` is a validating starting point for an exception
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

A task record is the durable evidence for those steps. A waiver authorizes only
its declared exception and scope; it does not alter the authority hierarchy or
become permanent debt by default. Related replacement work belongs in the
waiver's retirement section.

These schemas are foundational contracts. Automated scope enforcement, CI
validation, architecture fitness gates, and certification generation are later
work and are not implemented here.
