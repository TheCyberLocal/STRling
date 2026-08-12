# STRling regex-compatible source dialect 1.0

## Status and authority

This directory is the normative syntax contract for frontend identity
`strling.regex-compat` at dialect version `1.0.0`. Its scope is deliberately
narrow: it defines the compatibility/import source language accepted before
semantic lowering. It does not ratify Semantic STRling, define Semantic IR
meaning, select a target engine, or define target output.

The machine catalog is [`dialect.json`](dialect.json), validated by
[`dialect.schema.json`](dialect.schema.json). The exact grammar is
[`grammar.ebnf`](grammar.ebnf). Specification-authored cases are validated by
[`case.schema.json`](case.schema.json) and content-addressed by
[`fixtures/manifest.json`](fixtures/manifest.json).

## Source identity and encoding

A canonical `SourceDocument` selects this frontend out of band:

```json
{
    "frontend": {
        "id": "strling.regex-compat",
        "dialect_version": "1.0.0"
    }
}
```

The source is UTF-8. Invalid bytes are rejected at the protocol boundary before
frontend parsing. All offsets and half-open spans use UTF-8 byte coordinates;
CRLF therefore occupies two bytes. LF and CRLF line endings are accepted. A
leading U+FEFF is an ordinary literal scalar and is never silently stripped.

Missing or conflicting frontend metadata is a protocol error. The source never
infers its own dialect or a target. Media type
`text/x-strling-regex-compat` may assist transport selection but cannot replace
the explicit frontend identity.

The deterministic resource limits are 1,048,576 source bytes, nesting depth
128, 65,535 capture groups, and quantifier bounds no greater than
4,294,967,295. The first error in source order is reported.

## Preamble and flags

Blank lines and comment-only lines beginning with optional horizontal space
and `#` may precede the pattern. One optional `%flags` directive may follow that
preamble. It occupies its complete physical line. No directive may appear once
pattern content starts.

The flags are `i`, `m`, `s`, `u`, and `x`. Letters are case-insensitive,
duplicates collapse, and comma or ASCII whitespace separators are accepted;
optional square brackets retain compatibility with existing inputs. An empty
`%flags` line selects no flags. Multiple directives, unknown letters, inline
pattern content, `%engine`, `%lang`, and all other percent directives are
rejected.

Only `x` changes lexical treatment. With `x`, ASCII space, tab, CR, and LF are
ignored outside character classes and `#` starts a comment through the next
line ending. Escaped space and `#` remain literals. Inside a character class,
whitespace and `#` are always literal. Without `x`, whitespace after the
preamble is pattern content.

## Syntax and context rules

The grammar has four precedence layers, from tightest to loosest: atom,
quantifier, concatenation, and alternation. Empty source and empty group bodies
are accepted; alternation branches are not empty.

Accepted atoms include Unicode scalar literals, dot, character classes,
captures, noncapturing and atomic groups, lookahead and lookbehind, line/word
and absolute assertions, prior numeric/named backreferences, and the escapes
enumerated by the grammar.

The following context rules are normative even where EBNF alone cannot express
them:

-   capture names match `[A-Za-z_][A-Za-z0-9_]*` and are unique;
-   capture numbers follow opening delimiters from one, and backreferences must
    resolve to a capture opened earlier in source order;
-   quantifiers apply to one preceding consuming atom, not an assertion, and may
    have at most one lazy `?` or possessive `+` suffix;
-   brace ranges have decimal bounds with minimum no greater than maximum;
-   character classes contain at least one item;
-   `]` is literal only in the first item position, `-` is literal first or last,
    and `^` negates only in the first position;
-   class ranges have two scalar endpoints in nondecreasing code-point order;
-   Unicode property names and optional values are nonempty ASCII identifiers;
    and
-   hexadecimal and Unicode escapes must encode Unicode scalar values, never
    surrogates or values above U+10FFFF.

Identity escapes are closed: only punctuation listed in the grammar, space,
and `#` may be identity-escaped. `\0` is the null scalar, never group zero.
Octal, `\z`, `\a`, `\e`, `\cX`, `\R`, `\h`, `\H`, `\Q...\E`, POSIX classes,
inline modifiers, recursion, subroutines, conditionals, and branch-reset groups
are outside this dialect.

## Semantic and target boundary

This frontend produces structure suitable for semantic lowering. It does not
preserve an opaque raw-regex node. Every accepted extension—such as atomic
groups, possessive quantifiers, absolute anchors, braced code-point escapes, or
lookbehind—must lower to an explicit semantic construct or capability
requirement.

Target support is evaluated later against a versioned target profile. A source
file cannot select a target or cause a frontend spelling to be copied directly
to emitted output. Unsupported target realization is a portability or target
diagnostic, not a frontend parse decision.

## Diagnostics and fixtures

`dialect.json` defines 45 stable `STRL-FRONTEND-xxxx` identities. Protocol and
resource identities may require synthetic boundary tests; every syntax,
directive, escape, and reference diagnostic is represented in the 45 negative
cases. The 30 positive cases cover every accepted and compatibility-only
feature. Rejected features cannot appear in positive fixtures.

Run:

```text
python3 tooling/legacy_regex_contract.py
```

The certifier validates both JSON Schemas, grammar-rule correspondence, feature
and diagnostic uniqueness, complete positive/negative coverage, UTF-8 fixture
offsets, manifest hashes, and deterministic identity. The initial contract
fingerprint is
`sha256:0cb32dd3ed534d13ce6d4278a2723898ac40bc374fa6d40c5ac43c553a2265ad`.

## Version changes

Backward-compatible additive syntax requires a new minor dialect version.
Removing accepted syntax, changing tokenization or context rules, changing an
existing diagnostic trigger/offset contract, or changing semantic-lowering
intent requires a new major dialect version. Editorial explanation and newly
added fixtures that do not change accepted input may retain the version, but
the checked manifest and certification fingerprint must change visibly.
