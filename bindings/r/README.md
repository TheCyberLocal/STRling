# STRling R adapter

This package is a thin R projection of the canonical STRling compiler. Registered `.Call` routines perform explicit dynamic loading and bounded byte transport over a caller-selected `strling.c-abi` version 1 library; R functions project versioned requests and canonical results. The package does not implement parsing, semantics, validation, target planning, or emission.

The adapter is a provisional Preview candidate during the Fourth Edition migration. This is not a publication or permanent support-tier promise.

## Requirements

-   R `>= 4.3, < 5.0`
-   `jsonlite >= 1.8.8`
-   a compatible native STRling library chosen by the application

## Use

```r
library(strling)

client <- strling_load_native("/absolute/path/to/libstrling_interop.so")
result <- strling_compile(
  client,
  strling_source_compile_request('literal "hello"')
)

builder <- strling_simply_builder_request(list(sl_email("root")), "root")
simply_result <- strling_simply_compile(client, builder)

strling_close(client)
```

Generated helpers are lexical-shape recipes, not semantic validators. Loading is explicit and fails closed on path, ABI, symbol, encoding, JSON, duplicate-property, size, ownership, and lifecycle violations. No ambient or fallback compiler route exists.

See the [canonical interop contract](../../spec/interop/1.0/README.md) and the [migration record](../../docs/migration/dynamic-language-adapter-migration.md).
