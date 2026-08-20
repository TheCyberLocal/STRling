# Kotlin adapter API reference

[Back to the Kotlin adapter](../README.md)

The exact governed source and binary surface is the generated
[`kotlin-public-api` snapshot](../../../governance/contracts/snapshots/kotlin-public-api.json).

| Package           | Supported surface                                                 | Contract                                                                          |
| ----------------- | ----------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `strling`         | `Compiler`, `SourceCompileOptions`, `STRling`                     | Builds canonical requests and returns canonical result data.                      |
| `strling`         | `Simply`, `SimplyBuilder`, `Pattern`, `Essential`, `STRlingError` | Idiomatic Kotlin projection of Simply 1.1 and registry-derived helper identities. |
| `com.strling.jvm` | Public compile dependency                                         | The shared native transport and adapter-error surface.                            |

`Compiler.compile` accepts a canonical request. `Compiler.parse` is a
compatibility name for a Semantic STRling source request, and
`parseToArtifact` requires an exact target profile and reference. Kotlin
defaults, nullability, and collections are host ergonomics only; they do not
create semantics.

The retired `strling.core` and `strling.emitters` packages are not supported
APIs. `Pattern.toString()` and `Pattern.exec()` reject local regex rendering or
execution. Generated `Essential` helpers preserve `lexical_shape` behavior and
do not claim semantic validation.

See the [shared bridge reference](../../jvm/README.md) and the
[canonical contracts](../../../spec/contracts/1.0/README.md).
