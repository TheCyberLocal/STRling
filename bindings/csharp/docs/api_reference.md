# API Reference - C#

[← Back to README](../README.md)

This document provides a comprehensive reference for the STRling API in **C#**.

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

#### Usage (C#)

```csharp
using Strling.Core;

// Start/End of line anchors
var start = new Anchor("Start");
var end   = new Anchor("End");
```

### Start/End of String

Matches the absolute beginning (`\A`) or end (`\z`) of the string, ignoring multiline mode.

#### Usage (C#)

```csharp
using Strling.Core;

// Absolute start/end of string
var absoluteStart = new Anchor("AbsoluteStart");
var absoluteEnd   = new Anchor("AbsoluteEnd");
```

### Word Boundaries

Matches the position between a word character and a non-word character (`\b`), or the inverse (`\B`).

#### Usage (C#)

```csharp
using Strling.Core;

// Word boundary and inverse
var wordBoundary    = new Anchor("WordBoundary");
var notWordBoundary = new Anchor("NotWordBoundary");
```

---

## Character Classes

### Built-in Classes

Standard shorthands for common character sets.

-   `\w`: Word characters (alphanumeric + underscore)
-   `\d`: Digits
-   `\s`: Whitespace
-   `.`: Any character (except newline)

#### Usage (C#)

```csharp
using Strling.Core;

// Built-in class shorthands using class escape items
var digitClass = new CharClass(false, new List<ClassItem> { new ClassEscape("digit") });   // \d
var wordClass  = new CharClass(false, new List<ClassItem> { new ClassEscape("word") });    // \w
var spaceClass = new CharClass(false, new List<ClassItem> { new ClassEscape("space") });   // \s
```

### Custom Classes & Ranges

Define a set of allowed characters (`[...]`) or a range (`a-z`).

#### Usage (C#)

```csharp
using Strling.Core;

// Custom class and range
var customClass = new CharClass(false, new List<ClassItem> { new ClassRange("a", "z"), new ClassLiteral("@") });
```

### Negated Classes

Match any character _not_ in the set (`[^...]`).

#### Usage (C#)

```csharp
using Strling.Core;

// Negated class: [^abc]
var negated = new CharClass(true, new List<ClassItem> { new ClassLiteral("a"), new ClassLiteral("b"), new ClassLiteral("c") });
```

### Unicode Properties

Match characters based on Unicode properties (`\p{...}`), such as scripts, categories, or blocks. Unicode property escapes allow matching by Script (e.g. `\p{Latin}`), General Category (e.g. `\p{Lu}` for uppercase letters) or named blocks.

#### Usage (C#)

```csharp
using Strling.Core;

// Unicode property match (script or category)
var latinScript = new CharClass(false, new List<ClassItem> { new ClassUnicodeProperty("Script", "Latin", false) });
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

#### Usage (C#)

```csharp
using Strling.Core;

// Control character escapes
var newline = new Lit("\\n");
var tab     = new Lit("\\t");
```

### Hexadecimal & Unicode

Define characters by their code point.

-   `\\xHH`: 2-digit hexadecimal (e.g. `\\x0A`)
-   `\\x{...}`: braced hexadecimal code point (variable length, e.g. `\\x{1F}`)
-   `\\uHHHH`: 4-digit Unicode (e.g. `\\u00A9`)
-   `\\u{...}`: braced Unicode code point (variable length, e.g. `\\u{1F600}`)

#### Usage (C#)

```csharp
using Strling.Core;

// Hex / Unicode escapes
var hex    = new Lit("\\x0A");
var unicode = new Lit("\\u{1F600}");
```

---

## Quantifiers

### Greedy Quantifiers

Match as much as possible (standard behavior).

-   `*`: 0 or more
-   `+`: 1 or more
-   `?`: 0 or 1
-   `{n,m}`: Specific range

#### Usage (C#)

```csharp
using Strling.Core;

// Greedy quantifiers
var zeroOrMore = new Quant(new Lit("a"), 0, null, true, false, false);
var oneOrMore  = new Quant(new Lit("a"), 1, null, true, false, false);
var optional   = new Quant(new Lit("a"), 0, 1, true, false, false);
var rangeQ     = new Quant(new Lit("a"), 2, 4, true, false, false);
```

### Lazy Quantifiers

Match as little as possible. Appending `?` to a quantifier (e.g., `*?`).

#### Usage (C#)

```csharp
using Strling.Core;

// Lazy quantifier (minimizing)
var lazy = new Quant(new Lit("a"), 0, null, false, true, false);
```

### Possessive Quantifiers

Match as much as possible and **do not backtrack**. Appending `+` to a quantifier (e.g., `++`, `*+`).

> **Note:** This is a key performance feature in STRling.

#### Usage (C#)

```csharp
using Strling.Core;

// Possessive quantifier (no backtracking)
var possessive = new Quant(new Lit("a"), 0, null, false, false, true);
```

---

## Groups

### Capturing Groups

Standard groups `(...)` that capture the matched text.

#### Usage (C#)

```csharp
using Strling.Core;

// Capturing group
var cap = new Group(true, new Lit("abc"), null, false);
```

### Named Groups

Capturing groups with a specific name `(?<name>...)` for easier extraction.

#### Usage (C#)

```csharp
using Strling.Core;

// Named capturing group
var named = new Group(true, new Quant(new Lit("\\d"), 3, 3, true, false, false), "area", false);
```

### Non-Capturing Groups

Groups `(?:...)` that group logic without capturing text.

#### Usage (C#)

```csharp
using Strling.Core;

// Non-capturing group
var noncap = new Group(false, new Alt(new List<Node> { new Lit("yes"), new Lit("no") }), null, false);
```

### Atomic Groups

Groups `(?>...)` that discard backtracking information once the group matches.

> **Note:** Useful for optimizing performance and preventing catastrophic backtracking.

#### Usage (C#)

```csharp
using Strling.Core;

// Atomic group (prevents backtracking within)
var atomic = new Group(true, new Quant(new Lit("a"), 1, null, true, false, false), null, true);
```

---

## Lookarounds

Zero-width assertions that match a group without consuming characters.

### Lookahead

-   Positive `(?=...)`: Asserts that what follows matches the pattern.
-   Negative `(?!...)`: Asserts that what follows does _not_ match.

#### Usage (C#)

```csharp
using Strling.Core;

// Lookahead / negative lookahead
var posAhead = new Lookahead(new Lit("foo"));
var negAhead = new NegativeLookahead(new Lit("bar"));
```

### Lookbehind

-   Positive `(?<=...)`: Asserts that what precedes matches the pattern.
-   Negative `(?<!...)`: Asserts that what precedes does _not_ match.

#### Usage (C#)

```csharp
using Strling.Core;

// Lookbehind / negative lookbehind
var posBehind = new Lookbehind(new Lit("foo"));
var negBehind = new NegativeLookbehind(new Lit("bar"));
```

---

## Logic

### Alternation

Matches one pattern OR another (`|`).

#### Usage (C#)

```csharp
using Strling.Core;

// Alternation (OR)
var alt = new Alt(new List<Node> { new Lit("cat"), new Lit("dog") });
```

---

## References

### Backreferences

Reference a previously captured group by index (`\1`) or name (`\k<name>`).

#### Usage (C#)

```csharp
using Strling.Core;

// Backreferences by index and name
var byIndex = new Backref(1, null);
var byName  = new Backref(null, "area");
```

---

## Flags & Modifiers

Global flags that alter the behavior of the regex engine.

-   `i`: Case-insensitive
-   `m`: Multiline mode
-   `s`: Dotall (single line) mode
-   `x`: Extended mode (ignore whitespace)

#### Usage (C#)

```csharp
using Strling.Core;

// Flags object and helper
var flags = new Flags { IgnoreCase = true, Multiline = true };
var viaLetters = Flags.FromLetters("im");
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
%lang C#
%engine pcre2
```

```csharp
using Strling.Core;

// Example directives -> translated to programmatic objects
// %flags imsux
var directivesFlags = Flags.FromLetters("imsux");

// %lang C# and %engine pcre2 are hints for emitters; in code you generally pass a target engine when emitting
```
