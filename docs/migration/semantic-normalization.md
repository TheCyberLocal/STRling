# Canonical semantic normalization

## Stage boundary

Semantic normalization is the first executable transformation in the canonical
Rust kernel. Its public kernel boundary is conceptually:

```text
normalize(&SemanticProgram) -> Result<SemanticProgram, NormalizationErrors>
```

The input is a structurally decoded Semantic IR candidate. Normalization checks
semantic invariants that must hold before representation can be canonicalized,
recursively removes only contract-authorized variation, and validates the
result as `canonical-v1`. The stage has no filesystem, environment, network,
CLI, frontend, protocol, diagnostic, analysis, target-profile, lowering, or
emitter context.

The certified contracts under `spec/contracts/1.0` remain authoritative. The
legacy TypeScript and binding compilers are compatibility evidence only.

## Rule inventory

| Candidate                                   | Classification                           | Canonical behavior and authority                                                                                                                                                                                             |
| ------------------------------------------- | ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Nested sequences                            | Normative and implemented                | Normalize descendants, flatten directly nested sequences, and preserve item order. `INVARIANTS.md` and contract-suite 1.0 require flattening.                                                                                |
| Nested alternations                         | Normative and implemented                | Normalize descendants, flatten directly nested alternations, and preserve branch order.                                                                                                                                      |
| Adjacent literals                           | Normative and implemented                | Coalesce each adjacent run without Unicode normalization. The first literal is retained and receives the concatenated text.                                                                                                  |
| Single-child sequences                      | Normative and implemented                | Replace the wrapper by its normalized child.                                                                                                                                                                                 |
| Single-child alternations                   | Normative and implemented                | Replace the wrapper by its normalized child.                                                                                                                                                                                 |
| Empty sequence wrappers                     | Invalid input                            | No contract rule authorizes interpreting an empty collection as another semantic operation; canonical sequences require at least two items. Authors must use an explicit `empty` node for empty-string intent.               |
| Empty alternation wrappers                  | Invalid input                            | Canonical alternations require at least two branches, and the contract has no distinct empty-language replacement that would preserve the meaning of zero branches.                                                          |
| Empty literal text                          | Invalid input                            | Canonical literal text is nonempty. The normalizer does not guess that malformed literal data meant the explicit `empty` operation.                                                                                          |
| Explicit `empty` children/branches          | Explicitly preserved                     | The contract permits explicit empty nodes inside sequences and alternations. Removing them would be an unratified algebraic simplification.                                                                                  |
| Repetition                                  | Normative recursion; otherwise preserved | Normalize the body and validate `min <= max` for a finite maximum. Do not combine or rewrite quantifiers or modes.                                                                                                           |
| Character-set members                       | Normative and implemented                | Validate member semantics, remove exact duplicates, then sort by the contract key: literal, range, built-in, Unicode property; within a kind sort by semantic values and negation. Do not merge ranges or expand properties. |
| Source-origin collections                   | Normative and implemented                | Sort and deduplicate exact spans and prior node IDs. Accumulate exact contributions when wrappers/literals disappear; never widen discontiguous spans into a fabricated range.                                               |
| Positions/assertions                        | Explicitly preserved                     | Position nodes are semantic boundaries and retain their representation.                                                                                                                                                      |
| Captures                                    | Normative recursion; otherwise preserved | Normalize the body while retaining logical capture ID, optional name, node ID, and boundary.                                                                                                                                 |
| Backreferences                              | Explicitly preserved                     | Retain the referenced logical capture ID; validate that it resolves regardless of declaration order.                                                                                                                         |
| Lookarounds                                 | Normative recursion; otherwise preserved | Normalize the body while preserving direction, polarity, node ID, and boundary.                                                                                                                                              |
| Atomic nodes                                | Normative recursion; otherwise preserved | Normalize the body while preserving atomicity, node ID, and boundary.                                                                                                                                                        |
| Alternative sorting/deduplication/factoring | Explicitly preserved                     | Branch order and multiplicity remain semantic; no sorting, deduplication, or common-prefix factoring occurs.                                                                                                                 |
| Analysis or target rewrites                 | Deferred outside normalization           | Nullability, length, overlap, safety, capabilities, target syntax, and emission decisions belong to later stages.                                                                                                            |

## Identity policy

-   A node that survives normalization keeps its `node_id`, including a container
    whose children change.
-   A removed sequence or alternation wrapper has no node in the result. Its ID
    and origin contributions are accumulated into the retaining container when
    flattened, or into the surviving child when a single-child wrapper is
    removed.
-   Literal coalescing retains the first literal node and ID in input order. Each
    later literal's ID and origin are accumulated into the retained literal.
-   Capture IDs and backreference targets are never renamed or derived from
    traversal position.
-   The ratified rules require no synthesized nodes, so normalization allocates
    no node or capture IDs. A future rule requiring synthesis must define a new
    deterministic allocation contract before implementation.
-   Duplicate input node IDs, capture IDs, or governed capture names fail before
    wrapper removal can hide the collision.

These rules make identity treatment deterministic and idempotent without
randomness, clocks, hashing, or process state.

## Provenance policy

Unchanged nodes preserve their origins after canonical collection ordering.
When a wrapper is removed or a literal is absorbed, the survivor receives the
union of exact source spans and prior derived node IDs plus the removed node's
ID. Collections are sorted and deduplicated by their contract order.

Source spans themselves are never joined, widened, or otherwise rewritten.
Discontiguous source contributions therefore remain separate honest spans.
Source-less input remains source-less except that a removed node ID may be
recorded as derivation evidence. All retained inline spans are revalidated as
half-open UTF-8 byte ranges against their embedded source text.

## Failure model

Normalization returns ordered structured failures rather than panicking.
Stable failure categories distinguish invalid semantic structure, identity,
reference, repetition bounds, character sets, provenance, post-normalization
canonical invariant failures, and unsupported internal contract state. Paths
identify the input or result location; prose is explanatory and is not the
failure identity.

Noncanonical variation covered by the inventory is transformed. Malformed
semantic state that has no contract-authorized meaning-preserving rewrite is
rejected.

## Evidence classification

Normative requirements come only from the certified contract invariants and
contract-suite 1.0 documentation and schemas. Legacy TypeScript and Python
normalizers provide evidence for recursive sequence/alternation flattening,
single-child removal, literal coalescing, and traversal through repetition,
group, and lookaround nodes. Their missing stable identities/provenance, lack of
set canonicalization, combined group flags, and acceptance of zero-child
wrappers are historical implementation details, not canonical rules.
