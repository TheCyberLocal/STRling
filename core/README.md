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
diagnostics through `diagnostic_generation::generate_diagnostics`. The
diagnostic stage preserves the five certified safety mappings and constructs a
closed set of proof-backed semantic quality findings from normalized Semantic
IR plus exact foundational and structural facts; it does not inspect raw regex
text or target behavior. Pure
semantic requirements and factual profile support are available through
`capability_evaluation::extract_requirements` and
`capability_evaluation::evaluate_capabilities`. Representation decisions are
available through `portability_planning::plan_portability`, whose certified
plans preserve exact capability and proof evidence without changing Semantic
IR. `explanation::explain_semantics` projects completed target-neutral stages
into the independently versioned semantic-explanation model, and
`explanation::explain_target` adds exact completed capability and portability
evidence. These functions do not rerun stages, inspect source syntax, infer
from emitted patterns, or add explanation data to `CompileResult` 1.0. The
`semantic_conversion::convert_semantic_program` projection renders validated
canonical Semantic IR to Semantic STRling or a direct-operation Simply 1.0
request, reconstructs through the existing destination frontend, and publishes
`exact` only when the normalized alpha projection is equal. Missing or invalid
Semantic STRling capture names remain explicit partial conversions; unsupported
backreference topology returns no executable output. Optional explanation and
target evidence is correspondence-checked and cannot influence conversion
semantics. The
crate-private target-aware pipeline certifies that planning follows capability
evaluation, while the existing `CompileResult` projection remains
target-neutral and produces no portability plan or artifact.

Source compilation is selected only by explicit `SourceDocument.frontend`
identity. `regex_frontend` preserves the frozen compatibility grammar, while
`semantic_frontend` implements the ratified `strling.semantic@1.0.0` grammar,
all 27 frozen `STRL-DSL-*` diagnostics, bounded direct lowering, source spans,
and canonical formatting. The Semantic formatter retains private syntax
evidence for comments and authored set order; accepted programs still pass
through the sole `normalization::normalize` and existing compiler pipeline.
Neither frontend reads files, selects targets, lowers artifacts, or owns
runtime behavior.

`SimplyBuilder` is the native Rust construction surface for the immutable
`strling.simply-builder@1.0.0` protocol and its backward-compatible `1.1.0`
extension. It stores canonical `semantic::Node` candidates directly, derives
stable node and capture identities from explicit host keys, enforces immutable
single-parent values and import provenance, and consumes the graph through
`normalization::normalize`. The `1.1.0` `stdlib_helper` operation carries only
a governed helper identity and parameter map; it delegates to the sole
`stdlib` builders before importing the resulting canonical Semantic IR.
`finish_program` returns canonical `SemanticProgram`; `finish_request` adds
only explicit compile routing. Callers then use the existing crate-root
`compile` facade. The Simply module does not parse regex, model a second AST or
compiler, select a target, lower, emit, or execute a runtime.

`decode_simply_builder_request` and `replay_simply_builder_request` provide the
typed inward edge for the TypeScript and Python Preview adapters. The additive
`./strling simply [--target-profile PATH]` JSON transport decodes one
`BuilderRequest`, replays it through `SimplyBuilder`, and returns either stable
construction errors or the canonical `CompileRequest` plus `CompileResult`.
The transport owns only bounded I/O and exact profile-file loading; host
adapters remain protocol serializers and do not discover or implement compiler,
target, emitter, or runtime behavior.

Additional parsing surfaces, rewrite application, general satisfiability or
language-inclusion solving, style-only warnings, target-specific portability diagnostics,
exploitability or target-runtime verdicts, capture numbering, lowering,
emission, editor presentation, non-Preview bindings, and product integrations
remain deferred to separately contained tasks.
