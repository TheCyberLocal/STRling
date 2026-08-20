# Canonical TypeScript/WASM and Python/native adapter migration

## Outcome and authority

P17-T03 replaces the TypeScript and Python packages' binding-owned semantic
implementations with thin host adapters. TypeScript executes the governed raw
WebAssembly ABI; Python executes the governed native C ABI. The canonical
compiler contracts, frontend contracts, exact target profiles, Simply
protocols, standard-library registry, and `strling.interop` 1.0 remain the sole
semantic authority.

The task starts from clean `architecture/v4` commit
`e6c87a1ae2fed088bff7ec22653fccf5d00becde`. P17-T01 already certifies the
serialized protocol, native ABI, raw WebAssembly memory contract, ownership,
concurrency, fuzzing, and Linux sanitizer foundation. P17-T02 proves the
canonical native adapter chain and records the host/toolchain gaps inherited by
this task.

## Starting inventory

The two historical packages contain 40 authored source files and approximately
15,260 lines: 19 TypeScript files (6,658 lines) and 21 Python files (8,602
lines). Both packages independently implement parser, compiler, IR/node,
validator, hint, target-emitter, and Simply behavior. Those implementations are
migration evidence, not semantic authority.

The enforced TypeScript declaration snapshot contains 461 symbols, its package
entrypoint snapshot contains 11 fields, and the Python public snapshot contains
95 symbols. At the starting commit, the TypeScript suite passes 972 tests in 20
suites and the Python suite passes 798 tests. The TypeScript dry-run package has
38 entries. These results establish a starting denominator; the TypeScript run
uses host Node 24.4.1 rather than the governed `>=22,<23` runtime and is not
governed runtime certification.

The TypeScript root entrypoint imports successfully, but its declared `./core`,
`./simply`, and `./emitters/pcre2` subpaths point to paths not emitted by the
build. The actual Simply output is under `dist/STRling/simply`. This is a known
public-surface defect, not evidence that the local compiler stages should be
preserved. The Python package imports from the source tree, but this host lacks
the declared build backend modules, so a wheel cannot yet be certified. CP2
must freeze both facts rather than converting either into a passing claim.

## Locked dependency direction

```text
TypeScript facade ──> raw strling.wasm-abi v1 ──> strling-interop

Python facade ──> generated strling_interop.h/native ABI v1
                                      |
                                      v
                              strling-interop
                                      |
                                      v
                              public strling-kernel
```

TypeScript owns WebAssembly loading, instance-scoped allocation, bounded byte
transfer, response release, JSON transport, host-value projection, and package
entrypoints. Python owns native-library discovery/loading, bounded byte
transport, owned-response release, JSON transport, host-value projection, and
wheel/package mechanics. Neither package may parse language source, validate
semantic meaning, plan portability, lower targets, emit regex, or implement a
standard helper independently.

Both adapters are local and capability-closed. They may not infer targets from
the host, consult the filesystem or network for semantics, download a runtime
artifact implicitly, or fall back to the historical implementation when the
canonical library is absent or rejects a request.

## Public-surface dispositions

| Package    | Preserved canonical facade                                                                                                                                                                                                                  | Explicit compatibility disposition                                                                                                                                                                                                                                                                                                                                                                     |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| TypeScript | Package root namespaces, ergonomic Simply builder names and mechanically representable signatures, `SimplyPreviewBuilder`, canonical request/result projection, generated standard-helper identities, and a repaired `./simply` entrypoint. | Historical `parse`, `parseToArtifact`, and `Compiler` names may remain only as canonical request/result conveniences with reviewed shapes. `./core`, `./emitters/pcre2`, local node/IR exposure, and compiler-stage methods are breaking retirements where they expose independent semantics. Any exact deprecated convenience must delegate and refuse unrepresentable values without local fallback. |
| Python     | Root `simply`, ergonomic Simply builder names and mechanically representable signatures, canonical request/result projection, generated standard-helper identities, and governed native loading.                                            | Binding-local parser/compiler/emitter/validator/hint/intelligence modules are not supported semantic surfaces. Historical `Pattern.exec` returns simulated labels rather than executing a governed engine and cannot be preserved as a runtime claim; it must be removed or explicitly refuse/deprecate. Exact compatibility shims must delegate and preserve canonical error data.                    |

Preserving an ergonomic name does not preserve a local AST, IR, parser result,
or emitter contract. CP2 snapshots every declaration, export, exception,
sync/async boundary, artifact shape, package entrypoint, import route, and
compatibility decision before implementation. Additions, deprecations,
signature changes, and removals are classified explicitly.

The Program Owner authorizes only the TypeScript generated fingerprint and
`typescript-public-api` snapshot regeneration mechanically caused by the prior
Rust standard-library ownership-path cleanup. That authorization does not
permit TypeScript semantic, behavioral, API-shape, or implementation changes.
P17-T03's own reviewed adapter API changes require the task evidence and public
change classification defined here; they must not be disguised as that narrow
fingerprint authorization.

## Target, errors, lifecycle, and concurrency

Canonical compile calls require an exact caller-supplied target profile. A
deprecated targetless string convenience may use only an explicit generated
`pcre2-10.43` profile, must disclose that identity, and must remain separate
from new canonical APIs. There is no ambient repository or host-language
default.

Canonical failed compile results remain values. Stable canonical diagnostic and
interop codes, JSON paths, spans, result data, and exact target identity remain
recoverable after host projection. WebAssembly instantiation/allocation errors
and Python library/load/FFI errors are transport or host errors and remain
distinguishable from canonical failures.

TypeScript follows the raw ABI's per-instance serialized execution model:
independent instances may run concurrently, but shared-memory or concurrent
calls into one instance are not promised. Allocated request and response bytes
are bounded and released on every success and failure path. Python follows the
native ABI's borrowed-input copy, zeroable owned response, same-descriptor free,
panic containment, reentrancy, and concurrent-call guarantees. Host wrappers
must prove repeated create/use/release cycles and failure cleanup.

## Simply and standard-library boundary

Simply builders may construct protocol data and retain ergonomic operator or
method syntax, but evaluation occurs only through `simply.compile`. Generated
standard-library names and metadata derive from the canonical registry. A
helper declared `lexical_shape` remains a lexical-shape helper: acceptance may
include semantically invalid values, and neither adapter may silently
strengthen it into a semantic validator. Future entries that genuinely promise
semantic validation must use canonical semantic validation, never host regex
approximation.

## Historical evidence and retirement gates

The migration differential currently observes 24 TypeScript and 20 Python
historical cases by executing the product sources. Before those sources change,
CP2 must freeze their starting-commit identity, exact corpus, result
disposition, and independent reproduction route. A narrowly scoped immutable
copy under `tooling/legacy_reference` is permitted only to preserve historical
observation. It remains non-normative and must never become a product fallback.

Semantic copies are deleted only after all of these hold:

1. CP2 freezes public, package, compatibility, conformance, lifecycle,
   concurrency, error, Simply, standard-library, clean-install, architecture,
   deletion, and historical denominators with shrinkage resistance.
2. Replacement adapters produce canonical requests, results, and artifacts for
   every applicable case; intentional differences are reviewed and recorded.
3. Public snapshots and package-entrypoint checks identify every compatible,
   deprecated, additive, and breaking change.
4. Architecture fitness proves TypeScript uses only the raw WASM boundary and
   Python uses only the native ABI, with no compiled or reachable semantic copy.
5. Historical runners execute their frozen evidence path, not the migrated
   product implementation.

## Packaging, verification, and exclusions

P17-T03 certifies local TypeScript build/package assembly, Node and browser
WebAssembly use, Python wheel/build/import behavior, clean installs, lifecycle,
concurrency, error projection, Simply behavior, standard-helper portability,
cross-binding canonical parity, and repository public/generated/architecture/
security profiles. The governed Node range is `>=22,<23`; Python retains its
declared `>=3.8` support unless a separately authorized support-tier decision
changes it. Host Node 24 and source-tree Python imports may inform baselines but
cannot substitute for those governed clean-environment proofs.

The task may regenerate registered lockfiles, public snapshots, generated
standard-library projections, version metadata, and immutable migration
evidence only from their governing sources. No package version, language
semantic, target profile, interop ABI, support tier, package publication,
release, tag, upload, or branch push is authorized. Other bindings and
P17-T04-or-later migrations remain out of scope.

## Frozen CP2 evidence

The CP2 suite freezes 72 cases across twelve families, thirteen runners, four
interop operations, and four governed runtime positions. Its seventeen
canonical contract inputs fingerprint to
`sha256:0c6189b30042c50481228314ca35f69e55c9536288aad7299dce5c4816770924`;
the evidence manifest fingerprints to
`sha256:545d73f3b75199592657c37ae1da83e51f27dd8649a49b22e81f0ad2a7b627cc`.
Thirteen mutation tests reject contract, fingerprint, case, family, runner,
binding, operation, runtime, corpus, semantic-copy, and source-bundle
shrinkage.

The registered compatibility baseline records exact task-start hashes for 18
public/package inputs and 31 semantic-copy paths. It also embeds 45 historical
TypeScript/Python source, manifest, lock, and compiler-config inputs so the
historical runners no longer import mutable product source. The baseline
fingerprint is
`sha256:6a1ac87338417c442e0a2abfb3dad289d60e71f68a83f7850fd41e23d43b8191`.
This executable bundle remains isolated non-normative evidence.

The isolated runner suites pass 43 Node tests and 29 Python/launch tests. Three
runs preserve all 24 TypeScript plus 20 Python observations with zero
nondeterministic results. The guarded migration differential retains baseline
`sha256:621ef0867c3611e9dc153353002a2ac33d56408e10f8a047552d4d1935c9f791`,
records zero blocking canonical replacements, and leaves six historical peer
differences evidence-only. These are frozen implementation obligations, not
claims that a migrated adapter already passes them.
