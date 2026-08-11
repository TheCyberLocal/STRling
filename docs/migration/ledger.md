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

## Canonical semantic normalization

-   Status: Complete
-   Starting branch: `architecture/v4`
-   Starting commit: `350a1ab7bb76b4cd4546f4a8f129199eec4c31a9`
-   Contract suite: `1.0.0`
-   Kernel stage: `core::normalization`
-   Behavior change: No existing STRling runtime/compiler behavior
    intentionally changed.
-   Completion record:
    [`semantic-normalization.yaml`](records/semantic-normalization.yaml)
-   Readiness: `READY`

### Checkpoint evidence

| Checkpoint                                 | Result | Commit                                     | Accomplishment                                                                                        |
| ------------------------------------------ | ------ | ------------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| Normalization contract and rule inventory  | Passed | `023ce26a00b695ece2eb5d9cfc3457aaa0dd5695` | Normative transformations, preserved forms, invalid states, identity, provenance, and failure policy  |
| Recursive structural normalization         | Passed | `3842363bad75f9740b7b0386ec73819024396ac5` | Pure recursive normalization across all ratified Semantic IR variants with structured failures        |
| Identity and provenance preservation       | Passed | `902302d91a26327f7cfa0b73af4513ba132e4aee` | Stable surviving IDs, logical capture integrity, derivation evidence, and exact UTF-8 source origins  |
| Idempotence, determinism, and properties   | Passed | `4d7c7a985b89eea20a918cff3e3f8102d458416b` | Fixed-seed generated certification of canonical normalization invariants                              |
| Legacy compatibility evidence              | Passed | `ed8527eb6a5f112873d2a8311cf168bd07b3ca54` | Nine parser-free structural comparisons with zero unexplained differences                             |
| Compiler-stage and repository hardgate     | Passed | `6fd2ad674150e519e3ac054f62c222aac883e837` | Canonical schema ownership, source-boundary guards, controlled failures, and repository certification |
| Completion and semantic-analysis readiness | Passed | Recorded by the readiness commit           | Final API, behavior, evidence, explicit exclusions, carry-forward, and readiness recorded             |

### Normalization architecture and canonical rules

The canonical kernel exposes one small public stage boundary: `normalize`
borrows a canonical `SemanticProgram` and returns a new canonical program or a
structured `NormalizationError`. The traversal remains private, requires no
filesystem, environment, clock, random source, network, frontend, binding, or
target profile, and validates both external input invariants and its normalized
postcondition.

Normalization recursively covers all 12 ratified node variants. It flattens
nested sequences and alternations, removes single-child sequence and
alternation wrappers, coalesces adjacent literals, and orders/deduplicates
character-set members and provenance collections by their contract keys.
Sequence items and alternative branches retain their original order. Empty
sequence/alternation wrappers and empty literal strings fail as invalid input;
the explicit `empty` semantic node remains unchanged.

The stage deliberately does not reorder or deduplicate alternatives, factor
common prefixes, rewrite repetitions, normalize Unicode, eliminate assertions,
cross captures, lookarounds, atomic nodes, or repetition operands, expand
Unicode categories, infer target support, or attach nullability, length,
overlap, safety, portability, or target facts.

### Identity, provenance, and property certification

Every surviving semantic node retains its input node ID. Removed wrapper IDs
remain deterministic derivation evidence on the retaining node. A merged
literal keeps the first literal's ID and records subsequent literal and wrapper
IDs as derivations. No node ID is randomized, regenerated, synthesized from
traversal position, or allowed to collide. Logical capture IDs and
backreference relationships are preserved without target capture numbering.

Unchanged nodes retain their origins. Merged or unwrapped structures accumulate
the exact contributing source spans, sort and deduplicate spans and derivation
IDs, and never widen discontiguous material into a fabricated span. Source-less
input remains source-less. All retained spans continue to use half-open UTF-8
byte boundaries, including tested two-byte and four-byte scalar boundaries.

Four fixed 64-bit seeds generated 512 valid depth-bounded programs spanning
every node variant. Each proved `N(N(x)) == N(x)`, repeated structural and JSON
determinism, canonical output validation, capture/backreference integrity, and
target neutrality. A separate deterministic corpus of 256 malformed programs
proved stable structured failures for semantic structure, identities,
references, repetition bounds, character sets, and provenance.

### Compatibility, unchanged behavior, and carry-forward

Nine representative parser-free structural cases matched historical
TypeScript/Python flattening, unwrapping, coalescing, and recursive-child
outcomes after erasing canonical-only identity and provenance data. There are
zero unexplained differences. Canonical stable IDs/origins and separated
capture/atomic representation are representational-only differences; rejecting
empty wrappers/literals and deterministically ordering/deduplicating character
sets are intentional certified-contract corrections rather than legacy product
changes.

No parser migration, grammar change, user-facing diagnostic generation,
semantic fact or ReDoS analysis, portability planning, target capability
resolution, lowering, regex emission, binding migration, Simply migration,
LSP/editor migration, package change, or publishing was implemented. Existing
runtime/compiler execution does not yet invoke the kernel normalizer, so public
product behavior remains untouched.

The next contained canonical compiler task is semantic fact analysis over
normalized Semantic IR, beginning with foundational target-neutral facts needed
by later safety and portability reasoning.

## Canonical semantic fact analysis

-   Status: Complete
-   Starting branch: `architecture/v4`
-   Starting commit: `986abcd394f16fca5cc24f721cd53fe2b391115c`
-   Kernel stage: `core::semantic_analysis`
-   API: `analyze(&SemanticProgram) -> Result<SemanticFacts, SemanticAnalysisErrors>`
-   Behavior change: No existing STRling runtime/compiler behavior
    intentionally changed.
-   Completion record:
    [`semantic-analysis.yaml`](records/semantic-analysis.yaml)
-   Readiness: `READY`

### Checkpoint evidence

| Checkpoint                                   | Result | Commit                                     | Accomplishment                                                                                            |
| -------------------------------------------- | ------ | ------------------------------------------ | --------------------------------------------------------------------------------------------------------- |
| Semantic fact contract and analysis rules    | Passed | `1063c70bb357fea3129c123549a65913720ea8bd` | Target-neutral fact model, Unicode-scalar length unit, complete node rules, conservative cases, deferrals |
| Analysis framework and fact store            | Passed | `d35f4fe054984c3d0938d7f498752bbbcf6abf2a` | Pure API, external NodeId-keyed store, deterministic traversal, structured input and depth failures       |
| Nullability and consumption bounds           | Passed | `4e1711deae54c91603742ced2811acbe731896c4` | Compositional nullable, minimum, finite/unbounded maximum, and consumption facts across all variants      |
| Capture and reference facts                  | Passed | `deaa2c321c247ee43ab100d666849d83a03a2ef2` | Logical definitions, subtree use sets, exact resolution, deterministic ordering, malformed failures       |
| Property and differential certification      | Passed | `5cf7c973eca3c5241e0a30ff771d43b8f918a74d` | Fixed-seed determinism, completeness, consistency, capture integrity, and independent length evidence     |
| Compiler pipeline and repository hardgate    | Passed | `4ba19798266c4b007d2a2878e1fcde9435e3c075` | Stage ownership, prohibited-dependency fitness, kernel and full repository certification                  |
| Completion and analysis-foundation readiness | Passed | Recorded by the readiness commit           | Final facts, properties, exclusions, unchanged behavior, carry-forward, and next-layer readiness          |

### Analysis architecture and foundational facts

The canonical kernel exposes one small pure boundary: `analyze` borrows an
already-normalized canonical `SemanticProgram` and returns `SemanticFacts` or
ordered `SemanticAnalysisErrors`. It never normalizes or repairs input. It
requires no filesystem, network, environment, clock, randomness, frontend,
binding, target, diagnostic, lowering, or emitter information. The contract
mapping registers analysis after normalization while keeping the stages
separately callable.

Facts remain external to Semantic IR in a deterministic `BTreeMap` keyed by
stable `NodeId`. Every reachable node receives a `NodeFacts` record. The
small foundational vocabulary is nullability (`Nullable`, `NonNullable`, or
`Unknown`), minimum consumption, maximum consumption (`Finite(n)` or
`Unbounded`), and consumption classification (`AlwaysZeroWidth`,
`AlwaysConsuming`, `Variable`, or `Indeterminate`). Global and subtree
capture/reference collections preserve logical `CaptureId` relationships and
exact reference resolution without engine numbering or target syntax.

Match-consumption lengths count Unicode scalar values. They do not count UTF-8
source bytes or target-engine code units. Source spans remain half-open UTF-8
byte coordinates. Focused two-byte and four-byte Unicode tests certify this
separation.

All 12 ratified Semantic IR variants compose deterministically. Sequence sums
bounds; alternation selects the minimum and maximum branch bounds; repetition
uses certified lower and upper counts with checked multiplication; captures
inherit their body; assertions and lookarounds are outer zero-width while
their children retain independent facts; atomic nodes inherit their body;
backreferences use resolved capture-body bounds. Optional consuming nodes are
nullable but not intrinsically zero-width. Unbounded repetition of a nullable
body remains unbounded when that body can consume positively.

Backreference nullability remains `Unknown` when canonical meaning cannot
prove empty success. Cyclic capture-reference bounds are conservatively zero
to unbounded. Checked arithmetic and a 128-level semantic nesting limit produce
structured failures rather than panics.

### Property, compatibility, and repository certification

Four fixed 64-bit seeds generated 512 valid normalized programs across every
node variant. They proved repeated-analysis determinism, one fact per reachable
node, unchanged normalized input, finite `minimum <= maximum`, always-zero-width
zero bounds, exact resolved capture identity, and target neutrality. A
separate deterministic corpus of 256 malformed programs proved stable ordered
failures. An independent bounded semantic enumerator compared 128 cases with
zero unexplained minimum/maximum differences.

All 76 kernel tests passed with rustfmt, warnings-denied Clippy, and
warnings-denied cargo check, build coverage, normalization regression, canonical
fixtures, and focused analysis suites. Contract validation certified all 11
schema mappings and 62 fixtures. Controlled architecture tests prove analysis
fails if it gains normalization, target, protocol, diagnostic, emitter,
binding, frontend, editor, environment, clock, randomness, profile, or
portability dependencies.

Repository formatting, hygiene, lint, all-language typecheck, generation,
public and canonical contracts, governance, architecture fitness, frozen
baseline validation, and the human and structured `check all` and
`certify all` aggregates passed from committed state. The explicit TypeScript baseline
passed 19 suites and 963 tests. Pinned Ruff 0.15.21, Swift 6.2.1, and Bundler
2.4.20 were used.

### Explicit exclusions, unchanged behavior, and carry-forward

No ReDoS, progress/termination, overlap or first-set analysis, target
capability evaluation, portability planning, optimizer or semantic rewrite,
user-facing diagnostic generation, lowering, emission, parser migration,
binding migration, Simply migration, LSP/editor migration, public API change,
package version change, or publishing was implemented.

Existing parsers, runtime/compiler execution, targets, emitters, bindings,
Simply, and editor tooling do not yet invoke this analyzer. No existing
STRling runtime/compiler behavior intentionally changed.

Subsequent safety and portability analyses can consume the immutable normalized
program and these facts together. They must preserve conservative `Unknown`
backreference nullability, zero-to-unbounded cyclic-reference bounds, and the
distinction between lookaround child examination length and outer consumed
length. The next contained task is the semantic-analysis layer required for
safety and portability reasoning on this certified foundation.

## Canonical structural semantic analysis

-   Status: Complete
-   Starting branch: `architecture/v4`
-   Starting commit: `d9af94674928ccae32ce9165fb366ee849c0e651`
-   Kernel stage: `core::structural_analysis`
-   API:
    `analyze_structure(&SemanticProgram, &SemanticFacts) -> Result<StructuralFacts, StructuralAnalysisErrors>`
-   Behavior change: No existing STRling runtime/compiler behavior
    intentionally changed.
-   Completion record:
    [`structural-analysis.yaml`](records/structural-analysis.yaml)
-   Readiness: `READY`

### Checkpoint evidence

| Checkpoint                                   | Result | Commit                                     | Accomplishment                                                                                                  |
| -------------------------------------------- | ------ | ------------------------------------------ | --------------------------------------------------------------------------------------------------------------- |
| Structural analysis contract                 | Passed | `efd7c7e7f6249f7c35ff529ba33e1c868999ea37` | Target-neutral facts, complete variant rules, conservative unknowns, overlap vocabulary, bounds, and exclusions |
| Leading-consumption analysis                 | Passed | `bc81aae524dd84d0e0e47103a3804d3653ac973f` | Pure identity-validating API and symbolic first-consumption facts through nullable prefixes                     |
| Length and progress classification           | Passed | `3e4a45a41372ecc159e474a612693580d4014971` | Fixed, finite-variable, unbounded, and indeterminate lengths plus repetition progress and extent                |
| Structural overlap analysis                  | Passed | `e4293183fb87f1ef96804e1a9968c9804d8c4a62` | Conservative leading-set algebra, alternation branch pairs, repetition/follower relationships, resource limits  |
| Property and soundness certification         | Passed | `c404360c1f8b21506cac76c871204349772a09f9` | Fixed-seed determinism, completeness, consistency, exact disjointness evidence, and immutable inputs            |
| Pipeline and repository hardgate integration | Passed | `e3f1892c826d79a6a8d1e6821f54e412ed11779b` | Stage registration, controlled dependency failures, kernel regression, and full repository certification        |
| Completion and safety-analysis readiness     | Passed | Recorded by the readiness commit           | Final API, facts, unknowns, properties, exclusions, unchanged behavior, carry-forward, and readiness            |

### Structural-analysis architecture

The canonical kernel exposes one small pure boundary: `analyze_structure`
borrows an already-normalized `SemanticProgram` and its certified
`SemanticFacts`, then returns `StructuralFacts` or ordered
`StructuralAnalysisErrors`. It never normalizes or runs foundational analysis.
Before deriving facts it validates the Semantic IR specification version, a
private exact-program fingerprint, the complete reachable `NodeId` set, and
each corresponding semantic node kind. Externally supplied mismatched or
malformed state returns structured errors rather than panicking.

Facts remain outside Semantic IR in a deterministic `BTreeMap` keyed by stable
`NodeId`. Every reachable node receives one `NodeStructuralFacts` record.
The analyzer borrows inputs immutably and needs no filesystem, environment,
clock, randomness, binding, frontend, target profile, planner, diagnostic,
lowering, emitter, or runtime state. Architecture fitness registers it after
`semantic_analysis` and rejects dependencies on later safety and portability
stages.

### Implemented structural facts

Leading consumption uses a target-neutral symbolic vocabulary: `Empty`,
explicit Unicode `Scalar`, canonical `CharacterSet`, `Wildcard`, and typed
`Unknown`. Sequences union possible first consumers through prefixes using
certified nullability. Alternations retain branch contributions without
reordering. Repetition, captures, and atomic groups compose from their bodies.
Assertions and lookarounds are empty for enclosing consumption while their
children keep independent examination facts. Backreferences remain
conservative.

Semantic length is classified from certified foundational minimum and maximum
consumption as `Fixed(n)`, `FiniteVariable`, `Unbounded`, or
`Indeterminate`; foundational bounds are referenced rather than duplicated in
the structural record. Each repetition additionally records finite or
unbounded extent and classifies its operand as `AlwaysConsuming`,
`PotentiallyZeroConsuming`, or `Indeterminate`. Unbounded repetition over a
potentially zero-consuming operand is therefore representable as a structural
condition, never as a vulnerability verdict.

Leading overlap is `Disjoint`, `Overlapping`, or typed `Unknown`.
Case-sensitive scalars and finite literal/range sets support exact intersection;
wildcards overlap known consuming sets when inclusion is semantically certain.
Alternations record every deterministic branch-index pair. Sequences record a
nonzero repeated operand against its immediate following expression. The
analyzer never simulates engine backtracking and never converts relationships
into warnings.

Relationship generation is bounded at 4096 pairs and returns
`RelationshipLimitExceeded` before partial results escape. Individual overlap
proofs are bounded at 4096 symbolic term comparisons and return typed
`ComparisonLimitExceeded` uncertainty. Leading sets saturate deterministically
at 256 terms with an explicit unknown marker. Semantic nesting above the
certified 128-level limit returns a structured error.

### Soundness and controlled certification

Four fixed 64-bit seeds - `0x5354525543545552`,
`0x9e3779b97f4a7c15`, `0xd1b54a32d192ed03`, and
`0x94d049bb133111eb` - generated 384 valid normalized programs spanning all 12
Semantic IR variants. They proved repeated-analysis determinism, one complete
record per reachable node, fixed-length consistency with foundational minimum
and finite maximum, positive minimum for every guaranteed-consuming repetition
operand, independently checked exact scalar/interval support for every
`Disjoint` result, and immutability of Semantic IR and foundational facts.
There were zero unexplained property failures.

Sixty-four malformed normalized programs, an exact-program foundational-store
mismatch, and a specification-version mismatch returned deterministic
structured failures without panics. Focused suites independently cover equal
and distinct literals, multibyte Unicode scalars, nullable prefixes, nested
alternation, wildcard, finite sets and ranges, assertions and lookarounds,
fixed and variable lengths, repetition progress, cyclic references, overlap
proofs, deterministic ordering, and each configured limit.

All 105 kernel tests passed with rustfmt, warnings-denied Clippy,
warnings-denied cargo check, build coverage, normalization and foundational
regressions, canonical fixtures, and structural suites. Canonical validation
passed 11 schema mappings and 62 fixtures. Thirteen controlled architecture
tests prove target-profile, portability-planner, binding, frontend, editor,
emitter, safety, portability, runtime-state, risk-severity, and ReDoS
dependencies fail. Repository formatting, hygiene, lint, all-language
typecheck, generation, contracts, governance, architecture fitness, frozen
baseline, `check all`, `certify all`, and the TypeScript baseline of 19 suites
and 963 tests all passed.

### Conservative cases, exclusions, and carry-forward

Important intentional `Unknown` cases are backreference leading consumption,
unknown nullable prefixes, case-folded literal/set algebra, character
categories and negated Unicode-property algebra, wildcard exclusions of line
terminators, doubly negated sets, leading-term saturation, and overlap
comparison exhaustion. Foundational indeterminate consumption produces
indeterminate semantic length or repetition progress. These outcomes are sound
facts for later policy, not analysis failures. Relationship-count exhaustion is
a structured whole-analysis error because a complete relationship store is
required.

No ReDoS verdict, risk severity, safety warning, target-capability evaluation,
portability decision, rewrite or optimization plan, diagnostic generation,
lowering, regex emission, parser or grammar change, binding migration, Simply
migration, LSP/editor migration, public API change, package version change, or
publishing was implemented.

Existing parsers, runtime/compiler execution, targets, emitters, bindings,
Simply, and editor tooling do not yet invoke this analyzer. No existing STRling
runtime/compiler behavior intentionally changed. Normalized Semantic IR and
foundational facts remain unchanged because the analyzer only borrows them and
stores results externally.

The next contained task is the first principled semantic safety analysis. It
must consume these certified structural facts, preserve conservative unknowns,
and avoid raw-source regex heuristics. No target profile, portability decision,
or user-facing warning belongs in this structural layer.

## Canonical semantic safety analysis

-   Status: Complete
-   Starting branch: `architecture/v4`
-   Starting commit: `081f2b3dfd6b4f25f5e26c3a66698eb20da9cd90`
-   Kernel stage: `core::safety_analysis`
-   API:
    `analyze_safety(&SemanticProgram, &SemanticFacts, &StructuralFacts) -> Result<SafetyAnalysis, SafetyAnalysisErrors>`
-   Behavior change: No existing STRling runtime/compiler behavior
    intentionally changed.
-   Completion record:
    [`semantic-safety-analysis.yaml`](records/semantic-safety-analysis.yaml)
-   Readiness: `READY`

### Checkpoint evidence

| Checkpoint                                   | Result | Commit                                     | Accomplishment                                                                                               |
| -------------------------------------------- | ------ | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| Safety contract and threat model             | Passed | `67f8d788a3243014da707f4989241a8a71bd3dcf` | Pure API, five stable proof codes, typed uncertainty, identity evidence, bounds, explicit non-proofs         |
| Safety analysis framework                    | Passed | `c08936dedeb4076b4cd48ba77aaba1b71049f8bb` | Typed model, correspondence and completeness validation, deterministic ordering, evidence and limits         |
| Repetition progress and nested findings      | Passed | `949b9bee150cd7f98a6b20202723b385c7cae21c` | Nullable and indeterminate unbounded progress plus narrowly proved nested repetition amplification           |
| Ambiguity and follower competition           | Passed | `44c5cb871eaad2384c22a6bf33fc5a65ee0a18ff` | Certified repeated-alternation and repeated-operand/follower overlap with stable contributing identities     |
| Property and legacy evidence certification   | Passed | `bca35c9931686f17bd18d2bf6c9237bcbc130e56` | Fixed-seed soundness, immutable inputs, unknown preservation, and zero unexplained legacy corpus differences |
| Pipeline and repository hardgate integration | Passed | `a7836af0614998bbd6de97b26438fe01c155c030` | Stage registration, controlled dependency failures, check/certify, and unchanged TypeScript baseline         |
| Completion and diagnostic-safety readiness   | Passed | Recorded by the readiness commit           | Final API, findings, unknowns, evidence, properties, exclusions, legacy disposition, and readiness           |

### Safety architecture and evidence model

The canonical kernel exposes one pure target-neutral boundary. `analyze_safety`
borrows one already-normalized `SemanticProgram`, its complete certified
`SemanticFacts`, and its complete certified `StructuralFacts`. It validates
contract and specification versions, a private exact-program identity, complete
reachable `NodeId` coverage, structural record and relationship shapes, every
returned evidence reference, and resource limits. It never invokes
normalization, foundational analysis, or structural analysis and never mutates
any input.

`SafetyAnalysis` contains deterministic positive `SafetyFinding` and applicable
`SafetyUncertainty` collections. A positive finding carries a stable
machine-readable code and category, primary node identity, sorted contributing
node identities, typed proof evidence, and any exact structural relationship
reference. Nested evidence retains the stable-node path from outer to inner
repetition. Alternation evidence retains both branch identities and branch
indexes. Follower evidence retains the sequence, repetition, operand, immediate
follower, and sequence indexes. English prose, traversal allocation order, raw
source text, target syntax, and diagnostic severity are not finding identity.

The stage performs one deterministic semantic traversal and consumes already
bounded structural relationships without recomputing character-set overlap.
Semantic input is limited to 65,536 nodes and the result to 4,096 findings and
4,096 uncertainty records. Shared semantic depth and structural relationship
and comparison limits remain effective. Exhaustion is a structured whole-stage
error where complete positive output cannot be exposed safely; findings are
never silently truncated.

### Implemented findings and proof conditions

| Stable code                        | Exact positive proof requirement                                                                                                                                                                                                                                      |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `unbounded_nullable_repetition`    | The repetition extent is certified `Unbounded` and operand progress is certified `PotentiallyZeroConsuming`. `AlwaysConsuming` and `Indeterminate` do not satisfy this proof.                                                                                         |
| `unbounded_indeterminate_progress` | The repetition extent is certified `Unbounded` and operand progress is certified `Indeterminate`. This records missing progress proof separately from proved zero consumption.                                                                                        |
| `nested_repetition_overlap`        | The outer repetition is unbounded and non-possessive; the inner repetition is variable-count and non-possessive; the inner operand is `AlwaysConsuming` with a concrete consuming leading self-witness; and the path crosses only captures or one alternation branch. |
| `repeated_alternation_overlap`     | An enclosing non-possessive repeated region can execute at least twice; no atomic or lookaround barrier intervenes; the certified branch-pair relationship is `Overlapping`; and at least one branch has mandatory consumption so empty-only ambiguity is excluded.   |
| `repetition_follower_overlap`      | A certified immediate sequence relationship exists; the repetition has more than one possible count and is non-possessive; the operand is `AlwaysConsuming`; and the certified operand/follower relation is `Overlapping`.                                            |

These findings prove only the recorded structural facts and risk-enabling
relationships. They do not prove universal vulnerability, denial-of-service
exploitability, catastrophic or other runtime complexity, attacker control,
rejecting input suffixes, resource exhaustion, or behavior of PCRE2,
ECMAScript, Python, or another target engine.

### Unknown preservation and evidence guarantees

`Unknown` is neither safe nor unsafe and is never converted to `Overlapping` or
`Disjoint`. Applicable uncertainty is retained for indeterminate backreference
progress or leading consumption, unsupported Unicode-property or category
algebra, wildcard exclusions, case-folding uncertainty, saturated leading
sets, overlap comparison exhaustion, unknown branch or follower relationships,
unknown-only nested leading evidence, and branch overlap that may be empty-only.
Unknown relationships never produce positive competition findings, and this
stage does not produce a user-facing warning merely because uncertainty exists.

Every positive reference resolves to the same normalized program. Progress
evidence resolves to the repetition and its certified operand fact. Nested
paths consist entirely of directly connected stable semantic identities.
Alternation and follower relationship references resolve to the exact
`Overlapping` record in `StructuralFacts`. Malformed, incomplete, or mismatched
stores and evidence are structured errors rather than partially exposed
analysis.

### Soundness and legacy evidence certification

Four fixed 64-bit seeds - `0x5341464554595f31`,
`0x9e3779b97f4a7c15`, `0xd1b54a32d192ed03`, and
`0x94d049bb133111eb` - generated 384 normalized programs spanning all 12
Semantic IR variants. Six deterministic proof witnesses cover every positive
finding code and unknown preservation. The property suite certifies repeated
analysis determinism, complete evidence integrity, disjointness protection,
progress protection, unknown preservation, and immutability of
`SemanticProgram`, `SemanticFacts`, and `StructuralFacts` with zero soundness
failures.

A six-case comparison with the historical source-text/nested-quantifier
detector has zero unexplained differences. It records one direct agreement, a
canonical semantic improvement for bounded inner partition competition, a
legacy false positive for possessive protection, legacy false-negative
candidates for repeated alternation and follower competition, and an
unsupported historical Unicode/property relationship left unknown. Canonical
behavior was not altered to match the donor heuristic.

The historical raw-source ReDoS logic is superseded as canonical semantic
authority. It is retained only as compatibility evidence and remains
temporarily present in existing donor product surfaces because changing or
migrating those surfaces is outside this task.

All 133 canonical kernel tests passed with rustfmt, warnings-denied Clippy,
warnings-denied cargo check, build coverage, normalization, foundational and
structural regressions, canonical fixtures, and all safety suites. Canonical
validation passed 11 schema mappings and 62 fixtures. Fifteen controlled
architecture tests reject missing prerequisites and injected raw-source scan,
parser, target, planner, portability, binding, frontend, diagnostics, emitter,
runtime-state, severity, ReDoS, and target-engine dependencies.

From committed state the governed repository `check` returned 40 passing
results and `certify` returned 42 passing results. Repository formatting,
hygiene, lint, all-language typecheck, generation, contracts, governance,
architecture fitness, frozen baseline validation, focused quality/governance
tests, patch integrity, and clean-tree verification passed. The unchanged
TypeScript baseline built, typechecked, and passed all 19 suites and 963 tests.

### Explicitly unchanged behavior, exclusions, and carry-forward

No existing STRling runtime/compiler behavior intentionally changed. The new
capability is internal to the canonical Rust kernel. Existing parsers,
compilers, runtimes, targets, emitters, bindings, Simply, and editor tooling do
not invoke it. Grammar acceptance, diagnostics, severity, target decisions,
regex output, public APIs, package versions, and published artifacts remain
unchanged.

No user-facing safety diagnostic or prose, severity policy, remediation
metadata, automatic possessive or atomic rewrite, target-specific risk or
exploitability model, portability plan, target lowering, emission, grammar or
parser change, binding migration, Simply migration, or LSP/editor migration was
implemented.

The only carry-forward is the next contained compiler layer. It should convert
certified semantic and safety evidence into structured compiler diagnostics and
remediation metadata, preserve stable identity paths and uncertainty, and keep
target-specific behavior outside semantic safety analysis. The canonical
safety stage is `READY` for that work.

## Canonical structured diagnostic generation

The canonical Rust kernel now owns a dedicated target-neutral communication
stage after semantic safety analysis:

```text
SemanticProgram
  -> normalize
  -> analyze
  -> analyze_structure
  -> analyze_safety
  -> generate_diagnostics
  -> CompileResult diagnostics
```

`diagnostic_generation::generate_diagnostics(&SemanticProgram,
&SemanticFacts, &StructuralFacts, &SafetyAnalysis)` is pure and validates that
all four inputs describe the same exact normalized program before producing a
canonically ordered `DiagnosticGeneration`. The generation records retain
contract `Diagnostic` values alongside stable semantic provenance. A
crate-private compiler pipeline proves the full stage ordering and projects
diagnostics into a successful validated `CompileResult` with complete semantics
and analysis, no portability plan, and no target artifact.

Diagnostic generation communicates certified evidence. It does not rediscover
safety conditions, parse source regex text, modify Semantic IR, invoke emitters,
consult target profiles, plan portability, or apply fixes.

### Stable mappings and canonical severity

| Diagnostic code    | Certified safety finding           | Severity | Primary evidence | Related evidence                  | Descriptive remediation                                                                  |
| ------------------ | ---------------------------------- | -------- | ---------------- | --------------------------------- | ---------------------------------------------------------------------------------------- |
| `STRL-SAFETY-0001` | `unbounded_nullable_repetition`    | warning  | repetition       | operand when source-backed        | Require progress before another unbounded iteration.                                     |
| `STRL-SAFETY-0002` | `unbounded_indeterminate_progress` | info     | repetition       | operand when source-backed        | Make progress explicit or bound repetition when progress cannot be established.          |
| `STRL-SAFETY-0003` | `nested_repetition_overlap`        | warning  | outer repetition | inner repetition and operand path | Remove the ambiguous nested partition or make repetitions consume distinct regions.      |
| `STRL-SAFETY-0004` | `repeated_alternation_overlap`     | warning  | repeated region  | exact overlapping branches        | Narrow branches so repeated input selects a distinct alternative.                        |
| `STRL-SAFETY-0005` | `repetition_follower_overlap`      | warning  | repetition       | operand and immediate follower    | Separate repeated content from follower input competing for the same leading characters. |

Finding identity, evidence confidence, diagnostic severity, and later
target-specific policy are independent. These severities use
`compiler_policy` and communicate target-neutral structural actionability.
They do not assert exploitability, catastrophic runtime complexity, universal
vulnerability, attacker control, or behavior of any target engine. Messages and
advice make that limitation explicit. `fixes` is always absent, and advice
contains no atomic-group or possessive-quantifier target syntax.

### Identity, evidence, source projection, and uncertainty

Every generation record retains the primary `NodeId`, sorted contributing
`NodeId` values, applicable `StructuralRelationshipRef`, exact typed
`SafetyEvidence`, and available canonical `SourceOrigin` values. Diagnostics
remain valid without source text. When provenance exists, projection selects
the smallest honest half-open UTF-8 byte span. Outer repetitions or repeated
regions are primary; inner repetitions, overlapping branches, operands, and
followers are separately ordered related locations. Discontiguous origins are
never merged into a fabricated range, and UTF-16/LSP conversion remains outside
the kernel.

Equivalent evidence is deduplicated before output. Stable zero-based
`DiagnosticOccurrence` ordinals are assigned only after sorting by durable
diagnostic code, primary semantic identity, contributing identities, and typed
evidence identity, followed by canonical contract ordering. Identical semantic
input and evidence therefore produce identical diagnostics and occurrence IDs
without randomness, time, or traversal-order counters.

Typed `SafetyUncertainty` records do not become positive warnings or
informational noise. Unknown overlap, unsupported Unicode-property algebra,
wildcard or case-folding limits, comparison exhaustion, and other uncertainty
remain preserved in `SafetyAnalysis` for later policy.

### Property, contract, pipeline, and hardgate certification

Four reproducible seeds - `0x444941475f505231`, `0x9e3779b97f4a7c15`,
`0xd1b54a32d192ed03`, and `0x94d049bb133111eb` - generated 256 programs
and 189 diagnostics, including 34 uncertainty-only programs. The suites certify
determinism, stable occurrence identity, evidence integrity, exactly-once
finding correspondence, no uncertainty promotion, honest provenance, and
immutability of Semantic IR and all prerequisite analyses.

All 153 kernel tests passed. Contract validation passed 11 schemas, 30 positive
fixtures, 33 negative fixtures, 9 diagnostic documents, and 63 mapped kernel
fixtures. Twenty-one controlled diagnostic architecture tests reject missing
prerequisites and injected target, planner, portability, emitter, binding,
frontend, editor, runtime-state, raw-source, and engine-specific dependencies.
Eighty-nine focused governance and quality tests passed.

From committed checkpoint-six state, governed `check` returned 40 passing
results and `certify` returned 42. Formatting, hygiene, lint, all-language
typecheck, generation, contracts, governance, architecture fitness, frozen
baseline validation, patch integrity, and clean-tree verification passed. The
unchanged TypeScript baseline built, typechecked, and passed 19 suites and 963
tests.

### Unchanged behavior, exclusions, and readiness

No existing STRling runtime/compiler behavior intentionally changed. Only the
canonical kernel gained structured diagnostic-generation capability. Grammar
and parser behavior, target decisions, regex output, public package APIs,
package versions, bindings, Simply, LSP/editor presentation, and published
artifacts remain unchanged.

Target capability diagnostics, portability diagnostics and decisions, automatic
rewrites, target-specific remediation, target lowering, emission, parser
migration, binding migration, Simply migration, and LSP/editor presentation
migration were not implemented.

The only carry-forward is target-aware semantic capability modeling and
portability reasoning. That work must preserve the target-neutral safety and
diagnostic layers, add target policy outside them, and keep remediation
non-executable until semantic preservation is proven. Readiness is `READY`.

## Canonical target capability evaluation

The canonical Rust kernel now owns the first target-aware factual stage after
all target-neutral semantic, structural, safety, and diagnostic work:

```text
SemanticProgram
  -> normalize
  -> analyze
  -> analyze_structure
  -> analyze_safety
  -> generate_diagnostics
  -> extract_requirements
  -> evaluate_capabilities(TargetProfile)
```

`capability_evaluation::extract_requirements` validates that normalized
`SemanticProgram`, `SemanticFacts`, and `StructuralFacts` describe the exact
same immutable program, then produces canonical requirement occurrences keyed
by stable `NodeId`. `capability_evaluation::evaluate_capabilities` validates
the supplied profile, exact compatible specification, profile revision, and
canonical fingerprint before binary-searching its enumerated capability table.
The profile is the complete target authority; no installed engine, filesystem,
environment, network, clock, randomness, frontend, binding, editor, or emitter
state is consulted.

### Requirements and factual outcomes

Typed requirements cover lookahead; fixed and variable lookbehind; named
logical captures and backreferences; Unicode properties, built-in classes, and
non-ASCII scalar data; atomic semantics; lazy and possessive repetition;
anchors and word boundaries; and insensitive matching. Evidence retains exact
capture/reference resolution, assertion polarity, structural lookbehind body
and length, position kind, Unicode member data, and repetition mode. It never
contains target spelling, emitted flags, final capture numbers, or rewrite
instructions.

Base composition constructs, ASCII-only literal/set semantics, wildcard,
greedy repetition, and unnamed capture add no special target requirement by
themselves. Child requirements remain independently visible.

| Disposition           | Meaning                                                                  |
| --------------------- | ------------------------------------------------------------------------ |
| `Supported`           | The exact profile proves native support and every constraint is met.     |
| `Unsupported`         | The exact profile explicitly declares native capability unavailable.     |
| `ConstraintViolation` | The capability exists, but certified semantic facts exceed a constraint. |
| `Unknown`             | Capability data or comparable constraint evidence is absent.             |

Missing profile data always remains `Unknown`; absence never implies false.
These outcomes are factual native-support evidence, not the later portability
vocabulary. In particular, `Unsupported` does not rule out an independently
proved equivalent rewrite.

Typed `equals`, `at_most`, `at_least`, `one_of`, and `requires_option`
constraints compare exact scalar values and units. Fixed, finite-variable,
unbounded, and indeterminate lookbehind classifications come only from
certified foundational and structural facts. Any proved violation wins;
otherwise missing or incomparable evidence stays unknown, and only
all-satisfied constraints establish support.

### Version, profile, and property certification

The same requirement set produces different factual results across authored
profiles without hard-coded engine assumptions. PCRE2 10.42 explicitly lacks
variable-length lookbehind. PCRE2 10.43 evaluates its certified maximum but
keeps the overall result unknown when matcher-API context is unavailable.
ECMAScript 2024 and Python `re` 3.11 independently demonstrate available,
unavailable, constrained, option-dependent, and absent information. Every
result records profile identity/revision/fingerprint and engine/runtime version
alongside the requirement, exact capability record or absence, constraint
facts, constraint evaluations, and disposition.

Four fixed seeds - `0x4341504142494c49`, `0x9e3779b97f4a7c15`,
`0xd1b54a32d192ed03`, and `0x94d049bb133111eb` - generated 256
normalized programs and 2,048 repeated evaluations across the four authored
profiles. Determinism, exactly-one-result completeness, unknown preservation,
profile sensitivity, constraint-violation evidence, and immutability of all
inputs passed. Sixteen controlled malformed profiles were rejected with zero
unexplained failures.

All 169 kernel tests passed with rustfmt, warnings-denied Clippy and cargo
check, authored target-profile fixtures, focused capability suites, pipeline
tests, and prior regressions. Canonical validation retained 11 schema mappings
and 63 fixtures. Controlled architecture tests reject target-neutral reverse
dependencies, prerequisite re-execution, runtime or filesystem probing,
emitters, planners, portability policy, bindings, frontends, editors, and
engine-specific assumptions. Governed repository quality, generation,
contracts, governance, baseline, check, certify, patch integrity, clean-tree
verification, and the unchanged 19-suite/963-test TypeScript baseline passed.

### Unchanged behavior, exclusions, and readiness

No existing STRling runtime/compiler behavior intentionally changed. Only the
canonical kernel gained target-capability evaluation. Existing grammar and
parsers, compilers and runtimes, target selection, portability policy,
diagnostics, lowering, regex emission, public APIs, package versions, bindings,
Simply, LSP/editor integrations, and published packages remain unchanged.

Equivalent rewrite planning, final portability states, target-specific
diagnostics, target lowering, regex emission, automatic remediation, runtime
engine probing, and parser/binding/Simply/LSP migration were not implemented.

The next contained task is canonical portability planning: transform factual
capability results into `native`, `equivalent_rewrite`, or `unsupported`
decisions without emitting target syntax. Readiness is `READY`.

## Canonical portability planning

The canonical Rust kernel now owns a pure representation-strategy stage after
factual, version-sensitive capability evaluation:

```text
SemanticProgram
  -> normalize
  -> analyze
  -> analyze_structure
  -> analyze_safety
  -> generate_diagnostics
  -> extract_requirements
  -> evaluate_capabilities(TargetProfile)
  -> plan_portability
```

`portability_planning::plan_portability(&SemanticProgram, &SemanticFacts,
&StructuralFacts, &TargetProfile, &CapabilityEvaluation)` validates exact
correspondence among the normalized program, certified facts, extracted
requirements, evaluation fingerprint, and immutable profile. It consumes the
supplied factual results without recomputing capabilities and produces a
deterministic `PortabilityPlan`. The stage has no filesystem, environment,
network, runtime probe, clock, randomness, frontend, binding, editor, emitter,
or target-syntax dependency and mutates none of its inputs.

### Decision and aggregation semantics

Every capability result receives exactly one independently ordered decision,
including when several requirements belong to one semantic node.

| Planning disposition | Certified meaning                                                                                                                                                                                                 |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `native`             | The exact supplied profile produced `Supported`; the plan retains the complete capability and constraint evidence.                                                                                                |
| `equivalent_rewrite` | Native support is negative, a registered target-neutral strategy applies, every semantic proof precondition is satisfied, and every replacement requirement is supported by the same supplied evaluation/profile. |
| `unsupported`        | Native support is explicitly unavailable or constraint-violating and the complete certified registry establishes that no available equivalent rewrite applies.                                                    |
| unresolved evidence  | Capability data is `Unknown`, a rewrite proof prerequisite is indeterminate, or replacement support is unknown. This is planning evidence outside the final status enum.                                          |

Aggregation is completeness-first. Any unresolved requirement suppresses the
program-level final status, even alongside explicit negative evidence. With
complete evidence, `unsupported` takes precedence over
`equivalent_rewrite`, which takes precedence over `native`; a requirement-free
program is natively portable. This preserves the normative final vocabulary
exactly and prevents factual `Unknown` from becoming negative evidence.

Rewrite dependencies are stable requirement-identity edges. They must connect
distinct rewrite decisions, are deterministically ordered, and must be
acyclic. No optimizer or commutativity assumption is present.

### Certified rewrite registry and proof boundary

The initial closed registry contains one strategy:
`rewrite.atomic_literal.elide.v1`. It may remove atomic semantics around a
literal because certified foundational facts prove the original node is
`Atomic`, Semantic IR proves its direct body relationship, and foundational
facts prove that body is `Literal`. The strategy introduces no replacement
semantic requirements and stores no engine spelling or regex fragment.

Variable-length lookbehind transformations, arbitrary atomic or possessive
elimination, safety-motivated atomic or possessive changes, capture numbering,
flag spelling, and other engine-specific forms are not registered. They require
additional semantic proof or belong to later target lowering. Failed proof
preconditions make a strategy unavailable; indeterminate proof or replacement
support remains unresolved.

### Property, pipeline, and hardgate certification

Four reproducible seeds - `0x504f525441424c45`, `0x9e3779b97f4a7c15`,
`0xd1b54a32d192ed03`, and `0x94d049bb133111eb` - generated 256
normalized programs across four authored profiles. The harness performed 1,024
capability evaluations and 2,048 repeat planner invocations, producing exactly
64 rewrite plans, 695 unresolved decisions, and 160 semantic plan
differentials caused only by profile changes. Sixteen malformed correspondence
cases were reproducibly rejected. Determinism, completeness, native soundness,
rewrite proof soundness, unsupported soundness, Unknown preservation, profile
sensitivity, self-validation, and five-input immutability passed with zero
unexplained failures.

All 194 kernel tests passed with rustfmt, warnings-denied Clippy and cargo
check, 11 schema mappings, and 63 fixtures. Sixteen controlled architecture
tests reject capability recomputation, reverse dependencies, emitters, target
artifacts, runtime probing, bindings, frontends, editors, and incorrect stage
ordering. One hundred eight focused governance and quality tests passed.

From committed checkpoint-six state, hygiene, all-language typecheck,
generation, contracts, governance, architecture fitness, frozen-baseline
validation, patch integrity, and clean-tree verification passed. Structured
`check` and `certify` completed and retained their governed nonzero disposition
only for declared incomplete or unavailable repository capabilities, including
the local Ruff and Bundler version mismatches; no enforceable operation relevant
to this work failed. The unchanged TypeScript baseline built, typechecked, and
passed all 19 suites and 963 tests.

### Explicitly unchanged behavior, exclusions, and readiness

No existing STRling runtime/compiler behavior intentionally changed. Only the
internal canonical kernel gained portability planning. Existing parser and
grammar behavior, runtimes, safety analysis and diagnostics, target selection,
regex output, public APIs, package versions, bindings, Simply, LSP/editor
behavior, and published artifacts remain unchanged.

Rewrite application, target-specific diagnostics, capture numbering, target
lowering, regex emission, `TargetArtifact` production, runtime engine probing,
and binding/Simply/LSP migration were not implemented.

The next contained task is target-aware lowering of certified portability plans
into target-neutral lowering structures before actual emitter serialization.
Readiness is `READY`.

## Baseline repository security hardgates

-   Status: Complete
-   Starting branch: `architecture/v4`
-   Starting commit: `cb5c92c975d1820c50234babecbe0b3e08a7fee0`
-   Behavior change: Repository engineering tooling and CI only; no STRling
    runtime/compiler behavior intentionally changed
-   Completion record:
    [`baseline-repository-security.yaml`](records/baseline-repository-security.yaml)
-   Readiness: `READY WITH RECORDED CARRY-FORWARD`

### Checkpoint evidence

| Checkpoint                                    | Result        | Commit                                     | Verification                                                                                                                                                                                                                          |
| --------------------------------------------- | ------------- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Security contract and repository inventory    | Passed        | `11fc5c737183b3ed25799c6fccf89360f48ac74a` | Twenty-two dependency roots, two workflows, 16 action references, existing credential handling, waiver schema, structured operations, and tool pins inventoried; normative policy and result schemas validated                        |
| Dependency and lock integrity                 | Passed        | `1c305bd9f41579f2a7e0d1f2011c0dd316168622` | Twenty-four initial repository checks passed; controlled missing-lock, inconsistency, malformed-lock, unmanaged-manifest, and tool-drift cases failed without modifying dependency state                                              |
| Secret and workflow safeguards                | Passed        | `2068c731b721da8915ba03a8bb62dc6920fead47` | Tracked content passed high-confidence secret detection; both workflows use read-only defaults, exact privilege elevation, immutable action commits, and bounded checkout credential persistence                                      |
| Vulnerability and license policy              | Failed closed | `51ad419cb924e70a7b1c91abd35bf7153d932a49` | Live npm evidence exposed 53 blocking high/critical bindings and ten unknown VSCE licenses; missing Cargo and 30 legacy ecosystem checks remained UNAVAILABLE; no dependency was silently upgraded or finding hidden                  |
| Security waivers and certification properties | Passed        | `ce3f29dc0e986f3fdedb9fb513108b507f37b0f6` | Two exact accepted waivers bind all 63 reviewed findings through 2026-09-10; 23 security tests certify determinism, no false pass, containment, expiry, fixture safety, unknown-ID failure, and input immutability                    |
| Root command, CI, and hardgate integration    | Passed        | `10f612e332a07a80bb6eb143c03d0ee323970aed` | Fast gates run under `check`; network risk runs under `certify`; root JSON preserves nested five-state results; CI invokes the same implementations and installs the exact cargo-audit 0.22.2 pin; semantic dependency fitness passes |
| Completion and readiness                      | Passed        | Recorded by the readiness commit           | Coverage, exceptions, structured semantics, environmental limits, unchanged behavior, production supply-chain exclusions, and next-task readiness recorded                                                                            |

### Security coverage

-   The normative inventory covers npm, Cargo, Dart Pub, Composer, Bundler, Go,
    SwiftPM, NuGet, Maven, Gradle, Python, LuaRocks, CPAN, R, and C/C++
    dependency/build metadata across 22 roots.
-   Deterministic local checks enforce governed manifest discovery, required
    locks, parseability, manifest/lock correspondence, integrity/checksum
    metadata, exact quality pins, prohibited floating declarations, tracked
    secret patterns, and workflow least privilege.
-   Live vulnerability evidence uses `npm audit` for three lockfiles and the
    exact `cargo-audit` 0.22.2 adapter for two Cargo locks. License evidence uses
    npm lockfile v3 metadata and offline locked Cargo metadata. Go and Swift
    certify only their current no-external-dependency state.
-   CI actions use full immutable commits; validation retains read-only default
    permissions and no release secrets; only exact publication/tag jobs elevate
    permissions or preserve checkout credentials.

### Active exceptions

| Waiver                     | Exact scope                                                                                                           | Expiry       |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------- | ------------ |
| `WVR-SEC-NPM-TOOLING-001`  | 53 enumerated high/critical npm advisory/package/version/severity bindings in development or packaging chains         | `2026-09-10` |
| `WVR-SEC-VSCE-LICENSE-001` | Ten enumerated VSCE signing package/version bindings whose metadata is `SEE LICENSE IN LICENSE.txt` and stays unknown | `2026-09-10` |

Every match retains its waiver ID in structured evidence. New, stale,
overlapping, expired, unknown, path-mismatched, or unaccepted scope fails.

### Structured security semantics

-   `PASS`: configured evidence completed and contains no blocking finding.
-   `FAIL`: an unwaived blocking finding or malformed governed input exists.
-   `WAIVED`: every otherwise-blocking finding is covered by an exact accepted,
    unexpired record and remains visible.
-   `UNAVAILABLE`: a required scanner, advisory source, dependency cache, or
    configured ecosystem implementation cannot produce evidence.
-   `INCOMPLETE`: configured coverage or structured evidence cannot support a
    pass/fail decision, including root identity/status/exit disagreement.

`FAIL`, `UNAVAILABLE`, and `INCOMPLETE` fail root aggregates. Generated evidence
does not amend policy or exceptions.

### Verification and carry-forward

The complete tooling suite passes 230 tests, including 23 focused security tests
and 42 root quality-routing tests. Repository formatting, hygiene, generation,
contracts, governance, architecture fitness, and frozen baseline validation
pass. TypeScript typecheck/build and all 19 suites with 963 tests pass. Rust
formatting, warnings-denied Clippy, cargo check, and all 194 kernel tests pass.

Local all-language lint is `UNAVAILABLE` only for the existing Bundler mismatch;
all-language typecheck is `UNAVAILABLE` only for missing Swift. Security
integrity and content/workflow operations pass. Dependency risk contains four
`WAIVED`, nine `PASSED`, and 32 `UNAVAILABLE` checks, so structured `certify`
truthfully remains `UNAVAILABLE`. Thirty of those checks are the explicitly
configured ecosystems without authoritative repository scanners; two are the
locally absent Cargo scanner that CI installs at its exact pin.

SBOM generation, provenance/attestation, signing, release credentials,
publication, unavailable ecosystem adapters, remediation of both expiring
waivers, and a fully available structured CI/certification profile remain
recorded next work.

### Explicitly unchanged behavior and readiness

No existing STRling runtime/compiler behavior intentionally changed. Language
semantics, parsers, Semantic IR, safety analysis, target selection, lowering,
regex emission, adapters/bindings, public APIs, package versions, and release
artifacts remain unchanged. No dependency was upgraded merely to satisfy a
scanner and no functional credential was added.

The baseline is `READY WITH RECORDED CARRY-FORWARD` for the remaining structured
CI/certification-profile task. The carry-forward prevents an unqualified
`READY` and a passing certification claim; it does not weaken the implemented
fail-closed hardgates.

## Structured CI profiles and certification artifacts

-   Status: Complete
-   Starting branch: `architecture/v4`
-   Starting commit: `77d9a9b2b54dbbc66369cc16186ea36f0fad78c3`
-   Behavior change: Repository engineering tooling and CI only; no STRling
    runtime/compiler behavior intentionally changed
-   Completion record:
    [`structured-certification-profiles.yaml`](records/structured-certification-profiles.yaml)
-   Readiness: `READY WITH RECORDED CARRY-FORWARD`

### Checkpoint evidence

| Checkpoint                                | Result | Commit                                     | Verification                                                                                                                                                                                                                         |
| ----------------------------------------- | ------ | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Profile and certification contract        | Passed | `e6294e485c0ef3443354aac0681a148ac5e98b6c` | Defined stable identities, canonical operation ownership, centralized membership/order, network and component scope, fail-closed aggregation, artifact/summary ownership, and profile evolution rules                                |
| Canonical profile selection and execution | Passed | `ea91b06555511cc688cfdc41cca5e7c65d8eb33e` | Implemented one profile executor and selection surface; 47 focused tests covered every profile, unknown inputs, deterministic membership/order, global gates, network policy, unavailable tooling, and status precedence             |
| Structured certification artifact         | Passed | `0d03fc099e2bcb221701f1e0e266a728d7f72839` | Added schema 1.0.0, deterministic fingerprints, exact result/exit fidelity, positive and invalid fixtures, atomic writing, and artifact-derived summaries; 56 profile/artifact tests passed                                          |
| Documentation and example integrity       | Passed | `a60bbd2bcd440b7ad059b06e5b8f0bec69eadba4` | Added non-mutating structured documentation validation for 118 Markdown files and seven parser examples; controlled broken-link/reference/example/aggregate negatives passed; local became 22 passing operations                     |
| CI profile routing                        | Passed | `f9aba576568b70ecbeb73da4d37b6722b2469fdb` | Routed event classes and release preflight through canonical profiles, retained structured artifacts with an immutable action, preserved least privilege, and enforced no CI substitution with architecture and controlled negatives |
| Profile certification and hardgates       | Passed | `731af34a7a5b394a24d9e7e0fefda4ecc7c4ecee` | Eight explicit properties and all 267 tooling tests passed; clean committed-state repository, TypeScript, kernel, Rust-binding, profile, alias, artifact-fidelity, patch-integrity, and input-immutability checks completed          |
| Completion and phase readiness            | Passed | Recorded by the readiness commit           | Architecture, artifact contract, workflow mapping, exact clean-state results, carry-forward, unchanged product behavior, and the Notion source-of-truth handoff recorded                                                             |

### Profile architecture

All profiles are version 1.1.0 ordered policies over
`policy.operation_registry`; operations contain no reverse profile-membership
metadata. Repository operations execute once regardless of component selection,
while target-bearing operations preserve declared target order and may be
narrowed only where the profile permits. `check` resolves to `pull-request` and
`certify` resolves to `full` through the same executor.

The profiles share dependency-integrity, content/workflow security, frozen
baseline, canonical/core/public contracts, generated-state, documentation,
governance, formatting, hygiene, lint, and typecheck operations at their
declared target breadth.

-   `local` is offline and selects 13 ordered memberships expanding to 22
    operations. It keeps formatting, hygiene, lint, and typecheck to the fast
    repository/LSP/kernel/Python/TypeScript baseline.
-   `pull-request` is offline and selects 14 memberships expanding to 43
    operations. It broadens deterministic format/lint/typecheck coverage and
    runs kernel and TypeScript tests for merge confidence.
-   `full` permits network operations and selects 16 memberships expanding to
    75 operations. It adds dependency risk and broad configured builds/tests.
-   `release` is a distinct stable pre-release identity, also network-permitted,
    and currently selects the same 16 memberships/75 operations as full. This
    does not claim release readiness; later packaging, engine matrices,
    adapters, provenance, signing, and clean-room gates may ratchet into this
    identity without changing executor or artifact semantics.

Aggregate precedence is `FAILED`, `INCOMPLETE`, `UNAVAILABLE`, `WAIVED`, then
`PASSED`. Deliberate `NOT_APPLICABLE`, `NOT_YET_CONFIGURED`, and
`NOT_YET_ENFORCEABLE` capability evidence is retained rather than renamed.
Failed, incomplete, and required unavailable evidence produces a nonzero exit;
waived evidence never becomes passed.

### Certification artifact and summary

Artifact kind `strling.profile-certification` uses schema version 1.0.0. Its
deterministic evidence contains repository commit and dirty state, profile
identity/version/purpose/network policy/fingerprint, requested and resolved
component scope, the exact ordered operation-result projection, operation and
result IDs, commands and environment/tool evidence, status/reason/findings,
waiver references, aggregate counts/status/exit, and a deterministic evidence
fingerprint. Execution-instance timestamp and machine-local metadata are kept
separate and do not define semantic identity.

Schema validation rejects malformed fixtures, duplicate results, aggregate
disagreement, and fingerprint tampering. The human summary consumes only the
validated artifact model and reports profile/repository state, aggregate and
counts, passed/failed/waived/unavailable/incomplete evidence, and the applicable
next action. There is no stdout-scanning or second summary authority.

### CI mapping

-   Manual CI dispatch selects the requested profile and defaults to `local`.
-   Pull requests and branch pushes select `pull-request`.
-   The weekly scheduled certification selects `full`.
-   Version tags and the delivery workflow's release preflight select `release`.

Profile jobs invoke `./strling profile ... --artifact`; supplemental binding
jobs use canonical leaf commands and are not certification substitutes. Artifact
upload runs even after a failed profile, is pinned immutably, has warning-only
missing-file behavior, and cannot change the profile exit. Delivery depends on
successful release certification; no publication behavior was added.

### Clean committed-state certification

From committed checkpoint `731af34a7a5b394a24d9e7e0fefda4ecc7c4ecee`:

| Execution      | Aggregate     | Passed | Unavailable | Other governed states | Exit |
| -------------- | ------------- | -----: | ----------: | --------------------: | ---: |
| `local`        | `PASSED`      |     22 |           0 |                     0 |    0 |
| `pull-request` | `UNAVAILABLE` |     41 |           2 |                     0 |    1 |
| `full`         | `UNAVAILABLE` |     68 |           7 |                     0 |    1 |
| `release`      | `UNAVAILABLE` |     68 |           7 |                     0 |    1 |

`check` reproduced the pull-request identity, counts, and exit; `certify`
reproduced full. Every JSON stdout document was semantically identical to its
retained artifact, repository state was clean in every artifact, `git diff
--check` passed, and certification left the tree clean.

The two pull-request limitations are the repository-managed Bundler mismatch
for Ruby lint and missing Swift for typecheck. Full/release additionally retain
Ruby build/test, Swift build/test, and dependency risk as unavailable. Nested
dependency risk contains nine `PASSED`, four `WAIVED`, and 32 `UNAVAILABLE`
checks, with both exact waiver references retained.

All 267 tooling tests passed, including eight explicit certification properties
and controlled schema/profile/documentation/CI/security negatives. TypeScript
typecheck/build and 19 suites with 963 tests passed. Kernel rustfmt,
warnings-denied Clippy, typecheck/build, and 194 tests passed. Rust binding
typecheck/build and 638 tests passed. Repository formatting, hygiene, static
analysis, generation, public snapshots, governance, architecture, documentation,
local security hardgates, and patch integrity passed.

### Carry-forward, unchanged behavior, and readiness

`WVR-SEC-NPM-TOOLING-001` and `WVR-SEC-VSCE-LICENSE-001` remain exact and
expire 2026-09-10. Unavailable ecosystem scanners, the local Bundler mismatch,
missing Swift, transitional Node 18, deferred npm executable governance,
external-link/anchor validation, packaging, real-engine matrices, adapters,
SBOM/provenance/attestation, signing, clean-room release checks, and publication
remain explicit later work. None was broadened or reported as passed.

No existing STRling runtime/compiler behavior intentionally changed. Language
semantics, Semantic IR, parser behavior, portability, target lowering/emission,
runtime behavior, bindings/adapters, public package APIs, package versions, and
publication remain unchanged. No product dependency was installed or upgraded.

The result is `READY WITH RECORDED CARRY-FORWARD`. The next incomplete task in
the Notion source of truth is
[P04-T04 — Define safety, diagnostics, standard-library, and validation guarantees](https://app.notion.com/p/3b97d940647581c6a592fa3ae8dec08f),
currently `Partial`; its recorded remaining work is full ratification of
standard-library validation guarantees without claiming stronger validation or
safety than STRling can prove.

## Validation guarantee and standard-library claim contracts

-   Status: Complete
-   Starting branch: `architecture/v4`
-   Starting commit: `f3803225581099c24308ae0d1478bb839769c290`
-   Behavior change: Normative specification and canonical contract validation only; no existing STRling runtime/compiler behavior intentionally changed
-   Completion record:
    [`validation-guarantee-contracts.yaml`](records/validation-guarantee-contracts.yaml)
-   Readiness: `READY WITH RECORDED CARRY-FORWARD`

### Checkpoint evidence

| Checkpoint                          | Result | Commit                                     | Verification                                                                                                                                                                                                                                                   |
| ----------------------------------- | ------ | ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Existing guarantee claim audit      | Passed | `e8b0e234bc9524df05439392e12b3fb641a30dbf` | Classified precise, descriptive, ambiguous, overstrong, implementation-specific, and historical claims; documented ambiguity patterns, controlling safety/diagnostic/portability/rewrite contracts, scope lock, later audit ownership, and explicit non-goals  |
| Validation guarantee taxonomy       | Passed | `a67658b9bd31e7421671389542309fd3c4180ec6` | Ratified three finite guarantee levels, evidence and runtime-stage rules, permissible and prohibited claims, conservative unknown/unsupported behavior, independent target availability, standards scope, and versioning                                       |
| Standard-library claim contract     | Passed | `ac939201ca5a0b2dcc973dbf4512889496556e0a` | Added schema 1.0.0, three positive examples, and seven isolated invalid mutations covering missing levels, unsupported strict claims, undefined standards scope, contradictory completeness, embedded portability, safety claims, and malformed evidence       |
| Compiler guarantee reconciliation   | Passed | `95c675e9ee11078b9803cb9ab57f7b06071ffac0` | Kept helper-definition, helper-argument, value-rejection, compiler-semantic, safety, and portability identities separate; preserved certified safety, uncertainty, target, portability, and rewrite-proof ownership                                            |
| Contract fixtures and documentation | Passed | `2900178593c124f03c5e96ad9c9fc6e77541dc95` | Added the exact five-helper transition inventory, focused honesty/scope/evidence/independence/determinism/soundness tests, canonical contract integration, and qualified stdlib prose without changing helper behavior                                         |
| Canonical hardgate certification    | Passed | `f9a990b5f6fdc5932bf52b13deacd834f83c35f6` | Proved the standard-library contract suite runs only through the canonical contract operation in all four profiles; completed clean-state repository, contract, security, TypeScript, kernel, Rust-binding, artifact-fidelity, and controlled-invalid evidence |
| Completion and readiness            | Passed | Recorded by the readiness commit           | Recorded exact taxonomy, metadata and standards rules, guarantee boundaries, mechanical evidence, profile results, carry-forward inventory, unchanged behavior, and the next incomplete Notion task                                                            |

### Guarantee taxonomy

The normative validation-guarantee vocabulary is version `1.0.0` and contains
exactly three levels:

-   `lexical_shape` proves only that the whole textual input satisfies its
    declared character, token, delimiter, width, branch, encoding, and
    anchoring conditions. It does not inherently prove ranges, calendar
    validity, cross-field relationships, normalization, domain semantics, or
    external-standard completeness.
-   `normalized_structure` proves deterministic decomposition into a declared
    component model plus every listed structural constraint and canonicalization
    rule. It may prove explicit ranges or relationships, but it does not imply
    unlisted environmental, business, or domain semantics.
-   `semantic` proves every and only the semantic conditions enumerated in its
    versioned definition. Every condition requires an executable deterministic
    stage and condition-to-evidence correspondence. `strict` is allowed only as
    the `strict_semantic` documentation class for a claim-eligible semantic
    definition and adds no conditions by itself.

A regex is sufficient only when it proves every declared condition under the
exact execution semantics. Parsing, arithmetic, lookup, normalization, or
cross-field conditions require another deterministic stage when regex execution
cannot prove them. A required indeterminate stage or missing proof yields
`unknown` or `unsupported`; it never becomes acceptance, rejection, or an
implicit weaker guarantee.

No level implies deliverability, existence, authorization, business validity,
universal correctness, external-standard conformance, ReDoS safety, complexity,
security, target support, portability, or rewrite equivalence.

### Standard-library claim contract

A governed definition requires structured `kind`, `contract_version`, `status`,
`helper_id`, `guarantee_id`, `guarantee_version`, `guarantee_level`,
`accepted_domain`, `validation_definition`, `validator_pipeline`, `standards`,
`excluded_cases`, `checks`, `target_support`, `safety`, `rewrite_equivalence`,
`evidence`, `documentation_claim`, and `known_limitations` fields. Cross-field
validation enforces unique identities, exact condition/check/category coverage,
resolved stage/check/evidence references, one evidence binding per performed
check, semantic evidence for semantic checks, standards evidence where required,
and existing repository-relative evidence targets.

External-standard scope is independent of validation level and is exactly one
of `none`, `inspired`, `subset`, `profile`, or `complete`. `inspired` claims no
conformance. `subset` records included and excluded provisions and cannot be
described as complete. `profile` names its identity, edition, and deviations.
`complete` requires all applicable requirements of the identified edition and
conformance target plus complete evidence, and cannot coexist with subset
exclusions. A citation without structured scope authorizes no conformance claim.

Guarantee definitions are independently versioned. Strengthening a helper from
shape to structure or semantics, or changing a condition, stage, standard scope,
exclusion, or omitted check, is an explicit guarantee-contract change rather
than a silent behavior-strengthening claim.

### Safety, diagnostic, portability, and rewrite boundaries

Validation metadata fixes safety and rewrite-equivalence claims to
`not_claimed`. It cannot prove universal ReDoS immunity, bounded complexity,
exploitability, engine-independent security, or safety by stdlib provenance.
Canonical safety findings and uncertainty remain authoritative and neither
suppress nor are suppressed by a value-validation result.

Invalid helper metadata, an invalid invocation argument, a runtime input rejected
by a validator, a compiler semantic error, a safety warning, and a portability
failure are distinct events with distinct owners and identities. Input rejection
is ordinarily a helper/runtime result, not a compiler diagnostic. English words
such as “invalid,” “safe,” and “portable” never merge their structured evidence.

Validation success does not imply target support. Every required validator stage
must be separately supported for the exact target profile; unsupported stages
make that exact guarantee unavailable rather than silently weakening it. Only
the closed rewrite registry and certified portability-planning proof obligations
may produce `equivalent_rewrite`, and a guarantee survives only when the existing
proof covers every affected stage and condition.

### Mechanical evidence and clean-state certification

The contract directory contains the helper-guarantee schema, controlled-invalid
schema, transition-inventory schema, three positive level examples, seven
single-rule negative definitions, and the exact five-helper transition inventory.
The canonical contract operation reports 11 schemas, 30 positive fixtures, 33
negative fixtures, nine documents, three standard-library schemas, four
standard-library positive documents, and seven standard-library negatives.
Twelve focused standard-library tests prove guarantee honesty, standards scope,
strict evidence, safety and portability independence, determinism, schema
soundness, explicit historical classification, sole-runner ownership, and profile
membership.

From clean committed checkpoint
`f9a990b5f6fdc5932bf52b13deacd834f83c35f6`:

| Execution      | Aggregate     | Passed | Unavailable | Failed/incomplete/waived | Exit |
| -------------- | ------------- | -----: | ----------: | -----------------------: | ---: |
| `local`        | `UNAVAILABLE` |     16 |           6 |                        0 |    1 |
| `pull-request` | `UNAVAILABLE` |     36 |           7 |                        0 |    1 |
| `full`         | `UNAVAILABLE` |     65 |          10 |                        0 |    1 |

All three artifacts recorded that exact commit with `dirty: false`; their stdout
and retained artifacts were semantically identical, and the canonical contract
operation passed in each. The six shared unavailable operations are the current
installed Ruff `0.16.2` versus repository-required `0.15.21` mismatch across
repository/LSP/Python formatting and linting. Pull-request additionally retains
Ruby lint as unavailable. Full additionally retains Ruby build/test and
dependency risk. Nested dependency risk recorded nine passed, four waived, and
32 unavailable checks, retaining exact waivers `WVR-SEC-NPM-TOOLING-001` and
`WVR-SEC-VSCE-LICENSE-001`. No aggregate was weakened to force PASS.

All 279 tooling tests passed. TypeScript typecheck/build and all 19 suites with
963 tests passed. Kernel rustfmt, warnings-denied Clippy, typecheck/build, and all
194 tests passed. Rust-binding typecheck/build and all 638 tests passed.
Formatting, hygiene, documentation/examples, generation integrity, canonical,
core, and public contracts, governance, architecture fitness, frozen baseline,
security integrity/content, controlled invalid fixtures, and patch integrity
passed.

### Carry-forward, unchanged behavior, and readiness

The current `dateTime`, `email`, `ip`, `url`, and `uuid` helpers remain
`transitional_unclassified`, `not_ratified`, and entitled to
`no_validation_guarantee`. Later work must audit each Essential 5/stdlib helper,
correct real semantic false positives, implement a canonical registry if still
needed, expose generated binding/frontend metadata, and certify cross-target
stdlib conformance. None is silently grandfathered by historical behavior.

Current Ruff and Ruby limitations, unavailable dependency scanners, the two exact
security waivers, transitional Node 18, and deferred npm executable governance
remain owned carry-forward. They were not broadened, hidden, or reported as
passing.

No existing STRling runtime/compiler behavior intentionally changed. Pattern
matching semantics, the compiler pipeline, Semantic IR, safety detection,
portability planning, rewrites, target emission, parser behavior, bindings,
public package APIs, package versions, and publication remain unchanged. Existing
helper regexes, ASTs, fixtures, runtime execution, and exposed APIs are also
unchanged.

The result is `READY WITH RECORDED CARRY-FORWARD`. The next incomplete task in
the Notion source of truth is
[P06-T05 — Expose the pure CompileRequest to CompileResult kernel boundary](https://app.notion.com/p/3b97d94064758100a198f3d195459a6b),
currently `Partial`; the remaining work is a stable embeddable boundary,
deterministic fingerprints where needed, resource-limit hooks, and property/fuzz
smoke tests.

## Embeddable canonical compiler-kernel boundary

-   Status: Complete
-   Starting branch: `architecture/v4`
-   Starting commit: `2012dc2cedf24eae891ca126b83a829d1188c368`
-   Behavior change: Additive non-published kernel API and hardgates only; no
    existing STRling runtime/compiler behavior intentionally changed
-   Completion record:
    [`compiler-kernel-boundary.yaml`](records/compiler-kernel-boundary.yaml)
-   Readiness: `READY WITH RECORDED CARRY-FORWARD`

### Checkpoint evidence

| Checkpoint                                    | Result | Commit                                     | Verification                                                                                                                                                                                                                                                                                           |
| --------------------------------------------- | ------ | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Boundary contract lock                        | Passed | `9337c838a34553aa476458aec0d4eaec0c615174` | Locked contract `1.0.0`, exact target-profile evidence, executable/deferred modes, malformed/typed/result failure ownership, resource ceilings, purity exclusions, and unchanged product paths without changing the compiler protocol                                                                  |
| Public kernel facade                          | Passed | `a18494e3d6799bad12a1466c52f1cc97e4c95448` | Exposed borrowed `compile(&CompileRequest, Option<&TargetProfile>)` with strict validation, typed failures, explicit unsupported outcomes, source-less support, repeat equality, immutability, and 13 focused tests                                                                                    |
| Canonical orchestration and result projection | Passed | `0de6a7cb2d0bbe28a48fce2403545d268417b6e1` | Routed the facade through the single certified target-neutral path and optional exact-profile suffix; preserved stage correspondence and projected only requested SemanticResult, AnalysisResult, and PortabilityPlan evidence through five end-to-end and five mutation tests                         |
| Deterministic identity and resource bounds    | Passed | `aae7ed8990e392732d5f03635ce1468f62f16999` | Preserved canonical program/profile identity; bounded bytes, depth, nodes, relationships, comparisons, findings, diagnostics, requirements, decisions, and rewrite dependencies; nine exact/one-over tests proved whole-result deterministic exhaustion                                                |
| Property and fuzz-smoke certification         | Passed | `8b8d8202aae818de877aefd145bf22cc261f7e77` | Fixed seeds generated 256 valid, 64 profile, 256 malformed typed, 32 exhaustion, and 512 serialized mutation cases; determinism, purity, immutability, validation, profile sensitivity, source independence, resource containment, and panic resistance passed with zero unexplained failures          |
| Integration and hardgate certification        | Passed | `aaeb08eb0438cfc36d8853cd7f3b42ad8a912fbc` | Added core tests to the local canonical profile, locked the non-published facade snapshot, certified host/frontend/emitter/binding independence, and passed public-contract, generation, governance, documentation, security, architecture, TypeScript, Rust-binding, and clean-state kernel hardgates |
| Completion and readiness                      | Passed | Recorded by the readiness commit           | Recorded the stable API, exact stage flow, deterministic/resource evidence, certification totals, exclusions, truthful profile availability, carry-forward, unchanged behavior, and next ordered Notion task                                                                                           |

### API, orchestration, and deterministic evidence

The non-published `strling-kernel` crate exposes one crate-root facade:

```rust
pub fn compile(
    request: &CompileRequest,
    target_profile: Option<&TargetProfile>,
) -> Result<CompileResult, KernelCompileError>
```

It executes canonical semantic, analysis, source-less, and exact-profile
portability requests. Source input, unsupported specification revisions, and
target-artifact output return explicit structured failed results. Malformed
serialized contracts remain `ContractError`; invalid typed requests, missing or
mismatched profiles, stage correspondence failures, and invalid projections are
typed `KernelCompileError` values.

The sole path is validation, normalization, semantic facts, structural facts,
safety, diagnostics, optional target requirements/capability evaluation/
portability planning, then result and exchange validation. Target-neutral work
does not require target authority. Program, fact-store, profile, capability, and
plan correspondence remains stage-owned. Public projection never exposes facts,
lowered IR, regex syntax, capture numbering, emitter options, or target artifacts.

Identity derives only from canonical contract/specification/compiler identity,
normalized Semantic IR, exact profile evidence, and deterministic canonical
ordering/fingerprinting. The facade reads no files, environment, network, clock,
engine/package state, path, address, or mutable global.

Enforced ceilings are 8,388,608 request bytes; 1,048,576 profile bytes; depth
128; 65,536 semantic nodes; 256 leading terms; and 4,096 each for relationships,
overlap comparisons, findings, uncertainties, diagnostics, capability
requirements, portability decisions, and rewrite dependencies. Caller node and
diagnostic limits are honored without raising hard ceilings. Exhaustion returns
one deterministic `STRL-PROTOCOL-0003` failed result without truncation, partial
success, retry, or panic.

### Certification, exclusions, and readiness

All 213 kernel tests passed with rustfmt, warnings-denied Clippy, typecheck, and
build. Contract mapping certified 11 schemas and 63 fixtures. The boundary
corpora used four valid seeds (`0x4b45524e454c0001`, `0x9e3779b97f4a7c15`,
`0xd1b54a32d192ed03`, `0x94d049bb133111eb`), profile seed
`0x50524f46494c4501`, malformed seed `0x4d414c464f524d01`, resource seed
`0x5245534f55524301`, and fuzz seeds `0x46555a5a00000001` through
`0x46555a5a00000004`. They produced 256 valid, 64 profile, 704 total malformed,
32 exhaustion, and zero unexplained cases. Five controlled architecture mutation
tests and a 22-marker facade/global-state denylist passed.

From clean committed checkpoint `aaeb08eb0438cfc36d8853cd7f3b42ad8a912fbc`:

| Execution      | Aggregate     | Passed | Unavailable | Failed | Exit |
| -------------- | ------------- | -----: | ----------: | -----: | ---: |
| `local`        | `UNAVAILABLE` |     17 |           6 |      0 |    1 |
| `pull-request` | `UNAVAILABLE` |     36 |           7 |      0 |    1 |
| `full`         | `UNAVAILABLE` |     65 |          10 |      0 |    1 |

The six shared gaps are installed Ruff `0.16.2` versus governed `0.15.21`.
Pull-request additionally retains Ruby lint because Bundler differs from the
repository-managed version. Full additionally retains Ruby build/test and
dependency-risk availability. No profile/security rule was weakened. Every
available operation passed, including `test@core` in all three profiles,
TypeScript typecheck/build and 19 suites/963 tests, and Rust-binding
typecheck/build and 638 tests.

This task did not implement the legacy regex parser, Semantic DSL, Simply,
target lowering, regex emission, `TargetArtifact` production, runtime regex
execution, bindings/adapters, CLI/LSP migration, package-version changes, or
publication.

No existing STRling runtime/compiler behavior intentionally changed. Legacy
product paths still do not invoke the new facade.

The result is `READY WITH RECORDED CARRY-FORWARD`. Carry-forward is limited to
the recorded certification-environment availability gaps and separately
governed later campaign phases; no stable kernel-boundary work is deferred. The
next ordered incomplete task in the Notion source of truth is
[P07-T01 — Build a controlled legacy TypeScript reference runner](https://app.notion.com/p/3b97d940647581da94ffe41b544e6489?pvs=204),
currently `Not Started`. Its objective is to isolate TypeScript parser/compiler/
emitter/API history behind deterministic, independently versioned evidence
without granting it normative authority.
