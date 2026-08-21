# STRling Swift adapter

The Swift package is a semantic-free facade over a small C loader target and
the governed `strling.c-abi` v1. A caller supplies an absolute native library
path; the package performs no ambient lookup or download.

```swift
let client = try NativeClient(libraryPath: "/absolute/path/to/libstrling_interop.dylib")
let request = sourceCompileRequest("'hello'")
let result = try client.compile(request)
client.close()
```

`describe`, `compile`, `inspectTargetProfile`, and `simplyCompile` preserve
canonical JSON results. Canonical rejected responses use
`InteropProtocolError`; loading, ABI, lifecycle, size, encoding, and transport
failures use `NativeAdapterError`.

Generated `Essential` helpers create Simply 1.1 `stdlib_helper` steps. Their
guarantee is `lexical_shape`, not semantic validation. Apple, Linux, and Windows
support claims require execution under the governed CP4 toolchain matrix.
