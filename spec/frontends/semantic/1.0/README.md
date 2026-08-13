# Semantic STRling textual frontend 1.0

## Status and authority

This directory is the ratified source-language contract for frontend identity
`strling.semantic` at dialect version `1.0.0`. The in-source edition selector is
`semantic strling 1.0;` and the media type is
`text/x-strling-semantic`.

The ratification is deliberately contained. It makes the grammar, lexical and
context rules, frontend diagnostics, canonical formatting, and deterministic
Semantic IR mapping normative. It does not ratify the broader STRling Semantic
Specification 1.0 draft, implement a parser or formatter, select a target,
define canonical Semantic IR meaning, publish a package, or authorize a
release.

Normative inputs are:

-   [`grammar.ebnf`](grammar.ebnf), the formal source grammar;
-   [`language.json`](language.json), the complete machine language catalog;
-   [`mapping.json`](mapping.json), the Semantic IR projection table;
-   [`formatting.md`](formatting.md), canonical presentation rules; and
-   [`fixtures/`](fixtures/), specification-authored positive and negative
    cases with content-addressed ownership.

The JSON documents are validated by their adjacent schemas. Prose in this file
is normative where EBNF cannot express a context rule.

## A complete example

```text
semantic strling 1.0;
case insensitive;

pattern sequence {
    at input start;
    capture word {
        repeat from 1 to unbounded using greedy {
            character from {
                unicode word;
                scalar "_";
            }
        }
    }
    text "-";
    same text as word;
    at input end;
}
```

Composition is always explicit. `sequence` and `choice` require at least two
children. Every other block owns exactly one node. There is no transparent
grouping syntax, operator precedence, implicit concatenation, or postfix
quantifier.

## Lexical and source contract

Input is UTF-8. Invalid bytes are rejected by the protocol boundary. LF and
CRLF are accepted without normalization before spans are measured. A BOM is
not stripped and produces the first applicable frontend diagnostic. Canonical
spans are half-open UTF-8 byte ranges into the exact source.

Space, tab, CR, and LF are layout between tokens. `#` starts a comment outside
a string and continues through the physical line ending or end of input.
Comments cannot split a token.

Capture identifiers match `[a-z][a-z0-9_]{0,63}` and cannot equal a 1.0
identifier-reserved word. The reserved set contains the top-level declaration
starters and every construct-leading keyword; context-only keyword terminals
such as `word` remain valid capture names because their position is
unambiguous. Capture names are unique. A `same text as` reference must appear
after the complete declaration it names; forward, self, numeric, and recursive
references are unavailable.

Text strings are nonempty. A character-set `scalar` or range endpoint decodes
to exactly one Unicode scalar. Strings admit literal printable scalars plus the
closed escapes `\"`, `\\`, `\b`, `\f`, `\n`, `\r`, `\t`, `\0`, and
`\u{H...}`. A scalar escape has one to six hexadecimal digits and must not
encode a surrogate or value above U+10FFFF. Unknown escapes and raw control
characters are errors.

Integers are unsigned decimal without leading zeroes and cannot exceed
4,294,967,295. A finite repetition maximum must be at least its minimum. The
word `unbounded` is the only unbounded source value and maps to JSON `null`.

## Semantic boundary

The required case declaration maps to `SemanticProgram.case_matching`. Text
uses Unicode scalar values. Wildcard line-terminator behavior and builtin class
domain are explicit on each construct. No source flag or host default changes
their meaning.

Every material construct maps through [`mapping.json`](mapping.json) to one of
the twelve canonical Semantic IR node kinds or four set-member kinds. Nested
sequence and choice blocks flatten, single-child forms are rejected at the
frontend, adjacent text coalesces during canonical normalization, and set
members enter canonical member ordering. Node and capture identities are opaque
to consumers but deterministically allocated. Material source nodes use
one-based preorder identities `node:semantic/n1`, `node:semantic/n2`, and so on;
capture declarations independently use `capture:semantic/c1`,
`capture:semantic/c2`, and so on. Backreferences resolve human names to those
logical capture identities. Source offsets, child-array positions, content
hashes, human names, and target capture numbers are never identity. Semantic
comparison is alpha-equivalent and excludes identity and origin.

Exact targets and requested outputs belong to `CompileRequest`. Target
profiles, engine options, emitted fragments, runtime execution, raw regex,
modules/imports, macros, interpolation, recursion, conditionals, and
portability/safety policy directives have no 1.0 syntax. Target support for
atomicity, possessive repetition, lookbehind, Unicode properties, or other
explicit intent is decided after semantic analysis against an exact profile.

## Malformed input and diagnostics

Frontend failures use the stable `STRL-DSL-*` identities in `language.json`,
with severity `error`, severity basis `normative`, and either
`frontend_parse`/`syntax` or `semantic_lowering`/`semantic_validity`. Report the
earliest failing UTF-8 byte position. Where one token could trigger several
rules, lexical failure precedes structure, then reference/lowering validity.
No partial Semantic IR from a failed source may feed analysis or emission.

Resource limits are 1,048,576 source bytes, nesting depth 128, 65,535 material
nodes, 16,384 captures, 65,535 set members per set, and the integer limit above.
The resource diagnostic may be exercised by synthetic boundary tests rather
than embedding oversized fixture text.

## Versioning and implementation handoff

The source header selects exactly edition 1.0. Compatible additions require a
new minor directory/header; incompatible tokenization, syntax, diagnostic
trigger, or lowering changes require a new major. An implementation never
silently substitutes a later edition. Contract patch changes cannot alter
accepted syntax or meaning.

Run `python3 tooling/semantic_strling_contract.py` to certify schemas, grammar
reachability and ambiguity invariants, mappings, fixtures, manifests, spans,
diagnostics, and authority. The later parser and formatter tasks must consume
this contract and cannot regenerate or renew it from implementation output.
