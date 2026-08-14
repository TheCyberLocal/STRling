# Canonical VS Code and tooling packaging certification

## Outcome and authority

P16-T05 turns the VS Code extension from a source-tree-only editor client into
a reproducible, platform-targeted package whose only STRling semantic engines
are the canonical Rust processes. The package may contain transport adapters,
coordinate projection, generated client JavaScript, governed registries, and
the minimal local LSP protocol implementation. It may not contain a binding as
an alternate parser, validator, formatter, rewrite engine, or target planner.

The Semantic IR, canonical compiler kernel, canonical editor projection,
frontend contracts, certified rewrite registry, and target profiles retain
their existing authority. `package.json` governs the extension's public editor
surface. A new closed package contract will govern target identities, payload
layout, launch wiring, resources, and content-manifest requirements. The
generated payload and VSIX remain disposable release artifacts and are never
edited or committed.

The clean starting and rollback boundary is
`76050f62204544c3ded857bd28080803aeeedc7b` on `architecture/v4`, the
P16-T04 closure.

## Starting-state inventory

The tracked extension source consists of one TypeScript client, four authored
server modules, local `pygls` and `lsprotocol` transport subsets, the governed
island registry outside the package directory, extension metadata and assets,
two shell build entrypoints, a user-home synchronizer, examples, and 544
passing source-tree LSP tests. The canonical runtime already exposes two Rust
executables: `strling-kernel` for immutable compile results and
`strling-editor-core` for completion, navigation, tokens, formatting, and
certified actions.

The current generated-artifact entry describes `dist/**` as an unverified,
unenforced, transitional payload. Its input set omits the Rust core, lockfile,
transport subsets, package assets, and governed registries. The assembler has
the following concrete defects:

-   it copies only `server.py` and `island_extractor.py`, omitting
    `canonical_core.py` and `canonical_intelligence.py`;
-   it creates a temporary virtual environment and downloads unpinned `pygls`
    and `lsprotocol` wheels during every build;
-   it copies the complete legacy Python binding into `server/libs/STRling`,
    creating an inappropriate second semantic bundle;
-   it packages neither canonical Rust executable nor the Simply, stdlib, and
    island registry resources required by the authored adapters;
-   its repository-relative runtime discovery cannot resolve packaged paths;
-   it invokes `npx` rather than lock-resolved local Node executables and has no
    content manifest, target identity, reproducibility check, or package smoke
    test; and
-   it depends on a POSIX shell even for the Windows package path.

The manifest and lock root also disagree: `package.json` is version `1.0.0`
under Apache-2.0 while the lock root still records version `0.1.0` under MIT.
The extension does not activate for native `strling` documents. Its client
selects only seven of the 17 advertised host languages, while the package
redeclares several host-language extension associations it does not own. A
missing Python interpreter falls through to a command that is known not to
exist instead of producing an explicit activation error.

No tracked VSIX, `dist` payload, compiled editor binary, or other package
residue is present at the starting boundary. Historical residue named by the
donor inventory is already absent and will not be recreated.

## Supported package targets

P16-T05 certifies four native VSIX families, each built on its matching runner:

| Package target | Runtime architecture       | Certification runner |
| -------------- | -------------------------- | -------------------- |
| `linux-x64`    | `x86_64-unknown-linux-gnu` | `ubuntu-latest`      |
| `win32-x64`    | `x86_64-pc-windows-msvc`   | `windows-latest`     |
| `darwin-x64`   | `x86_64-apple-darwin`      | `macos-15-intel`     |
| `darwin-arm64` | `aarch64-apple-darwin`     | `macos-latest`       |

The package contract will reject every undeclared target and every mismatch
between the requested target, host OS, host architecture, executable suffix,
and Rust host triple. Cross-compiling a differently targeted payload is not a
substitute for running its smoke tests on that platform. ARM Linux and ARM
Windows remain unclaimed until matching non-preview certification capacity and
evidence are added deliberately.

## Canonical payload and launch contract

Every generated target has this closed logical layout:

```text
dist/
  package.json
  readme.md
  LICENSE.txt
  out/extension.js
  server/
    server.py
    canonical_core.py
    canonical_intelligence.py
    island_extractor.py
    libs/pygls/**
    libs/lsprotocol/**
    bin/strling-kernel[.exe]
    bin/strling-editor-core[.exe]
    resources/simply-protocol.json
    resources/stdlib-registry.json
    resources/island-boundaries.json
  strling-package-manifest.json
  extension assets and notices
```

The extension computes absolute paths beneath its own installed root and sets
`STRLING_KERNEL`, `STRLING_EDITOR_CORE`,
`STRLING_SIMPLY_PROTOCOL_PATH`, `STRLING_STDLIB_REGISTRY_PATH`, and
`STRLING_ISLAND_BOUNDARIES_PATH` for the server process. Configured command and
argument overrides remain advanced transport overrides; they cannot change the
canonical meaning contract. Source-tree discovery remains available for
developers, but an installed package never searches a repository checkout or
ambient `PATH` for either semantic process.

The server continues to require an installed Python 3 interpreter. The
extension probes supported command names without invoking a shell, reports a
specific activation error when none is available, and performs no runtime
download. The local `pygls`/`lsprotocol` subsets become the declared packaged
transport implementation. `requirements.txt` therefore records zero external
Python runtime dependencies, and the security inventory will retire its
transitional missing-lock status instead of inventing a lock for no packages.

The package includes only the three governed JSON resources read at runtime.
It excludes the legacy Python binding, source-tree compatibility wrappers,
tests, examples, caches, virtual environments, Node dependencies, Cargo
artifacts, source maps, temporary outputs, and repository metadata.

## Deterministic build and content evidence

One cross-platform Python entrypoint will replace shell-owned assembly. It
must use `cargo --locked` and executables resolved from the npm lock installation;
network access is forbidden after the explicit dependency-install step. Inputs
are copied with normalized paths, modes, and timestamps. A closed JSON content
manifest records package contract version, extension version, target, Rust
host, source commit, input registry fingerprints, and every payload path, size,
mode, and SHA-256 digest.

Two clean source snapshots at the same commit must independently install
locked build dependencies, build both Rust processes, assemble the client and
server payload, and create the target VSIX. Deterministic payload families must
match byte for byte. ZIP container metadata may be normalized by the packager;
if an upstream VSIX field is inherently variable, certification compares the
closed extracted-entry manifest and records the excluded field explicitly.
There is no whole-directory or filename-only equivalence.

The registered generated-artifact entry names every authoritative input, runs
the cross-platform builder, and requires the certification verifier. It is a
verified candidate because the generic generated-artifact check enforces only
checked-in projections; the dedicated Full/Release profile and CI checks own
the expensive, self-cleaning package certification. `dist/**` and `*.vsix`
stay ignored and unchecked in.

## Closed verification design

CP2 will freeze a shrinkage-resistant package corpus before implementation. It
will cover exact target mappings, required and forbidden paths, resource and
executable hashes, manifest mutation cases, activation and every declared
document selector, settings and override behavior, Python-missing failure,
both canonical processes, every LSP feature, embedded islands, CLI/editor
identity, bounded service failures, offline execution,
install/upgrade/uninstall in an isolated extension directory, and
duplicate-build equivalence.

Package end-to-end cases launch the generated server over stdio and compare
its diagnostics and editor projections with the packaged canonical processes
for the same source identity. An activation harness loads the generated client
against explicit VS Code and language-client doubles and proves the exact
command, arguments, environment, selector set, and error reporting. It does
not treat source-tree unit tests as packaged-runtime evidence.

The frozen package contract is `1.0.0` at
`sha256:3387c3aa55afdb2bee3c987a0e92038fc5a0caebbd1826709ba907f701c10945`.
It declares 17 copied source/resource paths, two generated files, two canonical
runtime binaries, 21 required payload paths, 15 forbidden path patterns, six
absolute runtime environment bindings, four exact target/runner pairs, ten
editor features, 21 VS Code document selectors, and zero external Python
packages.

The closed CP2 acceptance denominator contains 72 unique cases: four native
targets, 21 selectors, ten features, 12 failure dispositions, three isolated
lifecycle operations, six packaged/canonical identity groups, 12 controlled
mutations, and four reproducibility properties. Its canonical fingerprint is
`sha256:736f77bc8b912e5a3e48b5156cd4544a0c231c7e289164631686b983b1d91929`.
Eleven integrity tests validate the closed schema and fingerprints, exact
target/runner mapping, island-registry alignment, canonical-only payload,
offline runtime, owned extension surface, all case dimensions, and
denominator-removal resistance. These tests define evidence requirements; they
do not claim that the starting implementation already satisfies them.

## CP3 implementation and local certification evidence

Commit `b8b2d54cffb9d86093205964de2a2193314f80fc` implements the closed
package contract with the cross-platform canonical builder, packaged runtime
wiring, zero-external-dependency Python transport, client activation harness,
payload mutation tests, generated-artifact governance, security inventory,
profile membership, documentation, and four-target CI matrix. The complete
source-tree LSP suite passed with 566 tests; the focused package suite passed
with 22 tests; focused governance, security, and profile coverage passed with
122 tests and 15 subtests.

The clean-tree `win32-x64` certification at that commit completed two
independent locked release builds and produced the following evidence:

-   21 payload files; reproducible payload fingerprint
    `sha256:f2d1a60e1f3c87fc2df1788ba1689b9890e36049dae0dc289999647f078d042d`;
-   23 normalized VSIX entries; reproducible entry fingerprint
    `sha256:a2e8ed3266da4c18d734a34747d3de68684b8f419144b10d964de3a62533f55f`;
-   certified VSIX digest
    `sha256:594c358c776162047bc13482aa3c0ad43a2edf7469427d14b4c2b0fc2307eea7`;
-   kernel and editor runtime fingerprints
    `sha256:a1856b3c02db54ebf6436e35528c25e474cef3031b948d335fc298eaebb0bc46`
    and
    `sha256:ec13294dfe735c7d9a6de382a43e79ea25a95cd45ad34bfd0c67845dc0319b88`;
-   all ten editor feature families passed over packaged stdio, with canonical
    result fingerprint
    `sha256:1f7e58e5d51ba5b8c7df420d3f32424ffee1631159a0e42ed99960f671f984d7`
    and evidence fingerprint
    `sha256:79c940ea423706c8ee25800e7b0cb26b669a07413da28caa18b0da3da1c6f2d7`;
    and
-   isolated install, upgrade, and uninstall all passed.

The post-commit repository content/workflow security scan passed all four
checks with zero failed, incomplete, unavailable, or waived results. This is
native Windows evidence only. Linux x64, macOS x64, and macOS arm64 retain
their declared matching CI runners and remain unclaimed until those runners
produce retained artifacts and evidence.

CI will run the same certification command on all four supported runner/target
pairs and retain the content manifest and VSIX as test evidence. No workflow in
this task publishes, signs, uploads to a marketplace, changes release tags, or
installs into a developer's real VS Code directory. Lifecycle smoke tests use
an isolated temporary extension root and prove replacement and removal without
touching user state.

CP4 additionally runs the complete LSP and tooling suites, Rust all-targets,
public contracts, generated-artifact verification, dependency and security
checks, migration differential, architecture fitness, documentation and
formatting checks, Local/Pull Request/Full profiles, clean-tree checks, and the
package diff. Results unavailable without a remote runner remain unavailable;
they are never promoted to a passing platform claim.

## Task boundary

P16-T05 may correct extension activation, selectors, settings, package version
wiring, runtime discovery, assembly, generated-artifact governance, package
tests, and CI certification. It may not change STRling grammar, Semantic IR,
frontend meaning, diagnostics, rewrites, target behavior, stdlib semantics,
binding APIs, or canonical compiler/editor evidence. It does not publish the
extension, add a marketplace release, or restore any binding-owned fallback.

Rollback is the complete P16-T05 diff back to
`76050f62204544c3ded857bd28080803aeeedc7b`. Generated payloads are disposable
and may be deleted by their owning builder; rollback never resets unrelated
repository work or user editor state.
