# Shared cross-engine behavioral corpus

P11-T05 owns the specification-authored, target-neutral behavioral evidence
shared by the initial PCRE2, ECMAScript, and Python `re` targets. It does not
change canonical language meaning, settle the final portability matrix, add a
product compilation route, or treat engine agreement as specification
authority.

## Authority and case model

The existing `spec/conformance/cases/*.json` documents remain the canonical
vectors. Each case is validated by the versioned compiler conformance-case
contract and contains its Semantic IR or source input, stable identity,
specification-authored intent, semantic/diagnostic/match expectations, target
support expectations, tags, and optional compatibility references. The
content-addressed specification manifest continues to own every and only case.

The manifest remains `draft` because STRling Semantic Specification 1.0 is not
ratified. Draft status does not permit an implementation, target runtime,
historical fixture, or majority result to rewrite expected behavior. It means
the reviewed authored expectations are campaign evidence rather than a claim
of delegated normative specification authority.

A separate `shared-corpus-v1` document binds those cases into executable
cross-engine vectors. It contains no target pattern text. For every vector it
records sorted feature and requirement tags, the applicable match or diagnostic
operation, coverage roles, and one explicit disposition for every governed
profile:

-   `execute` requires a case target expectation of `native` or
    `equivalent_rewrite` and exact engine execution;
-   `unsupported` requires the case to declare unsupported target evidence and
    forbids artifact or runtime success; and
-   `not_applicable` requires a stable rationale and prevents coercing a text,
    Unicode, diagnostic-only, or semantic-only vector into an unrelated profile.

The initial profile denominator is exact and closed: PCRE2 10.42, PCRE2 10.43,
ECMAScript 2024 on Node 22, Python `re` 3.11 `str`, and Python `re` 3.11
`bytes`. Profile revisions and fingerprints are copied from the authored target
profiles and cannot float.

## Coverage and anti-shrinkage

The shared corpus covers literals and escaping, sequence and alternation,
character sets and built-ins, greedy/lazy/possessive repetition, captures and
backreferences, lookahead and fixed/variable lookbehind, atomic groups,
wildcards, input/line/word anchors, ASCII and Unicode behavior, case intent,
zero-length behavior, the certified atomic-literal rewrite, malformed source,
unsupported features, and cross-feature interactions.

Coverage obligations are data, not comments. Each semantic feature declares
the required union of positive, negative, boundary, interaction, rewrite,
diagnostic, or unsupported evidence and a minimum number of independently
identified cases. Every certified equivalence rewrite in the governed registry
must have an owned vector. Validation rejects missing profiles, duplicate or
unsorted identities, stale case/profile fingerprints, unowned case files,
missing applicability entries, corpus shrinkage below the declared denominator,
unmet feature obligations, and a rewrite without positive and negative
behavioral evidence.

## Deterministic projection and execution

A repository-only Rust example is the sole projection adapter. It reads the
authored cases and exact profiles, runs canonical analysis, capability
evaluation, portability planning, target lowering, and target serialization,
and writes bounded JSON containing artifacts and logical capture-slot maps. It
does not execute engines, edit cases, infer expected results, expose a product
API, or accept ambient profile substitutions.

The Python orchestrator validates corpus authority first, invokes the fixed
Rust projection, and dispatches only `execute` applications to the existing
exact-runtime adapters:

-   PCRE2 10.42 and 10.43 shared libraries from immutable upstream tags;
-   official Node 22.23.2/V8 12.4.254.21-node.56 on Linux x64; and
-   official-source CPython 3.11.15 on Linux x86-64 for both `str` and `bytes`.

Engine-native offsets and capture slots are normalized back to canonical UTF-8
subject spans and logical capture IDs. Full-match versus search is evaluated at
the observation layer; target artifacts are not wrapped or rewritten by the
harness. Unsupported and not-applicable entries never reach an engine.

Each run preserves the raw bounded engine observation beside its normalized
projection, artifact fingerprint, profile identity, plan status, harness and
runtime identity, corpus/manifest fingerprints, and comparison against the
authored expectation. At least two complete runs must be byte-identical after
excluding timing. A checked-in evidence artifact preserves the exact raw and
normalized observations for P11-T06; its fingerprint and denominator are
verified by Full and Release.

## Certified identity

The completed corpus contains 20 cases and 100 explicit applications: 88
execute, five unsupported, and seven not applicable. The per-profile
execute/unsupported/not-applicable counts are ECMAScript 2024 `18/1/1`, PCRE2
10.42 `17/2/1`, PCRE2 10.43 `19/0/1`, Python `re` 3.11 text `18/1/1`, and
Python `re` 3.11 bytes `16/1/3`. Two complete exact-runtime runs agree with all
19 semantic, 19 target, 19 match/capture, and one diagnostic expectations.

The canonical SHA-256 identities are:

-   case set:
    `8ce5b9874312e9527944960f84c722a8293e9030bc6d9d8550aca53012ae849d`;
-   vector set:
    `8d6fc71842065e7d1e8796e4ee3e210669220c2b129530e70d9e05ff08e17afc`;
-   corpus:
    `e8c069f068b8562518bfcf4f782a0961b53124660e4d40e63e49cbe8c6824fb1`;
-   projection:
    `029cf1c0df979774e71acb8f08e2a02bfd99001529a14faf9dcedfe01cda8089`;
    and
-   preserved observations:
    `9a575b86e8ea43590b24fcc2bda2d3a7b80ed25fa98694f46924b247abd3493c`.

Certification used exact PCRE2 10.42 and 10.43 libraries, official Node
22.23.2, and official-source CPython 3.11.15. Local passes all 26 operations.
Pull Request records 44 passed and two inherited host operations unavailable;
Full 1.7.0 records 75 passed and seven inherited host/scanner operations
unavailable. No operation failed, was incomplete, or was waived. All exact
runtime certification operations pass, including shared cross-engine
certification.

## Boundary with P11-T06

P11-T05 fixes schema defects, expectation defects, projection defects, and
harness defects until every declared executable vector agrees with its
canonical expectation. It does not create the feature-by-profile portability
matrix or classify all cross-target differences. P11-T06 consumes the exact
corpus and preserved observations, assigns explicit divergence dispositions,
and blocks on unresolved results.

Bindings, packages, versions, publication, release notes, performance policy,
new targets, and product-facing source-to-artifact orchestration remain outside
this task.
