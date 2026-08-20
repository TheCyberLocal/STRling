# Canonical Java/Kotlin JVM adapter migration

## Outcome and authority

P17-T04 replaces the Java and Kotlin packages' binding-owned semantic
implementations with thin host facades over one shared JVM/native bridge. The
canonical compiler contracts, frontend contracts, exact target profiles,
Simply protocols, standard-library registry, and `strling.interop` 1.0 remain
the sole semantic authority.

The task starts from clean `architecture/v4` commit
`29158b75f78e7eb272d07374d6447c74c01c6f9c`. P17-T01 certifies the serialized
protocol and native C ABI, including ownership, panic containment, concurrency,
fuzzing, and Linux sanitizer behavior. P17-T02 certifies native Rust/C/C++
delegation, and P17-T03 supplies the current cross-binding certifier and exact
host-projection precedent.

## Starting inventory

The historical JVM packages contain 47 production sources and 8,549 lines:
36 Java files/6,210 lines and 11 Kotlin files/2,339 lines. Their 12 test sources
contain 2,151 lines and 96 statically declared JUnit test, test-factory, or
parameterized-test annotations. The production tree includes independent
parsers, compilers, node/IR models, hint and diagnostic synthesis, PCRE2
emitters, and Simply/Essential behavior. Those implementations are migration
evidence, not semantic authority.

At the task-start commit the exact 70-file Java/Kotlin binding tree fingerprints
to `sha256:3512df75e0ccde7f5a958ec4c6a7ff9329177ba13404f1e976c86a4b1730ed3d`.
The 47 production sources fingerprint to
`sha256:811b6c9b9585cbbb8534057deaa4d33342887eca0b197b9fd85ff0eb8e0a728d`.
The 51 manifest/build/public-source inputs fingerprint to
`sha256:4784769e5bff0cdc1c27cd6bbcd19038c8b1d66805c62a781bfd6d1c7016fef5`.
CP2 must convert those starting facts into a generated, shrinkage-resistant
compatibility baseline rather than relying on this prose.

The public-surface registry currently marks both `java-public-api` and
`kotlin-public-api` transitional and has no committed snapshots. Java needs a
pinned isolated compiler plus normalized `javap` extraction. Kotlin needs a
metadata-aware source/binary extractor that excludes compiler bridges while
preserving idiomatic signatures. CP2 must activate both mechanisms before any
product-source migration. The Windows host currently exposes no JDK or Maven on
`PATH`; no JVM build or test result is claimed by CP1.

## Locked bridge and dependency direction

```text
Java facade ────┐
                ├─> shared strling-jvm bridge ─> strling.c-abi v1
Kotlin facade ──┘                                      |
                                                       v
                                               strling-interop
                                                       |
                                                       v
                                               public strling-kernel
```

The shared bridge is a dedicated, semantic-free JVM artifact under
`bindings/jvm`. It maps the existing generated C declarations with JNA 5.19.1;
both language packages depend on that artifact and may not carry separate JNI,
JNA, Panama, subprocess, socket, or compiler implementations. JNA is selected
because it calls the existing stable C ABI without a new native shim, works
inside the governed Java 11-through-21 range, has one core artifact with
cross-platform native dispatch, and is available under Apache License 2.0. The
dependency is pinned exactly and must pass repository security, license, and
release-graph certification before CP4.

The bridge owns explicit native-library loading, exact ABI-version checking,
bounded UTF-8 byte transport, `size_t` and owned-buffer projection, same-
descriptor response release, compact JSON serialization, protocol-envelope
validation, host-value projection, and host error types. It must not parse
language source, validate semantic meaning, select a target, plan portability,
lower or emit a target artifact, implement a standard helper, execute regex, or
fall back to a historical JVM compiler.

## Public-surface dispositions

| Package | Preserved canonical facade | Explicit compatibility disposition |
| --- | --- | --- |
| Shared JVM | Explicit `NativeClient` loading and the four interop operations; immutable JSON request/result projection; stable load, ABI, transport, and protocol errors. | No implicit PATH search, network download, native compilation, semantic fallback, ambient target, or runtime regex execution. Bridge types are additive and contain no language-specific Simply behavior. |
| Java | `com.strling.Strling.VERSION`; idiomatic `com.strling.simply` builder names and mechanically representable overloads; generated Essential identities; canonical compile, parse, artifact, inspect-profile, describe, and Simply conveniences. | `com.strling.core`, `com.strling.core.nodes`, and `com.strling.emitters` expose binding-owned AST/IR/parser/compiler/emitter behavior and are breaking retirements. A compatibility `Simply.build` may survive only as deprecated delegation to an exact generated `pcre2-10.43` profile, never as a local emitter or repository default. |
| Kotlin | `strling.STRling.version()`; idiomatic `Simply`, `Pattern`, and `Essential` names; nullability/default-argument/collection ergonomics where mechanically representable; canonical compile, parse, artifact, inspect-profile, describe, and Simply conveniences. | `strling.core` and `strling.emitters` are breaking semantic-copy retirements. Public `Pattern.node` exposes the local node model and must be replaced by an opaque canonical Simply recipe. Any compatibility rendering must delegate to the exact disclosed profile and refuse unrepresentable inputs. |

Preserving a name does not preserve a local AST, IR, parser result, emitter,
diagnostic, or target-default contract. CP2 snapshots every public class,
constructor, method, field/property, overload/default, exception, nullability,
collection, package/module route, artifact shape, and compatibility decision.
Additions, deprecations, signature changes, and removals must be classified
explicitly in generated Java and Kotlin contract evidence.

## Target, errors, lifecycle, concurrency, and classloaders

Canonical compile calls require an exact caller-supplied target profile. A
deprecated targetless string convenience may use only the generated and
disclosed `pcre2-10.43` profile and must remain separate from canonical APIs.
There is no ambient repository, JVM, operating-system, or host-language target.

Canonical failed compile results remain values. Stable diagnostic and interop
codes, JSON paths, spans, target identity, result data, and artifacts remain
recoverable after projection. Missing/unloadable native libraries, ABI
mismatch, allocation failure, malformed UTF-8/JSON, closed-client use, and JNA
mapping failures are host or transport errors and remain distinguishable from
canonical failures. Java exceptions are unchecked typed adapter exceptions;
Kotlin exposes the same underlying identities without inventing a second
exception hierarchy.

`NativeClient` is immutable after successful load and safe for concurrent
calls because the native ABI is reentrant and each request owns a distinct
input, output descriptor, and `finally` release path. Close prevents future
calls and releases bridge-owned temporary resources; the operating-system
library handle remains process/classloader-scoped because deterministic native
unload is not promised by the JVM. Library selection is explicit by absolute
path or by an exact packaged platform/architecture classifier. No current
directory, `PATH`, system-library, Maven Central, or network fallback is
allowed. Duplicate classloader loads must not share mutable request state.

The governed JVM execution matrix is JDK 11, 17, and 21. Package/runtime rows
are recorded separately for Windows x86_64, Linux x86_64, and any additional
platform classifier actually built and executed. CP4 must report unavailable
rows exactly and cannot infer macOS, Linux, or alternate-architecture support
from compilation alone.

## Simply and standard-library boundary

Java and Kotlin Simply builders may construct protocol recipes and preserve
idiomatic overload, default-argument, and fluent syntax, but evaluation occurs
only through `simply.compile` on the shared bridge. Generated helper names and
metadata derive from the canonical registry. A helper declared
`lexical_shape` may accept semantically invalid values; neither JVM facade may
silently strengthen it into a semantic validator. Future helpers that promise
semantic validation must use canonical semantic validation, never host regex or
string approximation.

## Historical evidence and retirement gates

The frozen removal denominator is 35 files: all 26 Java `core` files, the Java
PCRE2 emitter, all seven Kotlin `core` files, and the Kotlin PCRE2 emitter. It
fingerprints to
`sha256:e023c47d5dbe9ff63870d04f46d4c0005f4e553398ef21a14ff0aeaed6975a9e`
at the task-start commit. Java's eight `simply` sources and Kotlin's three top-
level facade sources are not counted as deletions because their paths may be
rewritten into thin recipes; CP2 must still freeze their historical behavior.

Semantic copies are retired only after all of these hold:

1. CP2 freezes public, package, compatibility, JVM, platform, load, lifecycle,
   concurrency, classloader, error, Simply, standard-library, cross-binding,
   architecture, deletion, and historical denominators with mutation tests.
2. Replacement facades produce canonical requests, results, diagnostics, and
   artifacts for every applicable case; intentional differences are reviewed
   and recorded.
3. Public snapshots identify every compatible, deprecated, additive, and
   breaking Java/Kotlin change.
4. Architecture fitness proves both packages use the same `strling-jvm`
   artifact and that no product parser/compiler/IR/validator/hint/emitter or
   alternate native bridge is compiled or reachable.
5. Historical runners execute an authenticated task-start bundle and can never
   become a product fallback.

## Packaging, verification, and exclusions

CP3/CP4 certify clean shared-bridge, Java, and Kotlin package builds; isolated
consumers; exact JDK rows; native load/refusal; ownership and repeated release;
concurrent calls; classloader isolation; Unicode and malformed data; Simply and
all registered helper variants; canonical cross-binding parity; public and
generated contracts; architecture; security/license; migration differential;
Local, Pull Request, and Full profiles; and a clean tracked tree.

The task may pin Maven execution, use the existing Gradle wrapper, add the
shared bridge build, regenerate registered dependency locks/verification
metadata, public snapshots, standard-library projections, version metadata,
and immutable migration evidence from their governing sources. It may not
change a package version, language semantic, canonical schema, target profile,
interop ABI, support tier, or non-JVM binding implementation. No package
publication, release, tag, upload, branch push, or public distribution is
authorized.
