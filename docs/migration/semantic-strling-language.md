# Semantic STRling language contract

## Ratification boundary

P13-T04 ratifies the syntax and canonical lowering contract for the flagship
Semantic STRling textual frontend. The frontend identity is
`strling.semantic`, the dialect version is `1.0.0`, and its media type is
`text/x-strling-semantic`. This is a contained frontend ratification under
`spec/frontends/semantic/1.0/`; it does not publish a package or release, claim
that the broader STRling Semantic Specification 1.0 draft is ratified, or
authorize a parser or formatter implementation.

The contract owns source syntax, lexical interpretation, source diagnostics,
and deterministic mapping into the existing canonical Semantic IR. It does not
own canonical semantic meaning, target capability, portability policy, target
syntax, runtime execution, or compiler transport. Its machine catalog must
therefore declare syntax and mapping authority while keeping canonical semantic
and target authority false.

## Language shape

Every file selects the language explicitly with `semantic strling 1.0;`,
declares `case sensitive;` or `case insensitive;`, and contains exactly one
`pattern` root. The root and every nested construct use keywords, braces, and
terminating semicolons. There are no regex operators, implicit concatenation,
postfix quantifiers, grouping punctuation, or precedence rules.

The 1.0 constructs are:

-   `empty`, `sequence`, and `choice` for explicit composition;
-   nonempty `text` literals and explicit wildcard line-terminator intent;
-   `character from` or `character except` sets containing scalar, range,
    ASCII/Unicode builtin, and Unicode-property members;
-   `repeat from ... to ... using ...` with finite or `unbounded` maxima and
    greedy, lazy, or possessive behavior;
-   readable position phrases for all seven canonical positions;
-   named `capture` declarations and `same text as` references;
-   `if`/`unless` followed-by or preceded-by lookaround phrases; and
-   `without backtracking` atomic intent.

Container constructs accept one explicit child except sequence/choice, which
require at least two. There is no transparent grouping construct. Nested
sequence/choice blocks are accepted for composition and flatten through the
existing canonical normalization contract. Empty text is rejected in favor of
the explicit `empty` construct.

## Lexical, identity, and source rules

Source is UTF-8 with LF or CRLF input. Canonical formatting writes LF, four
spaces per block, lowercase keywords, one leaf statement per line, braces on
the introducing line, and a final newline. ASCII horizontal/vertical layout is
insignificant between tokens. `#` begins a line comment outside a string.

Identifiers are lowercase ASCII snake identifiers beginning with a letter,
bounded to 64 bytes, and distinct from the complete 1.0 reserved-word set.
Identifiers name captures; names are unique and references may only name a
capture whose declaration has completed earlier in source order. This excludes
numeric, forward, recursive, and self references from 1.0.

Strings use double quotes, literal Unicode scalars, and only the closed escapes
for quote, backslash, named controls, null, and `\\u{...}` scalar values. Raw
control characters, surrogate values, values above U+10FFFF, unknown escapes,
empty text values, and multi-scalar character-set endpoints are rejected.
Integers are unsigned decimal without leading zeroes, bounded to 4,294,967,295.

Every material node receives the half-open UTF-8 byte span from its first
keyword through its semicolon or closing brace. Parsers allocate material node
identities in one-based source preorder (`node:semantic/n1`, then `n2`) and
capture identities in independent declaration preorder
(`capture:semantic/c1`, then `c2`). Consumers treat both as opaque. Identifiers,
source offsets, child-array positions, content hashes, and target capture
numbers do not become identity. Cross-implementation semantic comparison
remains alpha-equivalent because identity and origin are non-semantic.

## Explicit semantic mapping

The source-level case declaration is the sole program option and maps to
`SemanticProgram.case_matching`. Unicode scalar values are the fixed text
model. Wildcard line-terminator behavior and builtin-character domains are
always explicit at the construct, so the language has no hidden flag or
request default.

The mapping catalog must cover every one of the twelve canonical node kinds,
all four character-set member kinds, all repetition modes, all position kinds,
both wildcard behaviors, both builtin domains, all lookaround combinations,
and both case modes. It must also state the normalization effect and source-span
rule for each material construct. A grammar production without both authored
positive and negative fixture coverage cannot be certified.

The language contains no target/profile annotation. Exact target selection
belongs to `CompileRequest`. Modules/imports are deferred because canonical IR
has no module/linkage contract. Portability and safety directives are deferred
because current analysis and planning contracts expose facts and diagnostics,
not source policy nodes. Raw regex, emitted fragments, engine options,
suppression directives, interpolation, macros, conditionals, recursion, and
extension escapes are likewise unavailable in 1.0.

## Determinism and evolution

`language.json` will enumerate all productions, reserved words, disjoint
construct-opening phrases, limits, diagnostics, deferred constructs, and
formatting rules. Formal EBNF remains the syntax authority; the catalog makes
its completeness mechanically reviewable. The certifier will reject duplicate,
undefined, or unreachable productions, prefix-conflicting construct phrases,
missing mapping/enum coverage, stale fixture hashes, invalid UTF-8 spans,
uncovered diagnostics, and any source claim to semantic, target, portability,
runtime, parser, or formatter authority.

The in-source `1.0` selector is exact. New compatible syntax requires a new
minor dialect directory and header; breaking lexical, parse, diagnostic, or
lowering changes require a new major. Existing editions remain selected by
their own header and are never silently reinterpreted as the latest version.
Patch-level contract revisions may clarify or add independently reviewed cases
without changing accepted syntax or meaning.

## Implementation handoff

The later parser task must implement this contract rather than generate it. It
must consume explicit `SourceDocument` frontend metadata, verify that metadata
agrees with the in-source edition, emit the ratified `STRL-DSL-*` diagnostics
and UTF-8 spans, lower only to canonical Semantic IR, and call the existing
normalizer. The later formatter task must implement the canonical presentation
rules and prove parse/format/parse semantic stability. Neither implementation
may alter the language catalog, mappings, or fixtures to accept its output
without a separately reviewed specification change.
