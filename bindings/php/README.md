# STRling PHP adapter

This package is a thin PHP 8.2+ projection of the canonical STRling compiler. It uses the PHP FFI extension to call a caller-selected `strling.c-abi` version 1 library. It owns request construction, host data projection, and native lifecycle only; no PHP parser, semantic model, validator, target planner, or emitter remains.

The adapter is a provisional Preview candidate during the Fourth Edition migration. This is not a publication or permanent support-tier promise.

## Requirements

-   PHP `>= 8.2, < 9.0` with `ext-ffi` and `ext-json`
-   a compatible native STRling library chosen by the application

## Use

```php
<?php

use STRling\Requests;
use STRling\Stdlib;
use STRling\STRling;

$client = STRling::loadNative('/absolute/path/to/libstrling_interop.so');
$result = $client->compile(Requests::sourceCompileRequest('literal "hello"'));

$step = Stdlib::email('root');
$builder = Requests::simplyBuilderRequest([$step], 'root');
$simplyResult = $client->simplyCompile($builder);

$client->close();
```

Generated helpers record lexical-shape recipes; they do not promise semantic validity. The adapter rejects relative or missing paths, disabled FFI, ABI mismatch, missing symbols, malformed or oversized transport, duplicate JSON properties, release failure, and use after close. There is no ambient loading or fallback compiler.

See the [canonical interop contract](../../spec/interop/1.0/README.md) and the [migration record](../../docs/migration/dynamic-language-adapter-migration.md).
