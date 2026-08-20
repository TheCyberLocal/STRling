# STRling shared JVM bridge

`com.strling:strling-jvm:3.0.0` is the single semantic-free JVM bridge used by
the Java and Kotlin adapters. It maps the governed `strling.c-abi` v1 through
JNA and projects strict JSON values into immutable Java collections.

## Runtime contract

Load a native library by absolute path:

```java
try (NativeClient client = NativeClient.load(nativePath.toAbsolutePath())) {
    Object description = client.describe();
}
```

The bridge verifies ABI version 1 before executing requests, bounds request and
response sizes, rejects malformed UTF-8/JSON and duplicate keys, releases every
owned response through the same native descriptor, and distinguishes load,
ABI, transport, lifecycle, and canonical protocol errors. `NativeClient` is
immutable and reentrant. Closing it prevents later calls but does not promise
deterministic JVM native-library unload.

There is no current-directory, `PATH`, system-library, registry-download, or
network fallback. The certified artifacts contain no native classifier; the
caller supplies the platform library. P17-T04 executed Windows x86_64 only and
does not infer Linux, macOS, or alternate-architecture runtime support.

## Dependencies and release graph

The exact runtime graph is checked in at
[`tests/adapters/3.0/release-graph.json`](../../tests/adapters/3.0/release-graph.json).
JNA 5.19.1 uses its Apache-2.0 license branch. Jackson 2.18.9 is pinned after
live advisory remediation. Java and Kotlin share this bridge and may not carry
an alternate JNA/JNI/Panama or semantic route.

No package publication or native distribution is performed by the migration
certification.
