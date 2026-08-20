# STRling Python adapter

This package is the supported Python host adapter for the canonical STRling
compiler. It sends versioned JSON requests through `strling.c-abi` v1 using
`ctypes`; it does not contain an independent parser, validator, target emitter,
or standard-library implementation.

## Installation and runtime

Python 3.8 and later remain the declared support range. Platform wheels embed
the exact native interop library assembled from the governed Rust source. The
adapter never downloads a library, searches `PATH`, selects a semantic target,
or falls back to the historical Python compiler.

```python
from STRling import Compiler, load_native

client = load_native()
compiler = Compiler(client)

# Both objects are ordinary dictionaries pinned by the application.
result = compiler.compile(compile_request, exact_target_profile)
if result["outcome"] == "succeeded":
    print(result["artifact"])
```

Source-tree and development use can select one exact library explicitly:

```python
from STRling import load_native

client = load_native("/exact/path/to/libstrling_interop.so")
```

Canonical compile failures remain result values. Native loading, ABI, memory,
and interop-envelope failures use distinct adapter exceptions and preserve
stable interop codes and paths where the protocol supplies them.

## Simply requests

The `STRling.simply` namespace retains ergonomic constructors while recording
only canonical Simply protocol operations:

```python
from STRling import simply

pattern = simply.merge(simply.lit("A"), simply.digit(1, 3))
response = pattern.compile(client, compile_projection, exact_target_profile)
```

Standard helpers delegate by canonical registry identity. Helpers declared
`lexical_shape` remain lexical-shape helpers and may accept semantically invalid
values. `Pattern.exec` and implicit string rendering are retired because this
adapter does not simulate target-engine execution.

## Architecture

The host package owns only deterministic request construction, native-library
loading, bounded borrowed-input transfer, same-descriptor response release,
strict UTF-8/JSON projection, exceptions, package mechanics, and ergonomic
Simply recipes. Language semantics, diagnostics, portability, lowering,
serialization, and helper meaning remain in the canonical Rust kernel.
