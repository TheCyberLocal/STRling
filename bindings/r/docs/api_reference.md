# API Reference - R

[← Back to README](../README.md)

This document provides a comprehensive reference for the STRling API in **R**.

## Table of Contents

-   [Anchors](#anchors)
-   [Character Classes](#character-classes)
-   [Escape Sequences](#escape-sequences)
-   [Quantifiers](#quantifiers)
-   [Groups](#groups)
-   [Lookarounds](#lookarounds)
-   [Logic](#logic)
-   [References](#references)
-   [Flags & Modifiers](#flags--modifiers)

---

## Anchors

Anchors match a position within the string, not a character itself.

### Start/End of Line

Matches the beginning (`^`) or end (`$`) of a line.

#### Usage (R)

```r
# Line anchors: Start (^) and End ($)
pattern <- strling_sequence(parts = list(
	strling_anchor("Start"),
	strling_literal("abc"),
	strling_anchor("End")
))
# Start of line.
# End of line.
ir <- compile_ast(pattern)
print(ir)
```

### Start/End of String

Matches the absolute beginning (`\A`) or end (`\z`) of the string, ignoring multiline mode.

#### Usage (R)

```r
# Absolute string anchors: \A and \z
pattern <- strling_sequence(parts = list(
	strling_anchor("AbsoluteStart"),
	strling_literal("hello"),
	strling_anchor("AbsoluteEnd")
))
# Start of string.
# End of string.
ir <- compile_ast(pattern)
print(ir)
```

### Word Boundaries

Matches the position between a word character and a non-word character (`\b`), or the inverse (`\B`).

#### Usage (R)

```r
# Word boundary and its inverse
pattern <- strling_sequence(parts = list(
	strling_anchor("Start"),
	strling_group(strling_character_class(list(strling_class_escape("w"))), capturing = TRUE),
	strling_anchor("WordBoundary"),
	strling_group(strling_character_class(list(strling_class_escape("d"))), capturing = TRUE)
))
# Word boundary between word-char and non-word-char
ir <- compile_ast(pattern)
print(ir)
```

---

## Character Classes

### Built-in Classes

Standard shorthands for common character sets.

-   `\w`: Word characters (alphanumeric + underscore)
-   `\d`: Digits
-   `\s`: Whitespace
-   `.`: Any character (except newline)

#### Usage (R)

```r
# Built-in shorthand classes like \d, \w and \s
pattern <- strling_sequence(parts = list(
	strling_anchor("Start"),
	strling_quantifier(strling_character_class(list(strling_class_escape("d"))), min = 3L, max = 3L),
	strling_anchor("End")
))
# Match exactly 3 digits (\d{3})
ir <- compile_ast(pattern)
print(ir)
```

### Custom Classes & Ranges

Define a set of allowed characters (`[...]`) or a range (`a-z`).

#### Usage (R)

```r
# Custom character class and ranges
# Equivalent to [abc] or [0-9]
custom <- strling_character_class(items = list(
	strling_class_literal("a"),
	strling_class_literal("b"),
	strling_class_literal("c")
))
range <- strling_character_class(items = list(strling_class_range("0", "9")))
pattern <- strling_sequence(parts = list(strling_anchor("Start"), custom, range, strling_anchor("End")))
ir <- compile_ast(pattern)
print(ir)
```

### Negated Classes

Match any character _not_ in the set (`[^...]`).

#### Usage (R)

```r
# Negated character class (equivalent to [^aeiou])
not_vowels <- strling_character_class(items = list(
	strling_class_literal("a"), strling_class_literal("e"), strling_class_literal("i"),
	strling_class_literal("o"), strling_class_literal("u")
), negated = TRUE)
pattern <- strling_sequence(parts = list(strling_anchor("Start"), not_vowels, strling_anchor("End")))
ir <- compile_ast(pattern)
print(ir)
```

### Unicode Properties

Match characters based on Unicode properties (`\p{...}`), such as scripts, categories, or blocks. Unicode property escapes allow matching by Script (e.g. `\p{Latin}`), General Category (e.g. `\p{Lu}` for uppercase letters) or named blocks.

#### Usage (R)

```r
# Unicode property escapes: use ClassEscape with type 'p' and property name
upper <- strling_character_class(items = list(strling_class_escape("p", property = "Lu")))
pattern <- strling_sequence(parts = list(strling_anchor("Start"), upper, strling_anchor("End")))
# Match a single Unicode uppercase letter (\p{Lu})
ir <- compile_ast(pattern)
print(ir)
```

## Escape Sequences

Represent special characters, control codes, and numeric character code escapes. The template separates Control Character escapes from Hexadecimal/Unicode escapes so bindings can provide focused examples.

### Control Characters

Standard control escapes supported across most engines and in STRling's grammar:

-   `\\n`: Newline
-   `\\r`: Carriage Return
-   `\\t`: Tab
-   `\\f`: Form Feed
-   `\\v`: Vertical Tab
-   `\\0`: Null Byte

#### Usage (R)

```r
# Control escapes can be represented as literal content in the AST
pattern_n <- strling_sequence(parts = list(strling_literal("\n"), strling_literal("end")))
pattern_tab <- strling_sequence(parts = list(strling_literal("\t"), strling_literal("tab")))
ir_n <- compile_ast(pattern_n)
ir_tab <- compile_ast(pattern_tab)
print(ir_n)
print(ir_tab)
```

### Hexadecimal & Unicode

Define characters by their code point.

-   `\\xHH`: 2-digit hexadecimal (e.g. `\\x0A`)
-   `\\x{...}`: braced hexadecimal code point (variable length, e.g. `\\x{1F}`)
-   `\\uHHHH`: 4-digit Unicode (e.g. `\\u00A9`)
-   `\\u{...}`: braced Unicode code point (variable length, e.g. `\\u{1F600}`)

#### Usage (R)

```r
# Hex and Unicode escapes can be represented using literal values
pattern_hex <- strling_sequence(parts = list(strling_literal("\x41"), strling_literal("end")))   # \x41 -> 'A'
pattern_u <- strling_sequence(parts = list(strling_literal("\u0041"), strling_literal("end")))    # \u0041 -> 'A'
ir_hex <- compile_ast(pattern_hex)
ir_u   <- compile_ast(pattern_u)
print(ir_hex)
print(ir_u)
```

---

## Quantifiers

### Greedy Quantifiers

Match as much as possible (standard behavior).

-   `*`: 0 or more
-   `+`: 1 or more
-   `?`: 0 or 1
-   `{n,m}`: Specific range

#### Usage (R)

```r
# Greedy quantifier examples
letters_plus <- strling_quantifier(strling_character_class(list(strling_class_escape("w"))), min = 1L, max = NULL, mode = "Greedy")
pattern <- strling_sequence(parts = list(strling_anchor("Start"), letters_plus, strling_anchor("End")))
ir <- compile_ast(pattern)
print(ir)
```

### Lazy Quantifiers

Match as little as possible. Appending `?` to a quantifier (e.g., `*?`).

#### Usage (R)

```r
# Lazy quantifier (mode = "Lazy")
lazy_match <- strling_quantifier(strling_character_class(list(strling_class_escape("w"))), min = 0L, max = NULL, mode = "Lazy")
pattern <- strling_sequence(parts = list(strling_anchor("Start"), lazy_match, strling_anchor("End")))
ir <- compile_ast(pattern)
print(ir)
```

### Possessive Quantifiers

Match as much as possible and **do not backtrack**. Appending `+` to a quantifier (e.g., `++`, `*+`).

> **Note:** This is a key performance feature in STRling.

#### Usage (R)

```r
# Possessive quantifier (mode = "Possessive") — no backtracking
possessive <- strling_quantifier(strling_character_class(list(strling_class_escape("d"))), min = 1L, max = NULL, mode = "Possessive")
pattern <- strling_sequence(parts = list(strling_anchor("Start"), possessive, strling_anchor("End")))
ir <- compile_ast(pattern)
print(ir)
```

---

## Groups

### Capturing Groups

Standard groups `(...)` that capture the matched text.

#### Usage (R)

```r
# Capturing group
capt <- strling_group(strling_literal("abc"), capturing = TRUE)
pattern <- strling_sequence(parts = list(strling_anchor("Start"), capt, strling_anchor("End")))
ir <- compile_ast(pattern)
print(ir)
```

### Named Groups

Capturing groups with a specific name `(?<name>...)` for easier extraction.

#### Usage (R)

```r
# Named capturing group
named <- strling_group(strling_literal("\d\d\d"), capturing = TRUE, name = "area")
pattern <- strling_sequence(parts = list(strling_anchor("Start"), named, strling_anchor("End")))
ir <- compile_ast(pattern)
print(ir)
```

### Non-Capturing Groups

Groups `(?:...)` that group logic without capturing text.

#### Usage (R)

```r
# Non-capturing group
noncap <- strling_group(strling_alternation(list(strling_literal("a"), strling_literal("b"))), capturing = FALSE)
pattern <- strling_sequence(parts = list(strling_anchor("Start"), noncap, strling_anchor("End")))
ir <- compile_ast(pattern)
print(ir)
```

### Atomic Groups

Groups `(?>...)` that discard backtracking information once the group matches.

> **Note:** Useful for optimizing performance and preventing catastrophic backtracking.

#### Usage (R)

```r
# Atomic group — prevent backtracking after a match inside the group
atomic <- strling_group(strling_quantifier(strling_literal("a"), min = 1L, max = NULL), capturing = TRUE, atomic = TRUE)
pattern <- strling_sequence(parts = list(strling_anchor("Start"), atomic, strling_anchor("End")))
ir <- compile_ast(pattern)
print(ir)
```

---

## Lookarounds

Zero-width assertions that match a group without consuming characters.

### Lookahead

-   Positive `(?=...)`: Asserts that what follows matches the pattern.
-   Negative `(?!...)`: Asserts that what follows does _not_ match.

#### Usage (R)

```r
# Lookahead examples
pos_ahead <- strling_lookaround(strling_literal("end"), kind = "Lookahead", negated = FALSE)
neg_ahead <- strling_lookaround(strling_literal("nope"), kind = "Lookahead", negated = TRUE)
pattern <- strling_sequence(parts = list(strling_anchor("Start"), pos_ahead, strling_anchor("End")))
ir_pos <- compile_ast(pattern)
ir_neg <- compile_ast(strling_sequence(parts = list(strling_anchor("Start"), neg_ahead, strling_anchor("End"))))
print(ir_pos)
print(ir_neg)
```

### Lookbehind

-   Positive `(?<=...)`: Asserts that what precedes matches the pattern.
-   Negative `(?<!...)`: Asserts that what precedes does _not_ match.

#### Usage (R)

```r
# Lookbehind examples
pos_behind <- strling_lookaround(strling_literal("pre"), kind = "Lookbehind", negated = FALSE)
neg_behind <- strling_lookaround(strling_literal("pre"), kind = "Lookbehind", negated = TRUE)
pattern <- strling_sequence(parts = list(strling_anchor("Start"), pos_behind, strling_literal("x"), strling_anchor("End")))
ir1 <- compile_ast(pattern)
print(ir1)
```

---

## Logic

### Alternation

Matches one pattern OR another (`|`).

#### Usage (R)

```r
# Alternation (a|b)
alt <- strling_alternation(branches = list(strling_literal("a"), strling_literal("b")))
pattern <- strling_sequence(parts = list(strling_anchor("Start"), alt, strling_anchor("End")))
ir <- compile_ast(pattern)
print(ir)
```

---

## References

### Backreferences

Reference a previously captured group by index (`\1`) or name (`\k<name>`).

#### Usage (R)

```r
# Backreference by index or name
by_index <- strling_backreference(index = 1L)
by_name <- strling_backreference(name = "mycap")
pattern <- strling_sequence(parts = list(
	strling_group(strling_literal("foo"), capturing = TRUE, name = "mycap"),
	strling_literal("-"),
	by_name
))
ir <- compile_ast(pattern)
print(ir)
```

---

## Flags & Modifiers

Global flags that alter the behavior of the regex engine.

-   `i`: Case-insensitive
-   `m`: Multiline mode
-   `s`: Dotall (single line) mode
-   `x`: Extended mode (ignore whitespace)

#### Usage (R)

```r
# Flags / modifiers are typically handled at the emitter or directive layer.
# Build the AST then pass flags through emitters or directives. Example IR inspection:
pattern <- strling_sequence(parts = list(strling_anchor("Start"), strling_literal("Hello"), strling_anchor("End")))
ir <- compile_ast(pattern)
print(ir)
```

---

## Directives

STRling supports a small set of file-level directives which must appear at the top of a pattern file (before any pattern content). Directives are used to configure parsing and emission behavior and are applied per-file.

-   `%flags <letters>` — Sets global flags for the pattern. Letters mirror common regex engines (for example `i` for case-insensitive, `m` for multiline, `s` for dotall, `x` for free-spacing). Flags are parsed into the `Flags` object and may alter parsing semantics (e.g., free-spacing) or are handed off to emitters.
-   `%lang <language>` — (Optional) Hint to emitters about the target language for code generation or examples.
-   `%engine <engine>` — (Optional) Request a specific engine/emitter (for example `pcre2` or `js`). If omitted, the default emitter for the binding is used.

Example directives block:

```text
%flags imsux
%lang R
%engine pcre2
```

```text
%flags imsx
%lang R
%engine pcre2
```

```r
# In R you construct the AST with the constructor helpers and compilation happens via `compile_ast()`.
# Emitters that honor directives will consume the IR and directives to produce a final regex.
```
