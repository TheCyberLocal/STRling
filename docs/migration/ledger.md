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

## Deterministic toolchain and quality-command foundation

- Status: Complete
- Starting branch: `architecture/v4`
- Starting commit: `e6003d0cd5f299feaf74b53e5a2ce6a958f374bc`
- Behavior change: Developer tooling only; no STRling language/compiler
  semantics intentionally changed
- Completion record:
  [`deterministic-quality-foundation.yaml`](records/deterministic-quality-foundation.yaml)
- Readiness: `READY WITH RECORDED CARRY-FORWARD`

### Checkpoint evidence

| Checkpoint | Result | Commit | Verification |
| --- | --- | --- | --- |
| Toolchain contract | Passed | `62257da6ea7a561c13d8acc0c0f54585c42f98d3` | 19 environments and 26 initial executable policies inventoried; configuration and task record validated; TypeScript remained 19 suites and 963 tests |
| Root quality command framework | Passed | `1486385a6c762021ef7cc4066eb8027ddbade86a` | 10 routing/status tests passed; setup/build/test compatibility passed; JSON results and explicit incomplete states verified |
| Environment enforcement | Passed | `02d3184d5f1626d7181017d082a1fa31a7ff2b04` | 17 total tooling tests passed; matching, mismatch, unavailable, malformed, constrained, and transitional cases verified; representative setup/build/test passed |
| Quality-system integration | Passed | `61bcfd8021d2fb49c5e20881e08c2b0f0235211d` | CI and developer commands converged; check/certify passed; 63 incomplete capabilities remained explicit; swallowed-failure search, documentation links, and patch integrity passed |
| Completion and readiness | Passed | Recorded by the readiness commit | Completion, preservation, deferral, and next-task evidence recorded and schema-valid |

### Accomplished

- `toolchain.json` now governs 17 bindings, repository tooling, language-server
  tooling, executable version policy, dependency resolution, relevant files,
  language commands, capability state, and aggregate scope.
- `./strling` now provides format, format check, lint, typecheck, build, test,
  check, certify, and environment operations with optional component scope and
  JSON output.
- Configured commands fail on unavailable or hard-incompatible environments;
  bounded transitions and intentionally deferred tools remain visible.
- CI uses the canonical environment, build, and test operations and no longer
  converts a failed build into success.

### Preserved behavior

Existing parser, compiler, emitter, AST, IR, runtime, target, public API,
package-version, dependency-version, and generated-fixture behavior was not
intentionally altered. Omega remains in place and is not replaced by the new
certify command.

### Carry-forward

- All formatter and formatter-check capabilities remain unconfigured.
- General lint is configured only for Dart; type/static analysis remains
  unconfigured where no trustworthy canonical tool has been baselined.
- Sixty-three capabilities remain `not_yet_configured` and are returned by
  aggregate JSON results.
- Node 18 is a bounded local transition against supported Node 22; npm and
  several system/package tools remain version-deferred.
- Python, R, Lua, Perl, Java, Kotlin, and language-server Python dependency
  resolution is not yet lock-complete.
- The pre-existing C Makefile test loop does not propagate its accumulated
  failure count.
- Full generated-file, task-scope, architecture, public-API, release, and
  supply-chain certification remains deferred.

The next contained objective is canonical formatting and repository-hygiene
enforcement on top of this shared substrate.
