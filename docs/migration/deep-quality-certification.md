# Property, fuzz, sanitizer, and mutation certification

[← Back to Architecture](../architecture.md)

P18-T03 defines the verification boundary for STRling 4.0 deep-quality
certification. It tests behavior delegated by existing specifications and
contracts; it cannot create language semantics, target facts, diagnostics,
adapter behavior, public APIs, or support promises.

The starting kernel already has 21 dedicated property suites containing 58
test entrypoints. Those suites exercise deterministic and idempotent
normalization, semantic and structural analysis, capability and portability
planning, compiler boundaries, Semantic DSL and Simply frontends, diagnostics,
explanation and conversion, and target lowering and serialization. Interop
adds three deterministic hostile-boundary properties. P18-T03 will make these
obligations visible through structured evidence instead of treating an
aggregate Cargo success as a complete deep-quality claim.

P17's interop evidence remains independently governed: its 77-case contract,
six fixed-run libFuzzer targets, native ASan and LSan runs, and raw-WASM host
memory lifecycle do not move into T03 or change denominator. T03 adds separate
coverage for the canonical Semantic DSL and legacy-regex parsers, protocol
decoders, normalization and analysis, target serializers, and malformed host
data. New fuzz binaries stay publish-false and use the existing fuzz-only
dependency root; they cannot enter runtime or publishable graphs.

Focused source mutation will run only in isolated temporary copies. A checked
manifest will name exact critical source locations, deterministic mutation
operators, killing tests, time budgets, and criticality-specific thresholds.
Surviving critical mutants, missing tests, denominator shrinkage, or stale
source fingerprints will fail closed. Fixture mutation and fuzz-smoke tests do
not count as source-mutation kills.

Profile cost is explicit. Local retains fast offline contract checks. Pull
Request adds deterministic properties and a bounded critical-mutation subset.
Full and scheduled Linux add bounded core fuzzing, C/C++ and interop native
sanitizers, and the complete mutation campaign. Every producer emits the
shared structured certification result contract with exact toolchain,
platform, seed, budget, denominator, status, and fingerprint evidence.

This task does not repair the F# quality, Python package, or dependency-risk
findings recorded by P18-T02; their assigned later tasks remain authoritative.
It also does not change product source, public contracts, target profiles,
packages, support tiers, release policy, or global regex-engine research.
