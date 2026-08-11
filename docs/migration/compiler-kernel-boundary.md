# Embeddable compiler-kernel boundary

## Authority and purpose

The contract suite under `spec/contracts/1.0` remains authoritative. The
canonical Rust kernel exposes that contract through one deterministic in-memory
facade; it does not define another compiler protocol or another semantic
pipeline.

The facade accepts a borrowed `CompileRequest` and, only when target-aware work
is requested, a borrowed exact `TargetProfile`. The profile is explicit because
the request contract deliberately carries only its immutable
identity/version/SHA-256 reference. The kernel never resolves that reference
through files, environment, package state, installed engines, or a network.

The intended API shape is:

```rust
pub fn compile(
    request: &CompileRequest,
    target_profile: Option<&TargetProfile>,
) -> Result<CompileResult, KernelCompileError>
```

This is an internal public API of the non-published `strling-kernel` crate. It
does not change any published binding or product API.

## Supported request domain

Contract suite `1.0.0` is the only decodable contract version. A different
contract version is malformed contract data and is rejected during canonical
deserialization; it is not represented as a `CompileRequest` value. The facade
still verifies all request invariants before any semantic stage.

The current request fields and modes have these dispositions:

| Request authority                                                                                       | Current disposition                                                     | Boundary behavior                                                                                                                                                                                              |
| ------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `contract_version = 1.0.0`                                                                              | Supported now                                                           | Strictly validated with the complete request.                                                                                                                                                                  |
| Structurally valid `specification_version` implemented by this kernel                                   | Supported now                                                           | Preserved exactly in every result and stage. An unimplemented specification revision is a structured failed result.                                                                                            |
| `input.kind = semantic` with canonical Semantic IR                                                      | Supported now                                                           | May be source-less or carry valid optional source provenance. The borrowed program is normalized and analyzed without mutation.                                                                                |
| `input.kind = source`                                                                                   | Reserved for a later frontend                                           | The kernel has no frontend and returns failed result diagnostic `STRL-PROTOCOL-0002`; it never reads referenced content or fabricates Semantic IR.                                                             |
| `requested_outputs = semantic`                                                                          | Supported now for semantic input                                        | Returns only complete normalized Semantic IR authorized by the request.                                                                                                                                        |
| `requested_outputs = analysis`                                                                          | Supported now for semantic input                                        | Returns the existing target-neutral `AnalysisResult` projection.                                                                                                                                               |
| `requested_outputs = portability`                                                                       | Supported now for semantic input when the exact profile is supplied     | Resolves the supplied profile against the request reference, then evaluates capabilities and plans portability. Incomplete evidence produces a structured failed result rather than a fabricated final status. |
| `requested_outputs = target_artifact`                                                                   | Validated but not yet executable                                        | Target lowering and emission do not exist. The result fails explicitly and contains no artifact, target regex, capture numbering, engine options, or lowered IR.                                               |
| `partial_semantics`                                                                                     | Validated; executable only after a frontend supplies recovery semantics | Canonical semantic input is complete. Unsupported source input never invents a partial tree.                                                                                                                   |
| `diagnostic_policy.minimum_severity`                                                                    | Supported now                                                           | Filters advisory diagnostics deterministically; required error diagnostics are never filtered.                                                                                                                 |
| `resource_limits.max_semantic_nodes`                                                                    | Supported now                                                           | Applies before recursive contract/stage work and cannot raise the kernel hard ceiling.                                                                                                                         |
| `resource_limits.max_diagnostics`                                                                       | Supported now                                                           | A result crossing the requested bound fails as a whole; it is never silently truncated or labeled successful.                                                                                                  |
| `target_profile` reference without target-aware output                                                  | Valid but unused                                                        | No target-aware stage runs and no profile document is required.                                                                                                                                                |
| Unknown fields, input variants, output modes, enum values, or explicit nulls where omission is required | Invalid                                                                 | Canonical deserialization rejects them before the facade.                                                                                                                                                      |

Successful results contain every requested executable output. Unrequested
optional output sections remain absent. Failed results may retain requested
sections completed before a later unsupported stage, as permitted by the
contract, but never contain partial evidence labeled successful.

## Failure taxonomy

The boundary keeps three failure classes distinct:

1. Malformed serialized contracts are rejected by `validation::from_json` as a
   deserialization or domain-validation `ContractError`. Unsupported contract
   versions, unknown future modes, invalid tagged unions, and invalid scalar
   forms belong here.
2. Typed `KernelCompileError` values report failures of the in-process boundary
   contract: an invalid manually constructed `CompileRequest`, absent or
   mismatched exact target-profile evidence, an impossible certified-stage
   failure after preflight, or an invalid projected result. These errors are for
   embedders and are not compiler diagnostics.
3. A valid request that cannot complete under current compiler capability
   returns `Ok(CompileResult)` with `outcome = failed` and at least one
   deterministic normative error diagnostic. This includes unsupported source
   frontends, unsupported specification revisions, resource exhaustion,
   incomplete portability evidence, and requested target artifact emission.

Correspondence failures in generated fact stores, capability evaluations,
profiles, plans, or result projection are never downgraded to user-facing
success or target-unsupported decisions. They remain typed boundary failures
because they indicate violated internal evidence ownership.

## Canonical stage ownership

For supported semantic requests the facade delegates to the existing certified
orchestration, in this order:

```text
request validation
  -> normalization
  -> foundational semantic facts
  -> structural facts
  -> safety analysis
  -> structured diagnostics
  -> [when target authority is required]
       target requirements
       -> exact-profile capability evaluation
       -> portability planning
  -> requested CompileResult projection
  -> result and request/result exchange validation
```

The target-aware suffix consumes the completed target-neutral bundle. No
target-neutral stage depends on a target profile or target-aware result.
Normalization, analyses, diagnostic generation, capability evaluation, and
planning retain their existing correspondence and fingerprint checks; the
facade does not reproduce their semantics.

## Determinism and resource model

Deterministic evidence derives only from the borrowed request, the explicitly
supplied exact profile, canonical ordering rules, certified semantic-program
fingerprints, canonical profile SHA-256, and the kernel package identity. The
boundary uses no clock, duration, random source, process state, path, memory
address, environment value, mutable singleton, runtime probe, or unordered map
iteration.

Existing certified hard ceilings remain authoritative:

-   serialized request contract: 8,388,608 bytes;
-   serialized supplied target profile: 1,048,576 bytes;
-   semantic nesting depth: 128;
-   semantic nodes: 65,536;
-   leading-consumption terms: 256, with explicit conservative unknown evidence;
-   structural relationship pairs: 4,096;
-   overlap comparisons: 4,096, with explicit conservative unknown evidence;
-   safety findings: 4,096;
-   safety uncertainties: 4,096;
-   generated diagnostics: 4,096;
-   capability requirements: 4,096;
-   portability decisions: 4,096;
-   rewrite dependencies: 4,096.

The facade applies caller semantic-node and diagnostic bounds without weakening
those ceilings. Contract and profile value size is counted through a bounded
discarding serializer before semantic execution or profile fingerprinting; this
is an implementation safeguard and does not extend the serialized request
schema.

Every exhaustion is deterministic and whole-request: return a structured failed
result, do not truncate silently, do not retry with weaker limits, and do not
return partial success.

## Boundary invariant certification

Fixed-seed generated tests exercise the public facade and validated contract path
without adding a runtime random dependency:

-   256 source-less canonical semantic requests across four seeds;
-   64 exact-profile sensitivity cases from seed `0x50524f46494c4501`;
-   256 malformed typed requests from seed `0x4d414c464f524d01`;
-   32 deterministic caller-limit exhaustion cases from seed `0x5245534f55524301`;
-   512 serialized mutation/fuzz-smoke cases across four seeds: 64 valid and 448 malformed.

Every compile or deserialize/compile path is contained with `catch_unwind`, inputs
and supplied profiles are compared after execution, and every returned result is
validated. Static architecture mutation tests separately reject host-state and
global-mutable-state dependencies. The corpus records zero unexplained failures.

## Explicit exclusions

This boundary performs no filesystem, environment, engine, package-manager,
network, binding, CLI, LSP, editor, adapter, or runtime access. It does not
implement a legacy regex parser, Semantic DSL, Simply, target lowering, regex
emission, capture numbering, runtime options, `TargetArtifact`, runtime regex
execution, package APIs, package-version changes, or publication.

No existing STRling runtime/compiler behavior is intentionally changed.
The facade is not wired into any legacy product execution path.

## Kernel-phase readiness

The authoritative embedded boundary is the crate-root re-export of
`kernel::compile`. It accepts the canonical request contract plus optional exact
target-profile evidence and returns only the canonical result contract or a
typed `KernelCompileError`. Contract `1.0.0` semantic, analysis, and
profile-authorized portability requests are executable. Source frontends,
unsupported specification revisions, and target-artifact requests remain
explicit failed results; unknown contract data remains malformed input.

The reachable implementation path is exactly request validation, normalization,
semantic facts, structural facts, safety analysis, structured diagnostics, and,
when target authority is required, target requirements, exact-profile capability
evaluation, and portability planning, followed by validated result/exchange
projection. Stage-owned program/profile fingerprints and correspondence checks
remain mandatory. No lowered target IR, target regex, capture numbering, emitter
option, or `TargetArtifact` enters the public result.

Clean committed-state certification at integration checkpoint
`aaeb08eb0438cfc36d8853cd7f3b42ad8a912fbc` produced:

-   213 passing kernel tests, including 13 facade, five orchestration, nine
    resource-boundary, and five property/fuzz-smoke tests;
-   256 generated valid source-less requests, 64 profile-sensitivity cases, 256
    malformed typed requests, 32 exhaustion cases, and 512 serialized mutation
    cases (64 valid and 448 malformed), with zero unexplained failures;
-   11 schema mappings and 63 fixtures, 34 focused
    boundary/diagnostic/portability/public-contract tests, five architecture
    mutation tests, and passing public-contract, generation, documentation,
    governance, architecture, security, and patch-integrity hardgates;
-   passing TypeScript typecheck/build and 19 suites with 963 tests, and passing
    Rust-binding typecheck/build and 638 tests.

The governed profiles retained truthful aggregate availability:

| Profile        | Aggregate     | Passed | Unavailable | Failed |
| -------------- | ------------- | -----: | ----------: | -----: |
| `local`        | `UNAVAILABLE` |     17 |           6 |      0 |
| `pull-request` | `UNAVAILABLE` |     36 |           7 |      0 |
| `full`         | `UNAVAILABLE` |     65 |          10 |      0 |

All six shared gaps are installed Ruff `0.16.2` versus governed `0.15.21`.
Pull-request additionally retains the repository-managed Bundler mismatch for
Ruby lint. Full additionally retains dependency-risk availability and Ruby
build/test. The profiles were not weakened, and `test@core` passed in all three.

The carry-forward is limited to those certification-environment gaps and later
campaign work. This task did not implement the legacy regex parser, Semantic
DSL, Simply, target lowering, regex emission, `TargetArtifact` production,
runtime execution, bindings/adapters, CLI/LSP migration, package-version changes,
or publication.

Readiness is `READY WITH RECORDED CARRY-FORWARD`. The next ordered incomplete
task in the Notion campaign is
[P07-T01 — Build a controlled legacy TypeScript reference runner](https://app.notion.com/p/3b97d940647581da94ffe41b544e6489?pvs=204).
That runner must provide deterministic, independently versioned historical
evidence without becoming normative compiler authority.
