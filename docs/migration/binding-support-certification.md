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
