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

## Public contract snapshots and architecture fitness certification

-   Status: Complete
-   Starting branch: `architecture/v4`
-   Starting commit: `b5ff2f0cec8153388e80eec1aac738f882eb89e1`
-   Behavior change: Governance and quality enforcement only; no STRling
    language/compiler semantics intentionally changed
-   Completion record:
    [`public-contract-architecture-fitness.yaml`](records/public-contract-architecture-fitness.yaml)
-   Readiness: `READY WITH RECORDED CARRY-FORWARD`

### Checkpoint evidence

| Checkpoint                               | Result | Commit                                     | Verification                                                                                                                                                         |
| ---------------------------------------- | ------ | ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Public surface and fitness contract      | Passed | `66cecac811373c81876077a6dc07baba6394ee94` | Twenty-two surfaces, five compatibility classes, deterministic strategies, private exclusions, architecture categories, and explicit transition conditions validated |
| Deterministic API and contract snapshots | Passed | `ec5a250a178a75d43ddc4e5ca38e9e1f42adc581` | Ten exact snapshots reproduce; stale, missing, malformed, extraction, public-symbol, signature, and incompatible-schema cases fail                                   |
| Change classification enforcement        | Passed | `c66960e5b9248f095ea84402b1fadb63f4b183e2` | Git-base-relative classification requires exact change level, surface identifier, component match, evidence, and monotonic enforced coverage                         |
| Dependency architecture fitness          | Passed | `409c2c30e250ca851b90a86f4faf7055545e0e52` | Eight active rules pass; three transitions report current evidence; one future canonical-core rule stays non-blocking                                                |
| Quality and CI integration certification | Passed | `a943227c05c26e01ea29babe76962452e00a9faa` | Canonical human/JSON hardgates, 106 focused tests, affected binding suites, full 963-test TypeScript baseline, schema parsing, and CI routing passed                 |
| Completion and next-task readiness       | Passed | Recorded by the readiness commit           | Preservation, exact certification, transition retirement, carry-forward, and baseline-freeze readiness are recorded                                                  |

### Public contract state

-   All 17 binding APIs, TypeScript package entrypoints, the root CLI, and the
    stable base, conformance-fixture, and PCRE2 schemas are inventoried.
-   C, Go, Python, R, TypeScript declarations, TypeScript package entrypoints,
    the root CLI, and all three schemas have deterministic, normalized,
    reviewable snapshots.
-   Changes classify as unchanged, compatible, additive, breaking, or
    intentional correction. Detection is separate from task declaration and
    approval; exact affected surface identifiers are required.
-   C++, C#, Dart, F#, Java, Kotlin, Lua, Perl, PHP, Ruby, Rust, and Swift remain
    transitional until their registry-specific structural extractor,
    normalization, isolation, and reproducibility conditions are satisfied.

### Architecture fitness state

-   Eight current rules protect governance/product and quality/semantic import
    direction, generated-input acyclicity, implementation-derived fixture
    authority, task and top-level placement, specification-schema reference
    authority, and new tooling semantic-island placement.
-   Duplicated binding compilers, implementation-derived shared fixtures, and
    direct LSP-to-Python-binding imports are evaluated transitions with explicit
    migration-dependent retirement conditions.
-   Binding-to-canonical-core dependency direction remains future-state and
    activates per binding only after core implementation, adapter migration,
    legacy removal, and behavior-preservation certification.
-   No bounded task, contract, or architecture waiver was used.

### Hardgate state

-   `./strling contracts --check` fails on stale or missing snapshots, public
    symbol addition/removal, signature drift, extraction failure, malformed
    registry data, incompatible schema mutation, undeclared drift, incompatible
    declarations, and mismatched surface/component declarations.
-   `./strling governance` fails on malformed policy, active forbidden
    dependencies, out-of-authority schema references, implementation-derived
    evidence promoted to normative authority, and undeclared new semantic
    implementation islands.
-   `./strling check` and `./strling certify` execute contract verification,
    generated-artifact verification, and governance before component checks in
    human and structured modes. Pull-request CI fetches full history and invokes
    the same canonical `./strling check` command without duplicated logic.

### Certification evidence

-   Committed-state format, hygiene, lint, typecheck, generation, contracts,
    governance, check, structured check, certify, and structured certify passed.
-   All 106 governance/quality tests passed, including controlled CI-equivalent
    stale snapshot, undeclared symbol removal, breaking schema, forbidden
    dependency, malformed contract, and hardgate-propagation failures.
-   C passed 596 checks and 20 tests; Go passed; Python passed 789 tests; R passed
    725 tests; TypeScript passed all 19 suites and 963 tests.
-   Governance JSON, task YAML, structured output, and CI YAML parsing passed;
    `git diff --check` and checkpoint-5 clean-tree verification passed.

### Preserved behavior and carry-forward

Grammar, parser/compiler/emitter semantics, AST/IR meaning, diagnostics, targets,
standard-library semantics, public APIs, and package versions were not
intentionally changed. No canonical compiler, binding, target-engine, Simply, or
LSP-intelligence migration has begun, and no legacy implementation was removed.

The twelve language-specific extraction transitions, three current architecture
transitions, and one future dependency rule retain the exact retirement and
activation conditions in the completion record. These are the only
contract/architecture carry-forward findings material to baseline freeze and
later product-architecture migration.

The repository is ready for the certified baseline freeze and donor-branch
inventory that closes the hardgate foundation and establishes immutable starting
evidence for product-architecture migration, with the recorded carry-forward
above.

## Certified migration baseline and donor capability inventory

-   Status: Complete
-   Starting branch: `architecture/v4`
-   Starting commit: `95509d581cc47eba04ff38fa403b0c7f59901d51`
-   Certified baseline: `77f6a81e6b0a63cc6052fdadb428c719b16c7c61`
-   Preserved donor: `d41b0b73fea6c62f7bb32473f190cf4c8c9f14bc`
-   Main reference: `664d08de53565929c8f62379b006cd29f93b239f`
-   Behavior change: No STRling language/compiler semantics intentionally
    changed.
-   Completion record:
    [`certified-migration-baseline.yaml`](records/certified-migration-baseline.yaml)
-   Frozen manifest:
    [`migration-baseline.json`](../../governance/baselines/migration-baseline.json)
-   Readiness: `READY WITH RECORDED CARRY-FORWARD`

### Checkpoint evidence

| Checkpoint                                  | Result | Commit                                     | Verification                                                                                                                                     |
| ------------------------------------------- | ------ | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| Baseline identity and evidence contract     | Passed | `6e03884a3567cefa706fe132077eaa8e20745c4f` | Clean ancestry, five schemas, six donor dispositions, four preservation categories, and the required command model validated                     |
| Committed-state baseline certification      | Passed | `4abc8ec71b4466a13be19fb0b6435c7a6a6b6b13` | Baseline SHA passed 63 enforced certify results, 17 binding tests, 143 focused tests, exact generation/contracts, and clean-state checks         |
| Donor capability inventory                  | Passed | `78e494198a37711aa639d7643ac79531c3e0dccf` | Twenty-nine capabilities classified as 6 preserve, 8 port, 7 rewrite, 3 retire, 4 evidence, and 1 discard                                        |
| Frozen manifest and preservation matrix     | Passed | `6e87512d064f1c4cb095199cb530ff2559078c4c` | Twenty-seven fingerprints, 23 transitions, 5 waivers, 21 matrix entries, schema validation, and controlled tamper rejection passed               |
| Baseline protection and final certification | Passed | `97a4ff609ae93be829959022f2af74060ac4db29` | Canonical baseline hardgate, POSIX/Windows routing, 150 focused tests, 50 check results, 64 certify results, and all 17 binding baselines passed |
| Completion and next-task readiness          | Passed | Recorded by the readiness commit           | Exact identities, compatibility obligations, non-contractual defects, carry-forward, clean state, and next-task readiness are recorded           |

The contract checkpoint also required the behavior-neutral formatter correction
`c347bc3d57d4d2daaef5d850a89f6f285c7c4b9f` and the locked-Bundler selection
`77f6a81e6b0a63cc6052fdadb428c719b16c7c61`; the latter is the exact certified
baseline commit.

### Certified baseline state

-   The frozen registry pins manifest SHA-256
    `990d3d8827d8cbfd03d7a2cd03076a2e5b68c883974880caddbaf552dc1f5f3a`.
-   Twenty-seven path-set fingerprints cover enforced public snapshots,
    version-synchronized metadata, Swift compatibility fixtures, the current
    specification and Essential definition, relevant schemas, architecture and
    authority policies, toolchain and quality policy, registries, and the three
    frozen evidence records.
-   Certification evidence records 10 enforced and 12 transitional public
    surfaces; 3 enforced and 8 transitional generated families; 8 enforced, 3
    transitional, and 1 future architecture rules; 23 active transitions; and 5
    active or accepted waivers.
-   The baseline remains compatibility and engineering evidence subordinate to
    normative specifications and ratified versioned contracts. The formal
    specification is recorded as `unversioned-transitional`, not silently
    promoted to a new semantic authority.

### Donor and compatibility state

-   The donor SHA is an ancestor and merge base of the governed line. No donor
    commit is absent from the governed history, but capability representation
    ranges from equivalent or modified to superseded and intentionally removed.
-   Highest-value future inputs include structured diagnostic/result contracts,
    consolidated Python intelligence, embedded-language extraction, LSP
    diagnostics/hover/tokens/navigation/actions, the Essential definition,
    conformance contracts, emitter-edge inputs, and the VS Code client.
-   TypeScript-as-oracle tooling, per-binding semantic compilers, emitter-owned
    planning, direct LSP-to-binding semantics, vendored transport, and legacy
    audit/package assumptions are intentionally ported, rewritten, or retired
    according to the inventory rather than copied wholesale.
-   The preservation matrix records 7 must-preserve obligations, 4 evidence-only
    groups, 6 intentional replacements, and 4 known-defect/non-contractual
    behaviors. Callable TypeScript Pattern behavior, advertised TypeScript
    entrypoint paths, the Perl case-collision, and inconsistent emitter-safety
    behavior are not permanent compatibility promises.

### Hardgate and architecture state

-   `./strling baseline --check` validates the frozen registry, Git commits and
    merge bases, schemas, direct evidence hashes, certified-tree and frozen-file
    fingerprints, donor totals, matrix integrity, and transition/waiver
    consistency in human or structured mode.
-   `check` and `certify` run baseline, public-contract, generated-artifact, and
    governance validation before component operations. The final committed
    integration state passed 50 and 64 enforced results respectively, with zero
    failed or unavailable results and 39 declared incomplete capabilities.
-   Canonical compiler work has not begun. Duplicated binding semantics,
    implementation-derived shared fixtures, and direct LSP-to-Python semantics
    remain explicitly transitional; binding-to-canonical-core enforcement
    remains a future rule.

### Carry-forward

-   Establish the authoritative STRling product definition and reconcile the
    normative specification, versioned-contract, architecture,
    compatibility-evidence, and implementation-evidence hierarchy.
-   Choose and record the formal specification versioning model before canonical
    data-contract design.
-   Preserve accepted evidence and donor traceability while resolving known
    defects and replacing transitional semantic-oracle and per-binding
    architectures through later contained product decisions.

The hardgate foundation is complete enough to govern product migration. The
repository is ready for the authoritative STRling product/specification
architecture task with the recorded carry-forward above.

## Authoritative product and specification architecture

-   Status: Complete
-   Starting branch: `architecture/v4`
-   Starting commit: `df75b88614ef7848856191df1fdf7f8f6b04e557`
-   Behavior change: No STRling language/compiler runtime semantics intentionally
    changed.
-   Completion record:
    [`product-specification-architecture.yaml`](records/product-specification-architecture.yaml)
-   Contradiction inventory:
    [`product-specification-contradictions.md`](product-specification-contradictions.md)
-   Readiness: `READY WITH RECORDED CARRY-FORWARD`

### Checkpoint evidence

| Checkpoint                                       | Result | Commit                                     | Verification                                                                                                                   |
| ------------------------------------------------ | ------ | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| Product identity and contradiction contract      | Passed | `59805a8644947f6109291ea9fc3ebe95c8f635af` | Certified obligations, product identity, conceptual hierarchy, terminology, formatting, hygiene, contracts, and governance     |
| Specification authority and versioning           | Passed | `6f593cc13021f65fcbc59c1b216f6a3d806884dd` | Normative hierarchy, MAJOR.MINOR policy, draft/ratified states, unchanged generation, contracts, links, and structured parsing |
| Authoring surfaces and compiler responsibilities | Passed | `c89ac81d94dc98593f68072dfe791b30a16a6e6b` | Semantic STRling, Simply, regex import, compiler stages, adapters, tooling, and explicit transitions                           |
| Authoritative documentation reconciliation       | Passed | `4979a0a5ce4f5623a36d914915cde779a53c83ee` | Root/spec/architecture/contributor/testing guidance aligned; 29 Markdown files link-checked                                    |
| Architecture consistency certification           | Passed | No commit required                         | 50 check and 64 certify passes, 150 focused tests, 963 TypeScript tests, baseline validation, and authority searches           |
| Completion and canonical-contract readiness      | Passed | Recorded by the readiness commit           | Product, specification, authoring, compiler, transition, behavior-preservation, and next-task readiness recorded               |

### Ratified product and authoring architecture

STRling is a portable regex-intent compiler: developers express what a pattern
means once, and STRling produces verified, explainable, target-specific
regular-expression artifacts while surfacing portability and safety constraints
before runtime. Semantic intent is the flagship abstraction. Semantic STRling
is the future semantic textual frontend; Simply is a first-class idiomatic
semantic frontend; and the current regex-shaped `.strl` syntax is retained as
the low-level compatibility/import frontend. Target regex remains a necessary
compiler output, not the semantic public abstraction.

Host-language adapters identify the ecosystem from which the compiler is
invoked. Target engines identify the regex/runtime semantics for which it
compiles. Binding counts and target counts are not interchangeable, and adapters
and CLI/LSP/editor tooling consume the same canonical compiler capability rather
than defining independent semantics in the target architecture.

### Specification and compiler authority

Ratified versioned specifications, explicitly normative contracts,
specification-delegated conformance cases, and ratified semantic architecture
decisions can define behavior. The reference implementation implements that
authority without silently extending it. Existing binding behavior, historical
tests, generated fixtures, and legacy outputs remain compatibility evidence;
tutorials and examples remain explanatory documentation.

The STRling Semantic Specification uses independent `MAJOR.MINOR` versions.
Major versions permit semantic incompatibility, minor versions add
backward-compatible semantics or contracts, and non-semantic errata retain the
same version with traceability. Compiler/package versions and target-profile
versions are independent and declare their supported specification range. The
next specification identity is `1.0-draft.1`; it is unratified and makes no
current compiler-conformance claim.

The conceptual compiler owns canonical semantic representation, semantic
analysis, portability planning, target-profile interpretation, lowering,
target-specific emission, and versioned `TargetArtifact` production. Exact AST,
Semantic IR, request/result, diagnostic, target-profile, and artifact fields
remain deliberately undefined for the next contained task.

### Certification and carry-forward

Committed-state leaf gates and human/structured aggregates passed using the
repository-pinned Ruff 0.15.21, installed Swift 6.2.1, and Bundler 2.4.20. Full
profiles reported 50 enforced check passes and 64 enforced certify passes with
zero failures or unavailable capabilities. All 150 focused governance/quality
tests and all 19 TypeScript suites / 963 tests passed; 901 tracked JSON and 15
YAML files parsed; all local links in 29 changed Markdown files resolved; and
high-authority searches found no positive TypeScript, binding, or generated
fixture authority claim and no host/target conflation.

Carry-forward is explicit: the regex-shaped frontend, per-binding compilers,
TypeScript-derived compatibility evidence, current shallow AST/IR, target
limitations, binding-coupled tooling, and 26 lower-authority historical or
transitional wording hits remain for contained later migration. Existing
architecture fitness rules already prevent new semantic islands and
implementation-derived normative authority without prematurely invalidating
those transitions, so no new enforcement or empty certification commit was
created.

The repository is ready to define the canonical source model, Semantic IR,
diagnostics, compiler request/result, target profile, and target artifact
contracts with the recorded carry-forward above.

## Canonical semantic and compiler data contracts

-   Status: Complete
-   Starting branch: `architecture/v4`
-   Starting commit: `33f7a9ebe983029964be0a2ef9db96369f186282`
-   Contract suite: `1.0.0`
-   Behavior change: No STRling runtime/compiler semantics intentionally
    changed.
-   Completion record:
    [`canonical-compiler-contracts.yaml`](records/canonical-compiler-contracts.yaml)
-   Certification:
    [`spec/contracts/CERTIFICATION.md`](../../spec/contracts/CERTIFICATION.md)
-   Readiness: `READY WITH RECORDED CARRY-FORWARD`

### Checkpoint evidence

| Checkpoint                                          | Result | Commit                                     | Accomplishment                                                                                         |
| --------------------------------------------------- | ------ | ------------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| Representation audit and contract invariants        | Passed | `cf021a11044d3af6e65378b80391772c333a6558` | Syntax/semantic/target boundaries, UTF-8 coordinates, identity, normalization, and versioning ratified |
| Source and Semantic IR contracts                    | Passed | `436ceaafaa4e33cf5a86aae2557fae2e3146c44a` | Source/provenance and normalized target-neutral Semantic IR defined with positive/negative evidence    |
| Diagnostic and compiler protocol contracts          | Passed | `01e54ebc927f4c2a31476e2479b53cac797f00dd` | Stable diagnostics, request/result, structured failure, partial semantics, and keyed analysis defined  |
| Target profile, portability, and artifact contracts | Passed | `01e0d901cb85f9324f8f823c6712dbcf5e65ca93` | Version-aware capabilities, three portability statuses, and deterministic TargetArtifact defined       |
| Specification-authored conformance contract         | Passed | `2c5ca95d5fae47fd93fbc6c034a20252c296a0c9` | Specification-owned cases, draft seed corpus, and content-addressed authority manifest established     |
| Cross-contract certification                        | Passed | `83dd053de15168a145098d1976f598708dd6e99b` | Suite ownership, leakage, ordering, links, governance, and mandatory check/certify validation enforced |
| Completion and kernel-implementation readiness      | Passed | Recorded by the readiness commit           | Canonical system, unchanged behavior, transitions, carry-forward, and next task recorded               |

### Canonical contract system

-   `SourceDocument` owns opaque source identity, frontend/dialect identity,
    exact inline content or digest-pinned references, specification association,
    provenance, and half-open UTF-8 byte spans. Semantic nodes may have zero or
    more origins, so source-less Simply construction is valid and location does
    not participate in semantic equality.
-   Semantic IR is the single normalized, target-neutral representation for all
    frontends. It defines explicit empty, sequence, alternation, literal,
    wildcard, character set, repetition, anchor/boundary, capture,
    backreference, lookahead, and lookbehind semantics. Stable opaque node IDs
    and logical capture IDs are independent of target numbering and syntax.
-   Derived nullability, length, feature, overlap, and safety facts remain
    separate node-keyed analysis results. Target capability decisions remain
    portability results, not Semantic IR mutation.
-   Diagnostics use stable code, occurrence, severity ownership, phase,
    category, UTF-8 attribution, related locations, advice, and structured text
    edits. English message wording remains presentation unless a specification
    deliberately makes it normative.
-   Compile requests accept exactly one source or normalized semantic input and
    explicit target selection. Results separate semantic output, diagnostics,
    analysis, portability, artifact, support status, and structured failure;
    partial semantics are recovery-only and cannot feed downstream emission.
-   Immutable target-profile references identify profile revision and canonical
    content fingerprint separately from engine and runtime versions.
    Capabilities have enumerated scope and typed availability/constraints;
    unlisted capabilities remain unknown.
-   Portability status is exactly `native`, `equivalent_rewrite`, or
    `unsupported`. TargetArtifact keeps emitted UTF-8 pattern text, engine and
    runtime options, requirements, profile identity, mappings, portability, and
    emission diagnostics separate and deterministically ordered.
-   Specification-authored conformance cases can assert only the layers they
    exercise. Cases cannot self-promote; content-addressed manifest membership
    and ratified delegation own normative authority.

### Versioning and compatibility

Contract suite `1.0.0` is independent of Semantic Specification
`1.0-draft.1`, compiler/package releases, frontend dialect versions,
engine/runtime versions, target-profile revisions, and conformance-manifest
authority. Unknown fields are rejected. Major contract versions carry
incompatible shape, meaning, or ordering changes; minor versions add optional
shape; patch versions clarify or enforce already-stated invalidity.

All canonical arrays define deterministic ordering and uniqueness. Canonical
JSON uses UTF-8, sorted object keys, no insignificant spaces, unescaped Unicode,
and no non-finite values. Semantic equality excludes node IDs, source IDs,
origins, and derived analyses while preserving semantic node content and graph
relationships.

### Certification

The committed suite contains 11 Draft 2020-12 schemas, 29 authored positive
objects, 33 controlled invalid objects, four target-profile examples, four
specification-authored draft cases, and one content-addressed manifest. The
focused validator checks nine linked authority documents and 22 unit tests cover
schema validity, graph identity, UTF-8 boundaries, normalization, target
neutrality, diagnostic/result ordering, profile fingerprints, artifacts,
conformance authority, malformed combinations, and deterministic round trips.

From clean checkpoint commit
`83dd053de15168a145098d1976f598708dd6e99b`, both full all-component
`check` and `certify` aggregates passed with zero failed or unavailable
enforced results. Repository-pinned Ruff 0.15.21, formatting, hygiene, lint,
typecheck, build, generation, public contracts, governance, architecture
fitness, the frozen baseline, canonical validation, all binding checks, and the
TypeScript compatibility baseline of 19 suites / 963 tests passed.

### Transitional contracts and carry-forward

-   Current shallow frontend and binding AST/IR types remain implementation and
    compatibility evidence; they are not canonical Semantic IR.
-   Legacy `spec/schema/base.schema.json` and
    `spec/schema/pcre2.v1.schema.json` retain only their existing public
    compatibility scopes.
-   Implementation-generated `tests/spec` fixtures remain transitional
    evidence outside the specification conformance authority manifest.
-   Duplicated binding diagnostic/result/domain models and emitter capability
    tables remain until contained migrations replace them.
-   Existing parser acceptance, compiler and emitter output, diagnostics,
    targets, bindings, LSP behavior, public APIs, and package versions remain
    unchanged.

The next task may establish the canonical Rust kernel skeleton and schema-backed
domain types for contract suite `1.0.0`. It must not yet migrate Semantic
STRling, Simply, regex import, target planning/emission, bindings, or tooling.

## Canonical Rust kernel and schema-backed domain types

-   Status: Complete
-   Starting branch: `architecture/v4`
-   Starting commit: `7131db85ee0434795669cc6d6a8032d606588c5a`
-   Contract suite: `1.0.0`
-   Kernel crate: `core/` (`strling-kernel`)
-   Behavior change: No existing STRling runtime/compiler semantics
    intentionally changed.
-   Completion record:
    [`canonical-rust-kernel.yaml`](records/canonical-rust-kernel.yaml)
-   Readiness: `READY WITH RECORDED CARRY-FORWARD`

### Checkpoint evidence

| Checkpoint                                        | Result | Commit                                                                                 | Accomplishment                                                                                         |
| ------------------------------------------------- | ------ | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Kernel boundary and dependency contract           | Passed | `4eb0c4ec22b7ce750f8ac0caa09ea361ce9ac812`                                             | Standalone canonical kernel, minimal dependencies, governed quality component, and architecture rule   |
| Source, identity, and semantic domain types       | Passed | `3695415407605266eabd42d16b189ac0e32baad2`                                             | UTF-8 provenance, opaque identities, complete target-neutral Semantic IR, and structural validation    |
| Diagnostics and compiler protocol types           | Passed | `582c46cd6f129f82839e577d16e02ffd80738f1a`                                             | Structured diagnostics, deterministic requests/results, partial-result rules, and exchange validation  |
| Target profile and artifact domain types          | Passed | `db9f00b532550f8775ae9e865bc6d1e08ff8b1cf`                                             | Version-aware typed capabilities, immutable profiles, exact portability, and separated TargetArtifact  |
| Cross-domain validation and fixture certification | Passed | `6e0edd1546e98f082e9b8d204520d7f3a2e8ffa0`                                             | Conformance ownership, all 62 fixture references, exact schema mapping, and controlled drift rejection |
| Repository hardgate integration                   | Passed | `c99f1f8243a605db79be477593a577ffba75e509`, `81394827952b6951e6488ca5cb6552f4e13f3524` | Mandatory mapping guard, kernel quality gates, source hygiene exception, full check and certify passes |
| Completion and compiler-pipeline readiness        | Passed | Recorded by the readiness commit                                                       | Architecture, domains, invariants, unchanged behavior, transitions, and contained next task recorded   |

### Kernel architecture

`core/` is a standalone non-published Rust library and the reference
implementation of the certified contracts, never their authority. Its public
boundary exposes only typed domain and validation modules:

-   `source` owns identities, contract/specification associations, frontend and
    dialect identity, exact inline or digest-pinned content, provenance,
    source origins, and half-open UTF-8 byte spans.
-   `semantic` owns the target-neutral Semantic IR graph, opaque node and
    logical capture identities, character/repetition/assertion semantics, and
    normalized-form precondition validation without a normalization algorithm.
-   `diagnostic` owns stable diagnostic values, locations, advice, fixes, and
    contract-defined ordering independently of English message identity.
-   `protocol` owns compiler request/result, output selection, structured
    failure, partial semantics, keyed analysis results, and cross-envelope
    validation without executing compiler phases.
-   `target` owns engine/runtime versions, immutable profiles, typed capability
    constraints, the exact portability vocabulary, requirements, mappings, and
    deterministic TargetArtifact values without planning or emission.
-   `conformance` owns specification-authored case and manifest types; and
    `validation` owns structured, non-panicking external validation errors.

Runtime dependencies are limited to Serde/serde_json for contract
serialization and SHA-256 for exact canonical fingerprints. Architecture
fitness and mapping checks prohibit dependencies on bindings, CLI/editor
tooling, filesystem/network semantics, or implementation-generated fixtures.

### Domain and contract certification

The kernel preserves all required-versus-optional fields, closed objects,
tagged unions, enum spellings, nullable semantics, deterministic ordering, and
unknown-field rejection from contract suite `1.0.0`. External values validate
explicitly rather than being repaired or causing panics. Logical captures never
use target capture numbering, semantic locations remain attribution rather than
semantic equality, and target syntax and derived analyses cannot enter the
Semantic IR node union.

All 42 Rust tests passed. They cover every ratified semantic node, source-less
construction, multibyte Unicode byte boundaries, duplicate or unresolved
identities, malformed repetition bounds, diagnostic ordering, request/result
state combinations, partial results, multiple versions of the same engine,
typed constraints, exact profile fingerprints, pattern/options separation,
profile-aware artifacts, conformance ownership, and both JSON-to-Rust-to-JSON
and Rust-to-JSON-to-Rust structural equivalence.

The mandatory mapping guard pins all 11 normative schemas and accounts for all
62 canonical fixture objects: 29 positive and 33 controlled-invalid. Six
focused controlled tests prove incompatible schema drift, missing mappings,
dependency expansion, filesystem/network/binding leakage, target syntax in
Semantic IR, and embedded derived analysis fail before the kernel can be
silently declared current.

From committed checkpoint
`81394827952b6951e6488ca5cb6552f4e13f3524`, full all-component `check` and
`certify` aggregates exited zero. Kernel formatting, Clippy, warnings-denied
checking, build and tests; repository formatting, hygiene, lint, generation,
public contracts, governance, baseline and architecture fitness; canonical
schema/fixture validation; TypeScript typecheck/build/tests; and every other
configured binding baseline passed.

### Explicitly absent and carry-forward

No parser, semantic normalization algorithm, diagnostic generation, semantic
analysis, portability planner, target lowering, regex emitter, binding adapter,
Simply migration, LSP/editor integration, package API change, or runtime
semantic migration was implemented.

Existing binding compilers, shallow AST/IR types, duplicated diagnostic/result
models, emitter capability tables, legacy base/PCRE2 schemas, and
implementation-generated `tests/spec` fixtures remain transitional
compatibility evidence. Existing frontends and tooling do not yet consume
`strling-kernel`; their migration remains separately governed work.

The repository is ready for the first executable canonical compiler stage:
semantic normalization and invariant-preserving transformation over the
certified Rust domain model, without yet migrating frontends or target
emitters.
