# TypeScript API reference

[Package guide](../README.md) | [Compiler protocol](../../../spec/contracts/1.0/PROTOCOL.md)

The ESM package is a thin raw-WebAssembly client. It returns canonical JSON
values and does not implement an independent parser, emitter, or regex runtime.

## Entry points

-   `@strling-lang/strling` exports `WasmClient`, `instantiateWasm`, `Compiler`,
    `parse`, `parseToArtifact`, `sourceCompileRequest`, and the `simply` namespace.
-   `@strling-lang/strling/node` exports `loadBundledWasm()` and
    `loadWasmFile(path)`; these are the only Node filesystem loaders.
-   `@strling-lang/strling/simply` exports canonical Simply request builders.

`instantiateWasm(bytesOrModule)` constructs a client without fetching. Its
`describe`, `compile`, `inspectTargetProfile`, and `simplyCompile` methods cross
the governed `strling.wasm-abi` v1 boundary.

`new Compiler(client).compile(request, targetProfile?)` returns the canonical
`CompileResult`; `check` is the same operation. `sourceCompileRequest` defaults
to Semantic STRling. `parse` is a compatibility name for requesting canonical
semantic output, not a local AST. `parseToArtifact` requires both an exact
profile and its reference.

Simply `Pattern` values record recipes and expose `buildRequest(...)` and
`compile(...)`. `Pattern.exec`, `Pattern.toRegExp`, and implicit string
rendering intentionally throw: execute the pattern from a successful
`TargetArtifact` with its governed target runtime.
