# Canonical interop, C ABI, and WebAssembly foundation

## Outcome and authority

P17-T01 establishes one versioned serialized boundary between host adapters and
the canonical Rust compiler. The normative byte protocol and ABI descriptor
live under [`spec/interop/1.0`](../../spec/interop/1.0/README.md). Embedded
`CompileRequest`, `CompileResult`, target-profile, diagnostic, and Simply values
retain their existing authority. The migration record controls task evidence;
it does not create language semantics.

The additive reference bridge lives under `bindings/interop` and depends
only on the public `strling-kernel` facade. It may own JSON transport, raw C and
WebAssembly buffer handling, panic/error conversion, generated headers, and
package artifacts. It may not own a parser, semantic validator, target planner,
lowerer, emitter, runtime executor, or independent standard-library helper.

## Starting-state inventory

The clean task entry is `d4189e039810532c8447aeeffb18a8fc7a165e29` on
`architecture/v4`. The canonical kernel already exposes typed, deterministic
`CompileRequest`/`CompileResult` compilation, exact supplied target-profile
validation, and Simply 1.0/1.1 replay. The root CLI proves a JSON process
transport, but no stable native ABI or WebAssembly crate exists.

The historical `bindings/c` header and C implementation expose an AST-to-PCRE2
compatibility API with heap-owned historical structures. The historical
`bindings/rust` crate remains an independent compatibility compiler. Their
public snapshots are preservation evidence for P17-T02, not authority for the
new ABI, and they are unchanged in T01.

The kernel crate forbids unsafe code and deliberately excludes host binding
APIs. The new bridge therefore cannot be placed inside `core/src`, and a new
repository root would violate the enforced top-level-island rule. The contained
`bindings/interop` placement preserves both boundaries.

## Locked protocol and ABI

`strling.interop@1.0.0` is a compact UTF-8 JSON request/response protocol with
four operations: description, canonical compile, exact profile inspection, and
Simply compile. It has no separate semantic checker; an idiomatic `check`
surface constructs a canonical compile request without artifact output. A
failed canonical result is a completed interop exchange, not a transport error.

The native ABI is stateless and exports three `_v1` symbols over borrowed input
bytes and a library-owned output descriptor. The WASM ABI exports memory,
allocation/deallocation, execution, response release, and version symbols over
the same byte protocol. Neither ABI exposes a Rust type or handle. Native calls
are reentrant and concurrent; WASM calls are serialized per instance, with
parallelism through independent instances. Cancellation is by deterministic
limits or outer process/module termination, not a mutable in-call token.

The exact request ceiling is 10 MiB and the exact response ceiling is 32 MiB.
Native unwind is caught before the C boundary. The portable WASM contract does
not falsely promise unwinding: unexpected panic traps one instance, while the
hostile-input corpus must remain panic-free. All pointer retention, allocator
crossing, implicit profile selection, filesystem/network access, shared-memory
WASM, publication, and host package migration are excluded.

## Frozen verification design

Before implementation, CP2 will create a shrinkage-resistant corpus covering:

-   all four operations and both Simply protocol versions;
-   canonical successful and failed compile results, exact-profile matching,
    profile inspection, and describe identity;
-   invalid UTF-8/JSON/envelopes, version and operation mismatch, missing or
    extra fields, target mismatch, and both byte ceilings;
-   null, zero, non-empty output, ownership, repeated same-descriptor free,
    stale-copy refusal rules, and deterministic allocation/release;
-   native panic containment, reentrancy, concurrent calls, and isolation;
-   WASM range/alignment checks, memory growth, serialization, release,
    instance isolation, and import/export closure;
-   ABI/header/module snapshots, generated-source ownership, platform builds,
    architecture fitness, and mutation tests that reject a shadow semantic
    dependency.

Passing a schema test alone will not certify memory safety, binary layout,
thread behavior, target availability, or host lifecycle.

CP2 freezes 77 unique cases at contract fingerprint
`sha256:1dc0797483c2b87a4653411c5d8abc0e4f2681fd3c82aa70ed8da3f72db585c5`
and evidence fingerprint
`sha256:5419a7a3f29525cfa6c4c7ddf2227d7c6700bf8cd73c5b27e48b8ef006964e90`.
The denominator is ten protocol successes, sixteen protocol failures, twelve
native-memory cases, four native-concurrency cases, twelve WASM-memory cases,
six ABI snapshots, four architecture/security cases, five platform builds, six
fuzz properties, and two sanitizer hooks.

Ten integrity tests enforce JSON Schema validity, both fingerprints, exact
family and total counts, unique identities, closed operation and platform
coverage, the ten error identities, and the no-import/no-shared-memory WASM
boundary. Removing or substituting a case remains invalid even after changing
declared counts or resigning the evidence fingerprint. These are frozen
requirements, not implementation results: platform, fuzz, sanitizer, native
lifecycle, and WASM-host claims remain unpassed until their named runners
execute in CP3/CP4.

## Minimal implementation and local proof

CP3 implements the four operations once in a safe byte dispatcher and places
all unsafe code at the native and raw WASM pointer edges. Native entrypoints
contain unwinding, retain no caller memory, use an owned response descriptor,
and remain reentrant. The WebAssembly build uses the same dispatcher, imports
no host capability, validates linear-memory ranges, copies request bytes before
response allocation, and isolates ownership per module instance.

The installed C header is generated only from `abi.json`, then captured by the
enforced `strling-interop` public declaration snapshot. The Rust dependency
graph is isolated by its own manifest and lockfile. The Rust toolchain normally
exports `__data_end` and `__heap_base` metadata globals for a `cdylib`; the
deterministic sealing step removes only those two known globals and rejects any
other unexpected export, producing the exact governed surface of memory plus
five functions.

Local proof at the pinned Rust 1.75 floor passes 19 Rust tests: three internal
serialization/panic tests, three native lifecycle tests, ten protocol tests,
and three bounded property tests. The property corpus executes 517 arbitrary
byte lengths, five structured envelope mutations, and 256 execute/free cycles.
The sealed WASM module passes exact six-export/zero-import inspection plus a
two-instance Node lifecycle covering allocate, write, execute, read, response
free, request/descriptor deallocation, malformed UTF-8, misalignment,
out-of-range pointers, nonempty descriptors, and instance isolation.

These local results certify `x86_64-pc-windows-msvc` behavior and
`wasm32-unknown-unknown` under the available Node host. They do not certify the
three other declared native targets, sanitizer runners, or cargo-fuzz; those
remain CP4 requirements.

CP4 now has a registered adversarial execution surface rather than runner-name
placeholders. Six cargo-fuzz binaries map exactly to the six frozen fuzz cases.
The structured `certification.interop-adversarial` operation runs 10,000
fixed-seed, bounded inputs per target on pinned `nightly-2026-08-01` and
`cargo-fuzz 0.13.2`, then executes the complete native test suite separately
under AddressSanitizer and LeakSanitizer and repeats the raw-WASM host memory
lifecycle. It is a Full/Release profile member and a dedicated Linux CI job.
The operation is deliberately unavailable outside x86_64 Linux, matching the
actual libFuzzer and sanitizer support boundary instead of treating bounded
Windows property tests as equivalent evidence.

Governed local Linux execution against the current Cargo lock now passes all
eight checks. Each fuzz target completes 10,000 fixed-seed bounded runs, for
60,000 executions total. The complete native test suite separately passes under
AddressSanitizer and LeakSanitizer, and the raw-WASM host again proves six
exports, zero imports, two isolated instances, and the
alloc-execute-read-free-dealloc lifecycle. The structured evidence file has
SHA-256
`352110d0d802c1359f08a6c4cd54265616b4f423fea7bb12aadcd882ad595b21`.

The generated lock pins `cc` 1.2.55 and `jobserver` 0.1.32, whose MSRVs are
both Rust 1.63, so the fuzz graph remains readable at the declared Cargo 1.75
floor. Live dependency-risk certification nevertheless remains fail-closed:
`libfuzzer-sys` 0.4.13 declares `(MIT OR Apache-2.0) AND NCSA`, which current
policy does not classify, and the out-of-scope historical Rust binding retains
RUSTSEC-2026-0204 in `crossbeam-epoch` 0.9.18. No waiver, policy expansion, or
unrelated binding update is inferred.

The CP4 migration review renewed the historical-observation baseline for the
pinned Node change from 22.18.0 to 22.23.2. All 20 Python observations are
byte-identical. Across all 24 TypeScript observations, requests, outcomes,
classifications, routes, and evidence are unchanged; only the reported runtime
version and its derived implementation fingerprint change. Three repeated runs
produce baseline fingerprint
`sha256:8d25fe6f42e4366b1f80fa3b281b534e0d0fb8f2d3b2ba002ce9d4adefd965b0`
and full-corpus fingerprint
`sha256:f20d028b8cb35399896e60662c77e81cd25e5ddd260f2412ab7ac8d8d8843553`.
The canonical-boundary, contract, corpus case sets, and route coverage
fingerprints remain unchanged, and the signed migration-explanation manifest
validates the renewed evidence.

At clean commit `a2d7cd14e905fac1c8c0ab23bc000a9b7434123e`, Local passes
33/33 operations. Pull Request reports 43 passed, zero failed, and 11
unavailable legacy tool ecosystems. Full reports 59 passed, one failed, and 37
unavailable across 97 operations; live dependency risk is the sole failed
operation.

## Checkpoint state

CP1 locks the boundary above without implementing or migrating a host package.
CP2 owns the now-frozen closed evidence denominator and mutation-resistant
verification. CP3 adds the minimal bridge, generated C header, and local
native/WASM proof. CP4 now has current-lock Linux adversarial proof but remains
blocked only on the dependency-risk policy/scope decision. Unavailable exact
PCRE2 and native-platform rows remain explicit environment dispositions, not
certification claims or additional hardgates. FINAL will record exact
protocol/ABI fingerprints, operation counts, memory/thread dispositions,
fuzz/sanitizer evidence, platform results, carry-forward, and P17-T02 readiness.
