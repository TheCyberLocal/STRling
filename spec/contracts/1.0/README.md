# Canonical compiler contract suite 1.0

## Serialization standard

Every schema here uses JSON Schema Draft 2020-12 and contract version `1.0.0`.
Objects are closed unless a schema expressly defines an extension point. JSON
object order is insignificant; array order is significant unless a canonical
sort is declared below. The companion validator enforces graph, Unicode, and
cross-document invariants that JSON Schema cannot express safely.

Passing a public JSON Schema is therefore necessary but not sufficient for a
valid STRling exchange. The canonical additional content-validation path is
`python3 tooling/contract_validation.py`; it enforces canonical ordering,
cross-object identities, graph references, UTF-8 boundaries, and the other
invariants named below. `./strling contracts --check` separately verifies that
the published public-surface snapshots still match their implementations.

## SourceDocument

[`source.schema.json`](source.schema.json) separates source identity from any
frontend parse representation.

| Field                   | Contract reason                                                                    |
| ----------------------- | ---------------------------------------------------------------------------------- |
| `contract_version`      | Selects serialization independently of language semantics.                         |
| `source_id`             | Gives spans one opaque identity without assuming a path or URI.                    |
| `specification_version` | Selects semantic rules explicitly; there is no latest-version fallback.            |
| `frontend`              | Identifies authoring surface and dialect revision without exposing its parse tree. |
| `display_name`          | Provides optional non-identity presentation text.                                  |
| `content`               | Carries exact inline UTF-8 text or an immutable URI plus SHA-256 reference.        |
| `provenance`            | Records authored, imported, generated, or projected ownership and parents.         |

`SourceSpan` always carries `coordinate_system: utf8-bytes`; its zero-based
`start` and `end` form a half-open range in the exact UTF-8 text. The explicit
tag makes accidental LSP UTF-16 or legacy UTF-32 projection visible.

`SourceOrigin` may contain sorted source spans, sorted prior node IDs, or both.
A constructed semantic node omits origin. Multiple spans preserve all source
contributions without making attribution part of semantic equality.

## Semantic IR

[`semantic-ir.schema.json`](semantic-ir.schema.json) is the sole canonical,
target-neutral representation.

| Field                   | Contract reason                                                                         |
| ----------------------- | --------------------------------------------------------------------------------------- |
| `contract_version`      | Selects the shared contract suite.                                                      |
| `specification_version` | Selects every node's semantic meaning.                                                  |
| `normalization`         | Certifies the structural canonicalization rules below.                                  |
| `case_matching`         | Records global intent without target flags; the specification defines folding.          |
| `sources`               | Optionally embeds documents referenced by origins; absent for source-less construction. |
| `root`                  | Holds the normalized semantic operation tree.                                           |

Every node requires opaque `node_id` and discriminating `kind`; optional
`origin` is attribution only.

| Kind            | Meaning                                                                             |
| --------------- | ----------------------------------------------------------------------------------- |
| `empty`         | Matches the empty string; the only empty operation.                                 |
| `sequence`      | Matches ordered `items`.                                                            |
| `alternation`   | Tries ordered `branches`.                                                           |
| `literal`       | Matches nonempty literal `text`, without emitted escaping.                          |
| `wildcard`      | Matches one character with explicit line-terminator policy.                         |
| `character_set` | Matches a union of canonical members, optionally complemented.                      |
| `repeat`        | Repeats a body over finite or unbounded bounds in greedy, lazy, or possessive mode. |
| `position`      | Asserts input, line, word-boundary, or final-terminator position.                   |
| `capture`       | Declares logical `capture_id`, optional name, and body.                             |
| `backreference` | Refers only to a logical `capture_id`, never a target number.                       |
| `lookaround`    | Asserts a body with direction and polarity.                                         |
| `atomic`        | Matches a body without backtracking into it.                                        |

Character-set members are literal Unicode scalars, inclusive scalar ranges,
built-in classes with explicit ASCII/Unicode domain, or Unicode properties.
Target escape sequences are not semantic members. Noncapturing syntax-only
grouping is absent; capture and atomicity remain because they are semantic.

## Canonical normalization

A `canonical-v1` program certifies:

1. sequences and alternations are flattened and have at least two children;
2. adjacent literals are coalesced and literal text is nonempty;
3. repeat bounds are nonnegative, finite maximum is at least minimum, and JSON
   `null` alone means unbounded;
4. node/capture IDs and capture names are unique, and every backreference
   resolves by logical capture ID regardless of declaration order;
5. sequence and branch order is retained;
6. set members are unique and sort by `literal`, `range`, `builtin`, then
   `unicode_property`; within a kind they sort by their semantic values and
   negation, and range start does not exceed end;
7. origin spans sort by source ID/start/end and derived IDs lexicographically;
8. origin spans reference embedded sources and inline endpoints are UTF-8 scalar
   boundaries; and
9. every embedded source uses the program specification version.

Normalization is a contract, not an algorithm in this task. Implementations may
reach it however they choose while preserving identity for retained nodes.

Semantic equality ignores node ID spelling, consistent capture-ID renaming, and
origin. Nullability, length bounds, requirements, overlap, and safety findings
remain separate results keyed by stable IDs rather than new node fields.

## Authored evidence

[`examples/source/`](examples/source/) proves inline Unicode and immutable
references. [`examples/semantic-ir/`](examples/semantic-ir/) proves every node
kind, position kind, lookaround combination, logical capture, UTF-8 attribution,
and source-less construction. [`invalid/`](invalid/) contains controlled test
inputs, not conformance cases or language behavior definitions.

[`examples/compile-request/`](examples/compile-request/) and
[`examples/compile-result/`](examples/compile-result/) include paired
`strling.regex-compat@1.0.0` source exchanges for success, syntax rejection,
unsupported directives, caller-unresolved references, and exact-profile
portability. The specification-authored
[`frontend orchestration corpus`](../../frontends/legacy-regex/1.0/orchestration/cases.json)
exhaustively maps all historical source-bearing migration cases onto canonical
`CompileRequest` execution; the historical implementations remain evidence,
not semantic authority.

## Protocol, targets, and conformance

[`PROTOCOL.md`](PROTOCOL.md) governs diagnostics, keyed analysis, portability,
and deterministic compile request/result behavior. [`TARGETS.md`](TARGETS.md)
governs version-aware profiles, the three portability statuses, separate engine
options, source maps, and TargetArtifact. The
[`specification-authored conformance model`](../../conformance/README.md)
governs case ownership and content-addressed authority.

All eleven schemas use the same contract version. Source dialect, semantic
specification, compiler, engine/runtime, profile revision, and manifest
authority identities remain separate and explicit. Unknown fields are rejected;
a producer must not emit a newer contract version to a consumer that has not
declared support for it.

Authored positive and controlled invalid objects cover every family. The
repository hardgate additionally verifies canonical JSON fingerprints, graph
references, diagnostic and array ordering, UTF-8 boundaries, profile references,
compile exchanges, and conformance-manifest membership.
