# STRling Go adapter

The Go module is a semantic-free facade over the governed `strling.c-abi` v1.
It requires a caller-supplied absolute path to the native library and cgo for
execution. `CGO_ENABLED=0` builds fail closed with `ErrCgoUnavailable`.

```go
client, err := strling.LoadNative(`/absolute/path/to/libstrling_interop.so`)
if err != nil { /* handle host loading failure */ }
defer client.Close()

request := strling.SourceCompileRequest("'hello'", nil)
result, err := client.Compile(request, nil)
```

`Describe`, `Compile`, `InspectTargetProfile`, and `SimplyCompile` preserve the
canonical JSON result. Canonical rejected responses become `ProtocolError`;
loading, ABI, lifecycle, size, encoding, and transport failures remain
`NativeError` values.

The generated Essential helpers create Simply 1.1 `stdlib_helper` steps. They
retain the registry's `lexical_shape` guarantee and do not validate semantic
correctness. No ambient library probing, network download, subprocess route,
socket route, package-local parser, target selection, or regex emitter exists.
