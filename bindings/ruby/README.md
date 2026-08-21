# STRling Ruby adapter

This package is a thin Ruby projection of the canonical STRling compiler. It does not contain a parser, semantic model, validator, target planner, or regex emitter. The caller supplies an absolute path to a `strling.c-abi` version 1 library; Ruby's standard `Fiddle` interface carries strict JSON requests and canonical results across that boundary.

The adapter is a provisional Preview candidate during the Fourth Edition migration. This is not a publication or permanent support-tier promise.

## Requirements

-   Ruby `>= 3.0, < 4.0`
-   a compatible native STRling library chosen by the application

## Use

```ruby
require 'strling'

client = Strling.load_native('/absolute/path/to/libstrling_interop.so')
result = client.compile(Strling.source_compile_request('literal "hello"'))

step = Strling.email('root')
builder = Strling.simply_builder_request([step], 'root')
simply_result = client.simply_compile(builder)

client.close
```

The five generated standard-library helpers are lexical-shape recipes. They do not claim that accepted text is semantically valid.

Loading is explicit and fails closed: relative or missing paths, ABI mismatch, missing symbols, invalid UTF-8/JSON, duplicate JSON properties, oversized messages, release failures, and use after close are errors. The package never searches ambient library names and has no subprocess, socket, download, or local-compiler fallback.

See the [canonical interop contract](../../spec/interop/1.0/README.md) and the [migration record](../../docs/migration/dynamic-language-adapter-migration.md).
