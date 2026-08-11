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
diagnostics through `diagnostic_generation::generate_diagnostics`. Pure
semantic requirements and factual profile support are available through
`capability_evaluation::extract_requirements` and
`capability_evaluation::evaluate_capabilities`. Representation decisions are
available through `portability_planning::plan_portability`, whose certified
plans preserve exact capability and proof evidence without changing Semantic
IR. The crate-private target-aware pipeline certifies that planning follows
capability evaluation, while the existing `CompileResult` projection remains
target-neutral and produces no portability plan or artifact.

Parsing, rewrite application, target-specific portability diagnostics,
exploitability or target-runtime verdicts, capture numbering, lowering,
emission, bindings, editor presentation, adapters, and product integrations
remain deferred to separately contained tasks.
