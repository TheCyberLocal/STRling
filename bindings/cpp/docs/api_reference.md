# C++ adapter API

## `strling::response`

`response` owns the native response buffer. It is non-copyable, nothrow
move-constructible and move-assignable, and releases the buffer exactly once in
its nothrow destructor. A moved-from response is empty.

-   `transport_status()` returns only the C ABI transport status.
-   `owns_bytes()` reports whether a native response buffer is owned.
-   `bytes()` provides a borrowed view valid until the response is moved,
    assigned, or destroyed.
-   `text()` returns an owning copy.

Canonical failed compilation is encoded in the response JSON and is not a
transport exception.

## `strling::client`

-   `execute` transports exact bytes, including invalid UTF-8 for canonical
    boundary rejection tests.
-   `execute_json` transports one interop envelope.
-   `compile_json` mechanically wraps a canonical `CompileRequest` JSON value and
    an optional exact `TargetProfile` JSON value.
-   `simply_compile_json` mechanically wraps a Simply 1.0/1.1 `BuilderRequest`.

Target-aware requests do not infer or substitute a profile. Embedded NUL bytes
in wrapper inputs are rejected before dispatch because the stable C convenience
contract accepts NUL-terminated JSON.

## `strling::simply`

`pattern` is a move-only RAII owner of the opaque C construction handle.
Factories include `literal`, `digit`, `any_of`, `dot`, `start`, `end`,
`capture`, `may`, variadic `merge`, and `stdlib_helper`. `builder_request`
serializes the governed Simply 1.1 request; `compile` dispatches that request
through the canonical interop bridge.

`options` maps exactly to canonical case matching, built-in character domain,
and wildcard line-terminator behavior. C++ does not normalize Unicode or
construct regex source.

## `strling::essential`

The eight compatibility names select registered helper IDs and variants:

-   `email`, `url`, `uuid`, `uuid_v4`
-   `ip_v4`, `ip_v6`, `ip_any`, `date_time`

Unknown helpers fail through canonical Simply replay. Registered lexical-shape
helpers may intentionally accept semantically invalid values.
