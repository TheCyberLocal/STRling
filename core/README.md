# STRling canonical compiler kernel

`core/` is the reference Rust implementation of the contracts in
`spec/contracts/1.0`. The specification remains authoritative; this crate must
not generate normative expectations.

The kernel is a deterministic library. Its semantic operations do not depend on
filesystems, networks, command-line interfaces, editor tooling, host-language
bindings, or legacy compiler implementations. Runtime dependencies are limited
to serialization and contract fingerprinting support. Tests may read
specification-authored fixtures.

Current executable scope is deliberately narrow: schema-backed domain types,
validation, pure canonical Semantic IR normalization through
`normalization::normalize`, foundational semantic facts through
`semantic_analysis::analyze`, structural facts through
`structural_analysis::analyze_structure`, structured target-neutral safety
evidence through `safety_analysis::analyze_safety`, and canonical contract
diagnostics through `diagnostic_generation::generate_diagnostics`. A
crate-private pipeline certifies the ordering of those stages and projects
diagnostics into `CompileResult` without requiring portability or an artifact.
Parsing, target capability and portability diagnostics, exploitability or
target-runtime verdicts, automatic rewrites, lowering, emission, bindings,
editor presentation, adapters, and product integrations remain deferred to
separately contained tasks.
