# Canonical compiler contract invariants

## Ratified design boundary

These invariants translate the ratified product and architecture decisions into
data-contract rules. They are normative for canonical contract design and
implementation. They do not add, remove, or reinterpret a STRling construct.

```text
Semantic STRling --\
Simply ------------+--> Semantic IR --> analysis and planning --> target lowering
Regex frontend ----/                                             --> artifact
```

Frontend parsing owns syntax. Semantic IR owns target-neutral meaning. Target
profiles describe version-sensitive engine facts. Planning owns compatibility
decisions. Emitters serialize an already selected target plan. Host adapters
project these contracts without redefining them.

## Existing representation audit

| Evidence                                                              | Useful compatibility information                                                                                                                                                      | Constraint that is not canonical                                                                                                            |
| --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| TypeScript and duplicated binding node models                         | Accepted construct categories, parse-time grouping, flag handling, and source-error behavior                                                                                          | Class names, constructor layouts, nullable fields, and one AST shape per binding                                                            |
| TypeScript and duplicated binding IR models                           | Sequence/alternation flattening, adjacent-literal coalescing, character classes, repetition, captures, backreferences, lookarounds, anchors, atomic groups, and possessive repetition | Capture numbers/names as references, absent stable node identity, absent provenance, stringly typed variants, and emitter-oriented grouping |
| `spec/schema/base.schema.json`                                        | Historical node vocabulary, UTF-32 source-range convention, and a serializable artifact envelope                                                                                      | Semantic tree embedded in an artifact, target compatibility as arbitrary data, flags mixed with output, and no profile identity             |
| `spec/schema/pcre2.v1.schema.json`                                    | Existing PCRE2 capability assumptions that require migration review                                                                                                                   | Timeless booleans and an engine name standing in for engine/runtime/profile versions                                                        |
| Binding and LSP diagnostics                                           | Existing codes, messages, hints, and editor projection behavior                                                                                                                       | Exception/console prose as failure identity, inconsistent severity/location shapes, and LSP coordinates as semantic coordinates             |
| `spec/schema/conformance-fixture.schema.json` and `tests/spec/*.json` | A large differential corpus of accepted and rejected historical behavior                                                                                                              | TypeScript-generated expected AST/IR/output as a semantic oracle and exact English hints as default identity                                |
| `spec/features.json` and emitter tables                               | Candidate feature identifiers and known engine distinctions                                                                                                                           | Unversioned engine booleans and emitter-owned portability policy                                                                            |

This evidence must remain available during migration. It may motivate a
contract field or conformance case, but it cannot override the specification or
the canonical contracts.

## Cross-contract invariants

### Syntax, semantics, and target output

1. `SourceDocument` records source identity, dialect, text or an external
   reference, specification version, and provenance. It does not prescribe a
   frontend parse tree.
2. Frontend-specific syntax representations are private to their frontend and
   never cross the Semantic IR boundary.
3. Simply-generated nodes are source-less. Imported canonical nodes and
   programs preserve their identities, origins, and declared source documents;
   text spans remain optional origin metadata, not a precondition for semantic
   validity.
4. Semantic IR contains intent, never emitted fragments, engine option names,
   target escape spellings, capture numbers, or host-language values.
5. Noncapturing syntax-only grouping disappears during semantic lowering.
   Semantically material capture, atomicity, lookaround, and repetition remain
   explicit nodes.
6. A target profile cannot redefine STRling meaning. A backend cannot infer a
   different meaning from frontend identity or host language.
7. A Simply request is a closed, ordered, versioned construction graph. It
   cannot carry raw regex, emitted target syntax, engine option names, runtime
   objects, callbacks, or an implicit compiler/engine.
8. Simply semantic options belong to the projected Semantic IR. Requested
   outputs, compiler options, and an exact target profile belong only to the
   projected `CompileRequest`.

### Identity and attribution

1. Every Semantic IR node has a unique stable `node_id` within its semantic
   program. The identifier is opaque and is not an array index, source offset,
   or content hash.
2. A semantic-preserving phase keeps the identifier for a retained node. A
   phase that replaces a node allocates a new identifier and may record the
   source node identifiers in non-semantic origin metadata.
3. Every capture declaration has a unique logical `capture_id`. Backreferences
   resolve only by `capture_id`; an eventual target-engine capture number is an
   emission detail.
4. Human capture names are semantic labels and must be unique when the
   controlling specification requires it, but they are not logical identity.
5. Source origin and node/capture identifiers are excluded from semantic
   equality. Equality compares structure and semantic values, with consistent
   alpha-renaming of node and capture identifiers.
6. Source spans reference a declared `source_id`. A span cannot silently refer
   to a path, editor buffer, or another source document.
7. Simply-generated node and capture identities derive only from the explicit
   request namespace and stable step or capture key. Host object address,
   insertion position, target capture number, and content hash are forbidden
   identity sources.
8. Builder values are immutable and materialize under exactly one parent.
   Transparent grouping preserves its child's identity and records the removed
   deterministic group identity only as non-semantic derivation provenance.

### Canonical source coordinates

Canonical offsets are zero-based UTF-8 byte offsets into the exact source text,
and spans are half-open `[start, end)`. Both endpoints must be UTF-8 code-point
boundaries and `start <= end`. Newline spelling is not normalized before
offsets are measured. The source text or immutable referenced content therefore
defines one deterministic coordinate space across Rust and host bindings.

Line/column pairs are derived presentation data. LSP UTF-16 code-unit positions,
Unicode scalar indices, grapheme clusters, and host string indices must be
converted at adapter boundaries and must never be relabeled as canonical
offsets.

The legacy base schema described source ranges as UTF-32 code-point indices.
Canonical contracts intentionally change that convention. Migration must decode
legacy ranges using the legacy schema and convert them against the exact source
text; copying the integers is invalid for non-ASCII input. Public legacy
contracts are not changed in place.

### Normalization and analysis

Canonical normalized Semantic IR obeys all of these structural rules:

-   nested sequences and nested alternations are flattened;
-   sequences and alternations with one child are replaced by that child;
-   adjacent literal nodes are coalesced, and literal values are nonempty;
-   the empty language operation is represented by one explicit `empty` node;
-   canonical sequence and alternation nodes contain at least two children;
-   repetition bounds are nonnegative integers, with JSON `null` as the sole
    unbounded maximum, and a finite maximum is not less than the minimum;
-   child and branch order is semantic and is never sorted;
-   character-set member order is canonicalized by the normalization contract,
    not by target spelling; and
-   source origins are accumulated without affecting the normalized semantic
    value.

Analysis does not grow ad hoc fields on Semantic IR nodes. Nullability, length
bounds, capability requirements, overlap, and safety facts are separate,
versioned result sections keyed by stable `node_id` or `capture_id`.

### Diagnostics and deterministic results

1. A diagnostic is identified by stable code plus structured phase/category
   context, never only by English prose.
2. Source locations are optional because protocol, source-less construction,
   and target-profile failures may have no textual span. A supplied location
   must satisfy the source contract.
3. Syntax and semantic-invalidity error severity is normative. Unsupported
   requested emission is also an error. Advisory warning/info/hint severity is
   compiler policy unless a specification, profile, or conformance case
   explicitly makes it normative.
4. Diagnostics are ordered by primary source identity and offset when present,
   then phase order, severity order, stable code, and deterministic production
   ordinal. Related locations and fixes preserve their authored order.
5. A failed result is data, not an exception string. Error diagnostics suppress
   target artifacts. Partial semantic results are permitted only when
   explicitly requested, are marked partial, and cannot feed analysis,
   planning, or emission.

### Profiles, portability, and artifacts

1. Target identity includes engine identity and engine version. Profile
   identity and profile schema version are separate from both.
2. Capabilities use an explicit support state plus typed constraints. A bare
   engine-level boolean is invalid.
3. Portability status is exactly `native`, `equivalent_rewrite`, or
   `unsupported`. There is no implicit or reserved degraded status.
4. `unsupported` never yields an artifact. `equivalent_rewrite` must identify
   the requirements and decisions that caused rewriting.
5. Pattern text and engine/runtime/compiler options are separate artifact
   fields. Inline syntax cannot be the only representation of an option.
6. Artifact source maps use UTF-8 byte spans in emitted pattern text and link
   them to Semantic IR node identities and canonical source spans.

### Conformance ownership

Specification-authored cases live under `spec/conformance/`, carry an explicit
specification version and authority record, and state only the layers they
normatively exercise. A case may assert exact Semantic IR, semantic facts,
diagnostic identities, abstract matching/captures, or support against a declared
profile.

Implementation output cannot promote itself by satisfying the case schema.
Normative designation additionally requires a reviewed specification-owned
manifest and delegation from a ratified specification. Until such ratification,
authored seed cases are explicitly `draft`. Historical TypeScript-generated
fixtures remain transitional compatibility evidence under `tests/spec/`.

## Version and compatibility policy

The source, Semantic IR, diagnostics, compile protocol, target profile shape,
artifact, and conformance case use one compiler-contract suite version. The
initial version is `1.0.0`; individual families do not invent redundant schema
versions. Target profiles still have independent profile revisions because
their facts change independently.

-   A major contract version changes or removes a field, meaning, variant, enum
    member, identifier rule, ordering rule, or invariant incompatibly.
-   A minor contract version adds an optional field or variant. Producers must
    emit only a version the consumer declares it accepts.
-   A patch version clarifies prose or tightens validation only where every
    previously valid instance was already invalid under a stated invariant.
-   Semantic meaning changes additionally follow Semantic Specification
    versioning, even when the serialized shape is unchanged.
-   Unknown object fields are rejected. Extension maps, where deliberately
    defined, use namespaced keys and are non-semantic unless their owning
    contract says otherwise.
-   Array order is significant unless a field explicitly declares canonical
    sort order. JSON object member order is insignificant. Canonical examples and
    fingerprints use UTF-8 JSON, lexicographically sorted object keys, no
    insignificant whitespace, and a trailing LF only when stored as a file.

Specification, compiler, contract, dialect, engine, runtime, profile, and
artifact versions never imply one another. Every compatibility relationship is
explicit data.
