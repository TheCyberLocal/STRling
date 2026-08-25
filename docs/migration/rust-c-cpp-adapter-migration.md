# Canonical Rust facade and C/C++ adapter migration

## Outcome and authority

P17-T02 migrates the public Rust package plus the historical C and C++
packages onto the canonical compiler without creating another compiler
boundary. The canonical compiler contracts, frontend contracts, target
profiles, Simply protocols, standard-library registry, and `strling.interop`
1.0 remain authoritative. This migration decides host API, compatibility,
conversion, packaging, and dependency direction only.

### P18-T05 Rust distribution supersession

P18-T05 preserves P17-T02's curated Rust facade and sole-canonical-implementation
intent but supersedes its local facade-to-kernel Cargo edge. The permanent
publishable package is one repository-root `strling` crate whose curated
`core/src/lib_public.rs` crate root compiles the canonical `core/src` modules
directly. Internal stages remain private, while the repository-only
`strling-kernel` manifest lives at `core/internal/Cargo.toml` with
`publish = false`. Historical dependency arrows and path-dependency statements
below remain the record of P17's decision at that checkpoint; they are not the
current distribution graph and do not authorize a `strling-kernel` registry
package.

The task starts from clean `architecture/v4` commit
`b0eecd19b7f4680f6c90f3fecde92df5c11eddf7`. P17-T01 has already certified
the serialized protocol, native C ABI, raw WebAssembly ABI, generated native
header, ownership model, Linux fuzz/sanitizer suite, and local repository
profiles needed by these adapters.

## Starting inventory

The three historical packages contain approximately 22,000 lines across 93
Rust, C, C++, and header sources. They duplicate parsers, ASTs, IRs,
validators, hint engines, compilers, target emitters, and Simply construction.
Those implementations are compatibility evidence, not semantic authority.

Public governance is uneven. `c-public-api` is an enforced declaration
snapshot of `bindings/c/include/strling.h`. `cpp-public-api` is transitional
because the umbrella header is a stub and no compiler-backed extractor is
pinned. `rust-public-api` is transitional because the Rust 1.70 package floor
does not provide the governed rustdoc extraction path. C Simply and Essential
headers are installed in practice but absent from the enforced C snapshot.
CP2 must close these denominators before implementation or deletion.

The Rust manifest is lock-governed but has no canonical-kernel dependency. The
C Makefile builds a binding-local static compiler and uses system-managed JSON,
test, and PCRE2 dependencies. The C++ CMake project downloads nlohmann/json
without a content hash and builds a second compiler; its install rules are
disabled. None of those package graphs is an acceptable semantic route after
T02.

## Locked dependency direction

```text
Rust host package ──> public strling-kernel facade

C++ RAII facade ──> C adapter ──> strling.c-abi v1
                                      |
                                      v
                              strling-interop
                                      |
                                      v
                              public strling-kernel
```

Rust uses typed public kernel contracts directly. It must not expose the
kernel's module tree wholesale or retain binding-local semantic stages. C uses
only the generated `strling_interop.h` ABI and compact JSON envelopes. C++
owns C++ types, RAII, exceptions/status conversion, and serialization, but it
does not link Rust symbols or representations directly.

No adapter may parse Semantic STRling or regex-compatible source, validate
semantic meaning, plan portability, lower targets, emit regex, or implement a
standard helper independently. Host-side conversion from an existing public
builder/value shape into a versioned canonical request is adapter work only
when it is mechanical, closed, and differential-tested.

## Public-surface dispositions

| Package | Canonical supported surface                                                                                                                                                                                     | Compatibility disposition                                                                                                                                                                                                                                                                                     |
| ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Rust    | Curated request/result, source, target-profile, diagnostic, artifact, and Simply types plus compile/check conveniences over the public kernel facade.                                                           | Existing top-level Simply names and mechanically representable compiler conveniences remain as deprecated adapters. `core` and `emitters` cease to expose binding-owned stages; unrepresentable deep implementation paths are breaking removals recorded by the Rust public snapshot.                         |
| C       | The generated `strling_interop.h` byte ABI is the canonical low-level surface. A small owned-result adapter may provide exact-request and exact-profile conveniences without changing ABI v1.                   | Existing `strling.h` functions remain deprecated wrappers where legacy JSON can be translated mechanically. `strling_simply.h` projects Simply 1.1 requests, and `strling_essential.h` projects canonical registry helpers. Binding-local core headers and implementations are not supported public surfaces. |
| C++     | A `strling` RAII client owns native response buffers, exact request/profile values, typed errors, and move-safe results over the C/native boundary. The Simply facade serializes the canonical Simply protocol. | Documented Simply names remain adapters where representable. Historical `core/**`, parser, AST, IR, compiler, emitter, and hint-engine headers are transitional implementation exposure and may be intentionally removed after CP2 snapshots and differential evidence.                                       |

Every removal or signature change is classified as a public breaking change,
even when it corrects accidental implementation exposure. No compatibility
symbol may silently call retained local compiler logic. A compatibility path
that cannot be represented exactly must return a stable adapter error or be
removed explicitly; it must not approximate semantics.

## Target and compatibility behavior

Canonical compile APIs require an exact caller-supplied target profile. They do
not select a target from the host language, installed regex engine, filesystem,
or ambient default.

Deprecated historical compile conveniences that lack a target argument may
use only the generated `pcre2-10.43` profile projection. Their documentation
and result metadata must identify that profile. This is a bounded compatibility
adapter, not a repository default and not permission for new APIs to omit a
profile. Existing output differences are reviewed against canonical results
and classified rather than hidden.

Legacy JSON AST and host builder values may be converted into versioned Simply
or compile requests only through a closed mapping with refusal cases. Unknown
nodes, flags, helpers, or options fail. The old C/C++/Rust emitters are never a
fallback.

## Ownership, errors, and concurrency

C inherits the native ABI's borrowed-input copy, zeroable owned response,
same-descriptor free, panic containment, request/response ceilings, reentrancy,
and concurrency guarantees. Compatibility result structs remain self-contained
and use their existing free functions while internally owning exactly one
native response until conversion completes.

C++ results are move-safe RAII values. Destructors release native ownership
exactly once; moved-from values are empty; copy behavior is either a documented
deep copy or disabled. Transport failures map from stable `STRL-INTEROP-*`
codes, while canonical failed compile results remain values rather than C++
transport exceptions. No exception crosses the C ABI.

Rust exposes typed canonical errors and results without reparsing serialized
diagnostics. It may provide ergonomic error wrappers, but stable canonical
codes, paths, and result data remain recoverable.

## Source retirement gates

Semantic copies are deleted only after all of these hold:

1. CP2 freezes the exact API, compatibility, conformance, lifecycle, package,
   and deletion denominators and proves shrinkage fails closed.
2. The replacement route produces identical canonical requests, results, and
   artifacts for every preserved case, with intentional differences reviewed.
3. Public snapshots identify every additive, compatible, deprecated, and
   breaking surface change.
4. Architecture fitness proves Rust uses only the curated public kernel facade,
   C uses only the native ABI, and C++ uses only C/native declarations.
5. Builds and tests no longer compile deleted parser, compiler, IR, validator,
   hint, target, standard-helper, or emitter sources.

Historical fixtures may remain migration evidence, but passing them does not
grant semantic authority. Generated C fixtures, test skeletons, Rust build
source, public snapshots, version metadata, and lockfiles retain their registry
dispositions until deliberately retired or regenerated.

## Packaging and versioning

The task certifies local build, link, install, and package assembly without
publishing. Rust/C/C++ package versions remain governed by the existing version
synchronization workflow; T02 does not select a 4.0 release version.

The Rust facade may add a path dependency on the unpublished kernel for
repository certification. Making the kernel independently publishable or
publishing any crate is a later release decision. C and C++ builds consume a
locally built interop static or dynamic library and its generated header; they
must not download a compiler binary at build or runtime. Dependency resolution
must become lockable or content-addressed before a package is called
reproducible.

## Verification and exclusions

CP2 will freeze cross-language canonical request/result/artifact parity,
compatibility/refusal behavior, public extraction, ownership/error/concurrency,
RAII, Unicode, build/install/package, architecture, and deletion cases. CP3
implements only that denominator. CP4 runs supported compiler warnings,
sanitizers, native lifecycle, migration differential, public/generated
contracts, security, Local/Pull Request/Full profiles, and exact unavailable
platform dispositions.

The frozen CP2 suite contains 58 cases across ten exact families. Its 17
canonical authority inputs have fingerprint
`sha256:0c6189b30042c50481228314ca35f69e55c9536288aad7299dce5c4816770924`;
the case manifest has fingerprint
`sha256:d95581ae6bb95b5250fc5ffade82bba932ebb3a01276c406afe8f3db19080b70`.
A governed baseline reproduces 28 legacy public inputs and 35 semantic-copy
files directly from the immutable starting commit, with fingerprint
`sha256:bde6ddf77502663e13dd1957f9daefba82cda07c033ad029193467d380d17d4c`.
Eleven mutation tests prohibit authority, fingerprint, case, family, runner,
binding, path, and base-blob shrinkage. These are verification obligations,
not implementation passes; CP3 owns their executable adapter proof.

T02 does not change canonical language semantics, frontend grammars, target
profiles, diagnostics, standard-library guarantees, interop protocol/ABI v1,
kernel stages, other host packages, support tiers, or release versions. It does
not push, publish, tag, upload, or create a release.
