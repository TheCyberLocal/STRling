# Semantic STRling 1.0 canonical formatting

This document is normative for canonical presentation. It defines no parser or
formatter implementation and does not change semantic equality.

## File layout

-   Write UTF-8 without a byte-order mark, use LF line endings, and end with one
    LF.
-   Write `semantic strling 1.0;` on the first line and the case declaration on
    the second. Insert one blank line before `pattern`.
-   Use four ASCII spaces per block level. Never write tabs or trailing spaces.
-   Put an opening brace on the construct's introducing line and its closing
    brace alone at the introducing indentation. Do not append a semicolon after
    a block construct.
-   Write one leaf statement or set member per line and terminate it with `;`.
-   Write all keywords lowercase and use one ASCII space between adjacent word
    or literal tokens.

## Identifiers, numbers, and strings

Identifiers already use lowercase ASCII snake form and are preserved exactly.
Integers use their shortest decimal spelling. `unbounded` is never formatted as
a sentinel number.

Strings use double quotes. Printable Unicode scalars other than quote and
backslash are written directly. Quote and backslash use `\"` and `\\`. The
controls U+0008, U+000C, U+000A, U+000D, U+0009, and U+0000 use `\b`, `\f`,
`\n`, `\r`, `\t`, and `\0`. Other non-printable scalars use uppercase
hexadecimal `\u{...}` with no leading zeroes. A formatter never introduces a
surrogate escape or target-regex escape.

## Comments and sets

Canonical output preserves comments and their source order, normalizes one
space after `#` for nonempty comment text, and aligns a standalone comment with
the following construct. Blank-line runs collapse to one blank line.

Character-set members are written in authored order. Member order has no
semantic effect after canonical normalization, but formatting alone does not
sort, deduplicate, or otherwise rewrite authored structure. A later optional
semantic rewrite may canonicalize equivalent set syntax as a separate,
explicit operation.

## Stability requirement

A conforming formatter must be idempotent. Once the parser exists,
parse/format/parse must preserve the alpha-equivalent canonical Semantic IR,
all material capture names, and deterministic preorder identities. Formatting
changes source spans only; spans remain non-semantic attribution.
