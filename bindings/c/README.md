# STRling for C

This package is a thin C adapter over the generated `strling.c-abi` v1
surface. It owns byte-envelope conveniences, C allocation handles, and Simply
construction ergonomics; all parsing, validation, portability planning,
lowering, emission, diagnostics, and standard-helper semantics remain in the
canonical Rust kernel behind `strling-interop`.

## Build and test

```text
cmake -S bindings/c -B bindings/c/build -DSTRLING_C_WARNINGS_AS_ERRORS=ON
cmake --build bindings/c/build --config Release
ctest --test-dir bindings/c/build -C Release --output-on-failure
```

The build invokes the governed local Cargo manifest and links the resulting
static interop library. It does not download or publish a compiler.

Install to a local prefix with:

```text
cmake --install bindings/c/build --config Release --prefix /local/prefix
```

An external CMake consumer can then use `find_package(strling-c CONFIG)` and
link `STRling::c`. The installed closure is `strling.h`,
`strling_simply.h`, `strling_essential.h`, `strling_interop.h`, the C adapter
archive, the native interop archive, and the CMake package files.

## Canonical execution

`strling_execute_v1` forwards exact borrowed bytes. The convenience functions
`strling_compile_json_v1` and `strling_simply_compile_json_v1` only wrap
already-versioned JSON values in the fixed interop envelope. They never infer
a target; a target-aware request requires the exact caller-provided profile.

Responses remain owned by the interop library until
`strling_c_result_free_v1` zeros the same descriptor. A canonical failed
compile is still a JSON result value with a successful transport status.

## Simply and standard helpers

`strling_simply.h` builds a bounded Simply 1.1 construction graph and submits
it through `simply.compile`. The familiar literal, sequence, capture, repeat,
anchor, wildcard, and character-set helpers serialize governed operation IDs;
they do not implement an AST or regex emitter.

`strling_essential.h` selects canonical registry helper IDs. Current helpers
retain their registered lexical-shape guarantees and are not semantic
validators.

See [the API reference](docs/api_reference.md) for ownership and compatibility
details.
