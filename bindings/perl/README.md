# STRling Perl adapter

This distribution is a thin Perl projection of the canonical STRling compiler. `FFI::Platypus` carries strict JSON over a caller-selected `strling.c-abi` version 1 library. The distribution no longer owns parsing, semantics, validation, target selection, or regex emission.

The adapter is a provisional Preview candidate during the Fourth Edition migration. This is not a publication or permanent support-tier promise.

## Requirements

-   Perl `>= 5.10, < 6.0`
-   `FFI::Platypus >= 2.10` and `JSON::PP >= 4.00`
-   a compatible native STRling library chosen by the application

## Use

```perl
use STRling qw(load_native source_compile_request simply_builder_request email);

my $client = load_native('/absolute/path/to/libstrling_interop.so');
my $result = $client->compile(source_compile_request('literal "hello"'));

my $builder = simply_builder_request([email('root')], 'root');
my $simply_result = $client->simply_compile($builder);

$client->close();
```

Generated helpers are lexical-shape recipes, not semantic validators. Native loading is absolute and explicit; ABI, symbol, encoding, JSON, duplicate-property, size, ownership, and closed-client failures stop execution. No ambient lookup or alternate compiler route exists.

See the [canonical interop contract](../../spec/interop/1.0/README.md) and the [migration record](../../docs/migration/dynamic-language-adapter-migration.md).
