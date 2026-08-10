# Semantic normalization compatibility evidence

## Comparison boundary

The comparison is deliberately parser-free. Nine representative canonical
Semantic IR candidates are projected into the structural vocabulary shared
with the historical TypeScript/Python IR normalizers. The historical recursive
algorithm is applied to that projection, and IDs/origins are erased from the
canonical result before structural comparison.

This is transitional compatibility evidence, not specification authority. The
certified canonical contracts remain the oracle.

## Selected corpus

| Case | Shared behavior compared                                 | Result                                   |
| ---- | -------------------------------------------------------- | ---------------------------------------- |
| 1    | Nested and single-child sequence flattening              | Parity                                   |
| 2    | Adjacent literal coalescing without crossing a wildcard  | Parity                                   |
| 3    | Nested alternation flattening with branch order retained | Parity                                   |
| 4    | Recursive normalization of repetition body               | Parity                                   |
| 5    | Recursive normalization inside a capture boundary        | Parity                                   |
| 6    | Recursive normalization inside lookaround                | Parity                                   |
| 7    | Recursive normalization inside atomic grouping           | Parity                                   |
| 8    | Explicit empty node retained as a semantic boundary      | Parity                                   |
| 9    | Logical capture/backreference structure retained         | Parity after representational projection |

The executable corpus has zero unexplained differences.

## Classified differences

| Difference                                                                                                                                     | Classification                            | Contract basis                                                                                                                                                        |
| ---------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Canonical node IDs, logical capture IDs, and source origins have no legacy equivalent.                                                         | Representational-only                     | Canonical identity and attribution invariants require them; comparison erases only those fields.                                                                      |
| Zero-child legacy sequence/alternation results are rejected by canonical normalization.                                                        | Intentional canonical-contract correction | Canonical sequence/alternation nodes require at least two children after normalization, and no rule authorizes guessing a replacement for malformed zero-child input. |
| An empty legacy literal may survive outside a sequence; canonical normalization rejects it.                                                    | Intentional canonical-contract correction | Canonical literal text is nonempty and empty-string intent uses the explicit `empty` operation.                                                                       |
| Legacy normalization leaves character-set member order and duplicates untouched; canonical normalization sorts and deduplicates exact members. | Intentional canonical-contract correction | Contract suite 1.0 explicitly requires unique members in the declared semantic sort order.                                                                            |
| Legacy groups combine capture/noncapture and atomic flags; canonical IR uses only semantic capture and atomic nodes.                           | Representational-only                     | Syntax-only grouping is absent from Semantic IR; semantic boundaries remain explicit.                                                                                 |

No difference is classified as an unresolved blocker or as a reason to copy an
undocumented legacy quirk. No parser, binding, or target implementation is
invoked by the kernel test.
