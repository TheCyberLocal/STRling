# API Reference - Kotlin

[← Back to README](../README.md)

This document provides a comprehensive reference for the STRling API in **Kotlin**.

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

#### Usage (Kotlin)

```kotlin
import strling.core.*

// ^ and $ are represented with Anchor(at = "Start") and Anchor(at = "End")
val anchorStart = Anchor(at = "Start")
val anchorEnd = Anchor(at = "End")

// anchors in a sequence
val anchored = Sequence(parts = listOf(anchorStart, Literal("a"), anchorEnd))
```

### Start/End of String

Matches the absolute beginning (`\A`) or end (`\z`) of the string, ignoring multiline mode.

#### Usage (Kotlin)

```kotlin
import strling.core.*

// Absolute start/end of string
val absoluteStart = Anchor(at = "AbsoluteStart") // \A
val absoluteEnd = Anchor(at = "AbsoluteEnd")     // \z

// Example: match entire string "foo"
val full = Sequence(parts = listOf(absoluteStart, Literal("foo"), absoluteEnd))
```

### Word Boundaries

Matches the position between a word character and a non-word character (`\b`), or the inverse (`\B`).

#### Usage (Kotlin)

```kotlin
import strling.core.*

// Word boundary anchors
val wordBoundary = Anchor(at = "WordBoundary")      // \b
val notWordBoundary = Anchor(at = "NotWordBoundary") // \B

// Example: \bword\b
val bounded = Sequence(parts = listOf(wordBoundary, Literal("word"), wordBoundary))
```

---

## Character Classes

### Built-in Classes

Standard shorthands for common character sets.

-   `\\w`: Word characters (alphanumeric + underscore)
-   `\\d`: Digits
-   `\\s`: Whitespace
-   `.`: Any character (except newline)

#### Usage (Kotlin)

```kotlin
import strling.core.*

// Built-in / shorthand equivalents
val digits = CharacterClass(negated = false, members = listOf(Escape(kind = "digit"))) // \d
val wordChars = CharacterClass(negated = false, members = listOf(Escape(kind = "word"))) // \w
val whitespace = CharacterClass(negated = false, members = listOf(Escape(kind = "whitespace"))) // \s
val anyChar = Dot() // '.'

// Example: sequence of a digit then a word char
val seq = Sequence(parts = listOf(digits, wordChars))
```

### Custom Classes & Ranges

Define a set of allowed characters (`[...]`) or a range (`a-z`).

#### Usage (Kotlin)

```kotlin
import strling.core.*

// custom char class e.g. [A-Za-z0-9_-]
val custom = CharacterClass(
    negated = false,
    members = listOf(Range(from = "A", to = "Z"), Range(from = "a", to = "z"), Range(from = "0", to = "9"), Literal("-"), Literal("_"))
)

// example using it
val token = Sequence(parts = listOf(custom, Quantifier(target = Dot(), min = 0, max = null, greedy = true, lazy = false, possessive = false)))
```

### Negated Classes

Match any character _not_ in the set (`[^...]`).

#### Usage (Kotlin)

```kotlin
import strling.core.*

// negated class: [^0-9]
val notDigits = CharacterClass(negated = true, members = listOf(Range(from = "0", to = "9")))

// example: one non-digit
val oneNotDigit = Quantifier(target = notDigits, min = 1, max = null, greedy = true, lazy = false, possessive = false)
```

### Unicode Properties

Match characters based on Unicode properties (`\\p{...}`), such as scripts, categories, or blocks. Unicode property escapes allow matching by Script (e.g. `\\p{Latin}`), General Category (e.g. `\\p{Lu}` for uppercase letters) or named blocks.

#### Usage (Kotlin)

```kotlin
import strling.core.*

// unicode property 
val letter = UnicodeProperty(value = "Lu")          // General Category: uppercase letter
val scriptLatin = UnicodeProperty(value = "Latin", name = null, negated = false)

val classWithUnicode = CharacterClass(negated = false, members = listOf(letter, scriptLatin))
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

#### Usage (Kotlin)

```kotlin
import strling.core.*

// Control escapes are represented using Escape(kind = ...)
val newline = Escape(kind = "newline")   // \n
val tab = Escape(kind = "tab")           // \t
val nullByte = Escape(kind = "null")     // \0

val seqControls = Sequence(parts = listOf(newline, tab, nullByte))
```

### Hexadecimal & Unicode

Define characters by their code point.

-   `\\xHH`: 2-digit hexadecimal (e.g. `\\x0A`)
-   `\\x{...}`: braced hexadecimal code point (variable length, e.g. `\\x{1F}`)
-   `\\uHHHH`: 4-digit Unicode (e.g. `\\u00A9`)
-   `\\u{...}`: braced Unicode code point (variable length, e.g. `\\u{1F600}`)

#### Usage (Kotlin)

```kotlin
import strling.core.*

// Hex/unicode escapes example using LITERAL members or Escape when the
// binding represents them as Escape kinds.
val hex = Literal("\\u00A9")        // Example literal using a Unicode escape
val braced = Literal("\\u{1F600}") // grinning face (U+1F600)

// If you want to express numeric escapes explicitly as AST class items:
val escapedHex = Escape(kind = "x{1F600}")
```

---

## Quantifiers

### Greedy Quantifiers

Match as much as possible (standard behavior).

-   `*`: 0 or more
-   `+`: 1 or more
-   `?`: 0 or 1
-   `{n,m}`: Specific range

#### Usage (Kotlin)

```kotlin
import kotlinx.serialization.json.JsonPrimitive
import strling.core.*

// Greedy quantifiers: +, *, ?, {n,m}
val oneOrMore = Quantifier(target = Dot(), min = 1, max = null, greedy = true, lazy = false, possessive = false) // +
val zeroOrMore = Quantifier(target = Dot(), min = 0, max = null, greedy = true, lazy = false, possessive = false)   // *
val optional = Quantifier(target = Dot(), min = 0, max = JsonPrimitive(1), greedy = true, lazy = false, possessive = false) // ?
val rangeFiveToTen = Quantifier(target = Dot(), min = 5, max = JsonPrimitive(10), greedy = true, lazy = false, possessive = false) // {5,10}
```

### Lazy Quantifiers

Match as little as possible. Appending `?` to a quantifier (e.g., `*?`).  

#### Usage (Kotlin)

```kotlin
import kotlinx.serialization.json.JsonPrimitive
import strling.core.*

// Lazy quantifiers set lazy = true
val lazyZeroOrMore = Quantifier(target = Dot(), min = 0, max = null, greedy = false, lazy = true, possessive = false) // *?
val lazyRange = Quantifier(target = Dot(), min = 1, max = JsonPrimitive(5), greedy = false, lazy = true, possessive = false) // {1,5}?
```

### Possessive Quantifiers

Match as much as possible and **do not backtrack**. Appending `+` to a quantifier (e.g., `++`, `*+`).

> **Note:** This is a key performance feature in STRling.

#### Usage (Kotlin)

```kotlin
import kotlinx.serialization.json.JsonPrimitive
import strling.core.*

// Possessive quantifiers set possessive = true
val possessiveOneOrMore = Quantifier(target = Dot(), min = 1, max = null, greedy = true, lazy = false, possessive = true) // ++
val possessiveRange = Quantifier(target = Dot(), min = 0, max = JsonPrimitive(3), greedy = true, lazy = false, possessive = true) // {0,3}+
```

---

## Groups

### Capturing Groups

Standard groups `(...)` that capture the matched text.

#### Usage (Kotlin)

```kotlin
import strling.core.*

// Capturing group
val capture = Group(capturing = true, body = Sequence(parts = listOf(Literal("a"))))

// Non-capturing would set capturing=false (see other section)
```

### Named Groups

Capturing groups with a specific name `(?<name>...)` for easier extraction.

#### Usage (Kotlin)

```kotlin
import strling.core.*

// Named capturing group (name parameter)
val named = Group(capturing = true, name = "area", body = CharacterClass(negated = false, members = listOf(Range(from = "0", to = "9"))))

// `name` is optional — used for emitters that support named captures
```

### Non-Capturing Groups

Groups `(?:...)` that group logic without capturing text.

#### Usage (Kotlin)

```kotlin
import strling.core.*

// Non-capturing group
val nonCapture = Group(capturing = false, body = Sequence(parts = listOf(Literal("foo"))))
```

### Atomic Groups

Groups `(?>...)` that discard backtracking information once the group matches.

> **Note:** Useful for optimizing performance and preventing catastrophic backtracking.

#### Usage (Kotlin)

```kotlin
import strling.core.*

// Atomic group: mark with atomic = true
val atomic = Group(capturing = true, atomic = true, body = Sequence(parts = listOf(Literal("a+"))))
```

---

## Lookarounds

Zero-width assertions that match a group without consuming characters.    

### Lookahead

-   Positive `(?=...)`: Asserts that what follows matches the pattern.    
-   Negative `(?!...)`: Asserts that what follows does _not_ match.       

#### Usage (Kotlin)

```kotlin
import strling.core.*

// Positive lookahead (?=...)
val lookahead = Lookahead(body = Literal("foo"))

// Negative lookahead (?!...)
val negativeLookahead = NegativeLookahead(body = Literal("bar"))

// Example: assert 'foo' follows but don't consume
val example = Sequence(parts = listOf(Literal("x"), lookahead))
```

### Lookbehind

-   Positive `(?<=...)`: Asserts that what precedes matches the pattern.  
-   Negative `(?<!...)`: Asserts that what precedes does _not_ match.     

#### Usage (Kotlin)

```kotlin
import strling.core.*

// Positive lookbehind (?<=...)
val lookbehind = Lookbehind(body = Literal("foo"))

// Negative lookbehind (?<!...)
val negativeLookbehind = NegativeLookbehind(body = Literal("bar"))

// Example: assert something precedes the current position
val example = Sequence(parts = listOf(lookbehind, Literal("x")))
```

---

## Logic

### Alternation

Matches one pattern OR another (`|`).

#### Usage (Kotlin)

```kotlin
import strling.core.*

// Alternation: matches one of multiple patterns
val either = Alternation(alternatives = listOf(Literal("cat"), Literal("dog")))

// Combined with sequence
val sentence = Sequence(parts = listOf(Literal("I have a "), either))
```

---

## References

### Backreferences

Reference a previously captured group by index (`\\1`) or name (`\\k<name>`).

#### Usage (Kotlin)

```kotlin
import strling.core.*

// Backreference by index
val backref = Backreference(index = 1)

// Backreference by name
val namedBackref = Backreference(name = "area")

// Typical usage: capture then backreference
val pattern = Sequence(parts = listOf(Group(capturing = true, body = Literal("x")), backref))
```

---

## Flags & Modifiers

Global flags that alter the behavior of the regex engine.

-   `i`: Case-insensitive
-   `m`: Multiline mode
-   `s`: Dotall (single line) mode
-   `x`: Extended mode (ignore whitespace)

#### Usage (Kotlin)

```kotlin
import strling.core.*

// Flags object
val flags = Flags(ignoreCase = true, multiline = false, dotAll = false, unicode = true, extended = false)

// or from letters (i, m, s, u, x)
val fromLetters = Flags.fromLetters("imsux")
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
%lang kotlin
%engine pcre2
```

```text
%flags imsux
%lang kotlin
%engine pcre2
```

> Notes: Directives are a file-level hint to emitters / parsers and are
> binding-agnostic — %flags gets parsed into a `Flags` object (see above).
