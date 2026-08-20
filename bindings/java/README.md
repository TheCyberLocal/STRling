# STRling Java adapter

The Java package is a thin STRling 4.0 facade over the shared
`com.strling:strling-jvm` bridge. It does not contain a parser, compiler,
semantic IR, validator, diagnostic engine, or target emitter.

> **Migration status:** canonical adapter complete. The retired Java-owned
> implementation remains compatibility evidence, not the compiler boundary.

Semantic STRling is the flagship textual language. Regex-compatible text is an
import/compatibility surface, not Semantic STRling.
STRling 4.0 uses one canonical pipeline for Semantic, Simply, and explicit
compatibility requests.

## Build and test

The migration does not publish packages. From a source checkout, install the
shared bridge into a local Maven repository before building Java:

```text
cd bindings/jvm
mvn install
cd ../java
mvn test
```

Both artifacts target Java 11 and are certified on JDK 11, 17, and 21. The
runtime also needs an explicitly supplied absolute path to a compatible
`strling.c-abi` v1 native library.

## Canonical compile

```java
import com.strling.Compiler;
import com.strling.jvm.NativeClient;
import java.nio.file.Path;

try (NativeClient client = NativeClient.load(Path.of(args[0]).toAbsolutePath())) {
    Compiler compiler = new Compiler(client);
    Object result = compiler.parse("literal \"hello\"");
    System.out.println(result);
}
```

`Compiler.parse` is a compatibility name that returns canonical compile data,
never a Java-owned AST. Target artifacts require both an exact target-profile
reference and the matching profile document through `SourceCompileOptions`.
There is no ambient target selection.

## Simply and standard helpers

`com.strling.simply.Simply` records host-neutral Simply 1.1 recipes. A
`Pattern` is evaluated only by `Pattern.compile(NativeClient, ...)`; `exec()`
and implicit regex rendering are intentionally rejected.

`com.strling.simply.Essential` is generated from the canonical standard-library
registry and exposes `dateTime`, `email`, `ip`, `url`, and `uuid`. These helpers
currently promise `lexical_shape`, not semantic validity. For example, the IP
helper may accept a lexically shaped value whose numeric components are not a
valid IP address.

See the [Java API reference](docs/api_reference.md), the
[shared JVM bridge](../jvm/README.md), and the
[migration certification](../../docs/migration/jvm-adapter-migration.md).
