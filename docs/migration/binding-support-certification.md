# Binding support and semantic-ownership certification

P17-T08 closes the host-adapter phase by auditing every language package as a
consumer of canonical STRling semantics. It does not ratify permanent public
support policy: P20-T01 owns that decision. This task records evidence-backed
dispositions and makes duplicate semantic implementations a repository
hardgate.

## Locked denominator

The language denominator is exactly C, C++, C#, Dart, F#, Go, Java, Kotlin,
Lua, Perl, PHP, Python, R, Ruby, Rust, Swift, and TypeScript. The shared JVM
bridge and the C/native interop package are supporting transports and are
audited with their consumers, but they do not increase the seventeen-language
count.

For each language, the final evidence matrix must record:

-   an evidence disposition without presenting it as permanent P20 policy;
-   package manifest, dependency-resolution, install, import, build, and test
    status;
-   executed runtime and platform rows, with unexecuted rows left unclaimed;
-   public API extraction and snapshot status;
-   the sole canonical interop route;
-   canonical request, result, diagnostic, artifact, option, Simply, and standard
    library conformance; and
-   any explicit limitation or Legacy/unsupported recommendation.

The starting anchor is
`a5a0b9cfe65f00f91f3038a7e24ab97aed0624af` on `architecture/v4`. The tree is
clean. All six ordered adapter migration records are complete and preserve
their exact executed-platform and dependency-scanner limitations.

## Starting public and package state

All seventeen language packages have registered public surfaces. Sixteen are
enforced. Rust is the sole transitional surface: its snapshot path is
registered but absent because the original design depended on unavailable
stable rustdoc JSON under the declared MSRV. P17-T08 must install a
deterministic, repository-owned extractor for the curated Rust facade and
activate that snapshot without widening its API.

The machine-owned package matrix in `toolchain.json` remains the source for
manifests, locks, setup, and operations. C, C++, C#, Dart, F#, Go, Java,
Kotlin, PHP, Ruby, Rust, Swift, and TypeScript have repository-managed
dependency models. Lua and Perl are constrained but do not have complete lock
graphs. Python and R remain explicitly deferred dependency models. Those facts
are certification inputs, not inferred support claims.

## Zero-duplicate-semantics contract

Only canonical core and target modules may parse or normalize STRling,
construct semantic IR, analyze semantics or safety, plan portability, lower or
emit target artifacts, or define standard-library semantics. A binding may:

-   project canonical data into idiomatic host values;
-   serialize an exact versioned request and deserialize the exact result;
-   validate transport memory, UTF-8, JSON framing, ABI identity, and host value
    types needed for safe marshaling;
-   expose generated names and documentation derived from registered canonical
    sources; and
-   own package loading, lifecycle, and resource-release mechanics.

A binding may not reinterpret diagnostics, invent defaults, infer targets,
simulate matching, approximate validation with host regexes, or retain a
second parser, normalizer, analyzer, planner, lowering, emitter, or standard
library implementation. Generated projections and controlled historical
evidence are allowed only in their registered non-authoritative locations.

The current global `duplicated-binding-compilers` transition is stale: its
three filename matches are the canonical Python and TypeScript adapter facades
and a facade test, not independent compiler stages. The
`binding-canonical-core-dependency` future rule is also stale because every
ordered adapter migration is complete. P17-T08 will replace these descriptions
with structural, enforced rules and mutation-resistant tests. Any real product
semantic copy found by the closed scan is blocking and cannot be carried
forward.

## Verification boundary

Certification requires the closed seventeen-language matrix, all enforced
public snapshots, an exact forbidden-semantic inventory, the per-ecosystem
adapter boundaries, shared canonical behavioral fixtures, generated-artifact
checks, governance and security checks, Local/Pull Request/Full profiles, and
a clean committed tree. Unavailable tools or platforms remain explicit; an
unexecuted row cannot become passing evidence. Repository-wide failures outside
P17-T08 must be classified exactly and may not conceal a task-owned failure.

No package publication, registry upload, release, branch push, semantic
behavior change, public API redesign, or permanent support-tier ratification
is authorized by this task.

## Closed evidence design

The authored manifest under `tests/adapters/binding-support-4.0` fixes the exact
language order, canonical route, migration record, public surfaces, executed
platforms, limitations, and P17 certification tier. The generated evidence
joins that manifest to `toolchain.json`, the public-surface registry, the
architecture-rule registry, and the six completed adapter migration records.
Its schema fixes the seventeen-row denominator and the distinction between
language packages and shared transports.

The starting evidence contains twelve `supported_candidate` rows and five
`preview_candidate` rows. The latter are Ruby, PHP, Perl, Lua, and R, preserving
P17-T07's explicit provisional disposition. These labels mean that the
architecture and executed behavior meet the corresponding evidence bar; they
do not publish a package or ratify P20's permanent compatibility promise.

The generated matrix contains eighteen language public surfaces because
TypeScript has separate package-entrypoint and symbol snapshots. Seventeen are
enforced at the CP2 boundary. The Rust surface is recorded accurately as the
only incomplete row. The tracked-product scan admits exactly five named
compiler facade files whose bodies remain covered by their ecosystem adapter
rules; it finds zero parser, AST, IR, validator, hint-engine, or emitter product
paths. Exact mutation tests reject denominator shrinkage, row reordering, tier
or route substitution, public-enforcement promotion, semantic-path changes,
and fingerprint drift.

CP2 intentionally produces a valid but `not_ready` artifact. Its three closed
blocking requirements are Rust public-surface enforcement,
`duplicated-binding-compilers` enforcement, and
`binding-canonical-core-dependency` enforcement. CP3 must clear exactly those
requirements and regenerate the same registered artifact before the final gate
may use `--require-ready`.

## Enforced architecture closure

CP3 replaces the task-start transitions without changing binding product code.
The Rust public extractor reads only the curated Cargo manifest and facade
source, records nineteen package/module/re-export/constant/function symbols,
and requires the canonical `strling-kernel` path plus all seven public facade
modules. It is independent of unstable rustdoc JSON and therefore works under
the declared Rust 1.70 MSRV. Addition, removal, signature, re-export, module,
and canonical-dependency changes now make the checked snapshot stale or fail
extraction.

The Rust package has its own enforced canonical-kernel boundary. The former
duplicate-compiler transition is now a case-insensitive tracked-product rule
covering parser, compiler, AST, IR, analyzer/validator, hint-engine, node, and
emitter path identities. Its five exact exceptions are canonical request and
transport facades; tests, examples, and documentation are excluded from the
product-path namespace but not from their ecosystem checks. A controlled new
`bindings/go/parser.go` path fails the rule.

The former future dependency rule is now an enforced route-coverage closure.
It requires enforced Rust, C, C++, TypeScript, Python, shared JVM, .NET,
Go/Dart/Swift, and dynamic-language route boundaries. Each subordinate rule
continues to check its exact native/kernel/WASM markers, forbidden semantic
paths, and alternate dependencies. Removing or demoting any required rule
fails the closure.

The regenerated matrix now records all eighteen public surfaces enforced, all
thirteen required architecture rules enforced, zero forbidden product paths,
zero final blockers, and fingerprint
`sha256:eead75932095aa39aa0ddd3bfbfae5bb1de7cd630c5341a13514e5cb375526d3`.
This is ready evidence for integration execution; it is still not a P20
consumer-policy ratification or a publication action.
