# STRling interop protocol and ABI contract 1.0

## Status and authority

This directory defines the normative `strling.interop` byte protocol version
`1.0.0`, native C ABI `strling.c-abi` version `1.0.0`, and raw WebAssembly ABI
`strling.wasm-abi` version `1.0.0`. Its authority is limited to operation
dispatch, UTF-8 JSON envelopes, resource ceilings, exported symbols, primitive
layouts, ownership, error isolation, threading, and version compatibility.

The canonical compiler contracts under [`spec/contracts/1.0`](../../contracts/1.0/README.md),
the Simply protocols under [`spec/frontends/simply`](../../frontends/simply),
and the authored target profiles remain authoritative for every embedded
semantic value. An interop implementation may decode, validate, dispatch, and
serialize those values. It may not parse a new language, infer a target,
reinterpret diagnostics, lower or emit independently, or expose Rust structs,
enums, trait objects, allocator details, or module paths as ABI.

[`interop.schema.json`](interop.schema.json) is the normative byte-envelope
schema. [`abi.json`](abi.json), validated by [`abi.schema.json`](abi.schema.json),
is the normative machine-readable ABI descriptor.

## Closed operation set

Version 1.0.0 exposes four synchronous, stateless operations:

-   `describe` returns the exact ABI descriptor implemented by the library or
    module;
-   `compile` accepts one canonical `CompileRequest` and the exact
    `TargetProfile` when the request names one, then returns the canonical
    `CompileResult` unchanged;
-   `target_profile.inspect` validates one supplied target profile and returns
    that profile plus its computed immutable reference; and
-   `simply.compile` accepts a governed Simply 1.0.0 or 1.1.0 BuilderRequest,
    supplies the exact target profile when required, and returns the matching
    versioned Simply adapter response.

There is no second semantic validator or target registry in this protocol.
An idiomatic host `check` call constructs a canonical `CompileRequest` whose
requested outputs exclude `target_artifact` and invokes `compile`. Structural
contract failure is an interop error; semantic invalidity is a valid failed
`CompileResult`. A lexical-shape standard helper therefore retains its
registered lexical guarantee and is not silently strengthened by the adapter.

`target_profile.inspect` never selects a profile by alias, filesystem path, or
ambient installation. Host packages may offer discovery conveniences, but
they must supply the exact profile bytes to this boundary.

## Encoding and deterministic results

Every request and response is one compact UTF-8 JSON object with no BOM,
trailing bytes, or newline. Unknown fields are rejected. The maximum request is
10,485,760 bytes and the maximum response is 33,554,432 bytes. These interop
ceilings are in addition to the tighter limits owned by embedded contracts and
the kernel.

A recognized operation that produces a canonical failed compile still returns
`status = completed`. `status = error` is reserved for interop dispatch,
version, envelope, payload, resource, or internal-boundary failure. Stable
error identity consists of `code` and JSON `path`; prose and host exceptions
are not part of the protocol.

The closed error identities are:

| Code                | Meaning                                                   |
| ------------------- | --------------------------------------------------------- |
| `STRL-INTEROP-0001` | Request bytes are not UTF-8.                              |
| `STRL-INTEROP-0002` | UTF-8 request bytes are not one JSON object.              |
| `STRL-INTEROP-0003` | The protocol envelope is structurally invalid.            |
| `STRL-INTEROP-0004` | The requested interop protocol version is unsupported.    |
| `STRL-INTEROP-0005` | The operation is unsupported by this protocol version.    |
| `STRL-INTEROP-0006` | The request exceeds the interop request-byte ceiling.     |
| `STRL-INTEROP-0007` | The operation payload violates its referenced contract.   |
| `STRL-INTEROP-0008` | The canonical typed kernel/Simply boundary rejects input. |
| `STRL-INTEROP-0009` | The response exceeds the interop response-byte ceiling.   |
| `STRL-INTEROP-0010` | The adapter cannot complete deterministic serialization.  |

For the same interop implementation version and identical request bytes, the
response bytes are deterministic. JSON object member order is the order emitted
by the typed serializer; this contract does not claim general RFC 8785
canonicalization for arbitrary caller JSON.

## Native C ABI

The native bridge is an additive crate under `bindings/interop` that depends
only on the public `strling-kernel` facade. It is not part of the kernel crate
and may contain the narrowly reviewed unsafe code needed to copy raw buffers at
the ABI edge. The kernel remains `#![forbid(unsafe_code)]`.

The C ABI exposes only fixed-width status values, byte pointers, `size_t`
lengths, and `strling_interop_owned_bytes_v1`. Callers initialize an output
descriptor to `{NULL, 0}` and pass it to `strling_interop_execute_v1`. On
`STRLING_INTEROP_STATUS_RESPONSE_WRITTEN`, the descriptor owns one library
allocation and must be released by
`strling_interop_owned_bytes_free_v1`. That function zeros the same descriptor
before returning, so null free and repeated free of that same descriptor are
no-ops. Copying an owning descriptor, freeing a stale copy, passing an invalid
non-null pointer, overlapping input and output storage, or mutating a buffer
during the call violates the caller contract.

The bridge borrows and copies input only for the duration of the call, retains
no callback or caller pointer, and never asks the caller to free Rust memory
directly. A non-empty output descriptor is rejected without mutation. Native
entrypoints use the platform C calling convention, catch Rust unwinding before
it crosses the ABI, and leave the output descriptor empty on a boundary-status
failure. Allocation failure may terminate the process under the Rust global
allocator and is not falsely represented as a recoverable status.

Native calls are reentrant and may run concurrently because version 1 has no
mutable global compiler or handle state. Each request, target profile, result,
and allocation is isolated to its call. Mid-call cancellation is not supported;
callers use canonical deterministic resource limits or isolate work in a
process they can terminate.

## Raw WebAssembly ABI

The WebAssembly artifact targets `wasm32-unknown-unknown`, exports its linear
memory, imports no filesystem, network, clock, randomness, environment, or
host callback, and exposes only the symbols in `abi.json`. Its request and
response bytes are identical to the native byte protocol.

The host obtains linear-memory storage through `strling_wasm_alloc_v1`, writes
the request after the final allocation that could grow memory, and supplies an
eight-byte, four-byte-aligned zeroed output descriptor. The descriptor contains
little-endian `u32 data` and `u32 len` fields. Execution validates all linear
memory ranges before copying the input. The response is freed through
`strling_wasm_owned_bytes_free_v1`, which zeros the descriptor; the descriptor
storage and request storage are then released exactly once with
`strling_wasm_dealloc_v1` using their original lengths.

WebAssembly version 1 has no shared-memory or threads proposal dependency.
Calls on one instance are serialized by the host; independent instances may run
concurrently. Unexpected Rust panic traps the current instance because portable
unwind containment is not promised for this target. Hostile and malformed
input must instead be rejected without panic, and a trapped instance must not
corrupt another instance. Mid-call cancellation is unsupported; terminating an
isolated instance is the host cancellation boundary.

## Versioning and compatibility

Protocol, native ABI, WebAssembly ABI, compiler, semantic specification,
Simply, target profile, and host-package versions are independent.
`describe` is the only negotiation operation. An unsupported protocol version
is rejected; there is no implicit latest-version fallback.

A binary-incompatible native or WebAssembly change requires a new symbol/type
major suffix such as `_v2` while `_v1` remains available for its documented
support window. Additive protocol operations or optional evidence require a
new compatible protocol version and explicit `describe` advertisement. A
change to an embedded canonical contract follows that contract's own
versioning rules and is not hidden behind an ABI patch.

## Platform certification and exclusions

The initial native certification targets are
`x86_64-unknown-linux-gnu`, `x86_64-pc-windows-msvc`,
`x86_64-apple-darwin`, and `aarch64-apple-darwin`; the WebAssembly target is
`wasm32-unknown-unknown`. A declared target is not certified until its build,
ABI snapshot, lifecycle, hostile-input, memory, and concurrency evidence has
run on the matching governed runner/runtime.

Version 1 does not migrate or remove any existing host package, publish a
library or module, promise WASI or browser-JavaScript wrappers, expose runtime
regex execution, resolve source/profile URIs, or support shared-memory WASM.
The historical C and Rust packages remain compatibility baselines until their
separately ordered migration task proves replacement.
