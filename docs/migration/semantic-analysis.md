# Canonical semantic fact analysis

## Stage boundary

Semantic fact analysis is the first target-neutral read-only stage after
canonical normalization. Its kernel boundary is conceptually:

```text
analyze(&SemanticProgram) -> Result<SemanticFacts, SemanticAnalysisErrors>
```

The input must already satisfy the complete `canonical-v1` Semantic IR
contract. Analysis rejects malformed or noncanonical input and never invokes
normalization. It borrows the program, returns a separate fact store keyed by
stable `NodeId`, and does not add derived fields to Semantic IR.

The stage has no filesystem, environment, clock, randomness, network,
frontend, binding, diagnostic, protocol-result, target-profile, portability,
lowering, or emitter context. Identical canonical programs therefore produce
equivalent, canonically ordered facts.

## Canonical stage registration

The kernel contract mapping registers `semantic_analysis` after
`normalization` as an owner of canonical Semantic IR and as the executable
producer for the derived-analysis contract family. This records dependency
direction without composing the stages implicitly: callers normalize first and
then pass the resulting borrowed `SemanticProgram` to `analyze`.

Later stages consume `SemanticFacts` alongside the unchanged normalized
program. They do not receive an analysis-mutated Semantic IR.

## Fact model

Each reachable semantic node has one `NodeFacts` record. The store uses an
ordered map keyed by the node's opaque stable identity. A record contains only
these foundational facts:

-   `nullability`: `nullable`, `non_nullable`, or `unknown`;
-   `minimum_consumption`: a nonnegative semantic length;
-   `maximum_consumption`: `finite(n)` or `unbounded`, never a sentinel;
-   `consumption`: `always_zero_width`, `always_consuming`, `variable`, or
    `indeterminate`;
-   the canonically ordered logical captures defined in the node's subtree;
-   the canonically ordered backreferences used in the node's subtree; and
-   for capture and backreference nodes, their exact logical capture identity.

`unknown` is a sound, explicit nullability result for a backreference when the
canonical representation alone does not prove that it can successfully consume
zero. It is not unbounded length and it is not encoded as a missing field.
`indeterminate` consumption means the bounds prove possible positive
consumption but nullability remains unknown. An assertion is
`always_zero_width`; an optional literal is `variable`, not intrinsically
zero-width.

The existing versioned `analysis.schema.json` remains the normative wire
contract for nullable booleans, Unicode-scalar bounds, and feature
requirements. This internal fact store does not revise that public contract or
make serialization a new normative surface. A later protocol adapter may
project only facts representable by its versioned schema.

## Semantic length unit

Consumption is counted in **Unicode scalar values**. A literal's length is its
Rust `char` count, and a wildcard or character set consumes exactly one scalar.
No Unicode normalization is performed. For example, `é`, `λ`, and `😀` each
consume one semantic unit despite occupying two, two, and four UTF-8 source
bytes respectively; `e` followed by U+0301 consumes two units.

This unit follows canonical Semantic IR's Unicode-scalar literal and set
semantics. It is independent of UTF-8 byte offsets used by source spans and of
UTF-16 or other target-engine code units.

All addition and multiplication is checked in `u64`. A finite result that
cannot be represented is a structured arithmetic-overflow analysis failure,
never a wrapped value, artificial target limit, or panic.

## Compositional rules

In the table, `N`, `min`, and `max` are nullability and consumption facts for a
child. Finite maxima use checked arithmetic. Subtree capture/reference sets are
the ordered union of the node's own relationship, when any, and all child
relationships.

| Semantic node            | Nullability                                                                                         | Minimum consumption              | Maximum consumption                                                                                                                                                                                                        | Consumption disposition                                                                                                   |
| ------------------------ | --------------------------------------------------------------------------------------------------- | -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `empty`                  | nullable                                                                                            | 0                                | finite(0)                                                                                                                                                                                                                  | always zero-width                                                                                                         |
| nonempty `literal`       | non-nullable                                                                                        | Unicode scalar count             | same finite count                                                                                                                                                                                                          | always consuming                                                                                                          |
| `wildcard`               | non-nullable                                                                                        | 1                                | finite(1)                                                                                                                                                                                                                  | always consuming                                                                                                          |
| nonempty `character_set` | non-nullable                                                                                        | 1                                | finite(1)                                                                                                                                                                                                                  | always consuming                                                                                                          |
| `sequence`               | nullable iff every child is nullable; non-nullable if any child is non-nullable; otherwise unknown  | checked sum of child minima      | unbounded if any child is unbounded, otherwise checked finite sum                                                                                                                                                          | derived from bounds and nullability                                                                                       |
| `alternation`            | nullable if any branch is nullable; non-nullable if every branch is non-nullable; otherwise unknown | minimum branch minimum           | unbounded if any branch is unbounded, otherwise maximum finite branch maximum                                                                                                                                              | derived from bounds and nullability                                                                                       |
| `repeat`                 | nullable when `min` is zero; otherwise inherits body nullability                                    | checked body minimum times `min` | finite(0) when the certified maximum is zero or the body maximum is finite(0); unbounded for an unbounded repetition whose body can consume positively; otherwise checked body maximum times the finite repetition maximum | derived from bounds and nullability; mode does not affect consumption                                                     |
| `position`               | nullable                                                                                            | 0                                | finite(0)                                                                                                                                                                                                                  | always zero-width                                                                                                         |
| `capture`                | inherits body                                                                                       | inherits body                    | inherits body                                                                                                                                                                                                              | inherits body; also defines its logical capture ID                                                                        |
| `backreference`          | non-nullable when the referenced capture body has positive minimum; otherwise unknown               | referenced capture-body minimum  | referenced capture-body maximum                                                                                                                                                                                            | always consuming when minimum is positive; otherwise indeterminate unless the referenced body is proven always zero-width |
| `lookaround`             | nullable                                                                                            | 0                                | finite(0)                                                                                                                                                                                                                  | always zero-width; the body is analyzed independently but its examined length is not outer consumption                    |
| `atomic`                 | inherits body                                                                                       | inherits body                    | inherits body                                                                                                                                                                                                              | inherits body; atomicity changes backtracking, not accepted consumption lengths                                           |

Assertions are treated as nullable foundational expressions because successful
assertion matches consume zero; this stage does not attempt satisfiability or
context feasibility. Positive and negative lookaround bodies still receive
their own complete records. Position kind, lookaround direction and polarity,
case matching, repetition greediness, and atomicity do not change these
foundational consumption bounds.

An unbounded repetition of a nullable body is not assumed to have zero maximum.
If the body can consume any positive amount according to its maximum, the
repetition maximum is unbounded. Only a body with finite maximum zero keeps an
unbounded repetition's maximum at finite zero.

## Capture and reference relationships

Capture facts preserve opaque logical `CaptureId` values exactly. No traversal
ordinal or target engine number is assigned. Every capture definition records
its defining node, optional semantic name, and body node. Every backreference
records its own node and its resolved logical capture. Each node record exposes
the ordered set of definitions and reference nodes reachable in its subtree.

Canonical Semantic IR already requires unique node IDs, capture IDs, and
capture names, and requires every backreference to resolve regardless of
declaration order. Analysis verifies these invariants again at its stage
boundary. Duplicate nodes or captures and unresolved references are structured
invalid-input failures if externally constructed values bypass ordinary
validation.

## Explicit deferrals

This stage does not derive or decide:

-   satisfiability, first sets, character overlap, ambiguity, progress, or
    termination;
-   ReDoS or any other safety judgment;
-   feature requirements beyond the already defined protocol data model;
-   target capability, target limits, portability, or rewrite decisions;
-   optimizer transformations or other Semantic IR mutation;
-   user-facing diagnostics or source presentation;
-   target lowering, capture numbering, syntax, or emission; or
-   frontend, parser, binding, Simply, LSP, or editor behavior.

Later safety and portability analyses may consume these immutable foundational
facts. They must remain separate keyed results and must not reinterpret source
byte coordinates as semantic match length.
