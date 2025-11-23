# API Reference - Swift

[← Back to README](../README.md)

This document provides a comprehensive reference for the STRling API in **Swift**.

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

#### Usage (Swift)

```swift
// Start/end of line
let start: Node = .anchor("Start")
let end: Node = .anchor("End")
```

### Start/End of String

Matches the absolute beginning (`\A`) or end (`\z`) of the string, ignoring multiline mode.

#### Usage (Swift)

```swift
// Absolute start/end of string
let absStart: Node = .anchor("AbsoluteStart")
let absEnd: Node = .anchor("AbsoluteEnd")
```

### Word Boundaries

Matches the position between a word character and a non-word character (`\b`), or the inverse (`\B`).

#### Usage (Swift)

```swift
// Word boundaries
let wordBoundary: Node = .anchor("WordBoundary")
let notWordBoundary: Node = .anchor("NotWordBoundary")
```

---

## Character Classes

### Built-in Classes

Standard shorthands for common character sets.

-   `\w`: Word characters (alphanumeric + underscore)
-   `\d`: Digits
-   `\s`: Whitespace
-   `.`: Any character (except newline)

#### Usage (Swift)

```swift
// Built-in shorthand classes and dot (any char)
let digits: Node = .charClass(#"\d"#)
let words: Node = .charClass(#"\w"#)
let spaces: Node = .charClass(#"\s"#)
let anyChar: Node = .dot
```

### Custom Classes & Ranges

Define a set of allowed characters (`[...]`) or a range (`a-z`).

#### Usage (Swift)

```swift
// Custom classes and ranges
let vowelsOrDigits: Node = .charClass(negated: false, items: [.literal("a"), .literal("e"), .literal("i"), .literal("o"), .literal("u"), .range("0","9")])
```

### Negated Classes

Match any character _not_ in the set (`[^...]`).

#### Usage (Swift)

```swift
// Negated class (not a digit)
let notDigit: Node = .charClass(negated: true, items: [.range("0","9")])
```

### Unicode Properties

Match characters based on Unicode properties (`\p{...}`), such as scripts, categories, or blocks. Unicode property escapes allow matching by Script (e.g. `\p{Latin}`), General Category (e.g. `\p{Lu}` for uppercase letters) or named blocks.

#### Usage (Swift)

```swift
// Unicode property (General Category: Letter)
let letters: Node = .charClass(negated: false, items: [.unicodeProperty(property: nil, value: "L", negated: false)])
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

#### Usage (Swift)

```swift
// Control escapes (Swift string literals)
let newline: Node = .lit("\n")
let tab: Node = .lit("\t")
```

### Hexadecimal & Unicode

Define characters by their code point.

-   `\\xHH`: 2-digit hexadecimal (e.g. `\\x0A`)
-   `\\x{...}`: braced hexadecimal code point (variable length, e.g. `\\x{1F}`)
-   `\\uHHHH`: 4-digit Unicode (e.g. `\\u00A9`)
-   `\\u{...}`: braced Unicode code point (variable length, e.g. `\\u{1F600}`)

#### Usage (Swift)

```swift
// Hex / Unicode escapes (Swift string form)
let copyright: Node = .lit("\u{00A9}") // ©
let emoji: Node = .lit("\u{1F600}") // 😀
```

---

## Quantifiers

### Greedy Quantifiers

Match as much as possible (standard behavior).

-   `*`: 0 or more
-   `+`: 1 or more
-   `?`: 0 or 1
-   `{n,m}`: Specific range

#### Usage (Swift)

```swift
// Greedy quantifiers
let zeroOrMore: Node = .quant(body: .lit("a"), min: 0, max: "Inf", mode: "Greedy")
let oneOrMore: Node = .quant(body: .lit("a"), min: 1, max: "Inf", mode: "Greedy")
let optional: Node = .quant(body: .lit("a"), min: 0, max: "1", mode: "Greedy")
let exactly3: Node = .quant(body: .lit("a"), min: 3, max: "3", mode: "Greedy")
```

### Lazy Quantifiers

Match as little as possible. Appending `?` to a quantifier (e.g., `*?`).

#### Usage (Swift)

```swift
// Lazy quantifier (use mode: "Lazy")
let lazy: Node = .quant(body: .lit("a"), min: 0, max: "Inf", mode: "Lazy")
```

### Possessive Quantifiers

Match as much as possible and **do not backtrack**. Appending `+` to a quantifier (e.g., `++`, `*+`).

> **Note:** This is a key performance feature in STRling.

#### Usage (Swift)

```swift
// Possessive quantifier (use mode: "Possessive")
let possessive: Node = .quant(body: .lit("a"), min: 1, max: "Inf", mode: "Possessive")
```

---

## Groups

### Capturing Groups

Standard groups `(...)` that capture the matched text.

#### Usage (Swift)

```swift
// Capturing group
let capture: Node = .group(body: .lit("abc"), capturing: true)
```

### Named Groups

Capturing groups with a specific name `(?<name>...)` for easier extraction.

#### Usage (Swift)

```swift
// Named capturing group
let named: Node = .group(body: .lit("id"), capturing: true, name: "id")
```

### Non-Capturing Groups

Groups `(?:...)` that group logic without capturing text.

#### Usage (Swift)

```swift
// Non-capturing group
let nonCapture: Node = .group(body: .alt([.lit("a"), .lit("b")]), capturing: false)
```

### Atomic Groups

Groups `(?>...)` that discard backtracking information once the group matches.

> **Note:** Useful for optimizing performance and preventing catastrophic backtracking.

#### Usage (Swift)

```swift
// Atomic group (optimize backtracking)
let atomic: Node = .group(body: .quant(body: .lit("a"), min: 1, max: "Inf", mode: "Greedy"), capturing: false, name: nil, atomic: true)
```

---

## Lookarounds

Zero-width assertions that match a group without consuming characters.

### Lookahead

-   Positive `(?=...)`: Asserts that what follows matches the pattern.
-   Negative `(?!...)`: Asserts that what follows does _not_ match.

#### Usage (Swift)

```swift
// Lookahead (positive and negative)
let positiveAhead: Node = .look(dir: "Ahead", neg: false, body: .lit("foo"))
let negativeAhead: Node = .look(dir: "Ahead", neg: true, body: .lit("foo"))
```

### Lookbehind

-   Positive `(?<=...)`: Asserts that what precedes matches the pattern.
-   Negative `(?<!...)`: Asserts that what precedes does _not_ match.

#### Usage (Swift)

```swift
// Lookbehind (positive and negative)
let positiveBehind: Node = .look(dir: "Behind", neg: false, body: .lit("foo"))
let negativeBehind: Node = .look(dir: "Behind", neg: true, body: .lit("foo"))
```

---

## Logic

### Alternation

Matches one pattern OR another (`|`).

#### Usage (Swift)

```swift
// Alternation (pattern A or B)
let either: Node = .alt([.lit("cat"), .lit("dog")])
```

---

## References

### Backreferences

Reference a previously captured group by index (`\1`) or name (`\k<name>`).

#### Usage (Swift)

```swift
// Backreference by index or name
let withRef: Node = .seq([.group(body: .lit("x"), capturing: true), .backref(byIndex: 1)])
let withNamed: Node = .seq([.group(body: .lit("id"), capturing: true, name: "id"), .backref(byName: "id")])
```

---

## Flags & Modifiers

Global flags that alter the behavior of the regex engine.

-   `i`: Case-insensitive
-   `m`: Multiline mode
-   `s`: Dotall (single line) mode
-   `x`: Extended mode (ignore whitespace)

#### Usage (Swift)

```swift
// Flags (controls matching behaviour)
let flags = Flags(ignoreCase: true, multiline: false, dotAll: false, unicode: true, extended: false)
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
%lang Swift
%engine pcre2
```
