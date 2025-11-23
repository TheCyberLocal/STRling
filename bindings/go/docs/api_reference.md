# API Reference - Go

[← Back to README](../README.md)

This document provides a comprehensive reference for the STRling API in **{Language}**.

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

#### Usage (Go)

```go
// Start/End of line anchors (^ and $)
strling.Sequence{
	Parts: []strling.NodeWrapper{
		{Node: &strling.Anchor{At: "Start"}}, // ^
		{Node: &strling.Literal{Value: "hello"}},
		{Node: &strling.Anchor{At: "End"}}, // $
	},
}
```

### Start/End of String

Matches the absolute beginning (`\A`) or end (`\z`) of the string, ignoring multiline mode.

#### Usage (Go)

```go
// Absolute start/end (\A and \z)
strling.Sequence{
	Parts: []strling.NodeWrapper{
		{Node: &strling.Anchor{At: "AbsoluteStart"}}, // \A
		{Node: &strling.Literal{Value: "whole"}},
		{Node: &strling.Anchor{At: "AbsoluteEnd"}}, // \z
	},
}
```

### Word Boundaries

Matches the position between a word character and a non-word character (`\b`), or the inverse (`\B`).

#### Usage (Go)

```go
// Word boundary (\b) and not-word-boundary (\B)
strling.Sequence{
	Parts: []strling.NodeWrapper{
		{Node: &strling.Anchor{At: "WordBoundary"}}, // \b
		{Node: &strling.Literal{Value: "word"}},
		{Node: &strling.Anchor{At: "NotWordBoundary"}}, // \B
	},
}
```

---

## Character Classes

### Built-in Classes

Standard shorthands for common character sets.

-   `\w`: Word characters (alphanumeric + underscore)
-   `\d`: Digits
-   `\s`: Whitespace
-   `.`: Any character (except newline)

#### Usage (Go)

```go
// Shorthands: \d, \w, \s and dot
strling.CharacterClass{Negated: false, Members: []strling.NodeWrapper{{Node: &strling.Escape{Kind: "digit"}}}} // \d
strling.CharacterClass{Negated: false, Members: []strling.NodeWrapper{{Node: &strling.Escape{Kind: "word"}}}}  // \w
strling.CharacterClass{Negated: false, Members: []strling.NodeWrapper{{Node: &strling.Escape{Kind: "space"}}}} // \s
strling.Dot{} // .
```

### Custom Classes & Ranges

Define a set of allowed characters (`[...]`) or a range (`a-z`).

#### Usage (Go)

```go
// Custom class and range: [a-z_]
strling.CharacterClass{
	Negated: false,
	Members: []strling.NodeWrapper{
		{Node: &strling.Range{From: "a", To: "z"}},
		{Node: &strling.Literal{Value: "_"}},
	},
}
```

### Negated Classes

Match any character _not_ in the set (`[^...]`).

#### Usage (Go)

```go
// Negated class: [^0-9]
strling.CharacterClass{
	Negated: true,
	Members: []strling.NodeWrapper{{Node: &strling.Range{From: "0", To: "9"}}},
}
```

### Unicode Properties

Match characters based on Unicode properties (`\p{...}`), such as scripts, categories, or blocks. Unicode property escapes allow matching by Script (e.g. `\p{Latin}`), General Category (e.g. `\p{Lu}` for uppercase letters) or named blocks.

#### Usage (Go)

```go
// Unicode property in a class, e.g. \p{Latin}
strling.CharacterClass{
	Negated: false,
	Members: []strling.NodeWrapper{{Node: &strling.UnicodeProperty{Value: "Latin", Negated: false}}},
}
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

#### Usage (Go)

```go
// Control character literals
strling.Literal{Value: "\n"} // newline
strling.Literal{Value: "\t"} // tab
```

### Hexadecimal & Unicode

Define characters by their code point.

-   `\\xHH`: 2-digit hexadecimal (e.g. `\\x0A`)
-   `\\x{...}`: braced hexadecimal code point (variable length, e.g. `\\x{1F}`)
-   `\\uHHHH`: 4-digit Unicode (e.g. `\\u00A9`)
-   `\\u{...}`: braced Unicode code point (variable length, e.g. `\\u{1F600}`)

#### Usage (Go)

```go
// Hex and Unicode escapes represented as literal values
strling.Literal{Value: "\x41"}   // 'A' using hex
strling.Literal{Value: "\u263A"} // Unicode code point (☺)
```

---

## Quantifiers

### Greedy Quantifiers

Match as much as possible (standard behavior).

-   `*`: 0 or more
-   `+`: 1 or more
-   `?`: 0 or 1
-   `{n,m}`: Specific range

#### Usage (Go)

```go
// Greedy quantifiers
// *      => min:0, max: nil (interpreted as Inf)
strling.Quantifier{Target: strling.NodeWrapper{Node: &strling.Literal{Value: "a"}}, Min: 0, Max: nil, Greedy: true}
// +      => min:1, max:1
strling.Quantifier{Target: strling.NodeWrapper{Node: &strling.Literal{Value: "a"}}, Min: 1, Max: 1, Greedy: true}
// ?      => min:0, max:1
strling.Quantifier{Target: strling.NodeWrapper{Node: &strling.Literal{Value: "x"}}, Min: 0, Max: 1, Greedy: true}
// {n,m}  => explicit range
strling.Quantifier{Target: strling.NodeWrapper{Node: &strling.Literal{Value: "d"}}, Min: 2, Max: 5, Greedy: true}
```

### Lazy Quantifiers

Match as little as possible. Appending `?` to a quantifier (e.g., `*?`).

#### Usage (Go)

```go
// Lazy quantifier example (e.g., *?)
strling.Quantifier{Target: strling.NodeWrapper{Node: &strling.Literal{Value: "a"}}, Min: 0, Max: nil, Lazy: true}
```

### Possessive Quantifiers

Match as much as possible and **do not backtrack**. Appending `+` to a quantifier (e.g., `++`, `*+`).

> **Note:** This is a key performance feature in STRling.

#### Usage (Go)

```go
// Possessive quantifier example (e.g., *+)
strling.Quantifier{Target: strling.NodeWrapper{Node: &strling.Literal{Value: "b"}}, Min: 0, Max: nil, Possessive: true}
```

---

## Groups

### Capturing Groups

Standard groups `(...)` that capture the matched text.

#### Usage (Go)

```go
// Capturing group
strling.Group{Capturing: true, Body: strling.NodeWrapper{Node: &strling.Literal{Value: "abc"}}}
```

### Named Groups

Capturing groups with a specific name `(?<name>...)` for easier extraction.

#### Usage (Go)

```go
// Named capturing group
name := "area"
strling.Group{Capturing: true, Name: &name, Body: strling.NodeWrapper{Node: &strling.Literal{Value: "xxx"}}}
```

### Non-Capturing Groups

Groups `(?:...)` that group logic without capturing text.

#### Usage (Go)

```go
// Non-capturing group
strling.Group{Capturing: false, Body: strling.NodeWrapper{Node: &strling.Literal{Value: "no-capture"}}}
```

### Atomic Groups

Groups `(?>...)` that discard backtracking information once the group matches.

> **Note:** Useful for optimizing performance and preventing catastrophic backtracking.

#### Usage (Go)

```go
// Atomic group (no backtracking inside)
atomic := true
strling.Group{Atomic: &atomic, Body: strling.NodeWrapper{Node: &strling.Literal{Value: "fast"}}}
```

---

## Lookarounds

Zero-width assertions that match a group without consuming characters.

### Lookahead

-   Positive `(?=...)`: Asserts that what follows matches the pattern.
-   Negative `(?!...)`: Asserts that what follows does _not_ match.

#### Usage (Go)

```go
// Positive lookahead: (?=...)
strling.Lookaround{Dir: "Ahead", Neg: false, Body: strling.NodeWrapper{Node: &strling.Literal{Value: "end"}}}
// Negative lookahead: (?!...)
strling.Lookaround{Dir: "Ahead", Neg: true, Body: strling.NodeWrapper{Node: &strling.Literal{Value: "no"}}}
```

### Lookbehind

-   Positive `(?<=...)`: Asserts that what precedes matches the pattern.
-   Negative `(?<!...)`: Asserts that what precedes does _not_ match.

#### Usage (Go)

```go
// Positive lookbehind: (?<=...)
strling.Lookaround{Dir: "Behind", Neg: false, Body: strling.NodeWrapper{Node: &strling.Literal{Value: "pre"}}}
// Negative lookbehind: (?<!...)
strling.Lookaround{Dir: "Behind", Neg: true, Body: strling.NodeWrapper{Node: &strling.Literal{Value: "not"}}}
```

---

## Logic

### Alternation

Matches one pattern OR another (`|`).

#### Usage (Go)

```go
// Alternation (a|b)
strling.Alternation{
	Alternatives: []strling.NodeWrapper{
		{Node: &strling.Literal{Value: "a"}},
		{Node: &strling.Literal{Value: "b"}},
	},
}
```

---

## References

### Backreferences

Reference a previously captured group by index (`\1`) or name (`\k<name>`).

#### Usage (Go)

```go
// Backreference by index
idx := 1
strling.Backreference{Index: &idx}

// Backreference by name
name := "area"
strling.Backreference{Name: &name}
```

---

## Flags & Modifiers

Global flags that alter the behavior of the regex engine.

-   `i`: Case-insensitive
-   `m`: Multiline mode
-   `s`: Dotall (single line) mode
-   `x`: Extended mode (ignore whitespace)

#### Usage (Go)

```go
// Flags (core.Flags from the `core` package)
fw := core.Flags{IgnoreCase: true, Multiline: false, DotAll: false, Unicode: true, Extended: false}
_ = fw
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
%lang go
%engine pcre2
```

```go
// Example: directives are file-level, shown here as the pattern text input
// (directives are parsed by the binding's top-level parser)
pattern := "%flags imsux\n%lang go\n%engine pcre2\n\n^pattern$"
_ = pattern
```
