# Cross-target semantic corrections

Status: implementation design record for the bounded pre-4.0 semantic-
hardening campaign. Repository-owned V4-H01 through V4-H03 evidence is the
operational input; this record does not elevate empirical engine behavior into
language authority.

## Starting inventory

The V4-H03 evidence contains 121 findings owned by this correction: 117
`SEMANTIC_DIVERGENCE` findings and four `TARGET_COMPILE_FAILURE` findings. The
remaining two findings are the known public diagnostic-delivery defect assigned
to V4-H05.

| Causal family | Finding count | Current form and first causal boundary | Canonical disposition |
| --- | ---: | --- | --- |
| wildcard exclusions and scalar consumption | 45 | native dot or dot-all in target serializers; Python bytes consumes a byte | native only for an exact exclusion set and Unicode-code-point matching unit, otherwise explicit class or early refusal |
| line start, line end, and CRLF interiors | 15 | native/profile-specific anchors in all three serializers | all LF, VT, FF, CR, CRLF, NEL, LS, and PS; CRLF is atomic-longest; native only when exact, otherwise explicit assertions |
| before-final-line-terminator | 8 | native `\Z`/`$` or an incomplete ECMAScript assertion | end of input or before one final canonical terminator, excluding the LF interior of CRLF; explicit assertion |
| Unicode word class | 3 | target `\w`, Python Unicode `\w`, or ECMAScript property union | `L + Mn + N + Pc`; native only when the profile set is exact, property-based direct lowering when available, otherwise refusal |
| word boundary | 16 | native `\b`/`\B` | transition over the canonical word set; native only when its word set is exact, otherwise property/lookaround lowering or refusal |
| case folding | 12 | one native global insensitive mode per target | simple Unicode folding; reject only programs that intersect an engine-specific extra equivalence class |
| unset backreferences | 4 | native target backreference | an unset capture makes the reference fail; reject only where nonparticipation is structurally reachable and the profile uses empty behavior |
| repeated-capture state | 10 | native capture within repeated conditional control flow | retain the last participating capture; reject only where a later iteration can omit an externally observable capture and the profile resets it |
| PCRE2 compiled target acceptance | 4 | bounded quantifier passes the syntactic check but exact governed engines reject the compiled artifact | use the unknown compiled-pattern limit explicitly and refuse conservatively before emission when expansion is outside the governed predictable envelope |
| Python bytes scalar sets | 4 | negated atom-set guard consumes one byte | a negated semantic character set consumes one Unicode scalar; reject the bytes profile before lowering |

The counts are grouped by the first causal mechanism and sum to 121. Anchored
wildcard cases remain in the wildcard family; their position assertions are
also exercised by the line-family tests.

## Canonical semantic decisions

Canonical line terminators are the scalar set LF, VT, FF, CR, NEL, LS, and PS,
with CRLF recognized as one atomic-longest sequence. A wildcard that excludes
line terminators excludes the seven scalar values; an including wildcard
consumes exactly one Unicode scalar. Line boundaries occur outside, never
inside, the CRLF sequence.

Canonical Unicode word characters are general categories `L`, `Mn`, `N`, and
`Pc`. Word boundaries are transitions between that set and its complement.
This matches the already-governed PCRE2 10.43 fact; other profiles may use an
explicit property construction only when their separate property and assertion
capabilities support it.

Canonical case-insensitive matching uses simple Unicode folding. Canonical
unset backreferences fail, and captures inside repetition retain the last value
from an iteration in which they participated. Semantic wildcard and negated-set
consumption is by Unicode scalar, never by encoded byte.

## Implementation boundary

Target-neutral requirement extraction carries only semantic reachability facts:
wildcard scalar use, negated-set scalar use, bounded repetition, capture-reset
exposure, unset-reference exposure, and case-fold input atoms. Capability
evaluation compares those facts with the exact profile's governed sets,
algorithms, matching unit, and limits. Unsupported combinations become an
ordinary unsupported portability result before target emission.

Target lowering then selects native or explicit structured target operations by
comparing the exact profile facts with the canonical definitions. Serializers
only spell that selected operation. Any lookaround or Unicode property
introduced by an explicit operation remains covered by V4-H03 post-lowering
requirement extraction.

The explicit wildcard, anchor, and word forms are direct target serialization
of canonical semantic constructs, not optional Semantic IR rewrites. They do
not enter the user-requested rewrite registry. No character-set normalization,
new target, source-profile import, diagnostic transport repair, or performance
baseline change is part of this correction.

## Governed target dispositions

| Profile | Equivalent direct behavior | Precise refusal boundary |
| --- | --- | --- |
| ECMAScript 2024 | explicit canonical wildcard, line-position, final-terminator, Unicode-word, and word-transition forms | a possibly unset backreference or observable repeated-capture retention when the engine algorithm differs |
| PCRE2 10.42 | native canonical line/wildcard behavior; explicit `L + Mn + N + Pc` word classes and word transitions | bounded repetition above the conservative 4,096 envelope while compiled size remains artifact/configuration dependent |
| PCRE2 10.43 | native canonical line, wildcard, word, folding, backreference, and capture-state behavior; explicit final-terminator form | the same unknown compiled-pattern envelope as 10.42 |
| Python `re` 3.11 string | explicit canonical wildcard and line-position forms; native backreference and retained-capture behavior | canonical Unicode word/boundary requests and only those case-fold programs that intersect Python's extra dotted/dotless-I equivalence class |
| Python `re` 3.11 bytes | safe ASCII literals, positive ASCII sets, and non-scalar constructs remain available | wildcard, canonical line positions, negated sets, non-ASCII scalar operations, Unicode word/boundary operations, and reachable non-ASCII simple-fold relations |

The PCRE2 envelope is a compiler refusal threshold, not a claim that 4,097 is
an engine syntax limit. Exact 65,535-count artifacts were observed to fail for
the governed one-literal programs, while the profile truthfully keeps compiled
size unknown and artifact/configuration dependent. Count 65,536 remains the
separate governed syntactic constraint and retains the existing V4-H05 public
diagnostic-delivery reproduction.

No equivalence-registry rewrite was added. The alternate target spellings are
the canonical direct serialization of their Semantic IR constructs and remain
covered by V4-H03's emitted-requirement extractor.

## Audit reconciliation

The registered 41-program, 95-subject audit executes twice on the exact pinned
Node 22.23.2, PCRE2 10.42/10.43, and CPython 3.11.15 runtimes. At the historical
finding-ID level, every one of the 121 V4-H04 findings includes at least one
profile that now refuses the reachable mismatch precisely; the other involved
profiles use equivalent native or direct canonical target forms. Therefore the
non-overlapping finding reconciliation is:

| Disposition | Count |
| --- | ---: |
| Equivalent-native/direct-only finding IDs | 0 |
| Equivalence-registry rewrite finding IDs | 0 |
| Finding IDs closed by at least one precise constraint/refusal | 121 |
| Remaining V4-H04 findings | 0 |
| Remaining V4-H05 diagnostic-delivery findings | 2 |
| Unexpected or unaccounted findings | 0 |

This classification does not mean all target cells were rejected. ECMAScript,
both PCRE2 revisions, and Python string continue to execute the large majority
of the corrected corpus through exact native or explicit direct lowerings. The
shared conformance denominator is 84 execute, nine explicit unsupported, and
seven not-applicable applications; its 100-cell portability matrix has zero
semantic discrepancies and zero unresolved entries.

The explicit forms are longer than the previously emitted native shortcuts.
Focused runtime certification found no correctness or bounded-resource failure.
Pattern compaction and character-set normalization remain a post-4.0
optimization opportunity; no performance baseline or threshold changed here.

The compiler's public failed-result delivery still drops two structured PCRE2
target-lowering diagnostics. The repository-only lowering probe proves those
diagnostics internally; their transport is deliberately retained for V4-H05.
