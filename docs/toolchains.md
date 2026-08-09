# Deterministic toolchains and quality commands

## Authority and scope

`toolchain.json` is the authoritative inventory for repository engineering
environments, executable version policy, language-specific commands, capability
states, and relevant manifests, lock files, and configuration files. This
document explains that machine-readable contract; it does not duplicate command
arguments or version values as a second source of truth.

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

- `exact`: only the declared version is accepted.
- `constrained`: an installed version must satisfy the declared bounded or
  minimum-supported range.
- `repository_managed`: the repository file named by the entry resolves the
  version, such as a lock file or wrapper.
- `deferred`: the environment currently supplies the capability and the
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

| Environment | Runtime or compiler authority | Build/test implementation | Dependency resolution |
| --- | --- | --- | --- |
| Repository tooling | Bash and Python policy in `tools` | Root scripts and Omega remain existing implementations | Root `package-lock.json`; Python script dependencies remain environment-provided |
| Language server | Python plus Node/npm policy in `tools` | Existing LSP scripts and package scripts | Node lock present; Python requirements unbounded |
| C | C11 in `Makefile`; GCC version deferred | Make | Parson commit pinned; jansson, cmocka, and PCRE2 system-managed |
| C++ | C++17 and CMake >= 3.15 | CMake and CTest | nlohmann/json release URL is versioned but has no checked content hash |
| C# | .NET 9 project target | dotnet | Project files; no NuGet lock |
| Dart | Dart >= 3.0 and < 4.0 | Dart package tools | `pubspec.lock` |
| F# | .NET 9 project target | dotnet | Project files; no NuGet lock |
| Go | Go 1.22 policy | Go toolchain | `go.mod`; no external modules currently declared |
| Java | Java 11 source/target, supported JDK range in `tools` | Maven | Direct versions pinned in `pom.xml`; transitives unlocked |
| Kotlin | Supported JDK range in `tools` | Repository Gradle wrapper 8.5 | Direct versions pinned; transitives unlocked |
| Lua | Lua >= 5.1 and < 5.5 | LuaRocks and Busted | Rockspec constraints; test rocks installed without bounds |
| Perl | Perl >= 5.10 | MakeMaker and Prove | Minimum constraints; no lock |
| PHP | PHP >= 8.2 and < 9.0 | Composer and PHPUnit | `composer.lock` |
| Python | Python >= 3.8 and < 4.0 | setuptools and pytest | Requirements are unbounded; no lock |
| R | Runtime version deferred | R package tools and testthat | Dependencies are unbounded; no renv lock |
| Ruby | Ruby >= 3.0 and < 4.0 | Bundler and Ruby test runners | `Gemfile.lock`, including Bundler |
| Rust | Rust >= 1.70 and < 2.0 | Cargo | `Cargo.lock` |
| Swift | Swift >= 5.9 and < 7.0 | Swift Package Manager | No external packages currently declared |
| TypeScript | Node 22 policy | Repository TypeScript and Jest packages | Binding `package-lock.json` |

The exact executable constraints, version probes, command arrays, and file lists
are intentionally not copied into this table. Automation reads them from
`toolchain.json`.

## Capability states

Each component declares every governed quality capability with one of these
configuration states:

- `configured`: an authoritative command exists in the component entry.
- `not_applicable`: the operation has no meaningful language-level step.
- `not_yet_configured`: the operation may be useful, but no canonical
  repository command has been selected and baselined.

Runtime results use `passed`, `failed`, `not_applicable`,
`not_yet_configured`, or `unavailable`. A missing capability is always
reported; it is never converted into a fabricated passing command. During the
current transition, `not_applicable` and `not_yet_configured` are
non-failing results. `failed`, `unavailable`, malformed policy, and unknown
targets fail the invocation.

The present capability inventory records:

- tests are configured for all 17 bindings;
- builds are configured for C, C++, C#, F#, Go, Java, Kotlin, Perl, Python, R,
  Ruby, Rust, Swift, and TypeScript; Dart, Lua, and PHP builds are not
  applicable;
- compiler/static type analysis is configured for C#, Dart, F#, Go, Java,
  Kotlin, Rust, Swift, and TypeScript;
- Dart analysis is the only currently configured lint command;
- no formatter or formatter-check command is yet configured at the root;
- root and language-server quality capabilities are not yet configured; and
- build applicability and configuration are stated per component rather than
  inferred from an absent command.

Language ecosystems may already provide suitable tools, and release automation
may invoke analyses such as `dart analyze`. Those facts are inventory evidence,
not a canonical quality capability until the command is declared and routed
through `./strling`.

## Canonical command contract

The permanent root vocabulary is:

```text
./strling format [--check] [component|all]
./strling lint [component|all]
./strling typecheck [component|all]
./strling build [component|all]
./strling test [component|all]
./strling check [component|all]
./strling certify [component|all]
```

`format` selects the declared formatter write command, while
`format --check` selects the non-mutating formatter check command. `check`
is the fast shared developer/checkpoint aggregate. `certify` establishes the
broader aggregation contract without replacing Omega or the later release
certification architecture. Aggregate membership is authoritative in the
`policy.aggregates` section of `toolchain.json`.

Existing setup, bootstrap, clean, audit, cache, lockfile, and list behavior
remains supported. Component selection follows the existing binding names and
also recognizes `repository` and `lsp`. An omitted component on a leaf
operation or an explicit `all` selects all inventoried environments. An
omitted component on `check` or `certify` selects the policy's established
TypeScript baseline; `./strling check all` and `./strling certify all` are
the explicit full-inventory forms. This keeps the default aggregates reliable
while later hardening makes additional environments eligible.

The GitHub Actions quality matrix uses the same `environment`, `build`, and
`test` commands. Its Node, Go, .NET, and Bundler setup values are aligned with
this policy, and a failed build is no longer converted into success. The
TypeScript setup command uses `npm ci --no-audit --no-fund`: dependency
lifecycle scripts and exact lock resolution remain enabled, while unrelated
audit and funding network calls are excluded from setup.

## Structured result contract

Every leaf operation produces an internal result with:

- `operation`;
- `component`;
- `status`;
- `command`, or null when nothing is configured;
- `exit_code`, or null when nothing executes; and
- `reason`, or null when no explanation is needed.

Aggregate results contain their ordered leaf results and an overall exit code.
The default console presentation is human-readable. JSON output is the stable
machine interface; automation must use result fields and exit codes rather than
parse prose emitted by language tools.

Append `--json` to any canonical quality command to receive one JSON object:

```text
./strling check --json
./strling test typescript --json
```

The JSON object contains the requested operation, overall status and exit code,
ordered leaf results, and the complete list of capabilities still marked
`not_yet_configured` for aggregate commands. Language-tool output is retained
for the human presentation but is not parsed to invent semantic results. Each
leaf also contains its executable version-probe results.

## Recorded transitional conditions

The following gaps are intentionally inventoried rather than broadly repaired:

- C system libraries, compiler versions, Maven, LuaRocks, R, Composer, npm, and
  several package-manager installers do not yet have defensible executable
  version pins.
- Python, R, Lua, and Perl dependency installation is not lock-complete.
- Java and Kotlin pin direct versions but do not lock transitive dependencies.
- C++ downloads a versioned archive without a repository-recorded content hash.
- the language-server Python dependencies are unbounded.
- Node 22 is the supported TypeScript runtime. Node 18 is a bounded
  transitional condition for the established local baseline and is reported on
  every TypeScript quality result; npm itself remains version-deferred.
- the CI runner image and several setup actions or channels are floating,
  including Dart `stable`, Rust `stable`, and a Posit `latest` snapshot.
- release compilation invokes language tools directly. Those release-specific
  paths remain in place until replacement through the root interface is proven
  behaviorally equivalent.
- the C test Makefile prints a failure count but its loop does not currently
  return a failing status. This pre-existing binding-level defect is outside
  command-orchestration scope and must be addressed before C test certification
  can be a hard gate.

No item in this list authorizes a silent fallback. Deferred policies and
unconfigured capabilities remain visible until contained hardening work
replaces them.
