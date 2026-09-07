# Ruby API reference

[Package guide](../README.md) | [Interop contract](../../../spec/interop/1.0/README.md)

The `Strling` module is a thin native-kernel adapter. It constructs protocol
hashes and returns canonical result hashes; it does not own STRling semantics
or execute emitted regexes.

## Module functions

-   `Strling.load_native(absolute_library_path)` returns a `NativeClient` for one
    caller-selected `strling.c-abi` v1 library.
-   `Strling.source_compile_request(source, options = {})` builds a canonical
    source request. Semantic STRling is the default; `frontend_id:
'legacy_regex'` explicitly selects compatibility syntax.
-   `Strling.stdlib_helper(step_id, helper_id, parameters = {})` builds one
    Simply standard-library step.
-   `Strling.simply_builder_request(steps, root_step_id, identity_namespace: ...)`
    builds a canonical Simply 1.1 request.
-   Generated helpers such as `Strling.email(step_id)` are lexical-shape recipes,
    not semantic validators.

## `Strling::NativeClient`

-   `describe`
-   `compile(compile_request, target_profile: nil)`
-   `inspect_target_profile(target_profile)`
-   `simply_compile(builder_request, target_profile: nil)`
-   `execute(interop_request)` for an explicit interop envelope
-   `library_path`, `closed?`, and `close`

A normal compiler rejection is returned as a structured `CompileResult`.
Loading, ABI, memory, lifecycle, JSON, and interop-envelope failures raise
`Strling::NativeAdapterError` or `Strling::InteropProtocolError` and remain
distinct from compiler diagnostics. The public module name is `Strling`, not
the retired all-caps `STRling` spelling.
