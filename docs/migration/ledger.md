# Architecture Migration Ledger

## Engineering governance foundation

-   Status: Complete
-   Starting branch: `dev`
-   Starting commit: `d41b0b73fea6c62f7bb32473f190cf4c8c9f14bc`
-   Architecture branch: `architecture/v4`
-   Behavior change: None — governance-only change
-   Completion record:
    [`engineering-governance-foundation.yaml`](records/engineering-governance-foundation.yaml)
-   Readiness: `READY WITH RECORDED CARRY-FORWARD`

### Baseline documentation inventory

-   Formal authority claims: `spec/README.md`, `spec/grammar/dsl.ebnf`,
    `spec/grammar/semantics.md`, and `spec/schema/`
-   Architecture and strategy: `docs/architecture.md` and
    `docs/project_architecture_strategy.md`
-   Contribution policy: `CONTRIBUTING.md` and `docs/guidelines.md`
-   Test policy and generated fixtures: `docs/testing_design.md`,
    `docs/testing_workflow.md`, and `tests/README.md`
-   Release and certification: `docs/releasing.md`, `docs/ci_cd_setup.md`, and
    `tooling/audit_omega.py`
-   Documentation index: `docs/index.md`

### Authority conflicts carried forward

-   The formal specification declares the grammar and semantics authoritative,
    while several testing and contribution guides call TypeScript implementation
    behavior or generated fixtures normative.
-   Existing architecture documentation assigns core semantic logic to every
    binding, which is transitional relative to the one-authority target.
-   Existing release documentation treats the Omega audit and publish pipeline as
    primary gates but does not establish independent installation verification
    from every supported public distribution channel.

These conflicts are recorded, not repaired here. The governance authority
hierarchy determines precedence while later contained work migrates the
transitional repository.

### Checkpoint evidence

| Checkpoint                                      | Result | Commit                                     | Verification                                                                                                                                                                                                                                                   |
| ----------------------------------------------- | ------ | ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Scope and baseline lock                         | Passed | `252d16b495d573051d8c317c980423bcc2bbc64b` | Starting SHA and documentation inventory recorded; JSON schemas and YAML templates parsed and validated; `git diff --check` passed; TypeScript suite passed (19 suites, 963 tests)                                                                             |
| Constitution and authority contract             | Passed | `264ff22c4930a21e39254d384a35aa64194cd5b4` | Permanent engineering rules, artifact precedence, and target invariants reviewed against the specification, architecture, testing, contribution, and release documentation; local Markdown links and `git diff --check` passed                                 |
| Governance contracts and migration traceability | Passed | `00524ab9635113ce5c7297be1c219850ae718a44` | Task and waiver schemas passed Draft 2020-12 schema checks; both templates and the active task record validated; negative cases rejected incomplete completion and a waiver without a retirement condition; local Markdown links and `git diff --check` passed |
| Integration and governance certification        | Passed | No corrective commit required              | Complete-diff scope and integrity passed; schemas, records, Markdown, local links, permanent vocabulary, and commit subjects passed; TypeScript suite passed (19 suites, 963 tests)                                                                            |
| Completion and readiness                        | Passed | Recorded by the readiness commit           | Completion evidence recorded; behavior change classified as none; subsequent quality-governance work assessed as ready with carry-forward                                                                                                                      |

### Accomplished

-   Normative engineering rules, authority precedence, and target architectural
    invariants now govern subsequent work.
-   Task and waiver contracts support scoped work, checkpoint evidence, meaningful
    commits, governed exceptions, completion, and readiness.
-   Migration work has a durable evidence ledger and schema-valid completion
    record without becoming product documentation or semantic authority.

### Preserved behavior

Existing parser, compiler, emitter, runtime, public API, package, and generated
fixture behavior was not intentionally altered.

### Deferred hard gates

-   Pinned toolchains and deterministic dependencies
-   Canonical formatting and lint enforcement
-   Warnings-as-errors and governed suppressions
-   Repository hygiene and generated-file enforcement
-   Task-scope automation and public API snapshots
-   Architecture fitness tests and machine-readable certification
-   CI gate hierarchy and public-distribution verification automation

The TypeScript baseline passed while emitting the existing `ts-jest` TS151002
configuration warning during the initial run. No TypeScript source, test, or
configuration differs from the recorded `dev` baseline, so the warning is
carry-forward quality debt rather than a result of this change.

### Permanent vocabulary boundary

Temporary sequencing identifiers belong only to migration-control records and
MUST NOT appear in implementation vocabulary, product documentation, generated
output, release notes, or permanent commit subjects.

## Deterministic toolchain and quality-command foundation

-   Status: Complete
-   Starting branch: `architecture/v4`
-   Starting commit: `e6003d0cd5f299feaf74b53e5a2ce6a958f374bc`
-   Behavior change: Developer tooling only; no STRling language/compiler
    semantics intentionally changed
-   Completion record:
    [`deterministic-quality-foundation.yaml`](records/deterministic-quality-foundation.yaml)
-   Readiness: `READY WITH RECORDED CARRY-FORWARD`

### Checkpoint evidence

| Checkpoint                     | Result | Commit                                     | Verification                                                                                                                                                                       |
| ------------------------------ | ------ | ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Toolchain contract             | Passed | `62257da6ea7a561c13d8acc0c0f54585c42f98d3` | 19 environments and 26 initial executable policies inventoried; configuration and task record validated; TypeScript remained 19 suites and 963 tests                               |
| Root quality command framework | Passed | `1486385a6c762021ef7cc4066eb8027ddbade86a` | 10 routing/status tests passed; setup/build/test compatibility passed; JSON results and explicit incomplete states verified                                                        |
| Environment enforcement        | Passed | `02d3184d5f1626d7181017d082a1fa31a7ff2b04` | 17 total tooling tests passed; matching, mismatch, unavailable, malformed, constrained, and transitional cases verified; representative setup/build/test passed                    |
| Quality-system integration     | Passed | `61bcfd8021d2fb49c5e20881e08c2b0f0235211d` | CI and developer commands converged; check/certify passed; 63 incomplete capabilities remained explicit; swallowed-failure search, documentation links, and patch integrity passed |
| Completion and readiness       | Passed | Recorded by the readiness commit           | Completion, preservation, deferral, and next-task evidence recorded and schema-valid                                                                                               |

### Accomplished

-   `toolchain.json` now governs 17 bindings, repository tooling, language-server
    tooling, executable version policy, dependency resolution, relevant files,
    language commands, capability state, and aggregate scope.
-   `./strling` now provides format, format check, lint, typecheck, build, test,
    check, certify, and environment operations with optional component scope and
    JSON output.
-   Configured commands fail on unavailable or hard-incompatible environments;
    bounded transitions and intentionally deferred tools remain visible.
-   CI uses the canonical environment, build, and test operations and no longer
    converts a failed build into success.

### Preserved behavior

Existing parser, compiler, emitter, AST, IR, runtime, target, public API,
package-version, dependency-version, and generated-fixture behavior was not
intentionally altered. Omega remains in place and is not replaced by the new
certify command.

### Carry-forward

-   All formatter and formatter-check capabilities remain unconfigured.
-   General lint is configured only for Dart; type/static analysis remains
    unconfigured where no trustworthy canonical tool has been baselined.
-   Sixty-three capabilities remain `not_yet_configured` and are returned by
    aggregate JSON results.
-   Node 18 is a bounded local transition against supported Node 22; npm and
    several system/package tools remain version-deferred.
-   Python, R, Lua, Perl, Java, Kotlin, and language-server Python dependency
    resolution is not yet lock-complete.
-   The pre-existing C Makefile test loop does not propagate its accumulated
    failure count.
-   Full generated-file, task-scope, architecture, public-API, release, and
    supply-chain certification remains deferred.

The next contained objective is canonical formatting and repository-hygiene
enforcement on top of this shared substrate.

## Canonical formatting and repository-hygiene hardgates

-   Status: Complete
-   Starting branch: `architecture/v4`
-   Starting commit: `99e953fdfae0bd4e9c9829e00dc9951d8bdfa900`
-   Behavior change: Developer tooling and tracked-repository state only; no
    STRling language/compiler semantics intentionally changed
-   Completion record:
    [`formatting-repository-hygiene.yaml`](records/formatting-repository-hygiene.yaml)
-   Readiness: `READY WITH RECORDED CARRY-FORWARD`

### Checkpoint evidence

| Checkpoint                       | Result | Commit                                     | Verification                                                                                                                                                |
| -------------------------------- | ------ | ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Formatting and hygiene contract  | Passed | `0052b461818a82b86c73f5113ee46769bfb2d932` | Every active source class received one disposition; tracked artifact and text debt was enumerated; policies and baseline behavior passed                    |
| Canonical formatter integration  | Passed | `c01437529e29151d363e160bc59b91caf85eeb16` | Write/check separation, scoping, structured results, missing tools, mismatches, and aggregate failure propagation passed                                    |
| Mechanical source formatting     | Passed | `2acaf53c0e8d85e1b592cee1b4073d6bedeb98fa` | Ninety files were mechanically formatted; C#, Dart, Python, TypeScript, and tooling baselines were unchanged                                                |
| Tracked-file hygiene enforcement | Passed | `a09b694b88c89856766cabaa04a88632ba32cb5c` | Nine accidental artifacts were removed; 143 files received text-only normalization; scanner and all 17 binding test baselines passed                        |
| Developer and CI hardgate        | Passed | `7dfe6331224ce3a39dd06303183ef5220d3031c5` | Ten-result root aggregate and JSON output passed; 41 tooling tests covered required negative cases; PR CI invokes the canonical root command without bypass |
| Completion and readiness         | Passed | Recorded by the readiness commit           | Completion, preservation, bounded deferral, exact verification, and next-task readiness are schema-valid                                                    |

### Accomplished

-   `governance/formatting.json` assigns one canonical strategy to every active
    source class. Prettier 3.3.3, Ruff 0.15.21, `dotnet format whitespace`, and
    `dart format` are enforceable for repository, LSP, C#, Dart, Python, and
    TypeScript targets.
-   `./strling format` is write mode and `./strling format --check` is
    non-mutating verification. Configured-tool absence, formatter mismatch,
    process failure, malformed policy, and aggregate failure propagate.
-   `governance/repository-hygiene.json` and `./strling hygiene` govern temporary,
    editor, log, scratch, coverage, package, build, binary, archive, credential,
    text-normalization, executable-mode, size, and case-collision hazards.
-   `./strling check` blocks all proven formatting and hygiene checks locally.
    GitHub Actions installs their governed tools and invokes the same command on
    every pull request and governed branch or tag change.

### Canonical formatting state

-   Prettier governs TypeScript, JavaScript, authored JSON, YAML, and Markdown.
-   Ruff format governs Python.
-   `dotnet format whitespace` governs C#.
-   `dart format` governs Dart.
-   Serializer-owned/generated data is explicitly not applicable to source
    formatting. Every remaining source ecosystem has a concrete technical
    reason and retirement condition rather than a fabricated passing gate.

### Repository hygiene state

-   Nine accidental `.new`, `.tmp`, ELF build, VSIX package, test-state, and log
    artifacts were removed from tracking.
-   The intentional Gradle wrapper JAR and LSP icon PNG have exact path, type,
    size, and SHA-256 allowlists; the example editor workspace has an exact
    documented exception.
-   The Perl `Parser.pm`/`parser.pm` case collision has one bounded governed
    waiver whose retirement condition is consolidation to a single canonical
    module path.
-   Governed authored text is UTF-8 with LF endings, no invalid trailing
    whitespace, and a final newline where appropriate. Exact-input and
    serializer-owned files have narrow exclusions.

### Preserved behavior

Grammar, parser, compiler, emitter, AST, IR, public API, target, package-version,
and dependency-version behavior was not intentionally changed. Canonical
Rust-core work, binding migration, specification redesign, and compiler
architecture migration have not begun.

### Carry-forward

-   Strict lint baselining, warnings-as-errors, and broader static-analysis
    coverage are the next contained hardgate objective.
-   Deferred formatter ecosystems retain the bounded, path-specific retirement
    conditions in `governance/formatting.json`.
-   Generated-artifact reproduction integrity, task-scope automation,
    architecture fitness tests, public API snapshots, and supply-chain
    certification remain separate work.
-   Node 18 remains an explicitly bounded local transition until developer
    environments converge on supported Node 22.

The repository is ready for strict linting, warning discipline, and expanded
static-analysis enforcement with the recorded carry-forward above.

## Strict linting, warning discipline, and static-analysis hardgates

-   Status: Complete
-   Starting branch: `architecture/v4`
-   Starting commit: `bb334b0980327b8f3599cd6da0562022c365641a`
-   Behavior change: Developer and CI quality enforcement only; no STRling
    language/compiler semantics intentionally changed
-   Completion record:
    [`static-analysis-warning-hardgates.yaml`](records/static-analysis-warning-hardgates.yaml)
-   Readiness: `READY WITH RECORDED CARRY-FORWARD`

### Checkpoint evidence

| Checkpoint                                 | Result | Commit                                     | Verification                                                                                                                        |
| ------------------------------------------ | ------ | ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| Static-quality contract and baseline       | Passed | `a2bd48f8ead42bd7d9dfe154e0074d7f3fda6f08` | All 19 ecosystems received explicit dispositions; 92 directives and reproducible analyzer findings were inventoried                 |
| Canonical lint and static-analysis routing | Passed | `8602659a75d5a371e4b3ba14610cadf690b8b95a` | Scoped human/JSON commands, analyzer process failures, unavailable tools, transitions, and aggregate propagation were verified      |
| Warning and suppression governance         | Passed | `5058bbdd20816d8827451f73978fc2e29a62044e` | Fatal mature warning paths and exact suppression governance passed controlled warning, unmanaged, invalid, and expired-waiver cases |
| Behavior-neutral remediation               | Passed | `43ca9b52a80e921d73408ce38770e053d99c107d` | Required Python, Dart, Kotlin, Ruby, Rust, and CMake findings were removed without changing recorded binding behavior               |
| Hardgate integration and certification     | Passed | `b19d18106202fb09400eb1bfdb279cedf45943bc` | Twelve lint and ten type/static operations, 87 managed directives/four waivers, structured output, CI routing, and 963 tests passed |
| Completion and next-task readiness         | Passed | Recorded by the readiness commit           | Completion, preservation, deferral, exact certification, and next-task readiness are recorded                                       |

### Enforced static-quality state

| Ecosystem  | Lint                                      | Type/static                          | Warning policy                                      |
| ---------- | ----------------------------------------- | ------------------------------------ | --------------------------------------------------- |
| Repository | Ruff plus suppression governance enforced | Python checker transitional          | Not applicable                                      |
| LSP        | Ruff enforced                             | Strict TypeScript enforced           | Not applicable                                      |
| C          | GCC strict-warning baseline transitional  | Not applicable                       | Transitional on four semantic-risk findings         |
| C++        | Compiler/static strategy transitional     | Not applicable                       | Configured; compiler authority/transitive debt open |
| C#         | .NET analyzers enforced                   | Compiler analysis enforced           | Warnings are errors                                 |
| Dart       | `dart analyze` enforced                   | `dart analyze` enforced              | Fatal                                               |
| F#         | Compiler analysis enforced                | Compiler analysis enforced           | Warnings are errors                                 |
| Go         | `go vet` enforced                         | `go build` enforced                  | Not applicable                                      |
| Java       | `javac -Xlint:all` through Maven enforced | Compiler analysis enforced           | Warnings are errors                                 |
| Kotlin     | Compiler analysis enforced                | Compiler analysis enforced           | All warnings are errors                             |
| Lua        | luacheck transitional                     | Not applicable                       | Not applicable                                      |
| Perl       | Native compile lint enforced              | Not applicable                       | Native warnings are fatal                           |
| PHP        | Recursive syntax lint enforced            | PHPStan transitional                 | Not applicable                                      |
| Python     | Ruff enforced                             | Python checker transitional          | Pytest warnings-as-errors configured                |
| R          | R CMD check/lintr transitional            | Not applicable                       | Transitional with package metadata/runtime          |
| Ruby       | Native warning lint enforced              | Not applicable                       | Native warnings are fatal                           |
| Rust       | Clippy transitional                       | `cargo check --all-targets` enforced | `RUSTFLAGS=-Dwarnings`                              |
| Swift      | SwiftLint transitional                    | Strict compiler build enforced       | `-warnings-as-errors`                               |
| TypeScript | ESLint transitional                       | Strict TypeScript 5.9.3 enforced     | Test-tool diagnostic has one exact governed waiver  |

### Hardgate and suppression state

-   `./strling check` blocks Ruff for repository, LSP, and Python; .NET C#/F#
    analysis; Dart analysis; Go vet/build; Java and Kotlin compiler analysis;
    Perl/Ruby fatal native warnings; PHP syntax; strict LSP/TypeScript checking;
    Rust warning-denied checking; Swift warning-denied compilation; and the
    repository suppression audit.
-   PR CI provisions the governed environments and invokes the canonical root
    aggregate; language jobs use scoped root lint/typecheck commands rather than
    embedded analyzer logic.
-   Six obsolete Rust `allow` attributes were removed. Eighty-seven remaining
    directives match four exact waivers with zero findings: 76 bounded Python
    directives, three suspected-product TypeScript directives, one exact
    ts-jest diagnostic-code waiver, and seven permanent shell interoperability
    directives.

### Preserved behavior

Grammar, parser, compiler, emitter, AST, IR, public API, target, package-version,
and dependency-version behavior was not intentionally changed. Canonical Rust
compiler work, target engines, host-binding migration, Simply redesign, and LSP
intelligence migration have not begun.

### Carry-forward

-   Four C `-Wformat-truncation` findings, three TypeScript callable-Pattern
    findings, and the Ruby interaction baseline are suspected product defects;
    they require contained semantic work and are not quality-baseline debt.
-   C/C++ analyzer authority, Lua, R, PHP/Python/repository type analysis,
    RuboCop, Clippy, SwiftLint, and ESLint remain bounded transitions with exact
    retirement conditions in `governance/static-analysis.json`.
-   The ts-jest 151002 exact-code waiver expires 2027-02-01. Enabling its
    recommended `isolatedModules` setting prevented all 19 suites from executing;
    strict `tsc` and all 963 tests remain green.
-   Generated-artifact integrity, contract governance, machine-enforced
    change/task scope, architecture fitness tests, public API snapshots, and
    supply-chain/release certification remain separate hardgates.

The repository is ready for generated-artifact integrity, contract governance,
and machine-enforced change/scope and architecture controls with the recorded
carry-forward above.

## Generated-artifact and change-integrity hardgates

-   Status: Complete
-   Starting branch: `architecture/v4`
-   Starting commit: `29fda4705cd39857eccdf079ada69d76d97f199a`
-   Behavior change: Governance and quality tooling only; no STRling
    language/compiler semantics intentionally changed
-   Completion record:
    [`generated-artifact-change-integrity.yaml`](records/generated-artifact-change-integrity.yaml)
-   Readiness: `READY WITH RECORDED CARRY-FORWARD`

### Checkpoint evidence

| Checkpoint                               | Result | Commit                                     | Verification                                                                                                                                                             |
| ---------------------------------------- | ------ | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Artifact and change-governance contract  | Passed | `30ff939c9d2dcef449c6088eeef1cf354245ab01` | Ten generated families inventoried; authority and transition classifications recorded; v2 task/change/scope/architecture schemas and eight contract tests passed         |
| Generated-artifact reproduction hardgate | Passed | `a1dd305649b0f5a7a689058d045ea4d05399a760` | Version metadata and 126 Swift compatibility fixtures reproduce exactly; controlled stale, failure, missing, malformed, mutation, extra-output, and cycle cases fail     |
| Task scope and architecture fitness      | Passed | `b6c864d79ba8e98a8a7f842dd463e8bb8562cc9d` | Complete Git diff classification, path scope, generated-output declarations, five active rules, two transitions, one future rule, and 17 controlled cases passed         |
| Quality and CI integration               | Passed | `7f31ebdcf416baf5309046be4ef7f213686e3d8f` | Check/certify run both repository hardgates first; CI uses the canonical command with full history; structured output, 86 focused tests, and 963 TypeScript tests passed |
| Completion and next-task readiness       | Passed | Recorded by the readiness commit           | Committed-state leaf, human, structured, aggregate, certification, schema, CI-YAML, patch-integrity, behavior-preservation, transition, and readiness evidence recorded  |

### Enforced generated-artifact state

-   `version-synchronized-metadata` is reproduced from
    `bindings/python/pyproject.toml` by `tooling/sync_versions.py`.
-   `swift-compatibility-fixture-projection` is reproduced byte-for-byte from
    `bindings/c/tests/fixtures/*.json` by
    `tooling/sync_fixture_projection.py`.
-   Check mode snapshots the entire repository before verification and fails if
    a generator changes tracked or untracked state, even when the changed path
    was already dirty.
-   Eight additional families remain explicitly transitional rather than
    receiving fabricated determinism claims: shared semantic fixtures, C
    compatibility fixtures, the C test skeleton, final audit report, package
    locks, Lua release rockspec, LSP extension payload, and Rust build source.

### Enforced change-governance state

-   Contained tasks declare semantic, public API, schema, diagnostic, target,
    architecture, generated-output, documentation-only, and internal change
    intent with evidence.
-   Git diff selection covers committed, staged, unstaged, untracked, renamed,
    and deleted paths. Allowed, forbidden, expected, and generated-output rules
    are deterministic and case-sensitive; violations fail.
-   Generated-output changes require registry membership, artifact permission,
    and an appropriate declaration.
-   Five active architecture rules protect governance/product dependencies,
    quality/semantic dependencies, generated-input acyclicity, task-record
    placement, and new top-level implementation islands.
-   Duplicated binding compilers and implementation-derived fixtures are
    recorded transitions with retirement conditions. Canonical-core dependency
    enforcement remains inactive until that architecture exists.
-   No bounded task or governance exemption was used.

### Preserved behavior

Grammar, parser, compiler, emitter, AST, IR, diagnostics, targets, public APIs,
standard-library semantics, and package versions were not intentionally
changed. No canonical compiler implementation, binding migration, or legacy
compiler removal has begun.

### Carry-forward

-   Make shared semantic evidence contract-derived and exactly reproducible.
-   Resolve or reclassify the C fixture and test-skeleton generator histories.
-   Make the final audit, checked lockfile families, and Lua release projection
    deterministic; certify disposable release/build outputs in their proper
    release context.
-   Add public API and contract snapshots, deeper dependency-graph fitness
    checks, supply-chain provenance, release installation verification, and the
    remaining recorded static-quality transitions.

The repository is ready for public API and contract snapshot enforcement plus
deeper architectural fitness certification before the migration baseline is
frozen, with the recorded carry-forward above.
