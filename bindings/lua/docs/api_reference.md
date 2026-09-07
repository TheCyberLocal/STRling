# Lua API reference

[Package guide](../README.md) | [Interop contract](../../../spec/interop/1.0/README.md)

The Lua rock is a thin projection of the canonical native kernel. It constructs
versioned request tables and returns canonical result tables; it has no local
parser, emitter, target selection, or regex execution fallback.

## Module functions

-   `strling.load_native(absolute_library_path)` returns a client for one
    caller-selected `strling.c-abi` v1 library.
-   `strling.source_compile_request(source, options)` builds a canonical source
    compile request. Semantic STRling is the default; `frontend_id =
"legacy_regex"` explicitly selects compatibility syntax.
-   `strling.stdlib_helper(step_id, helper_id, parameters)` builds one Simply
    standard-library step.
-   `strling.simply_builder_request(steps, root_step_id, identity_namespace)`
    builds a canonical Simply 1.1 request.
-   Generated helpers such as `email(step_id)` are lexical-shape recipes, not
    semantic validators.

## Client methods

-   `client:describe()`
-   `client:compile(compile_request, target_profile)`
-   `client:inspect_target_profile(target_profile)`
-   `client:simply_compile(builder_request, target_profile)`
-   `client:execute(interop_request)` for an explicit interop envelope
-   `client:library_path()`, `client:is_closed()`, and `client:close()`

A normal compiler rejection is returned as a structured `CompileResult`.
Library, ABI, ownership, size, UTF-8, JSON, and interop-envelope failures raise
Lua errors and remain distinct from compiler diagnostics.
