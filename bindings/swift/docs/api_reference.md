# Swift adapter API

-   `NativeClient.init(libraryPath:)` opens exactly one absolute native path.
-   `execute` transports one strict bounded JSON envelope.
-   `describe`, `compile`, `inspectTargetProfile`, and `simplyCompile` return
    canonical result data.
-   `sourceCompileRequest` records a canonical source compile request.
-   `simplyBuilderRequest` and generated `Essential.dateTime`, `email`, `ip`,
    `url`, and `uuid` functions record Simply 1.1 recipes.
-   `close` is idempotent, waits for in-flight calls, and rejects later calls.

The C target owns loading and descriptor release only. Compiler semantics and
target behavior remain canonical.
