# STRling Lua adapter

This rock is a thin Lua projection of the canonical STRling compiler. A minimal C module performs dynamic loading and bounded byte transport over a caller-selected `strling.c-abi` version 1 library; the Lua facade projects canonical requests and results. Neither layer implements STRling semantics.

The adapter is a provisional Preview candidate during the Fourth Edition migration. This is not a publication or permanent support-tier promise.

## Requirements

-   Lua `>= 5.1, < 5.5`
-   `lua-cjson >= 2.1, < 3.0`
-   a C toolchain compatible with the selected Lua ABI
-   a compatible native STRling library chosen by the application

## Use

```lua
local strling = require("strling")

local client = strling.load_native("/absolute/path/to/libstrling_interop.so")
local result = client:compile(strling.source_compile_request('literal "hello"'))

local builder = strling.simply_builder_request({ strling.email("root") }, "root")
local simply_result = client:simply_compile(builder)

client:close()
```

Generated helpers are lexical-shape recipes, not semantic validators. The adapter fails closed on path, ABI, symbol, UTF-8/JSON, duplicate-property, size, ownership, and lifecycle violations. There is no ambient loading, download, subprocess, socket, or local compiler.

See the [canonical interop contract](../../spec/interop/1.0/README.md) and the [migration record](../../docs/migration/dynamic-language-adapter-migration.md).
