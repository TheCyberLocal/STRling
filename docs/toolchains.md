# Deterministic toolchains and quality commands

## Authority and scope

`toolchain.json` is the authoritative inventory for repository engineering
environments, executable version policy, language-specific commands, capability
states, and relevant manifests, lock files, and configuration files. This
document explains that machine-readable contract; it does not duplicate command
arguments or version values as a second source of truth.

`governance/static-analysis.json` is authoritative for analyzer selection,
warning disposition, suppression inventory, and bounded transition conditions.
Analyzer executable versions and canonical commands remain governed by
`toolchain.json` or the lock/manifests named by that policy.

The root `./strling` command is the canonical quality interface for developers,
automation, continuous integration, and later release certification. Language
tools remain responsible for formatting, analysis, compilation, and testing.
The root command only selects targets, validates declared prerequisites,
dispatches configured commands, propagates results, and reports capability
state.

The inventory covers the root repository tooling, the language-server tooling,
and all 17 binding environments: C, C++, C#, Dart, F#, Go, Java, Kotlin, Lua,
Perl, PHP, Python, R, Ruby, Rust, Swift, and TypeScript.

## Resolution policy

Every entry in `tools` uses one resolution model:

-   `exact`: only the declared version is accepted.
-   `constrained`: an installed version must satisfy the declared bounded or
    minimum-supported range.
-   `repository_managed`: the repository file named by the entry resolves the
    version, such as a lock file or wrapper.
-   `deferred`: the environment currently supplies the capability and the
    absence of a defensible version contract is recorded with a rationale.

An executable being present on `PATH` is not itself a version policy.
Constrained and exact entries are checked before governed commands execute.
Repository-managed dependencies must be installed with the command already
declared for the component, such as `npm ci`, `composer install`, or
`bundle install`. Deferred entries are transitional and must remain visible
in environment reports; they are not described as deterministic.

The Bash and Python versions used by the root command are governed in the same
file. A component's `runtime` and `required_bins` values reference tool IDs
from the top-level `tools` inventory. Version policy is therefore declared
once and reused by every component.

Before a configured quality command executes, the coordinator probes the
declared root and component tools. A missing executable, failed or unrecognized
version probe, or hard version mismatch returns `unavailable` and prevents the
language command from running. A deferred tool is allowed but reported with its
rationale. A version outside the supported range is allowed only when it also
matches a separately bounded `transitional_version`; that result is reported
as `transitional`, never `compatible`.

Use the same root interface to inspect an environment:

```text
./strling environment typescript
./strling environment all --json
```

Environment results distinguish `compatible`, `incompatible`,
`transitional`, `deferred`, `unknown`, and `unavailable`. The JSON
result for every executed quality command includes the probes that authorized
execution.

## Runtime and engineering-tool inventory

| Environment        | Runtime or compiler authority                         | Build/test implementation                                                         | Dependency resolution                                                            |
| ------------------ | ----------------------------------------------------- | --------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| Repository tooling | Bash and Python policy in `tools`                     | Root scripts and structured product certification remain existing implementations | Root `package-lock.json`; Python script dependencies remain environment-provided |
| Language server    | Python plus Node/npm policy in `tools`                | Existing LSP scripts and package scripts                                          | Node lock present; Python requirements unbounded                                 |
| C                  | C11 in `Makefile`; GCC version deferred               | Make                                                                              | Parson commit pinned; jansson, cmocka, and PCRE2 system-managed                  |
| C++                | C++17 and CMake >= 3.15                               | CMake and CTest                                                                   | nlohmann/json release URL is versioned but has no checked content hash           |
| C#                 | .NET 9 project target                                 | dotnet                                                                            | Project files; no NuGet lock                                                     |
| Dart               | Dart >= 3.0 and < 4.0                                 | Dart package tools                                                                | `pubspec.lock`                                                                   |
| F#                 | .NET 9 project target                                 | dotnet                                                                            | Project files; no NuGet lock                                                     |
| Go                 | Go 1.22 policy                                        | Go toolchain                                                                      | `go.mod`; no external modules currently declared                                 |
| Java               | Java 11 source/target, supported JDK range in `tools` | Maven                                                                             | Direct versions pinned in `pom.xml`; transitives unlocked                        |
| Kotlin             | Supported JDK range in `tools`                        | Repository Gradle wrapper 8.5                                                     | Direct versions pinned; transitives unlocked                                     |
| Lua                | Lua >= 5.1 and < 5.5                                  | LuaRocks and Busted                                                               | Rockspec constraints; test rocks installed without bounds                        |
| Perl               | Perl >= 5.10                                          | MakeMaker and Prove                                                               | Minimum constraints; no lock                                                     |
| PHP                | PHP >= 8.2 and < 9.0                                  | Composer and PHPUnit                                                              | `composer.lock`                                                                  |
| Python             | Python >= 3.8 and < 4.0                               | setuptools and pytest                                                             | Requirements are unbounded; no lock                                              |
| R                  | Runtime version deferred                              | R package tools and testthat                                                      | Dependencies are unbounded; no renv lock                                         |
| Ruby               | Ruby >= 3.0 and < 4.0                                 | Bundler and Ruby test runners                                                     | `Gemfile.lock`, including Bundler                                                |
| Rust               | Rust >= 1.70 and < 2.0                                | Cargo                                                                             | `Cargo.lock`                                                                     |
| Swift              | Swift >= 5.9 and < 7.0                                | Swift Package Manager                                                             | No external packages currently declared                                          |
| TypeScript         | Node 22 policy                                        | Repository TypeScript and Jest packages                                           | Binding `package-lock.json`                                                      |

The exact executable constraints, version probes, command arrays, and file lists
are intentionally not copied into this table. Automation reads them from
`toolchain.json`.

## Capability states

Each component declares every governed quality capability with one of these
configuration states:

-   `configured`: an authoritative command exists in the component entry.
-   `not_applicable`: the operation has no meaningful language-level step.
-   `not_yet_configured`: the operation may be useful, but no canonical
    repository command has been selected and baselined.

Runtime results use `passed`, `failed`, `not_applicable`,
`not_yet_configured`, or `unavailable`. A missing capability is always
reported; it is never converted into a fabricated passing command. During the
current transition, `not_applicable` and `not_yet_configured` are
non-failing results. `failed`, `unavailable`, malformed policy, and unknown
targets fail the invocation.

The present capability inventory records:

-   tests are configured for all 17 bindings;
-   builds are configured for C, C++, C#, F#, Go, Java, Kotlin, Perl, Python, R,
    Ruby, Rust, Swift, and TypeScript; Dart, Lua, and PHP builds are not
    applicable;
-   compiler/static type analysis is configured for C#, Dart, F#, Go, Java,
    Kotlin, Rust, Swift, and TypeScript;
-   Dart analysis is the only currently configured lint command;
-   formatting is configured for repository and language-server Python and
    TypeScript/JavaScript, authored JSON/YAML/Markdown, C#, Dart, binding
    Python, and binding TypeScript;
-   repository hygiene validation is configured at the root, while its
    component-level applicability is explicitly declared for every target;
-   formatter dispositions that are not yet enforceable name a technical
    reason and retirement condition in `governance/formatting.json`; and
-   build applicability and configuration are stated per component rather than
    inferred from an absent command.

Language ecosystems may already provide suitable tools, and release automation
may invoke analyses such as `dart analyze`. Those facts are inventory evidence,
not a canonical quality capability until the command is declared and routed
through `./strling`.

## Canonical operation and profile contract

The permanent root vocabulary is:

```text
./strling format [--check] [component|all]
./strling hygiene
./strling lint [component|all]
./strling typecheck [component|all]
./strling build [component|all]
./strling test [component|all]
./strling generate [--check] [--json]
./strling contracts [--check] [--json]
./strling governance [--json]
./strling check [component|all] [--json] [--artifact path]
./strling profile <local|pull-request|full|release> [component|all] [--json] [--artifact path]
./strling certify [component|all] [--json] [--artifact path]
```

The `policy.operation_registry` object in `toolchain.json` is the only
canonical operation registry. Each entry identifies either a component
capability or one repository-wide command, declares whether it may use the
network, and, where applicable, names its structured result contract. Profile
membership never reimplements an operation.

`documentation_integrity` is an offline repository operation in every profile.
It validates tracked Markdown local references, executes the governed LSP
parser examples with their expected exit semantics, and checks that their
documented commands remain runnable from the repository root. Canonical
contract examples remain owned by `canonical_contracts_check`, while generated
documentation consistency remains owned by `generate_check`. Destination-
relative templates, external link reachability, Markdown anchors, and the
explicitly transitional generated audit are recorded exclusions or limitations
instead of shallow pass-producing checks.

Deep-quality certification is likewise routed only through the canonical
operation registry. Local executes the authenticated manifest contract, Pull
Request preserves that result and adds the fourteen deterministic property
obligations plus the representative Critical mutation subset, and Full and
Release preserve both cheaper layers before adding bounded Linux fuzz,
sanitizer, and complete mutation execution. The three structured result
identities remain distinct, so product certification can prove that every
cost tier actually ran instead of inferring a deeper pass from a shallower one.

Performance/resource certification follows the same cumulative routing. Local
validates the authored contract without timing, Pull Request adds the
deterministic resource-limit and controlled-regression proofs, and Full and
Release add live optimized comparison only when the producer can authenticate
an environment matching the active baseline. Native bare-metal Linux and
Windows x86_64 are eligible. Windows authority requires an exact hard
process-affinity mask and CPU-set assignment on the same authenticated logical
processor, fixed processor-frequency and HighQoS policy, unlimited CPU quota,
timer/toolchain/artifact fingerprints, a one-shot bounded quiescence check, and
the unchanged five-repetition stability gates. Core Reservation flags are
recorded when exposed, but are not required because the documented native
client API can query but cannot create that reservation. WSL2 and other guests
without attested physical placement fail closed. The operation registry invokes
the one producer, so
workflow YAML cannot substitute a weaker host check or a second measurement
implementation.

The ordered `policy.profiles` definitions are execution policies over that
registry:

-   `local` is the fast, offline developer baseline and runs the enforced
    canonical Rust-kernel test suite.
-   `pull-request` preserves the local guarantees and adds deterministic merge
    gates.
-   `full` is the broad repository envelope and may contain network-backed or
    environment-sensitive operations.
-   `release` is the stable pre-release envelope. Its existence is not a
    release-readiness claim; later work may ratchet its governed membership.

Each profile has a semantic definition version, a purpose, a network policy,
and an ordered member list. Validation requires pull-request to preserve local
membership and targets, full to preserve pull-request, and release to preserve
full. Offline profiles cannot contain network operations. Adding a member or
target advances the profile definition without changing executor semantics.

`check` is a compatibility alias for `pull-request`; `certify` is a
compatibility alias for `full`. Both resolve through the same profile
executor as the explicit `profile` command. `format --check` selects the
non-mutating formatter check command, while `format` selects its write
command.

An omitted component uses each profile member's ordered target set. An explicit
component replaces only those component target sets, and `all` selects the
canonical sorted component inventory. Repository operations always execute
once in their declared profile position. Therefore component selection cannot
bypass security, contract, generated-state, governance, architecture, or other
mandatory repository gates.

A profile's aggregate status uses the governed precedence `failed`, then
`incomplete`, then `unavailable`, then `waived`, then `passed`.
Component capability states `not_yet_configured` and
`not_yet_enforceable` make a selected profile incomplete.
`not_applicable` remains visible and neutral. A required unavailable
operation blocks the profile exit status; a waived result remains distinct
from passed. Direct leaf invocations retain their existing diagnostic
semantics.

Existing setup, bootstrap, clean, audit, cache, lockfile, list, and
environment behavior remains supported. Component identities follow the
existing binding names and also include `repository` and `lsp`. The
operation registry, profile definitions, compatibility aliases, and leaf
operation defaults are centralized under `policy` in `toolchain.json`.

GitHub Actions selects the same explicit profile command used locally. Pull
requests and branch pushes use `pull-request`; the weekly scheduled run uses
`full`; `v*` tags and the delivery preflight use `release`; manual CI dispatch
may select any profile and defaults to `local`. Every authoritative workflow
invocation supplies `--artifact`, and an always-run upload step retains that
file without changing the profile command's exit status. Full Git history is
checked out because the active contained task declares a commit-based diff
range. The binding matrix remains supplemental and uses canonical leaf
`environment`, `lint`, `typecheck`, `build`, and `test` commands.

The enforced `canonical-ci-profile-routing` architecture rule rejects workflow
use of compatibility aliases, direct quality implementation scripts, missing
artifact output, mutable artifact actions, or a delivery preflight that does
not depend on `release` certification. Workflows therefore cannot silently
substitute another certification authority.

## Structured certification artifact

Every leaf or repository operation produces one internal result containing its
canonical operation ID, component, status, command and exit evidence, reason,
capability state, formatter identity, tool/environment probes, and any nested
validated structured evidence. Language-tool stdout is never scanned to invent
a result state.

A profile execution projects the exact ordered result sequence used for
aggregation into a
`governance/schemas/profile-certification-artifact.schema.json` version
`1.0.0` artifact. Its `deterministic_evidence` contains:

-   repository commit identity and dirty state;
-   profile ID, definition version, definition fingerprint, purpose, and network
    policy;
-   selected component scope;
-   ordered operation and result IDs, status, command, tool evidence, structured
    findings, waiver references, and unavailable or incomplete reasons; and
-   aggregate status, exit code, operation count, and exact result-state counts.

The top-level `evidence_fingerprint` is the SHA-256 of canonical JSON for only
that deterministic evidence. `execution_metadata.generated_at` identifies the
execution instance but cannot change profile or evidence identity. Artifact
construction validates the aggregate against the same result statuses used for
process exit, validates the schema, and verifies the evidence fingerprint.

For profile executions, `--json` writes this artifact to stdout.
`--artifact path` writes the same validated object to the requested path and
may be combined with JSON or human output. CI should use a path outside the
tracked repository. Direct leaf-operation JSON retains the ordered operation
result wrapper.

```text
./strling profile local --json
./strling check --artifact /tmp/strling-pull-request.json
./strling test typescript --json
```

Without `--json`, profile output is a human summary rendered only from the
completed artifact. It reports the profile, repository and component scope,
aggregate result and counts, passed and failed operations, waived findings,
unavailable or incomplete operations, and the status-specific next action.
There is no independent summary aggregation path.

## Recorded transitional conditions

The following gaps are intentionally inventoried rather than broadly repaired:

-   C system libraries, compiler versions, Maven, LuaRocks, R, Composer, npm, and
    several package-manager installers do not yet have defensible executable
    version pins.
-   Python, R, Lua, and Perl dependency installation is not lock-complete.
-   Java and Kotlin pin direct versions but do not lock transitive dependencies.
-   C++ downloads a versioned archive without a repository-recorded content hash.
-   the language-server Python dependencies are unbounded.
-   Node 22 is the supported TypeScript runtime. Node 18 is a bounded
    transitional condition for the established local baseline and is reported on
    every TypeScript quality result; npm itself remains version-deferred.
-   the CI runner image and several setup actions or channels are floating,
    including Dart `stable`, Rust `stable`, and a Posit `latest` snapshot.
-   release compilation invokes language tools directly. Those release-specific
    paths remain in place until replacement through the root interface is proven
    behaviorally equivalent.
-   the C test Makefile prints a failure count but its loop does not currently
    return a failing status. This pre-existing binding-level defect is outside
    command-orchestration scope and must be addressed before C test certification
    can be a hard gate.

No item in this list authorizes a silent fallback. Deferred policies and
unconfigured capabilities remain visible until contained hardening work
replaces them.
