# Legacy regex-compatible frontend contract

## Outcome

The historical regex-shaped notation now has a bounded, versioned contract:
frontend `strling.regex-compat`, dialect `1.0.0`. It is a compatibility/import
frontend that lowers to canonical Semantic IR. It is not Semantic STRling, a
target profile, or emitted target regex.

This task defines contracts and specification-authored fixtures only. It does
not port, repair, or otherwise change a parser.

## Evidence inventory

The contract was derived under the campaign authority order from:

-   the canonical `SourceDocument`, Semantic IR, diagnostic, compile-request,
    target-profile, and artifact boundaries;
-   the transitional `spec/grammar/dsl.ebnf` and `spec/grammar/semantics.md`;
-   all 177 retained `tests/spec/*.pattern` compatibility cases and their paired
    implementation-derived artifacts;
-   TypeScript and Python parser/error tests and the independently fingerprinted
    20-case and 24-case historical runner corpora; and
-   the P07 comparison/differential contract, which preserves raw observations
    without granting them specification authority.

Implementation evidence was used to find syntax and contradictions. The new
specification-authored contract, not generated output or runner agreement,
owns the selected frontend behavior.

## Decisions by migration disposition

### `preserved_behavior`

The contract preserves literals, dot, whitespace rules, extended mode,
`%flags`, empty patterns/groups, concatenation, nonempty alternation, all four
group/lookaround forms, named and numeric prior backreferences, line/word and
uppercase absolute anchors, character classes/ranges/shorthands/properties,
closed identity/control/null/code-point escapes, and greedy/lazy/possessive
quantifiers. It retains case-insensitive flag letters, comma/space separators,
optional flag brackets, and preamble comments because repository evidence
demonstrates those compatibility shapes.

### `intentional_specification_correction`

The versioned contract resolves ambiguous behavior rather than encoding parser
accidents:

-   duplicate `%flags` directives reject instead of silently using the last one;
-   directive lines cannot contain pattern text;
-   malformed `{...}` after an atom rejects instead of sometimes becoming a
    literal brace sequence;
-   unknown escapes reject inside and outside character classes;
-   Unicode escapes must contain at least one digit and denote a Unicode scalar;
-   all spans and diagnostic offsets use canonical UTF-8 byte coordinates rather
    than host string indices; and
-   deterministic source, nesting, capture, and quantifier limits prevent
    unbounded frontend work.

These choices do not change current runtime behavior in P08-T01. They are the
requirements for the Rust parser and later differential dispositions.

### `unsupported_legacy_behavior`

The old transitional EBNF/prose mentioned constructs that the certified
frontend did not consistently implement or that belong to a target engine:
`%engine`, `%lang`, `\z`, `\a`, `\e`, `\cX`, `\R`, `\h`, `\H`, `\Q...\E`,
octal escapes other than `\0`, POSIX classes, inline modifiers, recursion,
subroutines, conditionals, and branch-reset groups. Version 1.0 rejects them
with stable frontend diagnostics. Equivalent intent must use explicit
target-neutral constructs and later portability evaluation.

### `unresolved_discrepancy`

There is no unresolved frontend syntax decision in version 1.0. The exact
cross-target meaning of word classes/boundaries, dot/newline behavior,
lookbehind width support, atomicity, possessive repetition, and absolute-anchor
realization is intentionally outside the frontend contract. Those are semantic
or target-profile questions, not hidden uncertainty in parsing.

The six P07 historical peer return-shape differences remain non-normative
migration evidence and do not affect this syntax contract.

## Contract surface

The machine catalog records 51 feature decisions: 32 accepted, six
compatibility-only, and 13 rejected. Forty-five stable frontend diagnostics are
defined. Thirty positive fixtures cover every accepted/compatibility-only
feature, while 45 negative fixtures cover every syntax/directive/escape/
reference rejection and every rejected feature.

UTF-8 source is limited to 1 MiB, nesting to 128, captures to 65,535, and
quantifier bounds to `2^32 - 1`. LF and CRLF are accepted; all locations are
UTF-8 byte offsets. Dialect identity is explicit in `SourceDocument`; no target
is inferred and no `%engine`/`%lang` source directive exists.

Raw target regex has no opaque representation. Accepted compatibility
extensions must lower structurally to Semantic IR and reach target planning
through explicit capabilities.

## Certification and handoff

`python3 tooling/legacy_regex_contract.py` validates schemas, catalog/grammar
correspondence, complete fixture coverage, canonical flag order, UTF-8
boundaries, manifest hashes, and deterministic identity. The initial
fingerprint is
`sha256:0cb32dd3ed534d13ce6d4278a2723898ac40bc374fa6d40c5ac43c553a2265ad`.

P08-T02 may implement the Rust parser only against the versioned files under
`spec/frontends/legacy-regex/1.0`. Historical TypeScript/Python parser code is
comparison evidence, not informal specification. P08-T03 owns source spans,
provenance, and canonical diagnostic implementation. P08-T04 owns public
frontend APIs and executable replacement differential certification.
