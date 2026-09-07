# Python API reference

[Package guide](../README.md) | [Compiler protocol](../../../spec/contracts/1.0/PROTOCOL.md)

The Python package is a thin client for the canonical native kernel. Functions
return ordinary protocol dictionaries; they do not parse, emit, or execute a
regular expression locally.

## Native client

-   `load_native(library_path=None) -> NativeClient` loads the wheel's sealed
    library or one explicit library path.
-   `bundled_library_path() -> Path` returns the installed sealed-library path.
-   `NativeClient.describe()` returns the interop/kernel description.
-   `NativeClient.compile(compile_request, target_profile=None)` returns the
    canonical `CompileResult`.
-   `NativeClient.inspect_target_profile(target_profile)` validates and inspects
    one exact target profile.
-   `NativeClient.simply_compile(builder_request, target_profile=None)` executes
    one canonical Simply request.

Native loading, ABI, memory, and malformed-envelope failures raise
`NativeLoadError`, `NativeAbiError`, or `InteropProtocolError`. A normal compile
failure remains a returned `CompileResult` with structured diagnostics.

## Compile conveniences

-   `Compiler(client).compile(request, target_profile=None)` delegates to the
    native client; `check` is the same operation.
-   `source_compile_request(source, options=None, fallback_outputs=(...))` builds
    a versioned Semantic STRling source request. Use `frontend_id="legacy_regex"`
    only for the explicit compatibility frontend.
-   `parse(client, source, options=None)` is a compatibility name that requests
    canonical semantic output; it does not return a Python-owned AST.
-   `parse_to_artifact(client, source, options)` requires both
    `target_profile_reference` and the exact `target_profile`, then requests a
    canonical target artifact.

## Simply

`STRling.simply` exports request-recording constructors. A `Pattern` can
`build_request(...)` or `compile(client, compile_projection, target_profile)`.
`Pattern.exec` and implicit string rendering are intentionally unavailable;
execute a successful `TargetArtifact` with the governed target runtime.
