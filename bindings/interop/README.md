# STRling canonical interop bridge

This crate is the reference implementation of
[`strling.interop` 1.0](../../spec/interop/1.0/README.md). It exposes one safe
byte dispatcher plus the generated native C and raw WebAssembly ABI symbols.
Every operation delegates semantic work to the public `strling-kernel` facade.

The bridge owns only bounded UTF-8 JSON decoding/encoding, operation dispatch,
exact target-profile transport, Simply replay transport, raw buffer ownership,
and platform ABI mechanics. It does not contain a parser, semantic validator,
target registry, planner, lowerer, emitter, or runtime executor. The historical
`bindings/c` and `bindings/rust` packages remain separate compatibility
baselines until P17-T02.

Use the checked-in generated header at
[`include/strling_interop.h`](include/strling_interop.h). Regenerate it with:

```text
python tooling/interop_contract.py --write-header
```

Run focused native verification from the repository root with:

```text
cargo test --manifest-path bindings/interop/Cargo.toml --all-targets --locked
```

The raw WebAssembly artifact is a `cdylib` for `wasm32-unknown-unknown`. A
declared target or export mapping is not a certification result until the
matching governed host/runtime evidence executes.
