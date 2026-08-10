# STRling canonical compiler kernel

`core/` is the reference Rust implementation of the contracts in
`spec/contracts/1.0`. The specification remains authoritative; this crate must
not generate normative expectations.

The kernel is a deterministic library. Its semantic operation does not depend
on filesystems, networks, command-line interfaces, editor tooling, host-language
bindings, or legacy compiler implementations. Runtime dependencies are limited
to serialization support. Tests may read specification-authored fixtures.

Current scope is deliberately structural: schema-backed domain types and
validation only. Parsing, normalization, analysis, planning, lowering,
emission, adapters, and tooling integrations belong to later contained tasks.
