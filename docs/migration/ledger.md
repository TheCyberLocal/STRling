# Architecture Migration Ledger

## Engineering governance foundation

- Status: Complete
- Starting branch: `dev`
- Starting commit: `d41b0b73fea6c62f7bb32473f190cf4c8c9f14bc`
- Architecture branch: `architecture/v4`
- Behavior change: None — governance-only change
- Completion record:
  [`engineering-governance-foundation.yaml`](records/engineering-governance-foundation.yaml)
- Readiness: `READY WITH RECORDED CARRY-FORWARD`

### Baseline documentation inventory

- Formal authority claims: `spec/README.md`, `spec/grammar/dsl.ebnf`,
  `spec/grammar/semantics.md`, and `spec/schema/`
- Architecture and strategy: `docs/architecture.md` and
  `docs/project_architecture_strategy.md`
- Contribution policy: `CONTRIBUTING.md` and `docs/guidelines.md`
- Test policy and generated fixtures: `docs/testing_design.md`,
  `docs/testing_workflow.md`, and `tests/README.md`
- Release and certification: `docs/releasing.md`, `docs/ci_cd_setup.md`, and
  `tooling/audit_omega.py`
- Documentation index: `docs/index.md`

### Authority conflicts carried forward

- The formal specification declares the grammar and semantics authoritative,
  while several testing and contribution guides call TypeScript implementation
  behavior or generated fixtures normative.
- Existing architecture documentation assigns core semantic logic to every
  binding, which is transitional relative to the one-authority target.
- Existing release documentation treats the Omega audit and publish pipeline as
  primary gates but does not establish independent installation verification
  from every supported public distribution channel.

These conflicts are recorded, not repaired here. The governance authority
hierarchy determines precedence while later contained work migrates the
transitional repository.

### Checkpoint evidence

| Checkpoint | Result | Commit | Verification |
| --- | --- | --- | --- |
| Scope and baseline lock | Passed | `252d16b495d573051d8c317c980423bcc2bbc64b` | Starting SHA and documentation inventory recorded; JSON schemas and YAML templates parsed and validated; `git diff --check` passed; TypeScript suite passed (19 suites, 963 tests) |
| Constitution and authority contract | Passed | `264ff22c4930a21e39254d384a35aa64194cd5b4` | Permanent engineering rules, artifact precedence, and target invariants reviewed against the specification, architecture, testing, contribution, and release documentation; local Markdown links and `git diff --check` passed |
| Governance contracts and migration traceability | Passed | `00524ab9635113ce5c7297be1c219850ae718a44` | Task and waiver schemas passed Draft 2020-12 schema checks; both templates and the active task record validated; negative cases rejected incomplete completion and a waiver without a retirement condition; local Markdown links and `git diff --check` passed |
| Integration and governance certification | Passed | No corrective commit required | Complete-diff scope and integrity passed; schemas, records, Markdown, local links, permanent vocabulary, and commit subjects passed; TypeScript suite passed (19 suites, 963 tests) |
| Completion and readiness | Passed | Recorded by the readiness commit | Completion evidence recorded; behavior change classified as none; subsequent quality-governance work assessed as ready with carry-forward |

### Accomplished

- Normative engineering rules, authority precedence, and target architectural
  invariants now govern subsequent work.
- Task and waiver contracts support scoped work, checkpoint evidence, meaningful
  commits, governed exceptions, completion, and readiness.
- Migration work has a durable evidence ledger and schema-valid completion
  record without becoming product documentation or semantic authority.

### Preserved behavior

Existing parser, compiler, emitter, runtime, public API, package, and generated
fixture behavior was not intentionally altered.

### Deferred hard gates

- Pinned toolchains and deterministic dependencies
- Canonical formatting and lint enforcement
- Warnings-as-errors and governed suppressions
- Repository hygiene and generated-file enforcement
- Task-scope automation and public API snapshots
- Architecture fitness tests and machine-readable certification
- CI gate hierarchy and public-distribution verification automation

The TypeScript baseline passed while emitting the existing `ts-jest` TS151002
configuration warning during the initial run. No TypeScript source, test, or
configuration differs from the recorded `dev` baseline, so the warning is
carry-forward quality debt rather than a result of this change.

### Permanent vocabulary boundary

Temporary sequencing identifiers belong only to migration-control records and
MUST NOT appear in implementation vocabulary, product documentation, generated
output, release notes, or permanent commit subjects.
