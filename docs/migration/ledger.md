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

## Controlled legacy TypeScript reference runner

-   Status: Complete
-   Starting branch: `architecture/v4`
-   Starting commit: `1619772f2aabe75182a26c9636ea5e219a7f948f`
-   Behavior change: Additive migration tooling and architecture hardgates only;
    no existing STRling runtime/compiler behavior intentionally changed
-   Completion record:
    [`legacy-reference-runner.yaml`](records/legacy-reference-runner.yaml)
-   Readiness: `READY WITH RECORDED CARRY-FORWARD`

### Checkpoint evidence

| Checkpoint                                      | Result | Commit                                     | Verification                                                                                                                                                                                                                                                                 |
| ----------------------------------------------- | ------ | ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Reference contract and legacy surface inventory | Passed | `4d69585f357157af6464787f20c3986472e3765f` | Inventoried the actual parser, compiler, PCRE2 emitter, diagnostics, directives/preprocessing, target/options, package-root, and Simply surfaces; locked the historical-evidence-only contract, stable projection rules, and source-derived identity model                   |
| Deterministic runner protocol and serialization | Passed | `210008566c90533556c30dd8722c7b6b59681ab3` | Established protocol/observation schema 1.0.0, exact surface validation, recursive canonical JSON, independent request/implementation identities, and structured stack-free failure evidence with nine focused tests                                                         |
| Parser and public API observation               | Passed | `cfdc09a9ff8e48fa0bc7d951bb5d4d670ffd0b2e` | Captured parser, package-root, and Simply projections for grammar/directive/malformed/API cases without changing source inputs or legacy behavior; 22 focused tests and the complete 19-suite/963-test TypeScript baseline passed                                            |
| Compiler and emitter observation                | Passed | `755be2f62f2a2d3c8496ebef9edd1f7c625b560c` | Added distinct compile, metadata, exact PCRE2 emission, diagnostic, option, target, depth, lookbehind, and stage-attributed failure observations; 32 focused tests passed                                                                                                    |
| Determinism and reference corpus certification  | Passed | `06039a9c5ac3dacfcb82bd4d2de23519703472bc` | Certified 24 stable cases over all 11 operations, three complete runs, 72 canonical comparisons, two malformed cases, fixture/source immutability, implementation sensitivity, independent versioning, and zero mismatches or unexplained failures                           |
| Tooling integration and architecture hardgates  | Passed | `3ed93f8325d7cddc9f310b5c141fd6b4893729fe` | Added one offline operation to every canonical profile and the root CLI; five mutation/live architecture tests, 11 governance-contract tests, profile routing, Node 22 typecheck, contracts, baseline, documentation, security, formatting, lint, and patch integrity passed |
| Reference runner readiness                      | Passed | Recorded by the readiness commit           | Recorded exact operations, protocol, fingerprints, corpus evidence, architecture boundary, unchanged product behavior, truthful platform availability, carry-forward, and the next ordered Notion task                                                                       |

### Runner architecture and observation protocol

The migration-only Python launcher builds the governed TypeScript implementation
in an isolated temporary directory and invokes the Node protocol worker. It
supports single request, complete corpus, certification, and focused-check
modes, plus the root `./strling legacy-reference` route. No core crate,
published binding, package entrypoint, or Rust planning stage depends on it.

The 11 exact operations are parser `parse` and `parseToArtifact`; compiler
`compile` and `compileWithMetadata`; PCRE2 `emit` and
`emitWithDiagnostics`; package-root `parse` and `parseToArtifact`; and
Simply `Pattern.toString`, `compileNode`, and `toRegExp`. Parser, compiler,
emitter, and API evidence remain independently addressable.

Protocol and observation schema version 1.0.0 require the operation-owned input
and options plus the exact expected legacy surface. Observations include
implementation and request identities, operation/surface, and exactly one
success or structured legacy-failure outcome. Malformed protocol or runner
failure exits nonzero; faithfully captured legacy exceptions are valid
observations. Canonical JSON sorts object keys recursively, preserves arrays and
meaningful text exactly, writes UTF-8 with one trailing LF, and excludes only
process-local paths, clocks, durations, IDs, temporary locations, and stacks.

Implementation identity hashes every tracked TypeScript source, package manifest
and lock file, tsconfig, and the actual Node runtime version. Node 22.23.2
produced
`sha256:520b1a43a8c8aac5c8a4c455017b6dfa6c0112baf8b18cb68606dc5d7ccebb22`;
the corpus produced
`sha256:744a4d0e029fbb2890e98e25d20402044f5b551a7642255a57c80f5dec48d30a`.

### Corpus, certification, and authority boundary

The source-authored corpus has 24 cases: 17 success and seven captured
legacy-failure observations, including two malformed requests. It covers
literal, escape, class, group, capture, alternation, repetition, lookaround,
directive/preprocessing, option/target, compiler metadata, exact emission,
warnings/failures, package-root, and Simply families. Three runs compared 72
canonical observations with zero mismatches or unexplained failures; corpus and
governed implementation inputs remained unchanged. Observations remain
ephemeral because generated-artifact governance has no legacy-oracle authority
class.

The enforced authority rule rejects product or normative consumption, normative
generation from legacy evidence, runner dependency on core/specification
authority, and target-artifact, portability, target-profile, or capability
authority inside the runner.

**Legacy TypeScript observations are historical evidence only and are
non-normative.**

From committed checkpoint
`3ed93f8325d7cddc9f310b5c141fd6b4893729fe`, every available runner,
architecture, governance-contract, profile-routing, TypeScript typecheck,
canonical/core contract, baseline, documentation, security, formatting, lint,
syntax, and patch check passed. Local, pull-request, and full attempts were
`UNAVAILABLE` before dispatch because WSL returned
`Wsl/Service/0x80072747`; the same host failure prevented final native Rust,
generated/public-contract, governance-wrapper, and complete Jest reruns. The
last complete TypeScript run remains 19 suites and 963 tests. No gate was
weakened or reported as passing.

No existing STRling runtime/compiler behavior intentionally changed. Legacy
parser/compiler/emitter behavior, diagnostics, directives, preprocessing,
targets/options, package-root/Simply APIs, Rust-kernel semantics, Semantic IR,
safety, portability, target authority, public APIs, package versions, generated
product artifacts, and publication remain unchanged.

The result is `READY WITH RECORDED CARRY-FORWARD`. Carry-forward is limited to
the recorded host availability gap and later complementary runners, canonical
comparison normalization/discrepancy taxonomy, and complete migration-corpus
execution. The next ordered incomplete Notion task is
[P07-T02 - Build complementary legacy/reference runners](https://app.notion.com/p/3b97d9406475815eba6ed6bb8f41f146?pvs=204),
currently `Not Started`.

## Complementary historical reference runners

-   Status: Complete
-   Starting branch: `architecture/v4`
-   Starting commit: `c3cc4b41262b79c891259db80e917f24634fa936`
-   Behavior change: Additive migration-only Python/multi-runner evidence,
    command routing, and authority hardgates; no existing STRling
    runtime/compiler behavior intentionally changed
-   Completion record:
    [`complementary-reference-runners.yaml`](records/complementary-reference-runners.yaml)
-   Readiness: `READY WITH RECORDED CARRY-FORWARD`

### Checkpoint evidence

| Checkpoint                                  | Result | Commit                                     | Verification                                                                                                                                                                                                       |
| ------------------------------------------- | ------ | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Complementary strategy and inventory        | Passed | `52c7fd8c576c2aa6c3c8d5762b5bb6770e107034` | Classified every binding/reference candidate, selected independent TypeScript and Python implementations, rejected redundant paths, and fixed the non-normative selection criteria                                 |
| Shared multi-runner evidence contract       | Passed | `35aa309a9213995f2926c5fe67fe87b2d6c61f26` | Preserved request protocol 1.0.0 while adding validated `typescript@1.0.0` and `python@1.0.0` provenance to observation/certification schema 1.1.0, runner-owned operation maps, and explicit unsupported outcomes |
| Python historical evidence                  | Passed | `a7ebc4155c072e648d484e43e4513dff48d5d5fc` | Directly observed seven implemented Python parser/compiler/emitter/Simply operations plus four not-exposed operations; 15 focused and 789 historical package tests passed                                          |
| Complementary path selection                | Passed | `21326cd616a66e9ea0ce953809ce4c0fb17c101b` | Certified that no third runner currently contributes proportionate distinct historical evidence; retained later runtime-engine testing ownership                                                                   |
| Cross-runner corpus certification           | Passed | `028d004bb26fc597660c2b49b502fc16456bb65a` | Certified 44 runner cases, 12 shared identities, 20 runner-specific identities, six runs, 132 canonical comparisons, four malformed cases, and zero repeat mismatches or unexplained failures                      |
| Tooling integration and authority hardgates | Passed | `9ac8ccfdf137e61c2e279b37542329a5ca85913d` | Unified root/launcher orchestration; 43 TypeScript runner tests, 28 Python/cross/launcher tests, six controlled architecture tests, language baselines, contracts, docs, and security passed                       |
| Complementary reference readiness           | Passed | Recorded by the readiness commit           | Recorded selected/rejected paths, exact identities and corpus counts, authority, unchanged behavior, truthful platform availability, carry-forward, and P07-T03 handoff                                            |

### Architecture, protocol, and corpus

The TypeScript peer observes 11 parser, compiler, emitter, package-root, and
Simply operations on Node 24.4.1. The Python peer observes seven implemented
parser, artifact, compiler, metadata, emitter/diagnostic, and Simply operations
and four explicitly not-exposed conceptual operations on Python 3.13.5. Each
retains its own runner and implementation identity; neither reads the other's
outputs or expected results. Shared orchestration compares stable case identity
and within-runner repeatability only.

Request protocol 1.0.0 and corpus version 1.0.0 remain compatible. Observation,
batch, and certification schema 1.1.0 carry explicit runner provenance. Canonical
JSON, request identity, structured stack-free legacy failures, explicit
unsupported outcomes, corpus identity, and independent implementation
fingerprints are deterministic.

The TypeScript implementation and corpus fingerprints are
`sha256:43cd3efde7b6afd11b1230ea26355f65255b5a79e7c0fcd7f54f6da2632b83a4`
and
`sha256:744a4d0e029fbb2890e98e25d20402044f5b551a7642255a57c80f5dec48d30a`.
The Python values are
`sha256:0748ef7994a2bf143cb71efc149f0e8929905533d05b4fa1c2365f596ba88bc5`
and
`sha256:f3114a423da9928ab12ff7afe5c2ce0eba97c2f57c3599cdc98b2105a5ef914d`.
The combined manifest fingerprint is
`sha256:844f9abee4870ac74fe986a7aa623ea0033d5b69bedaa89026c1970a8beeedb6`.

**Historical reference observations are non-normative evidence. Agreement among
historical implementations does not override the normative specification or
canonical Rust semantics.**

No existing STRling runtime/compiler behavior intentionally changed.
TypeScript, Python, and other binding semantics; the canonical Rust kernel;
Semantic IR; diagnostics; safety; portability; targets; package APIs; versions;
and publication remain unchanged.

All available committed-state runner, architecture, TypeScript, Python,
contract, documentation, security, formatting, lint, typecheck, build, syntax,
and patch checks passed. WSL continued to fail before dispatch with
`Wsl/Service/0x80072747`, so native Rust, POSIX governance/generation, and the
canonical local, pull-request, and full profiles remain recorded rather than
weakened.

The result is `READY WITH RECORDED CARRY-FORWARD`. The next ordered incomplete
Notion task is P07-T03, the separately versioned canonical observation
comparison and discrepancy taxonomy. It owns demonstrably irrelevant
representation normalization, discrepancy classification, migration
dispositions, and later full migration-corpus gating.

## Canonical observation comparison and discrepancy taxonomy

-   Status: Complete
-   Starting branch: `architecture/v4`
-   Starting commit: `52d1649003fb29ceab6cb277c0f99d0ad31e2c75`
-   Behavior change: Additive migration-only comparison, classification,
    certification, command routing, and authority hardgates; no existing STRling
    runtime/compiler behavior intentionally changed
-   Completion record:
    [`canonical-observation-comparison.yaml`](records/canonical-observation-comparison.yaml)
-   Readiness: `READY WITH RECORDED CARRY-FORWARD`

### Checkpoint evidence

| Checkpoint                                   | Result | Commit                                     | Verification                                                                                                                                                                                                                                                                                                                  |
| -------------------------------------------- | ------ | ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Comparison contract and taxonomy lock        | Passed | `4299157a0de0ae3728ea59005f543dcf7ffab2a9` | Locked separate comparison, projection, normalization, comparator, and taxonomy versions; factual comparability/relationship states; four substantive governed dispositions; machine-readable rationale; peer non-applicability; and explicit comparison exclusions                                                           |
| Canonical observation projection             | Passed | `688341c4501ff22998fb73da2ab9c9b9c9ece8ec` | Ten tests cover the sole authorized outcome-selection normalization, zero normalization, stable ordering and rule rejection, provenance/fingerprint sensitivity, malformed input, semantic non-loss, unsupported/failure preservation, source matching, and raw immutability                                                  |
| Deterministic pairing and comparison         | Passed | `7a6830d1badb0457639ef413abe44cb4e0f06067` | Twenty-three projection/comparison tests cover stable identity pairing, exact and normalized equality, nested JSON-Pointer differences, every special outcome, missing/incompatible cases, rejection, immutability, stable ordering, and repeated output                                                                      |
| Governed discrepancy classification          | Passed | `beffdf4f3aaa3d5310d42d9d7b77e9fe409f5211` | Thirty-three tests cover peer non-applicability, conservative unresolved defaults, all four dispositions, required replacement/scope/normative authority, exceptional correction justification, replacement-adapter rejection, supersession, identity validation, and comparison immutability                                 |
| Comparison taxonomy certification            | Passed | `e061673ee5c3588464a65b903710bb06f34801b8` | Three fixture runs certify 16 sources, 16 projections, eight comparisons, four comparable/four not-comparable, two equivalent/two differing, all dispositions, four malformed cases, nine mutations, 15 normalizations, zero mismatches, and zero unexplained failures                                                        |
| Differential comparison integration          | Passed | `df0e6d64661de790750058fd11a1179b96d390b8` | Added explicit project/compare/classify/certify modes, live comparison certification in the reference launcher and all canonical profiles, 104 affected tests, authority hardgates, 12 live shared comparisons, language/product checks, contracts, security, governance, docs, affected formatting/lint, and patch integrity |
| Comparison readiness and corpus-gate handoff | Passed | Recorded by the readiness commit           | Records exact identities, normalization proof, pairing/comparability/difference contracts, taxonomy requirements, fixture/live metrics, determinism, hardgates, platform limits, unchanged behavior, six unresolved live divergences, and P07-T04 handoff                                                                     |

### Versioned architecture and normalization

Comparison schema, projection schema, normalization rules, comparator
implementation, and discrepancy taxonomy are each `1.0.0`, independent of
runner protocol `1.0.0` and observation/batch/certification schema `1.1.0`.
The comparator identity is
`tooling.migration-comparison-comparator@1.0.0`, with certified source digest
`sha256:7602cea37c4cc6a58737bc4403e706bca11f67b1412360d20a205e985efecc71`.

The only normalization is `select-semantic-outcome@1.0.0`. It removes the
runner-owned implementation, kind, observation/protocol versions, operation,
request, runner, and surface envelope from the compared value while preserving
every field unchanged in projection provenance. It compares the complete
outcome, including status and all success evidence, legacy failure, or
unsupported reason. Tests demonstrate non-loss, raw immutability, failure and
unsupported preservation, zero-normalization fidelity, idempotence, stable rule
ordering, and fingerprint sensitivity. No array, diagnostic, AST, source
position, capture, warning, error, flag, emitted text, target, or semantic-node
ordering/content is normalized.

Pairing requires the exact cross-corpus case identity, case ID, conceptual
operation, input/options request tuple, projection/normalization versions, rule
IDs, and registered cross-runner surface correspondence. Name similarity is
never pairing authority. Results are structurally `comparable` or
`not_comparable`; relationships are `equivalent_observation`,
`differing_observation`, or `not_comparable`. Not-comparable reasons are
operation not exposed, unsupported operation, incompatible surface, missing
counterpart, or insufficient semantic correspondence.

Differences retain deterministic JSON-Pointer paths, left/right presence and
values, and `value_mismatch`, `type_mismatch`, `left_missing`, or
`right_missing`. Object keys use canonical order; arrays retain source order.

### Governed taxonomy and certification

`preserved_behavior` requires equivalent demonstrated replacement evidence
and a named preservation scope. `intentional_specification_correction`
requires a meaningful difference (or explicit exceptional justification), an
identified corrected rule, and normative specification, canonical contract, or
ratified architecture authority. `unsupported_legacy_behavior` requires
historical evidence, an explicit scope boundary, and supported-scope or stronger
authority. `unresolved_discrepancy` is the conservative state whenever
evidence, correspondence, replacement behavior, or authority is insufficient.
Historical peer evidence alone has disposition applicability
`not_applicable`.

The controlled fixture certifies eight comparisons: four comparable, four
not-comparable, two equivalent, and two differing. It contains one of each
substantive disposition, one peer non-applicable result, four malformed cases,
nine controlled mutations, and 15 normalization applications over 16
projections. Three repeated runs have zero mismatches and zero unexplained
failures.

Live certification retrieves all 44 TypeScript/Python source observations,
selects 24 observations for the 12 stable shared identities, builds 24
projections, and emits 12 comparable comparisons: six equivalent and six
differing. All six differences are retained at
`/outcome/evidence/return_shape`; they are `unresolved_discrepancy` because
historical peers cannot supply replacement or normative authority. Six
equivalent historical comparisons are disposition-not-applicable. Twenty
runner-specific observations remain unpaired. Three runs apply 24
normalizations with zero mismatches and zero unexplained failures.

Across fixture and live streams the machinery certifies 20 comparisons, 16
comparable and four not-comparable results, eight equivalent and eight differing
results, 40 projections, 39 normalization applications, and substantive
disposition counts of preserved 1, correction 1, unsupported 1, and unresolved 7. Fixture examples demonstrate taxonomy completeness; only the six live
unresolved records describe current shared historical divergence.

### Hardgates, verification, and unchanged behavior

Architecture fitness prohibits product/compiler/binding/kernel/target/spec
dependencies on comparison evidence; specification or target capability
authority from historical comparisons or dispositions; source-observation
rewrite operations in comparison tooling; normalization authority outside
tooling; unresolved-as-success mappings; majority or consensus authority; and
migration classifications in public APIs.

TypeScript formatting, direct typecheck/build, and 19 suites/963 tests passed.
Python package build and 789 tests passed. Rust formatting, Clippy, check, build,
and tests passed. Historical runner/cross-runner checks, 104 affected tests,
canonical/core/public contracts, frozen baseline, generated artifacts,
dependency/content security, governance, architecture, documentation,
TypeScript/documentation formatting, affected Python formatting/lint, and patch
integrity passed. Raw reference corpus and runner evidence remained unchanged.

Local, pull-request, and full profiles ran the new comparison operation and no
operation failed. Their aggregate result remains `UNAVAILABLE`: installed Ruff
0.16.2 differs from pinned 0.15.21; pull-request/full also report the existing
Bundler mismatch; full additionally reports dependency-risk scanning
unavailable. No policy was weakened or unavailable check reported as passing.

No existing STRling runtime/compiler behavior intentionally changed. TypeScript,
Python, and other legacy binding semantics; Rust-kernel semantics; Semantic IR;
diagnostics; safety analysis; portability planning; target behavior; package
APIs; package versions; publication state; and full-corpus migration gating
remain unchanged.

The result is `READY WITH RECORDED CARRY-FORWARD`. The next ordered incomplete
Notion task is
[P07-T04 — Run the complete migration corpus and gate unresolved differences](https://app.notion.com/p/3b97d940647581adb18afb462ffec125?pvs=204).
That task owns full-corpus execution and gating; it must retain conservative
uncertainty and may resolve the six live discrepancies only with explicit
governing authority.

## Complete migration differential gate

The repository now has a blocking, offline full-corpus differential command:

```text
./strling migration-differential --repeat-runs 3
```

The command executes all 20 Python and 24 TypeScript source observations,
validates three byte-stable runs, preserves every raw observation identity, and
emits one canonical artifact. The complete corpus fingerprint is
`sha256:04270620441db4715cc40f6c82cea832d1c8d7c85631d96638a427d9f4a968e6`;
the checked baseline fingerprint is
`sha256:cb763a33bf620c467b1633b7747096da31757f41736368ced0bc859e42464366`.

Eleven versioned canonical route reviews exactly cover every corpus operation.
The current compiler boundary makes 36 observations not comparable because the
operation is not exposed and eight legacy source-text compiler observations not
comparable because the kernel accepts structured source contracts. No canonical
replacement comparison is fabricated, no production divergence is approved,
and no product behavior changes.

The 12 exact historical peer comparisons remain visible: six equivalent and
six differing only at `/outcome/evidence/return_shape`. The six differences
retain `unresolved_discrepancy` evidence identities; they are not called
equivalent or accepted. They do not constitute historical-to-replacement
comparisons. Any future comparable canonical route without execution evidence,
or any unresolved replacement classification, fails the gate.

The checked baseline also rejects corpus shrinkage, source-observation changes,
historical-comparison drift, changed canonical-boundary inputs, stale route
reviews, baseline alteration, and missing or altered approved dispositions.
Controlled fixture classifications cannot enter production review records. The
gate is a mandatory operation in the `local`, `pull-request`, `full`, and
`release` profiles, whose definition versions advanced to `1.5.0`, `1.4.0`,
`1.4.0`, and `1.4.0` respectively.

The permanent contract, counts, fingerprints, authority treatment, update
protocol, and negative certification are recorded in
[`full-corpus-differential.md`](full-corpus-differential.md).

Implementation checkpoint `e1a68dd33b37571203b0a1c873f2972159bdebb3`
passed all 71 focused differential/profile/authority tests and every directly
executable formatting, contract, baseline, generation, documentation,
governance, architecture, security, legacy-evidence, and patch-integrity gate.
The canonical local, pull-request, full, and release profiles recorded 20, 39,
68, and 68 passed operations respectively, zero failed operations, and explicit
host-only unavailability for the Ruff/Ruby version pins and dependency-risk
scanner. P07-T04 is therefore `READY WITH RECORDED CARRY-FORWARD`; the next
ordered task is P08-T01, formalizing the legacy regex-compatible source dialect
contract before canonical parser implementation.

## Formalize the legacy regex-compatible frontend contract

The historical regex-shaped source notation is now frozen as frontend
`strling.regex-compat`, dialect `1.0.0`. Its versioned contract owns source
encoding, UTF-8 byte locations, preamble and `%flags` rules, exact grammar,
context constraints, resource limits, stable frontend diagnostic identities,
and specification-authored positive/negative fixtures. It does not define
Semantic STRling, Semantic IR meaning, target capability, or emitted syntax.

The machine catalog records 51 decisions: 32 accepted, six
compatibility-only, and 13 rejected. Thirty positive cases cover every accepted
feature; 45 negative cases cover every rejected feature and every required
syntax/directive/escape/reference diagnostic. The checked initial fingerprint
is
`sha256:0cb32dd3ed534d13ce6d4278a2723898ac40bc374fa6d40c5ac43c553a2265ad`.

The contract makes dialect identity explicit through `SourceDocument`, rejects
inline target/language directives and opaque target-regex fragments, and
requires all accepted constructs to lower structurally before target planning.
No parser or runtime behavior changes in this task. Evidence inventory,
preservation/correction decisions, exclusions, and the P08-T02 handoff are in
[`legacy-regex-frontend-contract.md`](legacy-regex-frontend-contract.md).

## Port the regex-compatible parser into the canonical Rust kernel

The canonical kernel now exposes the internal pure frontend
`strling_kernel::regex_frontend::parse(&SourceDocument)` for
`strling.regex-compat@1.0.0`. It validates the source contract and exact
frontend identity, parses the complete frozen grammar, normalizes the five
global flags, lowers directly to target-neutral Semantic IR, and validates the
result before returning. It does not perform target selection, emission,
binding behavior, package orchestration, filesystem/network access, or
diagnostic presentation.

The parser enforces 1,048,576 UTF-8 source bytes, 128 nesting levels, 65,535
captures, and quantifier bounds through 4,294,967,295. Thirty positive and 45
negative specification fixtures pass deterministically with exact diagnostic
identities and UTF-8 offsets. Resource-limit tests and 2,048 generated UTF-8
inputs complete without panic under the repository-governed Rust 1.75.0
toolchain.

A specification-authored five-case correspondence set covers the complete
governed parser case set. Migration-layer tests prove exact identity, source,
and accepted/rejected correspondence with both historical corpora, while Rust
tests consume only specification authority. The complete differential now
executes that focused Rust test before either historical runner, so canonical
route failure blocks the gate without creating a public probe or adapter.

Native Linux certification executes all 44 historical observations across
three stable runs. The parser route moves ten observations from
`operation_not_exposed` to `incompatible_surface`: canonical Semantic IR and
historical binding-specific ASTs have no authoritative structural
correspondence. The checked baseline is
`sha256:e52a2b48c01b214cf74a9aee967a55817637b11f5c68666a14a59799227dd845`;
the full-corpus, canonical-boundary, route-coverage, and final result
fingerprints are
`sha256:823a6b0806553ed08fe7c367c6510d80235079383632a11a9857c48d951ad2cb`,
`sha256:44b92e3636b8a28a9425261c5929c20637a8cd96231485c022631c5e22e2a395`,
`sha256:c6d41f9483e1235ab44e2f2b0e9322a8cb56b69c3ca13aff43de102c313048ae`,
and
`sha256:e8d610c1fd0ddac973507774f2a98f2a69be62504ec4b94ea8fec9d5ce77e01e`.
The P07 historical peer fingerprint remains unchanged and no Windows-specific
observation was promoted.

Implementation checkpoint `5fd88655966097ae09a1a81704045d8970a7823a`
passes Rust formatting, warning-denying Clippy/check, all-target tests, frozen
contract certification, canonical mapping, differential mutation tests, all
enforced governance/architecture rules, documentation integrity, task-scoped
pinned Ruff/Prettier checks, and patch integrity. Local and pull-request
profiles execute every P08-T02 operation successfully. Their aggregate result
retains a pre-existing repository-lint failure in earlier migration/reference
files; pull-request also retains the existing Ruby Bundler mismatch and missing
Swift executable. No policy or evidence was weakened.

P08-T02 is `READY WITH RECORDED CARRY-FORWARD`. The next ordered task is
P08-T03, attaching canonical provenance, source spans, and diagnostics without
moving presentation or orchestration policy into the frontend.

## Complete advanced and version-sensitive PCRE2 correctness

The canonical PCRE2 10.42 and 10.43 profiles now enumerate the complete
eighteen-capability advanced-feature vocabulary with exact release-tag
evidence. Their immutable revision 1.1.0 fingerprints are
`sha256:0204c9b8ac96ac04a73497ec9ef9f07a2b21728c9cf5f1ff580fa154b4c53a6d`
and
`sha256:0a40fef0e89ab341a031f335438d42203d21fa438358ab9a4aa1177fb8b9bbb4`.
Both explicitly select `pcre2_match`, UTF, UCP, multiline mode, and newline
ANY; only 10.43 carries the governed 255-character variable-lookbehind limit.

Capability extraction distinguishes one fixed width, differing fixed
top-level alternatives, genuinely bounded variable length, unbounded length,
and indeterminate length. This lets PCRE2 10.42 accept `(?<=a|bc)` while still
rejecting true variable lookbehind. A separate `common_fixed_width` fact keeps
Python `re`'s equal-width rule intact; its corrected profile revision 1.1.0 is
`sha256:d5cf41327257b97a68df551f5971c1e0e3b95bca810e8ac7b11b23020f23879d`.
Named captures now retain their semantic name and enforce PCRE2's exact
32-code-unit identifier limit through both profile constraints and final
serialization.

One shared 16-case conformance corpus covers lookahead, fixed and bounded
lookbehind, captures and references, anchors and boundaries, atomic groups,
lazy and possessive repetition, scoped caseless behavior, Unicode properties,
and the documented UCP word-category change. The complete pipeline produces
11 native/five unsupported cases on 10.42 and 14 native/two unsupported cases
on 10.43. Fixed alternatives serialize directly at assertion top level;
wrapping them in a noncapturing group was found by direct execution to make
PCRE2 10.42 reject an otherwise valid lookbehind.

Official PCRE2 tags were built as isolated 8-bit shared libraries. Tag 10.42
commit `52c08847921a324c804cabf2814549f50bce1265` produced library fingerprint
`sha256:fdb00bcb3dd68707ed155927738b454a4281bb664e830d60dd205b10d1a2edd1`
and deterministic result
`sha256:d4129048228a2136e884d90017ba0d080699d6685c78faf2756c4cf18d3623cc`.
Tag 10.43 commit `3864abdb713f78831dd12d898ab31bbb0fa630b6` produced library fingerprint
`sha256:c1426544954ea17aa2d006dca0b0c31d641d8fa3a22eeb5e591e2d51bc721b5c`
and result
`sha256:ebd3355cda411fb6ca25422349b0f374f937a3cab8fd03d6147656699508eb61`.
The test-only probe consumes only serialized patterns and explicit options,
calls `pcre2_match`, and has no product or kernel dependency.

All 281 Rust tests, warning-denying Clippy, 37 focused Python architecture and
probe tests, canonical/core/public/generated contracts, repository hygiene,
governance, documentation, and patch integrity pass. The reviewed three-run
migration differential has canonical-boundary fingerprint
`sha256:566a2fa7623493db7957353ff1e2ed6d20725f1c1971979c71916301a917bb94`
and baseline
`sha256:8a6c16b059dc4fd6a4854259ec90406fc82c557840e0a53eee4e0894307a5eeb`;
all corpora, case sets, route coverage, source observations, and historical-peer
evidence remain unchanged.

Local, pull-request, and full profiles record 20, 39, and 68 passing
operations, zero failures, and no waivers. Their aggregate status remains
`UNAVAILABLE` only because host Ruff 0.16.2 differs from pin 0.15.21, the Ruby
Bundler version differs from the repository-managed version on broader
profiles, and full dependency-risk scanning is unavailable. No unavailable
operation is represented as passing and no policy was weakened.

P10-T03 is `READY WITH RECORDED CARRY-FORWARD`. The next ordered task is
[P10-T04 — Prove PCRE2 runtime safety and performance](https://app.notion.com/p/3b97d9406475818299a0daf86ccd47f7?pvs=204),
which owns exhaustive real-engine execution, adversarial/pathological inputs,
runtime limits, sanitizer/JIT considerations, and performance budgets without
broadening semantic or release authority.

## Certify real PCRE2 runtime safety and performance

The canonical test-only runtime harness now executes already-governed PCRE2
artifacts against exact official 8-bit PCRE2 10.42 and 10.43 libraries. It
verifies compile and match outcomes, complete numbered and named capture
values, overall and capture byte spans, unmatched slots, options, Unicode and
boundary behavior, three explicit native resource-limit contexts, two
atomic-literal rewrite differentials, and 256 deterministic generated cases
per release. Missing exact libraries are structured `unavailable` evidence;
the harness never selects an ambient engine or becomes product runtime.

Both exact-tag libraries passed two ordinary repetitions. PCRE2 10.42 retained
semantic fingerprint
`sha256:2dc7a609e68f1d104d07a3d54d901b4942011a32f4a9d9860658d2464a93c1b1`;
PCRE2 10.43 retained
`sha256:d152cf55d2db232acb484959f6743885a7a1497b481a4c3747f7c75f67cad3b9`.
The fixed runtime corpus fingerprint is
`sha256:9a515fc6d1faff254081287784aebb8c1d9f470d691f8af30658fe4799d28c5b`,
the harness fingerprint is
`sha256:9bee8319ba62f025518df0be48dab1762cb07d34374c4905e7a96248104493a3`,
and the ordinary repeated result is
`sha256:90673d7a115a5b9fa21a24c9e170d2c7d533a2ab2ec42d50387a915ba9b87db4`.

Isolated GCC 13.3.0 builds of both exact tags used AddressSanitizer and
UndefinedBehaviorSanitizer with frame pointers and abort-on-error. The same
repeated matrix passed without an ASan or UBSan report and produced result
`sha256:6bcfa0cc6c5829db9a2c4a4759776a35e7bd4168db3e3ac70d40916e0fd99b67`.
Leak-only cleanliness is not claimed: enabling LeakSanitizer reported CPython
3.12/ctypes shutdown allocations outside PCRE2 after the corpus itself had
completed. This limitation is retained rather than reclassified or waived.

The Rust pathological corpus covers empty input, escape-heavy UTF-8, a dense
class, the maximum 65,535 quantifier, legal and illegal capture names, depth
128, malformed capture slots, and duplicate or conflicting options. Every
case is deterministic and panic-free or fails closed. With 16 warmups and 128
samples, median analysis/planning, lowering, and serialization were 1,158,
448, and 46 microseconds against deliberately generous fixed-corpus budgets of
10,000, 5,000, and 5,000 microseconds. These are reproducible STRling internal
stage budgets, not a universal regex-runtime performance claim.

The existing structured repository executor now validates
`certification-result-v1`. Full and Release definition version 1.5.0 require
the exact-engine operation; Local and Pull Request omit it. At clean commit
`a96408ff82be956e27b0d90e3e22b95ede4ad0e7`, Local recorded 20 passing,
zero failed, and six unavailable operations with evidence fingerprint
`sha256:58896d2ef24200a74e9c74cb4156d1536d195e24fc56f6f63eb76d97f23ce695`.
Pull Request recorded 39/0/seven with
`sha256:41c8124b2edaf10e091a0114a7865c10ed9a8be7bccc577a15d7e4727a1dc7cd`.
Full, supplied the exact libraries and tag commits, passed the new operation
and recorded 69/0/ten with
`sha256:fde06042313c647cef6a05e3d16424d9d399aa5527684b6d2ba5c0c94eb51cfa`.
All aggregates remain `UNAVAILABLE`, never failed, only because of the recorded
Ruff/Ruby tool-version mismatches and Full dependency-risk scanner absence.
No operation was waived or represented as passing.

All 283 core tests, warning-denying all-target Clippy, 404 discovered Python
tooling tests, focused runtime/profile and architecture suites, 11 schema
mappings and 78 contract fixtures, public/generated contracts, repository
hygiene, governance, seven documentation examples and 138-file link
validation, and patch integrity pass. The three-run migration differential is
unchanged at canonical-boundary fingerprint
`sha256:566a2fa7623493db7957353ff1e2ed6d20725f1c1971979c71916301a917bb94`
and baseline
`sha256:8a6c16b059dc4fd6a4854259ec90406fc82c557840e0a53eee4e0894307a5eeb`;
no evidence renewal was required.

P10-T04 and the Production PCRE2 Backend phase are `READY WITH RECORDED
CARRY-FORWARD`. The next ordered task is
[P11-T01 — Implement ECMAScript target lowering](https://app.notion.com/p/3b97d940647581329888eb59876fc4a2?pvs=204),
which must lower independently from normalized Semantic IR and portability-plan
evidence without reusing PCRE2 syntax or adding JavaScript serialization or
Node execution.

## Implement ECMAScript target lowering

The ECMAScript 2024 profile is complete at revision 1.1.0 with all eighteen
canonical capability facts, required compile-stage `u` mode, explicit atomic
and possessive unavailability, and immutable fingerprint
`5117ff6e6c30da54eb31a4621dce5f4807ab0e95f183848e70a01731a4bb4c9f`.
The specification-authored ECMAScript atomic-literal case is now certified as
an equivalent rewrite; its evidence fingerprints as
`ca9a1a3f80e946fad14a231d9c9322756892fc75d84f1f8201d30072dff1b4d2`,
and the exact governed strategy fingerprints as
`d1ac04c04241dff1423c22b5962fc7336c57e664e2510d557edb6e41f885a7d6`.
No possessive or nonliteral atomic rewrite was added.

The independent pure lowering module consumes normalized Semantic IR, the
exact target profile, and the completed portability plan. Its closed typed
representation covers every natively supported operation while retaining
case intent, options, deterministic capture slots and names, requirement
resolutions, certified applied rewrites, semantic identities, and source
spans. It does not import PCRE2 target code, recompute planning, serialize
JavaScript syntax, construct a `TargetArtifact` or `RegExp`, execute Node, or
consult ambient state. Unknown, unsupported, stale, cross-target, malformed,
over-limit, possessive, and nonliteral atomic inputs fail closed with stable
structured diagnostics and no partial plan.

At clean implementation commit
`4a5028cf68ee56fce051c62d28e9364d6e00ee7e`, eight focused lowering tests,
two generated-property tests over 196 programs, eight architecture tests, all
293 core tests, warning-denied Clippy, 11 schema mappings and 78 canonical
fixtures, public/generated contracts, governance, documentation, and patch
integrity passed. The reviewed three-run migration differential has
canonical-boundary fingerprint
`sha256:80b90a82bc74a994aebdc74ac93fdd9a1a75bd3549835936f0825983f190d109`
and baseline
`sha256:39f309162b403c4f3af21a587e3d88dbc9b55edb471c12498702f6ef57d3286a`;
all other corpus, route, source-observation, and historical-peer fingerprints
remain unchanged, with no replacement-review exemption.

Local recorded 20 passing, zero failed, zero waived, and six unavailable
operations with evidence fingerprint
`33a0c9edd488c5ddafe594c12bfbf796b37216f8d2d15d4174e72016d58a0cf3`.
Pull Request recorded 39 passing, zero failed, zero waived, and seven
unavailable operations. Both aggregates are `UNAVAILABLE`, never failed,
solely because host Ruff 0.16.2 differs from pin 0.15.21 and Pull Request also
records the repository-managed Ruby Bundler mismatch. No policy was weakened.

P11-T01 is `READY WITH RECORDED CARRY-FORWARD`. The next ordered task is
[P11-T02 — Implement ECMAScript serialization and Node execution certification](https://app.notion.com/p/3b97d9406475812aa633d2ea86e5a9f9?pvs=204),
which owns deterministic ECMAScript syntax and flags, `TargetArtifact`
construction, and pinned real Node/V8 execution evidence without moving
capability or rewrite policy into the serializer.

## Implement ECMAScript serialization and Node execution certification

Scope checkpoint `e1b27fcff4af5dd666ed88dabf229806381b7a58` fixes the
serializer boundary, optional per-program flag contract, exact Node/V8
identity, bounded execution corpus, and Full/Release-only certification gate.
The pure Rust serializer now consumes only a validated
`EcmascriptLoweringPlan`, emits deterministic ECMAScript source with canonical
`u` or `iu` flags, and constructs one validated `TargetArtifact` without
recomputing capability or rewrite policy. Empty PCRE2 flags remain omitted, so
existing PCRE2 artifact bytes and fingerprints are unchanged.

At implementation checkpoint
`b0ccc8c037319301fb03b3124ebae5ad83297e1d`, project-era Rust and Cargo
1.75.0 with rustfmt 1.7.0 pass formatting, warning-denied all-target Clippy,
and all 306 all-target core tests. The serializer/runtime architecture suite,
runtime orchestrator unit suite, 11 contract mappings with 78 fixtures, 15
existing core-contract tests, every enforced public-contract surface, all
three enforced generated-artifact families including 126 Swift fixtures, and
the complete governance/architecture evaluation also pass. Exact official
Node v22.23.2/V8 12.4.254.21-node.56 on the verified Linux x64 distribution
now executes all 145 bounded requests twice with stable semantic digest
`06d0cfdcc13324335464f795d8b6b9a6fc2fb778df4a22b7a0d3e8830e9ec23b`.
The official archive SHA-256 is
`d60acfe00a2932254bb0ad20e01b0d74397a0875595de719654b214f4b03f307`,
the extracted executable SHA-256 is
`3517c2df0b2f8cd7f422b4b8450ef81c6889f08eb03e281d6de9079b15e6a327`,
and the final formatted harness SHA-256 is
`93a26189d074e19ecb003692c724c4ba23ea52b0c811231c99ab4989d63b01a1`.
No host runtime was substituted.

Exact Node 22 changes historical TypeScript observation identities relative
to the earlier system Node 18 execution without changing corpus case coverage,
route approvals, or the intentional canonical-boundary fingerprint
`sha256:c8ee813968a98d410049b7581998a8b549766538380d69194842fc1c7ca2fbf8`,
so the exact-tool migration baseline is reviewed and renewed at
`sha256:b65732d9f174208a286acbb206222b2170aa022db67021112990fa3e33d0ad9e`.
The three-repeat differential result is
`sha256:4a44fddd19ef7c690994c88c959802d01e999731620de99ead94e68b16cc9bf0`
with zero mismatches. Exact Ruff 0.15.21 and Prettier 3.3.3 also exposed and
closed bounded repository formatting, import-bootstrap, unused-import, and
suppression debt; formatter and lint hardgates now pass with 80 governed
suppression directives and zero findings.

At clean exact-evidence commit
`3f7ef6ab6903144737b697c6e3a7dd16caca1b71`, Local 1.5.0 passes all 26
operations with fingerprint
`446ffd738a74c661aa340efc7d1ed2bc9db0b8f37ca47f798281c28a5eda03cb`.
Pull Request 1.4.0 records 44 passed and two unavailable operations with
fingerprint
`dbb62797f1ec281893c50a3361235d24a2af16cae1b9a180789b979297654f95`.
Full 1.6.0 records 73 passed and seven unavailable operations with fingerprint
`a27d35abe95c4c96e49d6c7352995a883ac5c3ba34f7bb031c816c67089a8f61`;
both PCRE2 runtime versions and exact ECMAScript Node certification pass. The
only carry-forward is inherited Ruby Bundler drift, missing Swift, and the
existing structured multi-ecosystem dependency-risk scanner unavailability.
There are zero failed, incomplete, not-yet, or newly waived operations.

P11-T02 is `READY WITH RECORDED CARRY-FORWARD`. P11-T03 is the next ordered
task and owns Python `re`-specific structured lowering from Semantic IR and the
completed portability plan without moving target behavior into semantic
authority.

## Implement Python re target lowering

P11-T03 starts from clean commit
`bff5414c3c822b5bffc7bfd17ef5d32d8a259a13`. The read-first inventory fixes
the boundary at normalized Semantic IR plus one exact CPython `re` profile and
the completed portability plan. The stage will produce typed Python-specific
structure only; it will not translate another target, serialize pattern text,
construct a `TargetArtifact`, execute Python, migrate a binding, or publish a
package.

Official Python 3.11 `re` documentation is the target authority. It establishes
separate `str` and `bytes` applicability, common-width fixed lookbehind,
lookahead, captures and references, anchors and boundaries, Unicode-aware
built-in classes for `str`, flags, and native atomic and possessive constructs
added in 3.11. Variable-length lookbehind and Unicode property escape syntax
remain unavailable. The current governed profile enumerates only five facts,
so this task must complete the capability vocabulary and renew exact profile
evidence before lowering can claim full coverage.

Profile revision 1.2.0 now enumerates all eighteen canonical requirements and
fingerprints as
`sha256:55e7f0bc93e2192d5f09f6c4ef65b6bff0dc831571059d80edf9b8b661f80a6c`.
It corrects Unicode property escapes to unavailable, retains variable-length
lookbehind as unavailable, admits common-width fixed lookbehind, and records
native atomic and possessive support. Required `python.pattern_kind=str`
remains typed runtime data, while the lowering boundary also accepts explicit
`bytes` profiles and rejects Unicode-only semantics with a stable diagnostic.

At implementation checkpoint
`0ad92f65b3d04a55563958ad527d25a4e23354a0`, the independent pure Rust
lowering owns a closed Python `re` operation tree for every Semantic IR
variant, deterministic capture slots, pattern kind, exact options,
requirements, certified rewrites, and node/source provenance. It returns
`STRL-PYTHON_RE_LOWERING-0001` through `0015` failures without emitting regex
text, constructing artifacts, invoking Python, translating PCRE2/ECMAScript
output, or consulting the historical Python binding.

All 318 Rust tests and warning-denied Clippy pass. The complete profiles
produce zero unknown generated requirements; 2,048 generated plan invocations
retain 64 certified rewrites, zero unresolved requirements, and 160 genuine
profile differentials. All 83 architecture tests, 15 core-contract tests, 11
schema mappings with 78 fixtures, enforced public/generated contracts,
governance, documentation integrity across 141 files, formatting, and patch
integrity pass. Under the verified official Node v22.23.2 Linux x64 binary,
the three-repeat migration gate has zero mismatches and renews only the
canonical boundary to
`sha256:7aac6d8221aa03b0b978b1cfe8047ea1a2ccbc344ac05d661e76adba153913a0`;
the reviewed baseline is
`sha256:58358b3edb3bcde30a07eb2bbabe1c35860bffb0f81ebf0bda355f085a9c6461`.

On the clean implementation commit, Local 1.5.0 passes all 26 operations with
fingerprint
`77582a99e81c55f86ff6418f560983984a70507d307a6c42e12fed3d2a53900f`.
Pull Request 1.4.0 records 44 passed, zero failed, and only the inherited Ruby
Bundler drift and missing Swift as unavailable, with fingerprint
`1320a4902a46e136b500900b616c2f7ec7685bd2267a50e6d64e2f17f6006246`.
No finding is waived or represented as passing.

P11-T03 is `READY WITH RECORDED CARRY-FORWARD`. P11-T04 is the next ordered
task and owns deterministic Python `re` syntax/escaping, flags and options,
`TargetArtifact` construction, and exact CPython execution certification from
the completed lowering plan without moving capability or rewrite policy into
serialization.

## Implement Python re serialization and CPython execution certification

P11-T04 started from clean certified commit
`7912736b4d3965be9f1bb9c37c5cad524a5d0a10` and is complete through the
verified implementation and prerequisite-correction commits
`6b1831c2eb25283cb609d4565752b1e72e82dbb3`,
`77bc18fe7588d1d2d217ede2841c9f6242eaf19e`, and
`3232e816bde01712912262bf4b1dffd1b178b00d`. The pure serializer consumes one
validated `PythonReLoweringPlan` and emits the existing `TargetArtifact`
contract with Python regular-expression source, canonical case flags, exact
pattern-kind options, requirements, rewrites, diagnostics, and generated
provenance. It does not inspect Semantic IR, recompute capabilities or
rewrites, execute Python, or translate peer-target output.

Official Python 3.11 `re` documentation governs syntax and observations. Exact
runtime evidence selects the official source-only CPython 3.11.15 release,
whose XZ archive SHA-256 is
`272179ddd9a2e41a0fc8e42e33dfbdca0b3711aa5abf372d3f2d51543d09b625`.
The controlled build and certification fingerprint the derived Linux x86-64
executable, ABI/runtime identity, profile revisions, corpus, harness, pattern
kind, flags, and repeated semantic results. The exact executable SHA-256 is
`1fbfa9ca2d8b4a1180be898c8de67732deee8aff7bb838012acb63764be83232`;
the host CPython 3.12.3 controller is explicitly recorded and rejected as a
target runtime.

No schema change is required. The existing pattern `flags` array represents
per-program `i`; required `python.pattern_kind` remains a separate runtime
option. Read-first implementation proof exposed that the existing immutable
profile permits only `str`, while this task explicitly requires executable
bytes artifacts. Scope therefore adds a separate exact
`profile:python-re/3.11-bytes` companion whose Unicode-only capabilities are
unavailable; it does not mutate the certified `str` profile or weaken exact
profile identity checks. Scoped syntax preserves wildcard, line-position, and
ASCII/Unicode class behavior without leaking global `s`, `m`, `a`, `u`, `L`,
or verbose behavior. String and bytes execution, captures and spans,
lookarounds, anchors/newlines, Unicode/case, atomic and possessive 3.11
boundaries, zero-length matching, compile errors, rewrites, negative runtime
identity, and repeat determinism are covered by 149 requests per run. Two
complete exact-runtime runs pass with 81 `str` and 68 `bytes` requests, zero
discrepancies, corpus SHA-256
`b778d5e9df54346666d2e7ca99eb56c97d477af1c7d15f29491a3df172512d0a`,
formatted harness SHA-256
`f335bd48b27e8b149b198371896f1aff8019370ead8b28151fd8ed4491f5e8b8`,
semantic result SHA-256
`3dc0ad3f8e93fb61c4fcccd12b1aa555390ac8d133604f36946e613a53dfc911`,
and deterministic operation SHA-256
`4d076e05837e10cc3a4bc0af9badd8d68161c5fbde9d3f634750886d3a2ab789`.

All Rust all-target tests and warning-denied Clippy pass. Exact Ruff 0.15.21,
Prettier 3.3.3, focused Python/runtime/architecture suites, 11 core schema
mappings with 79 fixtures, public/generated contracts, governance,
documentation integrity, the reviewed Node 22 migration differential, and
patch integrity pass. Local passes all 26 operations. Pull Request records 44
passed and only inherited Ruby Bundler and Swift availability as unavailable.
Full 1.7.0 records 74 passed, zero failed or incomplete, and seven explicit
inherited host/scanner unavailabilities; exact PCRE2 10.42, PCRE2 10.43,
ECMAScript Node 22, and Python `re` CPython 3.11.15 certifications all pass.
No finding is waived or represented as passing.

P11-T04 is `READY WITH RECORDED CARRY-FORWARD`. P11-T05 is the next ordered
task and owns the shared specification-authored cross-engine conformance corpus
without reopening serializer, lowering, product, binding, package, version, or
publication scope.

## Build the shared cross-engine behavioral corpus

P11-T05 starts from clean certified commit
`868c4a671aa5cc51db8daf0b377675616ee32279`. The existing draft
specification-owned cases already separate canonical semantic, diagnostic,
match/capture, and target-support expectations from implementation evidence.
This task expands that authority set and adds a separate corpus-v1 execution
manifest rather than changing the compiler contract suite or allowing runtime
observations to author expectations.

The exact denominator is PCRE2 10.42, PCRE2 10.43, ECMAScript 2024 on Node
22.23.2, Python `re` 3.11 `str`, and Python `re` 3.11 `bytes`. Every vector
must explicitly be executable, unsupported, or not applicable for every
profile. Coverage obligations and minimum counts guard literals/classes,
composition, repetition modes, captures/references, assertions, anchors,
Unicode/case behavior, the certified atomic-literal rewrite, diagnostic and
unsupported cases, and interactions against silent shrinkage.

A repository-only Rust adapter projects authored Semantic IR through the
completed canonical planning/lowering/serialization stages. A separate Python
orchestrator executes only declared applications through the already-fixed
exact PCRE2, Node, and CPython harnesses, normalizes engine offsets to UTF-8 and
capture slots to logical IDs, and preserves raw plus normalized observations in
one deterministic checked evidence artifact. The generated serializer owns
that artifact exclusively, so producer `--write` and verifier `--check` bytes
remain identical without exempting authored corpus JSON from formatting.

The certified corpus contains 20 cases and 100 explicit applications: 88
execute, five unsupported, and seven not applicable. ECMAScript records
18/1/1 execute/unsupported/not-applicable, PCRE2 10.42 records 17/2/1, PCRE2
10.43 records 19/0/1, Python `re` text records 18/1/1, and Python `re` bytes
records 16/1/3. All 19 semantic, 19 target, 19 match/capture, and one diagnostic
expectations agree across two exact runs. Canonical identities are case set
`8ce5b9874312e9527944960f84c722a8293e9030bc6d9d8550aca53012ae849d`, vector
set `8d6fc71842065e7d1e8796e4ee3e210669220c2b129530e70d9e05ff08e17afc`, corpus
`e8c069f068b8562518bfcf4f782a0961b53124660e4d40e63e49cbe8c6824fb1`, projection
`029cf1c0df979774e71acb8f08e2a02bfd99001529a14faf9dcedfe01cda8089`, and checked
observation `9a575b86e8ea43590b24fcc2bda2d3a7b80ed25fa98694f46924b247abd3493c`.

Exact shared execution passed on PCRE2 10.42 and 10.43, Node 22.23.2, and
official-source CPython 3.11.15. Rust all-target tests, warning-denied Clippy,
focused contracts and architecture checks, generated artifacts, formatting,
governance, documentation integrity, patch integrity, and the reviewed
three-run Node 22 migration differential pass. Local passes 26/26. Pull Request
records 44 passed and only the inherited Ruby Bundler mismatch and missing
Swift as unavailable. Full 1.7.0 records 75 passed, zero failed or incomplete,
and seven explicit inherited host/scanner unavailabilities; all exact runtime
certification operations, including shared cross-engine certification, pass.
No finding is waived or represented as passing.

P11-T05 is `READY WITH RECORDED CARRY-FORWARD`. P11-T06 owns the initial
feature-by-profile portability matrix and explicit classification of every
preserved cross-target divergence; it must consume this fixed corpus and
evidence without changing target behavior or treating engine majority as
authority.

## Certify the initial cross-engine portability matrix

P11-T06 starts from clean certified commit
`ae6de142cccf8ad73bd780d7c673dc5c7a3aceed`. The fixed input is the
specification-owned 20-case shared corpus with five exact profiles and 100
ordered case/profile applications plus checked observation SHA-256
`9a575b86e8ea43590b24fcc2bda2d3a7b80ed25fa98694f46924b247abd3493c`.
The matrix is a downstream certification artifact; it cannot change authored
expectations, target profiles, planner decisions, rewrite authority, target
implementation, harnesses, product behavior, or public contracts.

Read-first inventory records 87 native applications, one ECMAScript
planner-certified atomic-literal rewrite, five target unsupported or constrained
applications, seven not-applicable applications, and no currently observed
canonical semantic mismatch. The rewrite plus unsupported set forms six
explicit representation/support divergences. Matrix certification will retain
one row for every vector/profile pair, exact corpus/case/profile/runtime and
observation identities, modes/options, feature and requirement tags, normalized
observation fingerprints, and one explicit disposition. Feature-by-profile and
requirement-by-profile aggregates will name every contributing row rather than
hiding exclusions behind percentages.

A separate evidence-only controller will consume validated corpus and checked
observation bytes without executing runtimes, invoking target projection, or
inspecting emitted pattern syntax. It will require canonical expectation
agreement and one normalized semantic class across every comparable executed
profile. Missing or stale identities, absent rows, observations on unsupported
or not-applicable applications, semantic splits, unknown classifications, and
any unresolved difference fail closed. Engine consensus and historical output
remain non-authoritative.

The machine JSON will be authoritative and will deterministically generate a
human-readable Markdown projection. Both checked outputs will have exclusive
generated-artifact ownership. Full and Release will run the four exact runtime
and shared-corpus operations before the matrix check, preserving structured
unavailability rather than substituting ambient engines. This task closes P11
only after repeated exact execution, matrix determinism, all available
hardgates, explicit environment carry-forward, and a clean final commit.

The evidence-only controller, schema, machine artifact, generated summary,
mutation hardgates, and Full/Release routing are complete at implementation
commit `a38a42fdad264143a553a64b404c24f6fb3c1d53`. The certified matrix has 100
entries: 87 native, one planner-certified equivalent rewrite, five target
unsupported or constrained, seven not applicable, six explicit nonblocking
representation/support divergences, zero semantic-divergent cases, and zero
unresolved entries. All 19 comparable executed cases form one normalized
semantic class; the diagnostic-only case remains explicitly not compared.
Matrix SHA-256 is
`11f70923cdc200b132d7f68077fd840f3d38cf9aff63949fae24d703b68ea205`.

Exact PCRE2 10.42/10.43, Node 22.23.2, CPython 3.11.15, shared-corpus, and matrix
certifications pass. Rust all-target tests, warning-denied Clippy, 485 tooling
tests, canonical and core contracts, stage boundaries, public/generated
contracts, formatting, governance, documentation integrity across 145 files,
patch integrity, and the reviewed three-run migration differential pass. The
migration candidate matches checked baseline
`sha256:8127c22a016013ff9751540ce39615fa780291da675082f2668bae5d63e4da5c`;
no baseline renewal is required.

On the clean implementation commit, Local passes 26/26. Pull Request records
44/46 passed and Full 1.9.0 records 76/83 passed, with zero failures,
incomplete operations, or waivers. Only the inherited repository-managed Ruby
Bundler mismatch, missing Swift, and structured dependency-risk scanner remain
unavailable. P11-T06 and P11 are `READY WITH RECORDED CARRY-FORWARD`. P12-T04
is the next ordered task and resumes the partially completed overlap,
unreachable, degenerate, and suspicious-pattern diagnostics work without
reopening the completed cross-engine target boundary.

## Implement proof-backed semantic quality diagnostics

P12-T04 resumes from clean P11 completion commit
`ca665b3e98da66aab93857e9219bcf2d256ca865`. Its Partial predecessor state is
intentional: foundational and structural semantic facts, five target-neutral
safety findings, typed uncertainty, and `STRL-SAFETY-0001` through
`STRL-SAFETY-0005` are already complete and remain authoritative.

The remaining bounded gap is canonical communication of seven complete quality
proofs: a zero-maximum repetition whose operand is unreachable; a greedy or
lazy exact-once repetition wrapper; a later exact duplicate alternation branch;
same-position word-boundary and not-word-boundary assertions; same-direction,
canonical-equivalent lookarounds of opposite polarity; explicit literal/range
or range/range character-set overlap with a concrete scalar witness; and a
resolved backreference to a capture body with certified maximum consumption
zero. These become `STRL-QUALITY-0001` through `STRL-QUALITY-0007` in that
order.

Quality proof construction remains internal to canonical diagnostic generation
and consumes only normalized Semantic IR plus exact foundational and structural
facts. Typed safety and quality provenance share deterministic occurrence
ordering and the unchanged Diagnostic wire contract. Unknown overlap,
case-folding or Unicode-property guesses, shared leading prefixes, general
language inclusion or satisfiability, unused captures, forward-reference
behavior, possessive exact-once repetition, style-only advice, target/runtime
claims, raw-source scanning, fixes, and automatic rewrites remain excluded.
P12-T05 separately owns semantics-preserving rewrites.

The implementation checkpoint adds typed `QualityFinding` and
`QualityEvidence` values inside canonical diagnostic generation, distinct
`DiagnosticEvidence::Safety` and `DiagnosticEvidence::Quality` provenance, and
stable `STRL-QUALITY-0001` through `STRL-QUALITY-0007` mappings. Safety and
quality records share canonical code/node/evidence occurrence ordering and a
combined fail-closed bound of 4,096 records per class. The crate-private
target-neutral pipeline projects both as advisory diagnostics without adding a
target, binding, package, product, or editor route.

Thirteen focused Rust tests cover all seven positive mappings, adversarial near
misses, exact source projection, source-less programs, preservation of all five
safety codes, and 128 fixed-seed candidates through repeated normalization and
generation. The complete kernel all-target suite passes and warning-denied
Clippy passes. The additive quality example validates under the unchanged
Diagnostic schema; canonical contracts pass 11 schemas, 60 positive and 33
negative examples, while core contract mapping covers 96 fixtures. Forty-four
focused Python contract and architecture tests pass, including missing quality
ownership and injected target, portability, raw-source, and process
dependencies.

The implementation changes the migration differential's canonical-boundary
identity, as required for any governed core implementation edit. A reviewed
three-run candidate differs from the preceding checked baseline only in the
canonical-boundary fingerprint and the baseline's self-fingerprint. Corpus
identities, route coverage, source observations, historical peer evidence,
replacement reviews, and the full-corpus fingerprint remain byte-identical.
The renewed canonical-boundary fingerprint is
`sha256:23813360fc95b4a7f26dd07efcd5a126502f60e6a5e7fa12c2e813cefbafa6dd` and
the renewed baseline fingerprint is
`sha256:67d84aa74329f649c57c8f4004e749a567c7649ea71272a6b4e36aedda710f3b`.

P12-T04 closes from clean certification commit
`427902e331b401827dcb8489e79f2e2e38c69c73`. All Rust targets,
warning-denied Clippy, 486 tooling tests, canonical and core contracts,
formatting, public/generated contracts, governance, documentation integrity
across 146 files, patch integrity, and the reviewed three-run migration
differential pass. Two exact shared-corpus runs retain 20 cases, 100
applications, and observation SHA-256
`9a575b86e8ea43590b24fcc2bda2d3a7b80ed25fa98694f46924b247abd3493c`;
the portability matrix remains 87 native, one certified rewrite, five
unsupported, seven not applicable, six explicit nonblocking divergences, and
zero semantic-divergent or unresolved entries at SHA-256
`11f70923cdc200b132d7f68077fd840f3d38cf9aff63949fae24d703b68ea205`.

Local passes 26/26. Pull Request records 44/46 and Full records 76/83 passed,
with zero failures or waivers. Full passes exact PCRE2 10.42/10.43, Node
22.23.2, CPython 3.11.15, shared-corpus, and portability-matrix certification.
Only the inherited repository-managed Bundler mismatch, missing Swift, and
structured dependency-risk scanner unavailability remain explicit.
P12-T04 is `READY WITH RECORDED CARRY-FORWARD`; P12-T05 owns any
semantics-preserving rewrite suggestions and cannot infer rewrite authority
from a quality finding alone.

## Implement and certify a semantics-preserving rewrite library

P12-T05 starts from clean P12-T04 completion commit
`9c88584c2c22f92572d89a4a87711e3b738e2e1a`. The existing equivalence
registry, planner proof types, target lowering consumers, exact runtime
adapters, shared corpus, and portability matrix are preserved as prerequisites.
Atomic-literal elision remains the sole mandatory portability rewrite and is
not broadened.

The locked additive strategy is
`rewrite.repeat_exactly_once.elide.v1`: a request-only optional optimization
for a repetition whose minimum and bounded maximum are both one and whose mode
is greedy or lazy. Its exact count makes repetition choice non-observable, but
possessive mode remains excluded because commitment can suppress backtracking
inside the body. The action will retain the removed wrapper identity/origin as
evidence and leave direct-body provenance unchanged; it cannot emit source
edits, target syntax, or an automatically mutated program.

Registration will distinguish mandatory portability from optional
optimization and bind the exact Semantic IR shape, transformation, capability
effects, target applicability, proof obligations, rejected states,
provenance, explanation, conformance bytes, and execution vectors. Missing or
stale evidence, incomplete PCRE2 10.42/10.43, ECMAScript 2024, Python `re` str,
or Python `re` bytes coverage, an unknown strategy, or a widened precondition
will fail closed. Dedicated exact-runtime vectors will exercise captures,
alternative priority, zero-length bodies, Unicode/options, and positive and
negative subjects. The shared corpus and portability matrix must remain
semantically unchanged.

Zero-count repetition removal, duplicate-branch removal, general atomic or
possessive changes, and character-set overlap cleanup remain rejected because
capture contracts, priority, commitment, Unicode/case-folding, negation, or
source-member behavior lacks a complete proof. No safety or quality diagnostic
is rewrite authority; `STRL-QUALITY-0002` can explain an exact-once wrapper but
cannot select or apply the optional action.

The implementation closes the registry as exactly two strategies. The existing
`rewrite.atomic_literal.elide.v1` remains mandatory portability. The new
`rewrite.repeat_exactly_once.elide.v1` is request-only optional optimization for
greedy or lazy `{1}` wrappers; possessive mode and every broader candidate stay
unregistered. A pure target-neutral action boundary returns a certified,
unapplied replacement for an explicit stable-node request without mutating the
program, emitting diagnostics or edits, or exposing target/product behavior.
Portability planning filters mandatory strategies, and target lowerers reject an
optional strategy if one is injected into a plan.

The registry now binds exact shape, transformation, invariant, application kind,
capability effect, target applicability, proof, counterexamples, provenance,
explanation, conformance bytes, and exact execution evidence. Its certified
atomic-literal and exact-once strategy fingerprints are
`43f866c83d9e2dfbe3d2f9f4686a2578311c37060d2592dbdfae7560c332c6e1` and
`7116e5773e64815db90f31c78ca6ad90069925c0e43242346a95b3d01d62c837`.
Missing, stale, reordered, widened, profile-incomplete, or unknown evidence fails
closed. Deterministic, adversarial, fixed-seed property, registry, contract, and
controlled architecture-mutation tests certify that boundary.

Exact execution passes five rewrite cases on each PCRE2 10.42 and 10.43, four on
ECMAScript 2024, and five on each Python `re` str/bytes profile. Capture,
alternative-priority, zero-length, Unicode/options, positive, and negative
observations are identical before and after rewriting. The shared corpus remains
20 cases and 100 applications at observation SHA-256
`9a575b86e8ea43590b24fcc2bda2d3a7b80ed25fa98694f46924b247abd3493c`;
the matrix remains zero-unresolved at SHA-256
`11f70923cdc200b132d7f68077fd840f3d38cf9aff63949fae24d703b68ea205`.

P12-T05 closes from clean review commit
`0dfdbc08e0c47474646738be1cce34573f94488a`. All Rust targets,
warning-denied Clippy, 490 tooling tests, canonical/core/public/generated
contracts, formatting, governance, security, documentation integrity across 147
files, patch integrity, and the reviewed three-run migration differential pass.
The migration baseline is
`sha256:c6552f544b307f7ca9bb01c52fd79ea4c046248fcd03dedf57fb501b570aa0d0`;
only the intended canonical-boundary identity advances, while corpus, route,
source-observation, historical-peer, replacement-review, and full-corpus
evidence remains unchanged.

Local passes 26/26. Pull Request records 44/46 and Full records 76/83 passed,
with zero failures or waivers. Full passes exact PCRE2 10.42/10.43, Node
22.23.2, CPython 3.11.15, shared-corpus, and matrix certification. Only the
inherited repository-managed Bundler mismatch, missing Swift, and structured
dependency-risk scanner remain unavailable. P12-T05 and P12 are `READY WITH
RECORDED CARRY-FORWARD`; P13-T01 is the next ordered task and begins the
canonical builder protocol and Simply semantic contract without reopening the
completed rewrite authority boundary.

## Define the canonical Simply builder protocol

P13-T01 starts from clean P12 completion commit
`11368a125fff6f5a98b1c2e32ac477679e4b278b`. Canonical Semantic IR,
`CompileRequest`, normalization, analysis, planning, target backends,
diagnostics, and rewrite authority are stable prerequisites. This task defines
the host-neutral Simply construction contract and its evidence; it does not
implement or change any Rust, TypeScript, Python, binding, package, product, or
runtime API.

The locked protocol admits exactly empty, literal, wildcard, character-set,
sequence, alternation, transparent group, capture, backreference, position,
lookaround, atomic, repeat, imported-node, and imported-program operations.
Generated identities derive deterministically from a request namespace plus
stable step/capture keys. Generated nodes are source-less; imported identities,
origins, and sources are preserved and must remain unique and fully resolvable.
Builder values are immutable and single-materialization so host object aliasing
cannot create duplicate Semantic IR identities.

Unicode scalar text, case matching, built-in class domain, wildcard line
terminator treatment, positions, lookaround direction/polarity, and repetition
mode are semantic intent. Requested outputs, target-profile references,
diagnostic policy, partial-semantics policy, and limits remain compiler routing.
Raw regex, target fragments, engine flags, runtime values, host callbacks, and
implicit engine selection are forbidden. Decode, graph, projection, canonical
normalization, semantic, and `CompileRequest` validation will execute in a
deterministic fail-without-mutation order.

Historical literal behavior and immutable composition remain compatibility
evidence. The `max=0` unbounded sentinel is intentionally corrected to explicit
`null`; host repeat guards and Python capture duplication are not semantics;
direct `toString`, `compileNode`, `toRegExp`, and `exec` conveniences remain
separate compatibility obligations that must later route through the canonical
compiler; and formatted exception prose remains presentation only.

Completion requires versioned machine schemas and protocol data, exhaustive
positive and negative fixtures, a checked manifest, a certification-only
projector, canonical Rust normalization and CompileRequest equivalence, and
controlled architecture mutations. All affected contracts, Rust/tooling tests,
documentation, governance, migration, Local profile, and clean-tree checks must
pass before P13-T01 can close.

The implementation checkpoint now provides protocol `1.0.0`, three schemas,
nine positive cases, 13 negative cases, all 15 operations, all 12 stable errors,
eight historical dispositions, and a seven-input checked manifest at
`sha256:245bd1aa0745db78258f5c5f27e023d4bd07ffbc3814bfd751e577192a034740`.
The certification-only projector reproduces exact authored Semantic IR and
`CompileRequest` values. Rust proves all expected programs are canonical and
all requests validate. Mutation tests fail closed on inventory, fingerprint,
schema, raw/target authority, evidence, failure-identity, runtime/process, and
frontend-authority drift. Canonical kernel fixture accounting advances from 100
to 107 solely for the seven bound Simply JSON artifacts. Complete repository
and Local certification remain before task closure.

P13-T01 closes from clean review commit
`1d35c309acf2e3c6188bfae3b253d8951240b638`. All Rust targets,
warning-denied Clippy, 498 tooling tests, canonical/core/public/generated
contracts, formatting, linting, governance, security, documentation integrity
across 150 files, and the reviewed three-run migration differential pass. The
migration baseline remains
`sha256:c6552f544b307f7ca9bb01c52fd79ea4c046248fcd03dedf57fb501b570aa0d0`
and the canonical boundary remains
`sha256:2f58ec3fe3e9f1c4498a40b43c5a44eeb386e15973ae0cef7b4aaa47ab2998ed`.
Local passes 26/26 from a clean tree with zero failures, waivers, unavailable
operations, or incomplete operations. The task is READY; P13-T02 is next and
will implement the native Rust Simply API as a thin protocol/kernel layer
without a parallel semantic model or compiler.

## Implement the native Rust Simply API

P13-T02 starts from clean P13-T01 completion commit
`092fe005f6e0c3709ca6313d6a8d5b1ef0a3a100`. Protocol `1.0.0` is complete at
`sha256:245bd1aa0745db78258f5c5f27e023d4bd07ffbc3814bfd751e577192a034740`
with 15 operations, nine positive cases, 13 negative cases, 12 stable failures,
and exact canonical Rust equivalence. This task implements only the native
Rust host construction layer.

The locked `SimplyBuilder` stores canonical `Node` candidates directly behind
opaque immutable value handles. Explicit stable step and capture keys derive
the protocol node/capture identities. Values have one materializing parent;
cloned handles do not clone semantic subtrees and reuse fails before mutation.
Generated nodes are source-less, group is transparent derivation provenance,
and canonical imports preserve fully resolved identities, origins, and sources.

Finishing consumes the graph into the existing `canonical-v1` normalizer and
then into `SemanticProgram` or `CompileRequest`. Requested outputs, compiler
options, and target-profile references remain request routing. The API exposes
no parser, raw regex, target syntax, emitter, runtime, ambient state, direct
analysis/planning/lowering orchestration, or alternate compiler function;
compile-through uses the existing `compile` facade.

Completion requires all-operation/error/import equivalence, ownership and
fixed-seed property tests, deterministic serialization, direct-versus-Simply
compile results, intentional `strling-kernel` public snapshot expansion,
controlled architecture mutations, complete Rust/repository checks, reviewed
migration-baseline renewal if necessary, Local and Pull Request profiles, a
clean tree, and P13-T03 handoff.

P13-T02 closes from clean implementation commit
`a26a3a1966bd68c2ce25067106dd89465f3b5a68`. `SimplyBuilder` implements all 15
protocol operations directly over canonical `Node` candidates with opaque
immutable values, deterministic node/capture identities, validate-before-
mutation single-parent ownership, transparent group provenance, canonical
imports, normalization, explicit request projection, stable errors, and no
parallel semantic model or compiler.

All nine positive protocol fixtures, all 12 stable failures, 256 fixed-seed
property cases, malformed bounded inputs, import immutability, deterministic
serialization, and direct-versus-Simply compile results pass. Warning-denied
Clippy, every Rust target, 502 tooling tests, 11 schema mappings and 107
fixtures, protocol/core/public/generated contracts, controlled architecture
mutations, formatting, governance, security, documentation integrity across
151 files, and patch integrity pass. The additive `strling-kernel` snapshot is
intentional.

The reviewed three-run migration differential certifies 44 observations with
zero mismatches or blocking unresolved replacements. Its renewed baseline is
`sha256:3676dbe20c75ccd159aadd325ad2ada0a1a8736ae65591d956582f6352b3f0f4`
and canonical boundary is
`sha256:52abcfd126a02765086e93256cae70af4c1c86763f424136d879f0e52cca3eda`.
Local passes 26/26. Pull Request passes all 45 available operations with zero
failures or waivers; only the inherited missing Swift toolchain is explicitly
unavailable. The profile-generated Python venv was removed and the final tree
is clean. P13-T02 is `READY WITH RECORDED CARRY-FORWARD`; P13-T03 is next and
will implement the ordered TypeScript and Python preview adapters without
reopening semantic or compiler authority.

## Implement the TypeScript and Python Simply Preview adapters

P13-T03 starts from clean P13-T02 completion commit
`7d25b5fe0fe511c7942d0f6c32d808e5af30ce45`. The host-neutral protocol and
native Rust `SimplyBuilder` are certified prerequisites. The existing
TypeScript and Python `Pattern` trees, local compilers/emitters, target-string
helpers, and runtime conveniences remain historical compatibility evidence and
must not become Fourth Edition authority.

The locked design adds explicit Preview builder/value/error/transport surfaces
in both bindings. They serialize exactly the 15-operation BuilderRequest and
delegate through an additive `strling simply` JSON transport. Typed replay
belongs to `core::simply`; the CLI owns bounded I/O and exact profile loading
only, then calls the existing `compile` facade. Successful responses contain
the canonical `CompileRequest` and `CompileResult`; construction failures retain
ordered `STRL-SIMPLY` code/path records.

The complete public-operation inventory classifies adaptable construction
intent separately from unsupported private-node construction, implicit
rendering, runtime execution, formatted errors, capture-repeat quirks, and five
unratified standard-pattern recipes. Historical `max=0` becomes protocol
`null`; no operation remains unresolved. Preview additions do not silently
change the stable legacy `Pattern` APIs, and the Preview path may not import or
invoke their private semantic/compiler/target machinery.

Completion requires byte-stable serialization, all operations/errors/imports,
cross-language and direct-IR `CompileResult` equality, historical differential
review, intentional public snapshots, controlled one-core architecture
mutations, all affected binding/Rust/repository checks, Local, Pull Request,
Full, and a clean tree.

P13-T03 closes from clean implementation commit
`4c1ff024f58047a91430f3a110e1a1393ba74ae3`. The additive TypeScript and Python
Preview adapters cover all 15 operations using opaque builder-owned values,
deterministic protocol serialization, explicit/injected transports, and stable
construction errors. Typed Rust replay owns every graph and semantic rule, and
`strling simply` delegates only to `SimplyBuilder` plus the existing `compile`
facade. Historical binding compilers, emitters, target strings, runtime helpers,
and standard recipes are not invoked or promoted.

All nine positive and 13 negative fixtures, 12 stable errors, imports,
identities, explicit PCRE2 10.43 routing, malformed transport behavior, and
direct canonical `CompileResult` equivalence pass. The compatibility baseline
classifies 55 TypeScript and 53 Python operations with no unresolved entry at
source fingerprint
`sha256:6e8a143592cd80e40507135f3f8bdc8684212fd324e695bb50b819e378abc09b`.
Warning-denied Rust, complete TypeScript and Python suites, 508 tooling tests,
11 schema mappings and 108 fixtures, canonical/public/generated contracts,
architecture, governance, documentation, security, formatting, hygiene, and
patch integrity pass.

The reviewed three-run migration differential has zero blocking unresolved
replacements at baseline
`sha256:ba08a6c0c4718309bfa66c80fddeba7c62f0d997ec8970718da4b4d8058f896f`.
Local passes 26/26. Pull Request has 44 passed with no failures or waivers and
records only the inherited Ruby Bundler mismatch and missing Swift. Full has 76
passed with no failures or waivers, including every exact-runtime/cross-engine
gate; network dependency risk plus the inherited Ruby and Swift operations are
explicitly unavailable. The generated venv was removed and the final tree is
clean. P13-T03 is `READY WITH RECORDED CARRY-FORWARD`; P13-T04 is next and will
ratify the Semantic STRling DSL grammar before parser implementation.

## Semantic STRling textual language contract

-   Status: Complete
-   Starting commit: `ff85bbe381e8dbfb0ed9c689611280dc60922657`
-   Behavior change: Additive specification only; no parser, formatter, compiler,
    target, runtime, or package behavior
-   Task record:
    [`semantic-strling-language.yaml`](records/semantic-strling-language.yaml)
-   Readiness: READY WITH RECORDED CARRY-FORWARD

P13-T04 locks `strling.semantic` dialect `1.0.0` as a contained, versioned
frontend ratification. It uses an exact `semantic strling 1.0;` selector,
explicit case intent, keyword-led leaf statements, and brace-delimited
composition. Regex operators, implicit concatenation, postfix quantifiers,
grouping punctuation, precedence, target flags, and emitter spellings are not
part of the language.

The ratified surface will cover every canonical Semantic IR node and member
variant with explicit wildcard/domain/repetition/lookaround intent, named-only
captures, completed-prior references, UTF-8 byte spans, closed string escapes,
stable source diagnostics, and canonical formatting rules. Target/profile
selection remains in `CompileRequest`; modules/imports and portability/safety
directives are deferred because their canonical linkage or source-policy models
do not exist.

Completion requires formal EBNF, a complete Semantic IR mapping catalog,
positive and negative authored fixture coverage for every production, stable
diagnostic coverage, content-addressed manifests, grammar/ambiguity checks,
specification-sovereignty mutations, canonical contract integration,
repository documentation consistency, Local, and a clean tree. This task does
not implement the parser or formatter.

The specification bundle now ratifies frontend identity `strling.semantic`,
dialect `1.0.0`, and source edition `1.0`. Its formal EBNF contains 55 reachable
productions with prefix-disjoint construct phrases and no precedence or implicit
concatenation. Seventeen mapping entries cover all 12 canonical node kinds, all
four character-set member kinds, and every governed semantic enum value.

Material nodes and captures receive deterministic, independent one-based
preorder identities that consumers treat as opaque; offsets, names, child
positions, hashes, and target capture numbers never become identity. Three
frontend-local schemas govern the language, mapping, and authored cases.
The 12 positive and 30 negative cases cover every grammar production in both
directions, every mapping, and all 26 fixture-required diagnostics; the
resource-limit diagnostic remains a synthetic boundary obligation. Ten
unsupported families are explicitly unavailable. The complete contract
fingerprint is
`sha256:463ec4ada9d89340fafccfce4fece6294d2b699617898c6413b4bd991948956f`.

The no-parser certifier and 14 mutation tests reject grammar reachability and
phrase ambiguity failures, missing mappings or fixture coverage, invalid UTF-8
offsets, stale manifests, and authority promotion. Canonical contract
aggregation includes this suite, and a new enforced architecture rule prevents
the frontend identity or implementation claims from entering canonical
semantic or target authority.

P13-T04 closes from clean corrected implementation commit
`3be9a678c80fb3a4bb2aeff460b5ffd20161b580`. The versioned bundle contains
three schemas, 55 reachable grammar productions, 17 complete Semantic IR
mappings, 27 stable diagnostics, ten explicit unavailable construct families,
12 positive cases, and 30 negative cases. Every production has positive and
negative authored coverage, every mapping has positive evidence, and all 26
fixture-required diagnostics have negative evidence; the resource-limit
diagnostic remains the documented synthetic parser-boundary obligation.

The formatter-normalized contract fingerprint is
`sha256:463ec4ada9d89340fafccfce4fece6294d2b699617898c6413b4bd991948956f`.
All 16 focused mutation tests and all 524 tooling tests pass. Canonical
contracts, architecture, governance, documentation across 156 files,
generated-artifact and public-contract integrity, formatting, lint, hygiene,
and patch checks pass. Local passes 26/26 with no failures, waivers,
unavailable, or incomplete operations, and the tracked tree is clean.

P13-T04 is `READY WITH RECORDED CARRY-FORWARD`. P13-T05 is next and will
implement the exact parser and canonical formatter in Rust as pure frontends to
the existing semantic kernel; the ratified specification, not that
implementation, remains the syntax and mapping authority.

## Semantic STRling Rust parser and canonical formatter

-   Status: Complete
-   Starting commit: `c1787e35b93d00dcca3ae81d11d5eda940f4618e`
-   Behavior change: Additive internal Rust frontend and explicit canonical
    compiler dispatch; no language-contract, target, binding, default, package,
    or release change
-   Task record:
    [`semantic-dsl-parser-formatter.yaml`](records/semantic-dsl-parser-formatter.yaml)
-   Readiness: Pending implementation and Local/Pull Request certification

P13-T05 consumes the immutable `strling.semantic@1.0.0` bundle certified by
P13-T04. The locked Rust surface is
`semantic_frontend::parse(&SourceDocument) -> ParsedSemantic` plus
`semantic_frontend::format(&ParsedSemantic) -> String`. Successful parses expose
one validated canonical `SemanticProgram` and retain private syntax evidence so
formatting can preserve comments and authored set-member order that canonical
IR deliberately does not retain.

The implementation will use a dependency-free, demand-driven lexer and
recursive-descent parser over the explicit 55-production grammar. It will
return the earliest reached UTF-8 byte failure with the frozen 27 STRL-DSL
identities, retain exact material spans/provenance, allocate independent
one-based material-node and capture preorder identities, and reject incomplete,
duplicate, forward, self, recursive, or unresolved capture uses before any
partial semantics enter the compiler.

Existing `normalization::normalize` remains the sole owner of sequence/choice
flattening, adjacent-text coalescing, set canonicalization, and validation. The
kernel will dispatch only explicit `strling.semantic` source documents into the
same semantic, analysis, diagnostics, portability, lowering, and serialization
pipeline. The frontend itself cannot select targets or depend on emitters,
bindings, legacy runtimes, filesystems, environment, network, packages, CLI, or
editors.

The canonical formatter will emit LF-only source, four-space blocks, shortest
integers, canonical Unicode escapes, stable comment order/placement, and one
final newline. Fixture, property, and robustness suites will cover all 12
positive and 30 negative authored cases, exact diagnostics/offsets and spans,
all governed resource limits, parse-format-parse semantic stability,
format-format idempotence, generated valid programs, and arbitrary-input
no-panic behavior before Rust, repository, Local, Pull Request, and clean-tree
certification.

During the first direct P13-T05 fixture run, the positive capture/reference
case and canonical example exposed a P13-T04 catalog contradiction: both use
`word` as an identifier, while the machine catalog incorrectly treated every
grammar keyword terminal as identifier-reserved. P13-T04 is narrowly reopened
to separate the complete keyword-terminal inventory from the contextual
identifier-reserved set. Declaration starters and construct-leading keywords
remain reserved (`sequence` retains explicit negative evidence); context-only
keywords such as `word` remain legal where the grammar is unambiguous. The
contract fingerprint and all T04 certification evidence will be renewed before
T05 implementation resumes.

The correction closes from clean commit
`4f05d5989643b6cc379bcebc694c04d864390f2d`. The machine catalog now separates
the complete grammar keyword-terminal inventory from the contextual
identifier-reserved set. Declaration starters and every construct-leading
keyword remain reserved; non-leading contextual terms such as `word` are valid
capture names, reconciling the canonical example and positive fixture without
weakening the negative `capture sequence` obligation.

The renewed contract fingerprint is
`sha256:463ec4ada9d89340fafccfce4fece6294d2b699617898c6413b4bd991948956f`.
All 16 focused tests and all 524 tooling tests pass. Canonical aggregation
retains three schemas, 55 productions, 17 mappings, 27 diagnostics, ten
deferrals, 12 positive cases, and 30 negative cases. Local passes 26/26 with no
failure, waiver, unavailable, or incomplete operation, and the tree is clean.
P13-T04 is again `READY WITH RECORDED CARRY-FORWARD`; P13-T05 may resume from
this corrected authority rather than carrying an implementation exception.

P13-T05 resumes from corrected P13-T04 recertification commit
`2865ad33472de598f152d919123db22ef2484bb1`. Its locked design commit remains
`b57f097e3fb797f36a102ae3089c2168d5ee57df`; the preserved Rust work will be
replayed against contract fingerprint
`sha256:463ec4ada9d89340fafccfce4fece6294d2b699617898c6413b4bd991948956f`.
No parser exception is needed: contextual `word` identifiers and reserved
construct-leading `sequence` identifiers now follow one internally consistent
authority.

P13-T05 closes from reviewed commit
`ce05ed899507355ede431c545d661dcccfe0fdc0`. The complete ratified grammar now
has one bounded dependency-free Rust parser and canonical formatter. All 12
positive and 30 negative authored fixtures pass with exact diagnostic identity,
phase, category, UTF-8 location, and material spans. Property evidence covers
512 generated valid programs, 2,048 deterministic arbitrary UTF-8 inputs, all
seven governed resource families, nested comment placement, canonical
idempotence, semantic equivalence, capture names, and preorder identities.

Explicit `strling.semantic@1.0.0` requests now enter the same normalization,
analysis, diagnostics, portability, lowering, and serialization pipeline as
the other canonical inputs. The frontend retains only private presentation
evidence and has no target, emitter, binding, runtime, filesystem, network,
package, default, or specification-writing authority. The reviewed migration
baseline changes only canonical-boundary and self-fingerprints; all corpus,
route, source-observation, historical-peer, and classification evidence remains
unchanged.

All 377 Rust tests and 528 tooling tests pass. Core mapping validates 11 schemas
and 108 fixtures; documentation integrity passes 157 files and seven executable
examples. Local passes 26/26 with no failure, waiver, unavailability, or
incomplete result. Pull Request records 44 passed, zero failed or waived, and
only inherited Ruby Bundler drift and missing Swift availability. A fresh
archive of the clean commit reproduces all 24 focused Rust tests, four
architecture mutations, and core contract validation.

P13-T05 is `READY WITH RECORDED CARRY-FORWARD`. P13-T06 is next and owns the
complete cross-frontend convergence corpus plus canonical tutorial hierarchy;
no tutorial, default, package, version, tag, upload, or publication action was
taken here.

## Frontend convergence and canonical tutorials

-   Status: Complete
-   Starting commit: `f6dacb380f826207518f8285306fb5f922078aa5`
-   Behavior change: Test evidence and public documentation only; no semantic,
    target, runtime, binding implementation, public API, package, or release
    behavior
-   Task record:
    [`frontend-convergence.yaml`](records/frontend-convergence.yaml)
-   Readiness: `READY WITH RECORDED CARRY-FORWARD`

P13-T06 locks an eleven-case convergence denominator spanning authored Semantic
STRling, native Rust Simply, TypeScript and Python Simply Preview, source-less
Semantic IR, and nine structurally equivalent regex-compatible import cases.
Completeness is derived fail-closed from all 15 Simply operations, all 17
Semantic mapping entries, and all 38 accepted or compatibility-only legacy
features across ten families. The 13 rejected legacy features retain the
existing `unsupported_legacy_behavior` disposition; unresolved differences are
forbidden.

Semantic comparison alpha-renames frontend-specific node and capture identities
and removes only source/provenance/location metadata. Semantic values, reference
relationships, facts, diagnostic content, portability decisions, rewrite
identities, target options, artifact pattern and flags, and compile outcomes
remain compared. Public documentation migration is bounded to the root and
developer entry points, canonical tutorial/testing examples, frontend
references, architecture wording, and four binding README passages that still
call regex-compatible input the canonical DSL. Dedicated import/migration and
normative dialect documentation remains intact.

P13-T06 closes from reviewed commit
`7fe029c9b233e29974a95537def20b051cc6355a`. All eleven convergence cases,
15 Simply operations, 17 Semantic mappings, 38 accepted or compatibility-only
legacy features across ten families, 13 governed rejections, three exact
profiles, and three host routes pass with zero unresolved entry. Canonical
Rust execution performs 132 deterministic route/profile comparisons while the
TypeScript and Python Preview adapters reconstruct all shared builder requests
exactly.

All 379 Rust tests, 542 tooling tests, 970 TypeScript tests, and 796 Python
tests pass. Documentation integrity validates 158 Markdown files and seven
executable examples. Exact PCRE2 10.42/10.43, Node.js 22.23.2, and CPython
3.11.15 certification passes; the 20-case shared corpus and 100-entry
portability matrix retain zero semantic divergences and zero unresolved
entries. The three-repeat migration differential has zero determinism
mismatches and no blocking unresolved replacement.

Local passes 26/26. Pull Request records 44 passed and only inherited Ruby
Bundler drift plus missing Swift. Full records 76 passed, zero failed,
incomplete, or waived operations, and seven explicit unavailable results for
dependency-risk scanning plus Ruby lint/build/test and Swift
typecheck/build/test. A fresh no-hardlink clone of the reviewed commit remains
Git-clean and reproduces all Rust/tooling, focused Preview, documentation,
contract, architecture, governance, shared-corpus, and portability checks.

P13 and P13-T06 are `READY WITH RECORDED CARRY-FORWARD`. P14-T01 is next and
owns the complete Essential 5 and standard-library guarantee audit. No
compiler semantics, target behavior, binding implementation, public API,
package, default, version, tag, upload, publication, or product redesign was
changed here.

## Standard-library guarantee audit

-   Status: Complete
-   Starting commit: `82cf9e214b6747a1e831b529c699cda108cf8486`
-   Behavior change: Guarantee metadata, public claim wording, and editor
    reference labels only; no helper construction, emitted regex, match
    outcome, compiler, target, diagnostic, package, or public API behavior
-   Task record:
    [`stdlib-guarantee-audit.yaml`](records/stdlib-guarantee-audit.yaml)
-   Readiness: `READY WITH RECORDED CARRY-FORWARD`

P14-T01 inventories all five Essential helpers, eight behavior variants, 17
binding spellings, 19 implementation/header sources, shared fixtures, target
dependencies, and cited standards. Every current helper is retained under its
existing public name as `lexical_shape` with
`behavior_preserved_claim_narrowed` compatibility. No helper normalizes,
parses, proves semantic validity, or establishes complete standards
conformance. Stronger structural or semantic validators must be separately
named additive surfaces.

The ratified machine audit and 40-case fixture corpus cover accepted and
rejected shapes, known semantic false positives, known standards false
negatives, policy nonclaims, and target-dependent digit behavior. Seventeen
focused tests fail closed on missing coverage, semantic strengthening,
compatibility reclassification, erased boundary evidence, and stale audit
pointers. Public binding comments, compatibility manifests, and editor cards
now state lexical inspiration or exact subset scope; UUID references use RFC
9562, and editor cards label citations as `Reference scope` rather than
`Standard`.

All 547 tooling tests and 409 LSP tests pass. Fourteen canonical binding suites
plus core pass, including all 970 TypeScript tests and the Rust Essential and
conformance suites. Ruby's lock-selected full suite passes 611 tests. An
isolated Java copy passes all 15 Essential tests after neutralizing only three
unrelated pre-existing `serialVersionUID` warnings that the checked-in POM
promotes to errors; the repository Java command therefore remains explicit
carry-forward, and Swift remains unavailable on this host. Direct Python and
Node.js 22.23.2 assertions prove the audited target-specific `\\d` behavior.

The migration baseline candidate is identical across two independent
three-run captures. Corpus identities, case counts, the canonical boundary,
route coverage, and contract identity remain unchanged; only four
provenance-derived fingerprints are renewed. Local passes 26/26 from clean
commit `138756328fa0ecc13a25d2cc95c7121c0c2cfe8b` and again in a provisioned
fresh no-hardlink clone, with no failed, waived, unavailable, or incomplete
operation and a clean final tree.

P14-T01 is `READY WITH RECORDED CARRY-FORWARD`. P14-T02 is next and owns the
canonical standard-library registry and schema, using this audit as its sole
input for helper identities, variants, guarantee levels, standards scope,
compatibility dispositions, and generated-surface requirements. The current
`spec/stdlib/registry.json` remains a historical compatibility manifest until
that task replaces it; no package, version, tag, upload, publication, or
release action was taken here.

## Canonical standard-library registry

-   Status: In progress
-   Starting commit: `c3d67ac20690a63935699eaa913475fa2126a7c0`
-   Behavior change: Canonical metadata authority, validation, and generated
    projection ownership only; no helper construction, emitted regex, match
    outcome, target, diagnostic, package, or public API behavior
-   Task record:
    [`canonical-stdlib-registry.yaml`](records/canonical-stdlib-registry.yaml)
-   Readiness: `READY WITH RECORDED CARRY-FORWARD`

P14-T02 establishes
`spec/stdlib/registry/1.0/registry.json` as the single normative metadata
source for five helpers, eight variants, seventeen host-binding maps, and forty
audited edge cases. Stable helper IDs are separate from host-language names.
Every helper records its exact logical signature, lexical construction
identity, guarantee, standards scope, non-guarantees, target profiles and
constraints, Unicode/text assumptions, lifecycle and migration data,
documentation metadata, examples, diagnostics policy, and evidence.

A closed schema plus cross-object validation rejects duplicate identities or
names, unresolved references, missing examples or evidence, unsupported target
constraints, incomplete audit or binding coverage, cyclic or ambiguous
derivations, stale fingerprints, and nondeterministic serialization. Nine
controlled negative fixtures prove those failure classes. The initial registry
fingerprint is
`sha256:07065e1cb66d3277e4f482df0d9cf91c94be0417e05f1b157f15658ae504a382`.

The existing Essential fixture manifest and flat editor registry are now
deterministic, enforced, non-normative projections from the authored registry.
They remain compatible inputs for current bindings and language intelligence;
T03 still owns canonical Rust implementations, and T04 still owns broad
binding/frontend/documentation generation.

P14-T02 closes from reviewed implementation commit
`ee8f526a487cc82d1ff9bd6498efe8240b9d537b`. All 557 tooling tests and 409 LSP
tests pass. Local passes 26/26 from that clean commit and from a separately
provisioned no-hardlink clone, with no failure, waiver, unavailable, or
incomplete operation and clean trees. Fourteen canonical language suites plus
core pass; locked Ruby Essential passes 15 tests and 67 assertions, while an
isolated Java copy passes all 15 Essential tests after neutralizing only the
three unrelated `serialVersionUID` warning escalations outside the repository.

Pull Request passes 42 operations. Its only failures are those inherited Java
warnings promoted by `-Werror`; root Bundler selection and missing Swift remain
explicit unavailable results. Projection-normalized comparison proves all
helper names, regexes, fixtures, descriptions, reference wording, snippets,
keywords, and naming metadata remain unchanged except for explicit generated
authority descriptions and canonical construction references.

P14-T02 is `READY WITH RECORDED CARRY-FORWARD`. P14-T03 is next and owns
canonical Rust Semantic IR/builder implementations plus any separately named
strict validators required by registry guarantees. P14-T04 retains broad
binding, frontend, adapter, documentation, and portability-surface generation.
No package, default, version, tag, upload, publication, or release action was
taken here.

## Canonical standard-library semantics

-   Status: Complete
-   Starting commit: `6860b16d8e85bef3856303b95a7f28d95726aed0`
-   Behavior change: One canonical Rust semantic implementation for all
    registered helper variants plus exact target-runtime evidence; no public
    binding exposure and no semantic-validator claim
-   Task record:
    [`canonical-stdlib-semantics.yaml`](records/canonical-stdlib-semantics.yaml)
-   Readiness: `READY WITH RECORDED CARRY-FORWARD`

P14-T03 implements five lexical-shape helpers and eight variants through one
crate-private Rust builder source, with closed Semantic IR, Simply, and
Semantic DSL forms. The 117-record evidence denominator contains 40 audited,
60 compatibility, and 17 stress records. It deliberately retains known
semantic false positives and standards false negatives because registry 1.0.0
authorizes zero semantic validators; lexical shape is not semantic validity.

Exact two-pass execution on the governed Node 22.23.2, CPython 3.11.15, PCRE2
10.42, and PCRE2 10.43 runtimes passes all 580 applicable profile applications;
five Python bytes applications remain explicitly not applicable. All 575
tooling tests, Rust 1.75 all-target tests and warning-denied Clippy, public and
generated contracts, governance, formatting, static analysis, and the
three-run migration differential pass. The task closes through certification
commit `cde140daea2fc173f3822685c772916fc7d5f29d` and documentation closure
`2058190efbaffd91fad84bf5f1ef26004f7dc2e3`.

P14-T03 is `READY WITH RECORDED CARRY-FORWARD`. P14-T04 owns generated public
surfaces and adapter exposure; missing Windows ecosystem tools and inherited
dependency-risk state remain explicit without waiver.

## Generated standard-library surfaces and portability

-   Status: Complete
-   Starting commit: `adab09bcf5569e454958d080fd70bd33f3c46dc6`
-   Behavior change: Additive Simply 1.1 helper transport, supported canonical
    Rust/TypeScript/Python surfaces, and generated documentation, metadata, and
    portability views; no new helper semantics or target expectations
-   Task record:
    [`stdlib-surface-convergence.yaml`](records/stdlib-surface-convergence.yaml)
-   Readiness: `READY WITH RECORDED CARRY-FORWARD`

P14-T04 derives fourteen checked outputs from one canonical registry and the
sole Rust implementation. The generated denominator is five helpers, eight
variants, seventeen binding spellings, two supported Preview adapters, fifteen
compatibility-only bindings, five target profiles, forty portability cells,
580 executable applications, five explicit not-applicable applications, and
zero semantic validators. The output fingerprint is
`f8f165ccd26970e8b0d2e9e5db907fa8fd9d8806b505011794a4c8e1268ef132`.

Simply 1.1 adds one `stdlib_helper` operation while 1.0 remains immutable.
Rust, TypeScript Preview, and Python Preview delegate helper identity and
parameters through the canonical transport; no generated wrapper or document
contains an independent regex or validator. Cross-frontend convergence proves
all eight variants are equivalent after removing only representation identity
and provenance.

The reviewed implementation commit is
`7da56c7134f60747cfa5f467ef8a73c1d009c02b`. Certification commit
`6d0789af53e076497baa8dac673c3b108e839f5d` also repairs deterministic Windows
projection execution by preserving the bounded MSVC linker, SDK-library, and
temporary-directory environment. All 583 tooling tests, Rust all-target tests,
Rust 1.75 warning-denied Clippy, affected public snapshots, generated surfaces,
documentation, governance, affected-file formatting, and the three-run migration
differential pass.

At the clean certification commit, Local records 10 passed, 2 failed, and 14
unavailable operations; Pull Request records 10, 2, and 34; Full records 11,
3, and 70. The remaining failures are repository-wide Go-dependent wrappers
and inherited dependency-risk license/waiver drift. Exact-runtime and missing
ecosystem operations remain unavailable, never waived or labeled passing; the
unchanged exact T03 portability evidence supplies the task's target proof.

P14 and P14-T04 are `READY WITH RECORDED CARRY-FORWARD`. P15-T01 is next and
owns the structured semantic explanation model. No package, default, version,
tag, upload, publication, or release action was taken here.

## Canonical VS Code and tooling packaging

-   Status: Complete
-   Starting commit: `76050f62204544c3ded857bd28080803aeeedc7b`
-   Behavior change: Reproducible platform-targeted editor packaging,
    activation, runtime discovery, and lifecycle proof only; no language,
    target, diagnostic, rewrite, standard-library, binding, or publication
    behavior
-   Task record:
    [`lsp-packaging-certification.yaml`](records/lsp-packaging-certification.yaml)
-   Readiness: `READY WITH RECORDED CARRY-FORWARD`

P16-T05 replaces the incomplete extension assembler with a cross-platform,
locked package builder and a closed 21-file payload. The only STRling semantic
engines in that payload are `strling-kernel` and `strling-editor-core`; authored
Python modules and local protocol subsets remain transport/projection adapters.
The package includes exactly three governed runtime resources and excludes the
legacy Python binding, downloaded Python dependencies, source-tree fallbacks,
tests, caches, build trees, user-home synchronization, and repository metadata.

Package contract
`sha256:3387c3aa55afdb2bee3c987a0e92038fc5a0caebbd1826709ba907f701c10945`
has a 72-case verification denominator across four targets, 21 selectors, ten
features, twelve failures, three lifecycle operations, six identity groups,
twelve mutations, and four reproducibility properties. The implementation
commit is `b8b2d54cffb9d86093205964de2a2193314f80fc`.

At integration commit `9459b41562b78ab2a7557cef89dae0859ab784bf`, two clean
Windows builds reproduce all 21 payload files at
`sha256:f2d1a60e1f3c87fc2df1788ba1689b9890e36049dae0dc289999647f078d042d`.
The 23 normalized VSIX entries fingerprint to
`sha256:a272fc108e805ed4bed570e9afc2882cf8b521cad532a5ccf43ee1ed8e3f8914`
and the exact VSIX digest is
`sha256:a20c30850964c68e70542688775c4aeb55b2481655897901b6d1d5abdb6d5b72`.
Both canonical processes, all ten LSP feature families, canonical CLI/editor
identity, and isolated install, upgrade, and uninstall pass.

Rust all-targets passes, as do all 566 LSP tests, 645 tooling tests plus 699
subtests, the reviewed 44-observation migration differential, governance,
architecture, documentation, content/workflow security, task-owned generated
verification, and patch integrity. Local records 12 passed, two failed, and 14
unavailable operations; Pull Request records 12, two, and 35; the
network-restricted Full profile records ten, nine, and 70, while its clean LSP
package certification passes. Missing Go, denied network metadata egress,
sandboxed wrappers, governed Node/Python/Ruff probes, and optional binding
toolchains remain exact non-passing evidence.

P16 and P16-T05 close as `READY WITH RECORDED CARRY-FORWARD`. Linux x64,
macOS x64, and macOS arm64 retain exact native runner mappings and artifact
retention but remain unavailable and unclaimed until remote CI executes them.
P17-T01 is next and owns the stable serialized interop, C ABI, memory/error,
threading, and WASM foundation. No package was published, signed, tagged, or
uploaded.

## Canonical interop, C ABI, and WebAssembly foundation

-   Status: Complete
-   Starting commit: `d4189e039810532c8447aeeffb18a8fc7a165e29`
-   Behavior change: Additive serialized, native C, and raw WebAssembly
    interop surfaces over the canonical compiler; no language-semantic,
    target-profile, host-package, or publication change
-   Task record: [`interop-foundation.yaml`](records/interop-foundation.yaml)
-   Readiness: `READY WITH RECORDED CARRY-FORWARD`

P17-T01 selects the previously deferred host boundary as
`strling.interop@1.0.0`, `strling.c-abi@1.0.0`, and
`strling.wasm-abi@1.0.0`. Four stateless operations carry existing canonical
compiler, exact-profile, and Simply values as bounded compact UTF-8 JSON.
Idiomatic check surfaces remain canonical compile requests rather than a second
semantic validator.

The reference bridge is contained under `bindings/interop`, outside the
kernel's `#![forbid(unsafe_code)]` boundary and inside the governed top-level
adapter root. Native ownership uses one zeroable library-owned byte descriptor,
native calls are reentrant and concurrent, and unwind cannot cross C. Raw
`wasm32-unknown-unknown` uses an explicit eight-byte linear-memory descriptor,
per-instance serialized calls, no host capabilities, and instance isolation
rather than an unsupported unwind promise.

The frozen 77-case denominator has contract fingerprint
`sha256:1dc0797483c2b87a4653411c5d8abc0e4f2681fd3c82aa70ed8da3f72db585c5`
and evidence fingerprint
`sha256:5419a7a3f29525cfa6c4c7ddf2227d7c6700bf8cd73c5b27e48b8ef006964e90`.
Native proof covers ownership, unwind containment, 32-thread determinism, 517
bounded arbitrary-byte lengths, five structured mutations, and 256 ownership
cycles. Governed x86_64 Linux proof passes six cargo-fuzz targets at 10,000
runs each, AddressSanitizer, LeakSanitizer, and the raw-WASM two-instance memory
lifecycle. The Linux evidence file SHA-256 is
`352110d0d802c1359f08a6c4cd54265616b4f423fea7bb12aadcd882ad595b21`.

The exact fuzz-only `libfuzzer-sys` 0.4.13 license disposition is enforced by
selected-root reachability, and the runtime graph excludes it. The authorized
historical Rust lock update moves `crossbeam-epoch` 0.9.18 to 0.9.20 and clears
RUSTSEC-2026-0204 without manifest, source, or API work. Live risk records 17
passed, 28 unavailable, four waived, zero failed, and zero incomplete checks.

At clean implementation commit
`e124cfd2710df6e9c8f9f0423c79ac49ec8f5ad7`, Local passes 33/33. Pull Request
records 43 passed, zero failed, and 11 unavailable. Full records 59 passed,
zero failed, and 38 unavailable across 97 operations. Exact PCRE2 libraries,
legacy dependency scanners, and absent host toolchains remain explicit
carry-forward rather than certified results. The final evidence commit is
`b0eecd19b7f4680f6c90f3fecde92df5c11eddf7`. No package, branch, tag, upload,
publication, or release action was taken.

## Canonical Rust facade and C/C++ adapter migration

-   Status: Complete
-   Starting commit: `b0eecd19b7f4680f6c90f3fecde92df5c11eddf7`
-   Behavior change: Curated Rust facade plus thin C/native and C++ RAII
    adapters; explicit compatibility deprecation/removal and canonical target
    routing, with no language-semantic or interop-ABI change
-   Task record:
    [`rust-c-cpp-adapter-migration.yaml`](records/rust-c-cpp-adapter-migration.yaml)
-   Readiness: `READY WITH RECORDED CARRY-FORWARD`

P17-T02 locks Rust as a typed facade over the public kernel, C as a consumer of
`strling.c-abi` v1, and C++ as RAII over C/native declarations. Canonical APIs
require an exact target profile. Deprecated targetless compatibility calls may
use only a generated, disclosed `pcre2-10.43` profile; this is not a new
repository default.

The starting packages contain roughly 22,000 lines across 93 Rust, C, C++, and
header sources, including independent parsers, ASTs, IRs, validators, hint
engines, compilers, emitters, and Simply implementations. C has one enforced
legacy header snapshot; C++ and Rust extraction remain transitional.

CP2 freezes 58 cases across public API, canonical parity, compatibility
success/refusal, ownership/error, concurrency/RAII, Unicode,
build/install/package, architecture/deletion, and four native platforms. The
contract fingerprint is
`sha256:0c6189b30042c50481228314ca35f69e55c9536288aad7299dce5c4816770924`
and the evidence fingerprint is
`sha256:d95581ae6bb95b5250fc5ffade82bba932ebb3a01276c406afe8f3db19080b70`.
The generated legacy baseline reproduces 28 public inputs and 35 semantic-copy
files from `b0eecd19`, with fingerprint
`sha256:bde6ddf77502663e13dd1957f9daefba82cda07c033ad029193467d380d17d4c`.
Eleven mutation tests prevent denominator shrinkage. CP3 must implement this
closed evidence set before any removal is certified.

CP3 replaces the Rust binding-owned compiler pipeline with a curated facade
over `strling-kernel`, C with a native-ABI adapter, and C++ with a C++17 RAII
facade over C/native. All 35 frozen semantic-copy paths are absent. The exact
Rust 1.70 MSRV passes, release C tests pass 2/2, combined C++/C tests pass 4/4,
fresh isolated C11 and C++17 consumers compile and execute, and 512 calls across
eight threads prove the migrated ownership/concurrency routes. All eight
standard-helper variants delegate through the canonical registry without
turning the five lexical-shape helpers into semantic validators.

At integration commit `5c2133f74ec2dbc8dcf156b1b33164d2425cbb4a`, the
executable adapter denominator passes all 58 cases, ten families, eight runtime
cases, and sixteen cross-binding comparisons. Public contracts, generated
authority, architecture fitness, documentation, repository quality, migration
differential, and live RustSec/license checks pass. The exact generated
TypeScript change is limited to the Program-Owner-authorized standard-library
source fingerprint and its public snapshot.

Local records 25 passed, three failed, and five unavailable operations; Pull
Request records 38, three, and 20; Full records 50, four, and 47. Every
T02-owned operation passes. Missing governed Node 22 and Go, other binding
toolchains, exact PCRE2/CPython hooks, and Windows-host inability to re-run the
Linux wrapper sanitizer remain explicit, unwaived carry-forward. P17-T01's
governed Linux ASan/LSan evidence continues to cover the underlying native ABI.

The final documentation/evidence commit is
`e6c87a1ae2fed088bff7ec22653fccf5d00becde`. P17-T03 is next and owns
TypeScript/WASM and Python/native migration. No package, branch, tag, upload,
publication, or release action was taken.

## Canonical TypeScript/WASM and Python/native adapter migration

-   Status: Complete
-   Starting commit: `e6c87a1ae2fed088bff7ec22653fccf5d00becde`
-   Behavior change: Thin TypeScript/raw-WASM and Python/native adapters with
    explicit public/package compatibility dispositions; no language-semantic,
    target-profile, interop-ABI, support-tier, or publication change
-   Task record:
    [`typescript-python-adapter-migration.yaml`](records/typescript-python-adapter-migration.yaml)
-   Readiness: `READY WITH RECORDED CARRY-FORWARD`

P17-T03 locks TypeScript to `strling.wasm-abi` v1 and Python to
`strling.c-abi` v1. Hosts own loading, bounded byte transfer, lifecycle, JSON
transport, result projection, ergonomic Simply request construction, and
package mechanics only. Neither adapter may retain or fall back to a parser,
compiler, IR, validator, hint engine, target emitter, standard-helper semantic
implementation, or ambient target selection.

The starting denominator is 40 authored sources and approximately 15,260
lines: 19 TypeScript files/6,658 lines and 21 Python files/8,602 lines. Enforced
public evidence has 461 TypeScript declaration symbols, 11 TypeScript package
entrypoint fields, and 95 Python symbols. Baseline suites pass 972 TypeScript
tests and 798 Python tests. The TypeScript dry-run package contains 38 entries,
but its declared `./core`, `./simply`, and `./emitters/pcre2` paths do not match
the emitted layout. Host Node 24.4.1 is outside governed `>=22,<23`, and this
host lacks Python build backend modules, so those runs establish starting facts
rather than governed Node or wheel certification.

Root namespaces, mechanically representable Simply builder ergonomics,
canonical Preview transport, generated helper identities, and canonical
request/result data remain intended surfaces. TypeScript `./core` and
`./emitters/pcre2`, local node/IR shapes, compiler-stage methods, Python local
semantic modules, and simulated `Pattern.exec` behavior are explicit
compatibility/removal decisions rather than semantics to preserve. Exact
targetless compatibility may use only a disclosed generated `pcre2-10.43`
profile; new canonical APIs require an exact supplied profile.

The existing migration differential has 24 TypeScript and 20 Python source
observations. CP2 must freeze their starting-commit identity and isolated
historical reproduction route before product migration. Historical copies may
remain only as non-normative evidence under `tooling/legacy_reference`; they
must never execute as a product fallback. CP2 must also freeze every public
export, exception, sync/async boundary, artifact, package path, compatibility
disposition, clean-install, lifecycle, concurrency, error, Simply,
standard-library, cross-binding, architecture, and deletion case with
shrinkage resistance.

The Program Owner's fingerprint authorization remains limited to mechanically
derived TypeScript standard-library fingerprint/public-snapshot output from the
prior Rust ownership-path cleanup. It does not authorize a hidden semantic,
behavioral, API-shape, or implementation change. P17-T03's reviewed adapter
surface changes require their own task evidence. No push, publication, package
version, support-tier decision, interop v2, or later binding migration is
authorized.

CP2 freezes 72 cases across twelve families, thirteen runners, four interop
operations, and four runtime positions. The canonical contract fingerprint is
`sha256:0c6189b30042c50481228314ca35f69e55c9536288aad7299dce5c4816770924`
and the evidence fingerprint is
`sha256:545d73f3b75199592657c37ae1da83e51f27dd8649a49b22e81f0ad2a7b627cc`.
Thirteen mutation tests prevent shrinkage.

A registered compatibility baseline fingerprints 18 public/package inputs and
31 semantic-copy paths, and embeds 45 task-start source, manifest, lock, and
compiler-config inputs. Its fingerprint is
`sha256:6a1ac87338417c442e0a2abfb3dad289d60e71f68a83f7850fd41e23d43b8191`.
Historical runners now materialize only that non-normative bundle rather than
mutable product source. Forty-three Node tests, 29 Python/launch tests, and all
44 historical cases pass; three-run migration differential remains
deterministic with zero blocking canonical replacements and six evidence-only
historical peer differences. CP3 must implement the closed adapter denominator
before any product-local semantic path is certified retired.

CP3 replaces both product semantic copies with canonical host adapters. The
TypeScript package executes the raw WebAssembly ABI and the Python package
executes the native C ABI. All 31 frozen semantic-copy paths are absent, while
the 45-source authenticated task-start bundle remains non-normative historical
evidence. TypeScript passes 18 focused tests and a 27-entry package proof;
Python passes 22 focused tests and isolated CPython 3.12/3.13 wheel/native
proofs. Chrome 151 executes the browser-safe WASM path offline.

At implementation commit
`6e770ec80dda71b61780ec1caebb2f972a3aa32e`, three live 44-action cross-host
runs produce identical results. The 44-observation migration differential has
zero blocking replacements and six evidence-only peer differences. Exact
affected public/generated surfaces, canonical contracts, controlled historical
runners, governance, security integrity/content, documentation, formatting,
and the corrected 80-test focused suite pass. Local, Pull Request, and Full
profiles record every repository-wide pass, failure, and unavailable tool
exactly; every T03-owned operation passes directly.

The final evidence commit is
`29158b75f78e7eb272d07374d6447c74c01c6f9c`. Exact Node 22, CPython 3.8/3.11,
Go, Unix aliases, optional ecosystems, repository-wide scanner gaps, and
network-restricted profile wrappers remain explicit carry-forward rather than
passing claims. P17-T04 is next and owns the shared Java/Kotlin bridge and JVM
package/runtime migration. No package, branch, tag, upload, publication, or
release action was taken.

## Canonical Java/Kotlin JVM adapter migration

-   Status: Complete — integration and certification
-   Starting commit: `29158b75f78e7eb272d07374d6447c74c01c6f9c`
-   Behavior change: Thin Java/Kotlin facades over one shared JVM/native bridge
    with explicit public/package compatibility dispositions; no language-
    semantic, target-profile, interop-ABI, support-tier, or publication change
-   Task record:
    [`jvm-adapter-migration.yaml`](records/jvm-adapter-migration.yaml)
-   Readiness: `READY WITH RECORDED CARRY-FORWARD`

P17-T04 supplies one semantic-free `strling-jvm` artifact using pinned JNA
5.19.1 to map the existing `strling.c-abi` v1. Java and Kotlin depend on that
same artifact and may not carry separate JNI, JNA, Panama, subprocess, socket,
parser, compiler, IR, validator, hint, emitter, helper-semantic, or fallback
routes. Explicit native loading, bounded byte transport, same-descriptor
release, JSON projection, lifecycle, host errors, and packaging belong to the
bridge; all semantics remain in the canonical Rust kernel.

The frozen starting denominator contains 47 production sources/8,549 lines and
12 test sources/2,151 lines. The exact 70-file package tree fingerprints to
`sha256:3512df75e0ccde7f5a958ec4c6a7ff9329177ba13404f1e976c86a4b1730ed3d`.
The 35 Java/Kotlin core and emitter semantic-copy paths fingerprint to
`sha256:e023c47d5dbe9ff63870d04f46d4c0005f4e553398ef21a14ff0aeaed6975a9e`.
All 35 are absent from product packages. Exact snapshots now contain 45
shared-JVM, 104 Java, and 221 Kotlin symbols. The generated nine-package graph
fingerprints to
`sha256:cddff562833398adcae54ecbb0f4fa1034ad4dc74cb93ed8c606170967c0f072`;
JNA selects Apache-2.0, Jackson is remediated to 2.18.9, and a live OSV query
returns zero affected coordinates.

Temurin JDK 11, 17, and 21 pass the 13-test shared bridge and seven-test Java
and Kotlin suites. Three native parity runs fingerprint to
`sha256:a06e53b762a6f44ec75d56ae67ddec46176d50f20737f880acd8b0262581f8d3`.
Three product JARs contain no native or semantic-copy payload and two fresh
consumers pass. Windows x86_64 is the sole executed platform row; no native
classifier is advertised. Repository profiles preserve unrelated unavailable
Windows toolchains and global public-contract extraction limits exactly. No
package publication, branch push, release, tag, upload, support-tier change, or
interop v2 occurred.

## Canonical C#/F# .NET adapter migration

-   Status: In progress — verification design and evidence complete
-   Starting commit: 352d7c2547a58f692a709e464b458bf83103b09c
-   Behavior change: None through CP2; the task locks a future breaking
    replacement of binding-owned .NET semantics with canonical native adapters
-   Task record:
    [dotnet-adapter-migration.yaml](records/dotnet-adapter-migration.yaml)
-   Readiness: NOT READY

P17-T05 selects the C# STRling assembly as the sole built-in .NET
NativeLibrary/load-export substrate over strling.c-abi v1. The
STRling.FSharp assembly will depend on that package and may own only idiomatic
F# projections. The historical F# compiler assembly is also named STRling and
cannot coexist as the shared substrate; the currently separate
STRling.FSharp project builds no public type because Api.fs is not included.
CP2 must freeze both historical surfaces before consolidating them.

The clean 50-entry C#/F# tree fingerprints to
sha256:82633270ef02d21d267724a90dac9a92134cbd51eb811fffb31c2007a75d947f.
Its 32 production sources contain 4,462 lines. Eighteen closed semantic-copy
paths contain 4,080 lines and fingerprint to
sha256:fa3a2ab366719e9e4e93d5f7b0f4ca1fd502bf3521447cfd000d5c7f9fa7f7df.
On .NET SDK 9.0.302/net9.0, the historical C# and F# compiler suites pass
625 and 616 tests respectively; the incomplete secondary F# wrapper test
project fails at compile time and is recorded as debt.

The contract requires absolute-path or exact certified RID native resolution,
ABI-before-execution, bounded strict UTF-8/JSON transport, same-descriptor
release, IDisposable lifecycle, concurrent reentrancy, stable host errors, and
canonical response preservation. Public package IDs and idiomatic namespaces
remain compatibility inputs, while Core AST/IR/parser/compiler/emitter/hint
semantics and implicit targetless PCRE2 compilation are intentional retirement
candidates. No product source, package, version, support tier, native asset,
push, publication, release, or upload changes through CP2.

CP2 freezes 72 cases across twelve families and eleven runners. The exact
contract, evidence, and authenticated baseline fingerprints are
sha256:0c6189b30042c50481228314ca35f69e55c9536288aad7299dce5c4816770924,
sha256:0cc397456a771e2171594218f78f66086a4fa3bc2913963dab8794337e2906db,
and sha256:12034b0723bec7154da0eecf3f93b6e4e608fc488674ec43363a0703367574f2.
The baseline embeds all 50 task-start files and locks 26 public/build inputs
plus all 18 semantic-copy paths. Exact isolated Release snapshots contain 487
C# symbols across 48 types and 479 F# symbols across 54 types and both
task-start assemblies. SDKs 9.0.120, 9.0.200, and 9.0.302 each pass the
unchanged 625-case C# and 616-case historical F# suites; the incomplete wrapper
remains explicit debt. Nine shrinkage tests and 28 public-contract tests pass.
