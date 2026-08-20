# C adapter reference

## Installed headers

-   `strling_interop.h` is the generated low-level `strling.c-abi` v1
    contract.
-   `strling.h` provides owned-response and raw JSON envelope conveniences.
-   `strling_simply.h` provides a Simply 1.1 construction adapter.
-   `strling_essential.h` provides canonical standard-helper selections.

The historical binding-local `src/core` headers, JSON-AST compiler, hint
engine, IR, PCRE2 emitter, and warning projection are intentionally removed.
Their declarations are not supported implementation APIs.

## Owned responses

`strling_c_result_v1` separates the native transport status from the owned
response bytes. When the status is
`STRLING_INTEROP_STATUS_RESPONSE_WRITTEN`, the bytes contain either a completed
operation—including a failed canonical compile result—or a structured
`STRL-INTEROP-*` response. Call `strling_c_result_free_v1` on the same result;
null and repeated frees are safe.

## Exact JSON conveniences

-   `strling_compile_json_v1` wraps one canonical `CompileRequest` and an
    optional exact `TargetProfile`.
-   `strling_simply_compile_json_v1` wraps one Simply 1.0/1.1
    `BuilderRequest` and an optional exact `TargetProfile`.
-   `strling_execute_v1` remains available for every closed interop operation,
    including `describe` and `target_profile.inspect`.

These functions do not parse or reinterpret embedded contract values. Missing
or mismatched profiles, malformed JSON, invalid UTF-8, unknown operations, and
contract failures retain their canonical interop identities.

## Simply construction

`sl_pattern_t` is an opaque host construction value. Combinators transfer
ownership of their child values to the returned parent. `sl_free` releases one
root graph. `sl_builder_request_json_v1` exposes the generated Simply request
for inspection, and `sl_compile_v1` submits it through the native ABI.

`sl_options_v1` maps only the closed semantic options supported by Simply:
case matching, builtin character domain, and wildcard line-terminator policy.
There is no ambient regex flag or target selection.

Essential functions create a `stdlib_helper` operation with the exact
registry identity and parameters. Unknown identities are sent to canonical
Simply replay and fail closed; the C adapter never substitutes a regex shape.
