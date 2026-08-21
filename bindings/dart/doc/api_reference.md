# Dart adapter API

-   `NativeClient.load(absolutePath)` opens one governed native library.
-   `execute` transports one strict bounded JSON envelope.
-   `describe`, `compile`, `inspectTargetProfile`, and `simplyCompile` return
    canonical result data.
-   `sourceCompileRequest` records a canonical source compile request.
-   `simplyBuilderRequest` and generated `dateTime`, `email`, `ip`, `url`, and
    `uuid` helpers record Simply 1.1 recipes.
-   `close` is idempotent and rejects later calls; Dart does not expose an
    explicit `DynamicLibrary` unload operation.

The adapter supports Dart VM/native only and owns no compiler semantics.
