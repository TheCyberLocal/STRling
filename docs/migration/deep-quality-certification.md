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

Focused source mutation runs only in isolated temporary copies. The checked
manifest names exact critical source locations, deterministic mutation
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

The CP2 contract closes fourteen property obligations over sixteen authenticated
test sources. It also closes eleven fuzz targets: six inherited P17 targets and
five T03-owned targets for Semantic DSL, legacy regex, compiler protocol,
normalization/analysis, and target serialization. Each Full target is bounded
to 10,000 runs, 16,384-byte inputs, a ten-second per-input timeout, and 4,096
MiB RSS. Minimized regression retention is capped at 64 files and one MiB.

The sanitizer matrix contains four cases. P17 retains its Rust ASan/LSan and
raw-WASM host-memory cases. T03 adds C and C++ ASan/UBSan integration on
governed x86_64 Linux without changing adapter sources. The mutation campaign
contains fourteen exact source mutants across seven critical-logic categories:
eight Critical and six High. Both classes require a 100% kill rate and zero
survivors. Pull Request runs seven representative Critical mutants; Full runs
all fourteen. The authored manifest fingerprints to
`sha256:14690c765704c433d5a4dd023d5b75c0d8eaf9cdea56c0cbb35fcd0dae072cff`.

CP3 activates the five T03 fuzz targets and binds each to one authenticated
canonical seed. The targets exercise arbitrary UTF-8 through Semantic DSL and
legacy-regex parsing, arbitrary JSON through compiler-request decoding and
Semantic IR normalization/analysis, and generated literal programs through all
five governed target profiles. Repeated outcomes and successful canonical
round trips must agree; malformed inputs may be rejected but may not panic.
The active manifest fingerprint is
`sha256:bf1bc3a973f67300305e3a52c79f90055d5f238f73e31cc7a88b0b5252e6974f`.
It fingerprints the sixteen unique test sources used by the mutation commands
as well as every mutated critical source, so strengthening or weakening a
killing assertion necessarily changes the evidence identity.

The controller executes authored commands directly, records output hashes and
exact statuses, and binds the ordered check-status projection into its evidence
fingerprint. Mutation baselines and mutated commands run from a temporary copy
of tracked repository files, with build output in the same temporary root.
C and C++ sanitizer configuration, builds, and tests likewise use temporary
CMake trees with AddressSanitizer and UndefinedBehaviorSanitizer set to halt on
the first finding. A non-Linux Full invocation reports every owned fuzz and
sanitizer case as unavailable rather than skipping or promoting it.

CP4 registers three cumulative structured operations in the canonical quality
profiles. Local runs `certification.deep-quality-local`; Pull Request preserves
that contract result and adds `certification.deep-quality-pull-request`; Full
and Release preserve both and add `certification.deep-quality-full`. This
ordered preservation intentionally makes every cost tier independently visible
to product certification. Scheduled Linux already selects Full through the
canonical CI router, so it receives the bounded fuzz, sanitizer, and complete
mutation campaign without a second workflow-owned implementation.

The first clean Full run at `7c04d1173af68a47413eea01accaacfc51a0a919`
executed all 36 deep-quality checks. Every 10,000-run fuzz target and both
C/C++ ASan+UBSan lanes passed, but four Full-only mutants survived. Existing
property suites were strengthened to prove unknown-capability preservation,
safety-uncertainty canonicalization, and ECMAScript/Python case intent. Focused
isolated reruns kill all four survivors without a product-code change; the
failed first run remains part of CP4 evidence rather than being replaced by
the repair proof.

The same first clean Full artifact is minimized by the registered
target-adapter capture into 72 source results, then projected into 115 matrix
cells. The bootstrap matrix is deliberately not a readiness pass: it records
41 passed, 35 failed, and 39 unavailable cells from the under-provisioned
disposable environment. This truthful projection replaces the stale profile
identity; later certification may improve its source observations, but cannot
rewrite or promote the captured statuses.

## Final certification disposition

Clean Local 1.10.0 passes 35/35 operations and clean Pull Request 1.15.0 passes
73/73 at commit `59c8dcb70f36cf1621939da3e5b75cd47f54c9cc`. Full 1.21.0 executes all
116 operations from the same clean commit. The embedded deep Full producer
passes 36/36 in 332,454 ms with check-status fingerprint
`036c82a2b4ddc547e1aee84c4656eb17ef949880845c34337cbfd6d9b23ad850` and
evidence fingerprint
`87772862545618c37b725fc2ad81c0ff9d9b15c7cc80565b54585b8ecac67429`.
Every owned property, fuzz, sanitizer, and mutation obligation passes; all
fourteen Critical/High mutants are killed and no task-owned check is
unavailable.

The complete Full aggregate records 110 passed, five failed, and one
unavailable operation with no waiver. Those nonpasses remain explicit later
work: P18-T05 owns live dependency advisories, scanner coverage, and stale
waiver scope; P20-T02 owns the reproducible Python source-distribution omission
and governed package dependencies. The configured CPython 3.11.15 binary on
this host does not match the governed executable hash, so exact Python and its
dependent shared/standard-library checks fail closed without replacing
P18-T02's prior exact governed evidence. Isolated Python tests pass 22/22, and
configured C, C++, F#, JVM, and Perl checks pass.

The task is complete with READY WITH RECORDED CARRY-FORWARD disposition. Local
remains suitable for ordinary development, Pull Request adds bounded
deterministic property/mutation proof, and Full/scheduled Linux owns the heavier
fuzz, sanitizer, and complete mutation denominator. P18-T04 owns the next
ordered performance and resource-budget contract.
