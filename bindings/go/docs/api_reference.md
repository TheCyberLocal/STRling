# Go adapter API

-   `LoadNative(absolutePath)` loads exactly one `strling.c-abi` v1 library.
-   `NativeClient.Execute` transports one strict bounded JSON envelope.
-   `Describe`, `Compile`, `InspectTargetProfile`, and `SimplyCompile` return
    canonical result data.
-   `SourceCompileRequest` records a canonical source compile request.
-   `SimplyBuilderRequest` and the generated `DateTime`, `Email`, `IP`, `URL`,
    and `UUID` helpers record Simply 1.1 recipes.
-   `Close` is idempotent, waits for in-flight calls, and rejects later calls.

The adapter does not own STRling semantics or promise a target without an exact
canonical target profile.
