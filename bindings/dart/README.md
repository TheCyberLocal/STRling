# STRling Dart adapter

The Dart package is a semantic-free `dart:ffi` facade for Dart VM/native
runtimes. Web runtimes are not supported. A caller must supply an absolute path
to the governed `strling.c-abi` v1 library.

```dart
final client = NativeClient.load('/absolute/path/to/libstrling_interop.so');
final request = sourceCompileRequest("'hello'");
final result = client.compile(request);
client.close();
```

`describe`, `compile`, `inspectTargetProfile`, and `simplyCompile` preserve
canonical JSON results. Canonical rejected responses use
`InteropProtocolException`; loading, ABI, lifecycle, size, encoding, and
transport failures use `NativeAdapterException`.

Generated Essential helpers create Simply 1.1 `stdlib_helper` steps and retain
their `lexical_shape` guarantee. They do not validate semantic correctness.
Dart owns the `DynamicLibrary` lifetime, so `close` refuses later calls but does
not promise deterministic operating-system unload.
