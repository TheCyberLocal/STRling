# API Reference - Java

[← Back to README](../README.md)

This document provides a comprehensive reference for the STRling API in **Java**.

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

#### Usage (Java)

```java
import com.strling.core.Nodes;
import java.util.List;

// Start of line (^)
Nodes.Node start = new Nodes.Anchor("Start");

// End of line ($)
Nodes.Node end = new Nodes.Anchor("End");
```

### Start/End of String

Matches the absolute beginning (`\A`) or end (`\z`) of the string, ignoring multiline mode.

#### Usage (Java)

```java
import com.strling.core.Nodes;

// Absolute beginning (\A)
Nodes.Node absStart = new Nodes.Anchor("AbsoluteStart");

// Absolute end (\z)
Nodes.Node absEnd = new Nodes.Anchor("AbsoluteEnd");
```

### Word Boundaries

Matches the position between a word character and a non-word character (`\b`), or the inverse (`\B`).

#### Usage (Java)

```java
import com.strling.core.Nodes;

// Word boundary (\b)
Nodes.Node wb = new Nodes.Anchor("WordBoundary");

// Not a word boundary (\B)
Nodes.Node notWb = new Nodes.Anchor("NotWordBoundary");
```

---

## Character Classes

### Built-in Classes

Standard shorthands for common character sets.

-   `\w`: Word characters (alphanumeric + underscore)
-   `\d`: Digits
-   `\s`: Whitespace
-   `.`: Any character (except newline)

#### Usage (Java)

```java
import com.strling.core.Nodes;
import java.util.List;

// Shorthand classes via ClassEscape
// \d => digits
Nodes.Node digits = new Nodes.CharClass(false, List.of(new Nodes.ClassEscape("d")));

// \w => word characters
Nodes.Node word = new Nodes.CharClass(false, List.of(new Nodes.ClassEscape("w")));

// \s => whitespace
Nodes.Node space = new Nodes.CharClass(false, List.of(new Nodes.ClassEscape("s")));

// Dot (.) is represented as a Dot node
Nodes.Node any = new Nodes.Dot();
```

### Custom Classes & Ranges

Define a set of allowed characters (`[...]`) or a range (`a-z`).

#### Usage (Java)

```java
import com.strling.core.Nodes;
import java.util.List;

// Custom class: [A-Za-z0-9]
Nodes.Node alnum = new Nodes.CharClass(false, List.of(
	new Nodes.ClassRange("A", "Z"),
	new Nodes.ClassRange("a", "z"),
	new Nodes.ClassRange("0", "9")
));

// Explicit list of characters: [.- ]
Nodes.Node separators = new Nodes.CharClass(false, List.of(
	new Nodes.ClassLiteral("."),
	new Nodes.ClassLiteral("-"),
	new Nodes.ClassLiteral(" ")
));
```

### Negated Classes

Match any character _not_ in the set (`[^...]`).

#### Usage (Java)

```java
import com.strling.core.Nodes;
import java.util.List;

// Negated class: [^0-9] (not digits)
Nodes.Node notDigits = new Nodes.CharClass(true, List.of(
	new Nodes.ClassRange("0", "9")
));
```

### Unicode Properties

Match characters based on Unicode properties (`\p{...}`), such as scripts, categories, or blocks. Unicode property escapes allow matching by Script (e.g. `\p{Latin}`), General Category (e.g. `\p{Lu}` for uppercase letters) or named blocks.

#### Usage (Java)

```java
import com.strling.core.Nodes;
import java.util.List;

// Unicode property: \p{L} (letters)
Nodes.Node unicodeLetters = new Nodes.CharClass(false, List.of(
	new Nodes.ClassEscape("p", "L")
));
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

#### Usage (Java)

```java
import com.strling.core.Nodes;

// Newline (\n)
Nodes.Node newline = new Nodes.ClassEscape("n");

// Tab (\t)
Nodes.Node tab = new Nodes.ClassEscape("t");

// Null (\0)
Nodes.Node nul = new Nodes.ClassEscape("0");
```

### Hexadecimal & Unicode

Define characters by their code point.

-   `\\xHH`: 2-digit hexadecimal (e.g. `\\x0A`)
-   `\\x{...}`: braced hexadecimal code point (variable length, e.g. `\\x{1F}`)
-   `\\uHHHH`: 4-digit Unicode (e.g. `\\u00A9`)
-   `\\u{...}`: braced Unicode code point (variable length, e.g. `\\u{1F600}`)

#### Usage (Java)

```java
import com.strling.core.Nodes;

// 2-digit hex (\x0A) represented in Java usage as a literal
Nodes.Node hexExample = new Nodes.Lit("\u000A");

// Braced unicode code point (\u{1F600}) — use a Lit with the intended codepoint (surrogate pair in Java)
Nodes.Node smile = new Nodes.Lit("\uD83D\uDE00"); // U+1F600
```

---

## Quantifiers

### Greedy Quantifiers

Match as much as possible (standard behavior).

-   `*`: 0 or more
-   `+`: 1 or more
-   `?`: 0 or 1
-   `{n,m}`: Specific range

#### Usage (Java)

```java
import com.strling.core.Nodes;
import java.util.List;

// Greedy: * (0..Inf)
Nodes.Node star = new Nodes.Quant(new Nodes.Dot(), 0, "Inf", "Greedy");

// Greedy: + (1..Inf)
Nodes.Node plus = new Nodes.Quant(new Nodes.Dot(), 1, "Inf", "Greedy");

// Greedy: ? (0..1)
Nodes.Node opt = new Nodes.Quant(new Nodes.Dot(), 0, 1, "Greedy");

// Specific range: {2,5}
Nodes.Node range = new Nodes.Quant(new Nodes.Lit("x"), 2, 5, "Greedy");
```

### Lazy Quantifiers

Match as little as possible. Appending `?` to a quantifier (e.g., `*?`).

#### Usage (Java)

```java
import com.strling.core.Nodes;

// Lazy (e.g. *?) -- represented by mode "Lazy"
Nodes.Node lazyStar = new Nodes.Quant(new Nodes.Dot(), 0, "Inf", "Lazy");

// Lazy +? (1..Inf lazy)
Nodes.Node lazyPlus = new Nodes.Quant(new Nodes.Dot(), 1, "Inf", "Lazy");
```

### Possessive Quantifiers

Match as much as possible and **do not backtrack**. Appending `+` to a quantifier (e.g., `++`, `*+`).

> **Note:** This is a key performance feature in STRling.

#### Usage (Java)

```java
import com.strling.core.Nodes;

// Possessive (e.g. *+) — represented by mode "Possessive"
Nodes.Node possStar = new Nodes.Quant(new Nodes.Dot(), 0, "Inf", "Possessive");

// Possessive + (e.g. ++)
Nodes.Node possPlus = new Nodes.Quant(new Nodes.Dot(), 1, "Inf", "Possessive");
```

---

## Groups

### Capturing Groups

Standard groups `(...)` that capture the matched text.

#### Usage (Java)

```java
import com.strling.core.Nodes;
import java.util.List;

// Capturing group: (\d{3})
Nodes.Node capturing = new Nodes.Group(true, new Nodes.Quant(
	new Nodes.CharClass(false, List.of(new Nodes.ClassEscape("d"))), 3, 3, "Greedy"
));
```

### Named Groups

Capturing groups with a specific name `(?<name>...)` for easier extraction.

#### Usage (Java)

```java
import com.strling.core.Nodes;
import java.util.List;

// Named capturing group: (?<area>\d{3})
Nodes.Node named = new Nodes.Group(true,
	new Nodes.Quant(new Nodes.CharClass(false, List.of(new Nodes.ClassEscape("d"))), 3, 3, "Greedy"),
	"area"
);
```

### Non-Capturing Groups

Groups `(?:...)` that group logic without capturing text.

#### Usage (Java)

```java
import com.strling.core.Nodes;

// Non-capturing group: (?:foo)
Nodes.Node nonCapturing = new Nodes.Group(false, new Nodes.Lit("foo"));
```

### Atomic Groups

Groups `(?>...)` that discard backtracking information once the group matches.

> **Note:** Useful for optimizing performance and preventing catastrophic backtracking.

#### Usage (Java)

```java
import com.strling.core.Nodes;

// Atomic group (?>pattern) — create a Group with atomic=true
Nodes.Node atomic = new Nodes.Group(true, new Nodes.Lit("a+"), null, true);
```

---

## Lookarounds

Zero-width assertions that match a group without consuming characters.

### Lookahead

-   Positive `(?=...)`: Asserts that what follows matches the pattern.
-   Negative `(?!...)`: Asserts that what follows does _not_ match.

#### Usage (Java)

```java
import com.strling.core.Nodes;

// Positive lookahead: (?=foo)
Nodes.Node posAhead = new Nodes.Look("Ahead", false, new Nodes.Lit("foo"));

// Negative lookahead: (?!foo)
Nodes.Node negAhead = new Nodes.Look("Ahead", true, new Nodes.Lit("foo"));
```

### Lookbehind

-   Positive `(?<=...)`: Asserts that what precedes matches the pattern.
-   Negative `(?<!...)`: Asserts that what precedes does _not_ match.

#### Usage (Java)

```java
import com.strling.core.Nodes;

// Positive lookbehind: (?<=bar)
Nodes.Node posBehind = new Nodes.Look("Behind", false, new Nodes.Lit("bar"));

// Negative lookbehind: (?<!bar)
Nodes.Node negBehind = new Nodes.Look("Behind", true, new Nodes.Lit("bar"));
```

---

## Logic

### Alternation

Matches one pattern OR another (`|`).

#### Usage (Java)

```java
import com.strling.core.Nodes;
import java.util.List;

// Alternation: a|b|c
Nodes.Node either = new Nodes.Alt(List.of(new Nodes.Lit("a"), new Nodes.Lit("b"), new Nodes.Lit("c")));
```

---

## References

### Backreferences

Reference a previously captured group by index (`\1`) or name (`\k<name>`).

#### Usage (Java)

```java
import com.strling.core.Nodes;

// Backreference by index (\1)
Nodes.Node backrefIndex = new Nodes.Backref(1, null);

// Backreference by name (\k<name>)
Nodes.Node backrefName = new Nodes.Backref(null, "name");
```

---

## Flags & Modifiers

Global flags that alter the behavior of the regex engine.

-   `i`: Case-insensitive
-   `m`: Multiline mode
-   `s`: Dotall (single line) mode
-   `x`: Extended mode (ignore whitespace)

#### Usage (Java)

```java
import com.strling.core.Nodes;

// Build flags programmatically
Nodes.Flags flags = Nodes.Flags.fromLetters("imsux");

// Or set fields directly
Nodes.Flags custom = new Nodes.Flags();
custom.ignoreCase = true;
custom.multiline = true;
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
%lang Java
%engine pcre2
```

```java
import com.strling.core.Nodes;

// Example: parse or create file-level directives
// Flags directive shorthand
Nodes.Flags flags = Nodes.Flags.fromLetters("imsux");

// If you need a language hint for emitter selection use a simple string
String lang = "java";

// Engine hint example (pcre2 / js)
String engine = "pcre2";

// These values are typically parsed from an input file header, e.g.:
// %flags imsux
// %lang java
// %engine pcre2
```
