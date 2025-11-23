# API Reference - {Language}

[← Back to README](../README.md)

This document provides a comprehensive reference for the STRling API in **{Language}**.

## Table of Contents

-   [Anchors](#anchors)
-   [Character Classes](#character-classes)
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

#### Usage ({Language})

{Snippet_Anchors_Line}

### Start/End of String

Matches the absolute beginning (`\A`) or end (`\z`) of the string, ignoring multiline mode.

#### Usage ({Language})

{Snippet_Anchors_String}

### Word Boundaries

Matches the position between a word character and a non-word character (`\b`), or the inverse (`\B`).

#### Usage ({Language})

{Snippet_Anchors_Boundary}

---

## Character Classes

### Built-in Classes

Standard shorthands for common character sets.

-   `\w`: Word characters (alphanumeric + underscore)
-   `\d`: Digits
-   `\s`: Whitespace
-   `.`: Any character (except newline)

#### Usage ({Language})

{Snippet_CharClass_Builtin}

### Custom Classes & Ranges

Define a set of allowed characters (`[...]`) or a range (`a-z`).

#### Usage ({Language})

{Snippet_CharClass_Custom}

### Negated Classes

Match any character _not_ in the set (`[^...]`).

#### Usage ({Language})

{Snippet_CharClass_Negated}

### Unicode Properties

Match characters based on Unicode properties (`\p{...}`), such as scripts, categories, or blocks.

#### Usage ({Language})

{Snippet_CharClass_Unicode}

---

## Quantifiers

### Greedy Quantifiers

Match as much as possible (standard behavior).

-   `*`: 0 or more
-   `+`: 1 or more
-   `?`: 0 or 1
-   `{n,m}`: Specific range

#### Usage ({Language})

{Snippet_Quantifiers_Greedy}

### Lazy Quantifiers

Match as little as possible. Appending `?` to a quantifier (e.g., `*?`).

#### Usage ({Language})

{Snippet_Quantifiers_Lazy}

### Possessive Quantifiers

Match as much as possible and **do not backtrack**. Appending `+` to a quantifier (e.g., `++`, `*+`).

> **Note:** This is a key performance feature in STRling.

#### Usage ({Language})

{Snippet_Quantifiers_Possessive}

---

## Groups

### Capturing Groups

Standard groups `(...)` that capture the matched text.

#### Usage ({Language})

{Snippet_Groups_Capturing}

### Named Groups

Capturing groups with a specific name `(?<name>...)` for easier extraction.

#### Usage ({Language})

{Snippet_Groups_Named}

### Non-Capturing Groups

Groups `(?:...)` that group logic without capturing text.

#### Usage ({Language})

{Snippet_Groups_NonCapturing}

### Atomic Groups

Groups `(?>...)` that discard backtracking information once the group matches.

> **Note:** Useful for optimizing performance and preventing catastrophic backtracking.

#### Usage ({Language})

{Snippet_Groups_Atomic}

---

## Lookarounds

Zero-width assertions that match a group without consuming characters.

### Lookahead

-   Positive `(?=...)`: Asserts that what follows matches the pattern.
-   Negative `(?!...)`: Asserts that what follows does _not_ match.

#### Usage ({Language})

{Snippet_Lookarounds_Ahead}

### Lookbehind

-   Positive `(?<=...)`: Asserts that what precedes matches the pattern.
-   Negative `(?<!...)`: Asserts that what precedes does _not_ match.

#### Usage ({Language})

{Snippet_Lookarounds_Behind}

---

## Logic

### Alternation

Matches one pattern OR another (`|`).

#### Usage ({Language})

{Snippet_Logic_Alternation}

---

## References

### Backreferences

Reference a previously captured group by index (`\1`) or name (`\k<name>`).

#### Usage ({Language})

{Snippet_References}

---

## Flags & Modifiers

Global flags that alter the behavior of the regex engine.

-   `i`: Case-insensitive
-   `m`: Multiline mode
-   `s`: Dotall (single line) mode
-   `x`: Extended mode (ignore whitespace)

#### Usage ({Language})

{Snippet_Flags}
