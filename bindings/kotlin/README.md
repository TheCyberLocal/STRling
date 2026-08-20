# STRling Kotlin adapter

The Kotlin package is an idiomatic thin facade over the same
`com.strling:strling-jvm` bridge used by Java. It contains no independent
parser, compiler, semantic IR, validator, diagnostics, or target emitter.

> **Migration status:** canonical adapter complete. The retired Kotlin-owned
> implementation remains compatibility evidence, not the compiler boundary.

Semantic STRling is the flagship textual language. Regex-compatible text is an
import/compatibility surface, not Semantic STRling.
STRling 4.0 uses one canonical pipeline for Semantic, Simply, and explicit
compatibility requests.

## Build and test

The migration does not publish packages. From a source checkout, first install
`bindings/jvm` into the configured local Maven repository, then run:

```text
cd bindings/kotlin
./gradlew test
```

The adapter targets Java 11 and is certified on JDK 11, 17, and 21. Runtime
calls require an explicitly supplied absolute path to a compatible
`strling.c-abi` v1 native library.

## Canonical compile

```kotlin
import com.strling.jvm.NativeClient
import java.nio.file.Path
import strling.Compiler

NativeClient.load(Path.of(args[0]).toAbsolutePath()).use { client ->
    val compiler = Compiler(client)
    println(compiler.parse("literal \"hello\""))
}
```

`Compiler.parse` returns canonical compile data, never a Kotlin-owned AST.
Target artifacts require an exact target-profile reference and the matching
profile document through `SourceCompileOptions`; there is no ambient target.

## Simply and standard helpers

`Simply` records host-neutral Simply 1.1 recipes while retaining Kotlin
defaults and nullability where those are mechanically representable. A
`Pattern` is evaluated only through `Pattern.compile`; runtime-regex execution
and implicit rendering are rejected.

`Essential` is generated from the canonical registry and exposes `dateTime`,
`email`, `ip`, `url`, and `uuid`. The current guarantee is `lexical_shape`, not
semantic validity, so the host adapter deliberately does not strengthen these
helpers with local validation.

See the [Kotlin API reference](docs/api_reference.md), the
[shared JVM bridge](../jvm/README.md), and the
[migration certification](../../docs/migration/jvm-adapter-migration.md).
