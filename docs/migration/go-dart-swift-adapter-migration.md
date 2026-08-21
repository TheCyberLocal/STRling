# Canonical Go, Dart, and Swift adapter migration

Status: P17-T06 CP4 integration and certification

Starting commit: b6cefe0add189d687f7c2940f4a505621c60c8e4

## Objective

Replace the three package-local compilers with idiomatic facades over the
versioned native interop boundary. Go, Dart, and Swift may own request
construction, canonical JSON projection, native loading, allocation and
release, lifecycle, host errors, package metadata, and Simply ergonomics. They
may not parse, normalize, analyze, validate, plan, lower, emit, or reinterpret
STRling semantics.

## Starting state

The clean `architecture/v4` starting tree contains 204 tracked Go, Dart, and
Swift entries with fingerprint
`sha256:54fa3801fd073a0fb40ea237caed831fa66f414e69ab25ca195f0cf4f5f84b49`.
Thirty-two production language sources contain 10,409 lines and fingerprint to
`sha256:f0eb3565445bd4d60a404163730fdd7399db5ee153f985c96a118f7732248f04`.
Thirty-three test sources contain 8,438 lines. The large residual tree is mostly
Swift compatibility resources and package documentation.

Thirty product sources contain the closed local semantic footprint: Go and
Dart AST/node, parser, compiler, IR, diagnostic/hint, validator, emitter,
Simply, and helper routes plus their Swift equivalents. They contain 10,400
lines and fingerprint to
`sha256:f29f0f92d66da3ba6ecdc691a43e75ac7452e0f28aa5a608ef454455de81f674`.
The two excluded production sources are a Go package declaration and the Dart
root export. The thirty sources are compatibility evidence, not semantic
authority, and may be retired only after CP2 freezes their exact content and
behavior denominator.

The task-start Go compatibility snapshot contains 135 declarations, but the
current host cannot reproduce it because `go` is absent. Dart and Swift public
surfaces remain transitional and have no checked-in snapshots because the
configured analyzer and normalized symbol-graph extractors do not yet exist.
Go, Dart, and Swift executables are all absent on this Windows host. Those facts
are recorded as unavailable starting evidence, not passing or failing runtime
rows and not support claims.

Package identities remain compatibility inputs: Go module
`github.com/strling-lang/strling/bindings/go` with language level 1.22; Dart
package `strling` 3.0.0 with SDK range `>=3.0.0 <4.0.0`; and Swift package and
library `STRling` with tools version 5.9. The existing Apple platform minimums
are historical metadata until executed certification proves them.

## Bridge decisions

All three adapters consume the existing `strling.c-abi` version 1 symbols and
the canonical JSON protocol. They accept a caller-supplied absolute library
path. Ambient name lookup, current-directory search, PATH probing, network
download, subprocess transport, sockets, copied Rust layout, and direct access
to internal Rust modules are forbidden.

-   Go uses cgo with a package-local, semantic-free operating-system loader
    shim. The shim resolves the ABI-version, execute, and free functions from
    one absolute library handle. A build with `CGO_ENABLED=0` may compile only a
    fail-closed host-error stub; it cannot fall back to Go semantics. cgo and a
    working C compiler are prerequisites for an executable adapter row.
-   Dart uses `dart:ffi` and `DynamicLibrary.open` on Dart VM/native runtimes.
    Web is not a native-FFI surface and is unsupported by this adapter. The VM
    owns the dynamic-library handle lifetime; the adapter must free every
    native response descriptor and does not promise deterministic unload.
-   Swift uses a small C-interop loader target inside the Swift package. The
    target performs only absolute-path load, symbol resolution, ABI checking,
    invocation, and close. Swift projects canonical JSON and host errors. Apple,
    Linux, and Windows rows remain unclaimed until their exact Swift and C
    toolchains execute the governed matrix.

This is three ecosystem-appropriate transports over one ABI, not three native
semantic implementations. Any loader shim is restricted to the three governed
symbols and must remain free of compiler, frontend, target, diagnostic, Simply,
or standard-library meaning.

## Transport and lifecycle contract

-   Each client verifies ABI major version 1 before execution, enforces the
    10 MiB request and 32 MiB response ceilings, uses strict UTF-8 and strict
    JSON, and releases every owned response through the matching free symbol.
-   Empty, relative, missing, wrong-architecture, wrong-ABI, missing-symbol,
    disposed-client, encoding, size, allocation, transport, and native-status
    failures are stable host errors. Canonical completed or rejected protocol
    responses and diagnostics remain canonical values.
-   Go and Swift clients provide idempotent close and serialize close against
    in-flight calls. Calls are otherwise reentrant and concurrent because the
    native contract has no mutable global state. Dart provides the same call
    and response-allocation guarantees but cannot promise explicit unload.
-   Cancellation of an in-flight native call, deterministic OS unload timing,
    recovery from process-level allocation failure, and platform support not
    executed by the governed matrix are not promised.

## Public compatibility contract

The final public break is intentional:

-   binding-owned AST/IR, parser/compiler, emitter, validator, hint, warning,
    diagnostic synthesis, and target semantics are retired;
-   canonical operations accept or construct versioned request envelopes and
    return canonical JSON data rather than binding-private IR or regex strings;
-   target artifact operations require an exact target profile or reference;
-   targetless `ToRegex`, `compile`, and PCRE2 conveniences cannot silently
    preserve local semantic execution and must be removed, explicitly refused,
    or replaced by client-and-profile operations;
-   Go errors/raw JSON, Dart exceptions/maps, and Swift errors/Foundation JSON
    are facade-level projections only; and
-   Simply and Essential names may remain where they record canonical Simply
    protocol recipes without rendering or validating regex locally.

The five registered helpers remain `lexical_shape` conveniences across eight
variants and 117 edge records with zero semantic validators. No adapter may
strengthen lexical acceptance into semantic correctness.

## Package and verification boundary

CP2 freezes the exact task-start tree, all thirty semantic-copy paths,
public/build/package inputs, dependency locks, compatibility behavior,
toolchain absence, shared conformance cases, platform rows, and mutation
resistance before any semantic copy is deleted.

The generated evidence bundle is anchored to the immutable starting commit and
contains all 204 tracked files as authenticated base64, hashes for 36 public,
build, package, and lock inputs, and hashes for all 30 semantic-copy sources.
Its closed matrix contains 78 cases across twelve families, eleven runners,
four canonical operations, three bindings, and the three governed toolchain
ranges. The task-start observations for all three toolchains are `unavailable`
with no test count. Changing a count, identity, status, schema, source, path, or
editable hash does not create evidence; the nine mutation tests reject it.

## Generated and public evidence design

The post-migration public extractors are binding-specific views over small
facades, never semantic authorities:

-   Go discovers the surviving product packages and retains governed
    `go-doc-declarations` extraction and the existing JSON snapshot shape. CP4
    must reproduce it with Go `>=1.22,<1.23`.
-   Dart uses an analyzer-backed export-reachability extractor under SDK
    `>=3.0,<4.0`. It starts at `lib/strling.dart` and records exported
    declarations, members, parameters, nullability, and stable exception
    identities in the common public-contract snapshot envelope.
-   Swift uses a normalized symbol-graph extractor under Swift `>=5.9,<7.0`.
    It records the `STRling` product/module, public declarations,
    availability, signatures, and stable error identities while discarding
    paths, compiler build metadata, and ordering noise.

Snapshots are checked-in outputs of `public-contract-snapshots`; their
extractors and toolchain constraints are generator inputs. The three surfaces
are enforced; an unavailable toolchain or missing generated snapshot is a
hard failure and cannot be converted into a passing row.

The Essential/Simply helper surfaces are generated by
`go_dart_swift_stdlib_surfaces.py` from the canonical standard-library registry
and semantics, then compiled as part of each package. The generator may project
names, variants, parameters, documentation, and request recipes only. It may
not copy regexes, add semantic validation, or change the five `lexical_shape`
guarantees, eight variants, 117 edge records, or zero semantic validators.

CP3 may implement only the locked bridges, facade contracts, public extractors,
and standard-library projections. CP4 owns live
toolchain and native execution, memory/resource and concurrency certification,
package/build/install consumers, dependency risk and licenses, migration
differential, public/generated contracts, governance, and Local/Pull
Request/Full profiles. No package publication, branch push, release, tag,
upload, interop-v2 change, or unexecuted platform claim is authorized.

## Certified CP4 state

All thirty frozen product semantic-copy paths are absent. The replacement tree
contains the Go cgo/fail-closed no-cgo facade, Dart FFI facade, Swift C-interop
facade, generated Simply helper identities, and task-owned public extractors.
Each native client routes the four canonical operations, checks ABI version and
transport bounds, rejects non-strict UTF-8 and duplicate-key JSON, releases the
same response descriptor, and exercises idempotent close, closed-use refusal,
and its declared reentrancy model. Temporary C probes cover release, ABI
mismatch, oversize, duplicate-key, and invalid-UTF-8 responses.

The governed Linux toolchains are Go 1.22.12, Dart 3.4.4, and Swift 6.2.1.
Live execution passes all three adapters, four canonical operations, five
hostile transport probes, and three deterministic repeat runs at result
fingerprint
`sha256:181345f6c2d0623eac75c7b2074defb59b2bfffaeff3de8e2eea39db195086e5`.
Clean package consumers pass: Go and Swift have no external release
dependencies; Dart resolves `ffi` 2.1.3 and `path` 1.9.0 at runtime while the
analyzer remains development-only.

Go, Dart, and Swift public snapshots reproduce under their governed native
extractors. The authorized canonical standard-library reference repair and
every registered affected projection reproduce with registry fingerprint
`sha256:db3d1fc6ddd1b0ef83cb7bfb4a9bd84c8bcc547d5a6649a6747cc4b94fb4edff`.
Derived Python, TypeScript, JVM, and .NET changes are fingerprint/reference-only;
no helper semantics, validation level, behavior, or API shape changed. The
focused Linux suite passes 115 tests, the 78-case migration evidence remains
closed, and the generated baseline reproduces exactly.

Clean-consumer and release-graph certification passes for all three adapters.
Go and Swift have no external release dependencies. Dart's resolved graph has
`ffi` 2.1.3 and `path` 1.9.0 as its only direct runtime dependencies. The
governed vulnerability and license rows pass for Go and Swift. Because the
governed framework has no authoritative Pub scanner, its Dart rows remain
explicitly unavailable; an authorized supplemental live OSV query found no
advisories across all 48 hosted Pub dependencies, and official package license
texts classify both direct runtime dependencies as BSD-3-Clause.

The exact Windows Python 3.13 migration differential passes three deterministic
runs with zero blocking unresolved canonical replacements and result fingerprint
`sha256:a625055f60e2eda0b37ee785d68eabcbbc94dab2fca272bd0a4ff54ad87636ab`.
Six historical peer return-shape differences remain evidence-only. The same
profile operation exits 2 under WSL Python 3.12 and is recorded as an environment
limitation rather than a passing Linux differential row.

The final Local artifact records 31 passed and two failed operations. Pull
Request records 50 passed, 14 failed, and four unavailable. Full records 69
passed, 24 failed, and 17 unavailable with fingerprint
`9348df046fe5eb939523c00737dadf9a81c2fe3aa3b73cb16bf72583e2ddb67f`.
Every applicable Go, Dart, and Swift formatting, lint, typecheck, build, test,
native-runtime, clean-consumer, package, public-contract, generated-authority,
portability, architecture, and governance row passes. Remaining failures and
unavailable rows are exact repository-wide dependency, lint, ecosystem, and
tool-availability carry-forward. Certification claims only the executed WSL2
Linux x86_64 environment and does not claim package publication or unexecuted
platform support.
