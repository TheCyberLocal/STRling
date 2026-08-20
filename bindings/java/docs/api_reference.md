# Java adapter API reference

[Back to the Java adapter](../README.md)

The exact governed surface is the generated
[`java-public-api` snapshot](../../../governance/contracts/snapshots/java-public-api.json).
This page describes the supported groups without duplicating their signatures.

| Package              | Supported surface                                                 | Contract                                                                             |
| -------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `com.strling`        | `Compiler`, `SourceCompileOptions`, `Strling`                     | Builds canonical source requests and returns canonical result data.                  |
| `com.strling.simply` | `Simply`, `SimplyBuilder`, `Pattern`, `Essential`, `STRlingError` | Records Simply 1.1 recipes; generated helpers retain their registry guarantee level. |
| `com.strling.jvm`    | Shared dependency, documented separately                          | Native transport and stable adapter errors; not Java semantics.                      |

`Compiler.compile` accepts an already constructed canonical request.
`Compiler.parse` is a compatibility name for a Semantic STRling source request.
`Compiler.parseToArtifact` requires an exact target profile and reference.
`describe` and `inspectTargetProfile` delegate to the corresponding canonical
interop operations.

The retired `com.strling.core`, `com.strling.core.nodes`, and
`com.strling.emitters` packages are not supported APIs. `Pattern.toString()`
and `Pattern.exec()` reject attempts to recreate host-owned regex rendering or
execution.

See the [shared bridge reference](../../jvm/README.md) and the
[canonical contracts](../../../spec/contracts/1.0/README.md).
