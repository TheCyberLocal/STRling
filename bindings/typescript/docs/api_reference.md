# API Reference - TypeScript

[← Back to README](../README.md)

This document provides a comprehensive reference for the STRling API in **TypeScript**.

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

#### Usage (TypeScript)

```typescript
import { simply } from "@thecyberlocal/strling";

const s = simply;
const pattern = s.merge(s.start(), s.lit("abc"), s.end());
// Start of line.
// End of line.
console.assert(new RegExp(String(pattern)).test("abc"));
```

### Start/End of String

Matches the absolute beginning (`\A`) or end (`\z`) of the string, ignoring multiline mode.

#### Usage (TypeScript)

```typescript
import { simply } from "@thecyberlocal/strling";

// For absolute anchors use emitter directives.
const s = simply;
const pattern = s.merge(s.start(), s.lit("hello"), s.end());
// Start of string.
// End of string.
console.assert(new RegExp(String(pattern)).test("hello"));
```

### Word Boundaries

Matches the position between a word character and a non-word character (`\b`), or the inverse (`\B`).

#### Usage (TypeScript)

```typescript
import { simply } from "@thecyberlocal/strling";

const s = simply;
const pattern = s.merge(
    s.start(),
    s.capture(s.letter()),
    s.bound(),
    s.capture(s.digit()),
    s.end()
);
// Word boundary (\b) separates letters from digits
console.assert(new RegExp(String(pattern)).test("A1"));
```

---

## Character Classes

### Built-in Classes

Standard shorthands for common character sets.

-   `\w`: Word characters (alphanumeric + underscore)
-   `\d`: Digits
-   `\s`: Whitespace
-   `.`: Any character (except newline)

#### Usage (TypeScript)

```typescript
import { simply } from "@thecyberlocal/strling";

const s = simply;
const p = s.merge(s.start(), s.capture(s.digit(3)), s.end());
// Match exactly 3 digits (\d{3})
console.assert(new RegExp(String(p)).test("123"));
```

### Custom Classes & Ranges

Define a set of allowed characters (`[...]`) or a range (`a-z`).

#### Usage (TypeScript)

```typescript
import { simply } from "@thecyberlocal/strling";

const s = simply;
const pattern = s.merge(s.start(), s.anyOf("a", "b", "c"), s.end());
// Match one of: a, b, or c (custom class)
console.assert(new RegExp(String(pattern)).test("a"));
```

### Negated Classes

Match any character _not_ in the set (`[^...]`).

#### Usage (TypeScript)

```typescript
import { simply } from "@thecyberlocal/strling";

const s = simply;
const notVowels = s.notInChars("aeiou");
const pattern = s.merge(s.start(), notVowels, s.end());
// Match any character except vowels
console.assert(new RegExp(String(pattern)).test("z"));
```

### Unicode Properties

Match characters based on Unicode properties (`\p{...}`), such as scripts, categories, or blocks. Unicode property escapes allow matching by Script (e.g. `\p{Latin}`), General Category (e.g. `\p{Lu}` for uppercase letters) or named blocks.

#### Usage (TypeScript)

```typescript
import { simply } from "@thecyberlocal/strling";

const s = simply;
const pattern = s.merge(s.start(), s.charProperty("Lu"), s.end());
// Match a Unicode uppercase letter (\p{Lu})
console.assert(new RegExp(String(pattern)).test("A"));
```

### Escape Sequences

Represent special characters like newlines, tabs, or unicode values.

### Control Characters

-   `\\n`: Newline
-   `\\r`: Carriage Return
-   `\\t`: Tab
-   `\\0`: Null Byte

#### Usage (TypeScript)

```typescript
import { simply } from "@thecyberlocal/strling";

const s = simply;

// Control character examples
const patternN = s.merge(s.lit("\n"), s.lit("end"));
const patternN2 = s.merge(s.escape("n"), s.lit("end"));

console.assert(new RegExp(String(patternN)).test("\nend"));
console.assert(new RegExp(String(patternN2)).test("\nend"));
```

### Hexadecimal & Unicode

-   `\\xHH`: 2-digit Hex
-   `\\x{...}`: Hex code point
-   `\\uHHHH`: 4-digit Unicode
-   `\\u{...}`: Unicode code point

#### Usage (TypeScript)

```typescript
import { simply } from "@thecyberlocal/strling";

const s = simply;

const patternHex = s.merge(s.lit("\x41"), s.lit("end")); // \x41 -> 'A'
const patternU = s.merge(s.lit("\u0041"), s.lit("end")); // \u0041 -> 'A'
const patternBraced = s.merge(s.lit("\u{1F600}"), s.lit("end")); // U+1F600 😀

console.assert(new RegExp(String(patternHex)).test("Aend"));
console.assert(new RegExp(String(patternU)).test("Aend"));
console.assert(new RegExp(String(patternBraced)).test("\u{1F600}end"));
```

---

## Quantifiers

### Greedy Quantifiers

Match as much as possible (standard behavior).

-   `*`: 0 or more
-   `+`: 1 or more
-   `?`: 0 or 1
-   `{n,m}`: Specific range

#### Usage (TypeScript)

```typescript
import { simply } from "@thecyberlocal/strling";

const s = simply;
const pattern = s.merge(s.start(), s.letter(1, 0), s.end());
// Match one or more letters (greedy)
console.assert(new RegExp(String(pattern)).test("abc"));
```

### Lazy Quantifiers

Match as little as possible. Appending `?` to a quantifier (e.g., `*?`).

#### Usage (TypeScript)

```typescript
import { simply } from "@thecyberlocal/strling";

const s = simply;
const pattern = s.merge(s.start(), s.letter().rep(1, 5).lazy(), s.end());
// Match between 1 and 5 letters lazily
console.assert(new RegExp(String(pattern)).test("x"));
```

### Possessive Quantifiers

Match as much as possible and **do not backtrack**. Appending `+` to a quantifier (e.g., `++`, `*+`).

> **Note:** This is a key performance feature in STRling.

#### Usage (TypeScript)

```typescript
import { simply } from "@thecyberlocal/strling";

const s = simply;
const pattern = s.merge(s.start(), s.digit().rep(1, 0).possessive(), s.end());
// Match one or more digits possessively
console.assert(new RegExp(String(pattern)).test("12345"));
```

---

## Groups

### Capturing Groups

Standard groups `(...)` that capture the matched text.

#### Usage (TypeScript)

```typescript
import { simply } from "@thecyberlocal/strling";

const s = simply;
const pattern = s.capture(s.letter(3));
// Capture three letters for later extraction
const m = new RegExp(String(pattern)).exec("abc");
console.assert(m && m[1] === "abc");
```

### Named Groups

Capturing groups with a specific name `(?<name>...)` for easier extraction.

#### Usage (TypeScript)

```typescript
import { simply } from "@thecyberlocal/strling";

const s = simply;
const pattern = s.group("area", s.digit(3));
// Named group 'area' captures three digits
const m = new RegExp(String(pattern)).exec("123");
console.assert(m && (m as any).groups && (m as any).groups.area === "123");
```

### Non-Capturing Groups

Groups `(?:...)` that group logic without capturing text.

#### Usage (TypeScript)

```typescript
import { simply } from "@thecyberlocal/strling";

const s = simply;
const pattern = s.merge(s.start(), s.merge(s.digit(3)).nonCapture(), s.end());
// Non-capturing grouping used for grouping logic without occupying capture slots
console.assert(new RegExp(String(pattern)).test("123"));
```

### Atomic Groups

Groups `(?>...)` that discard backtracking information once the group matches.

> **Note:** Useful for optimizing performance and preventing catastrophic backtracking.

#### Usage (TypeScript)

```typescript
import { simply } from "@thecyberlocal/strling";

const s = simply;
const pattern = s.atomic(s.merge(s.digit(1, 0), s.letter(1, 0)));
// Atomic grouping prevents internal backtracking once matched
console.assert(new RegExp(String(pattern)).test("1a"));
```

---

## Lookarounds

Zero-width assertions that match a group without consuming characters.

### Lookahead

-   Positive `(?=...)`: Asserts that what follows matches the pattern.
-   Negative `(?!...)`: Asserts that what follows does _not_ match.

#### Usage (TypeScript)

```typescript
import { simply } from "@thecyberlocal/strling";

const s = simply;
const pattern = s.merge(s.letter(), s.ahead(s.digit()));
// Assert that a digit follows (lookahead)
console.assert(new RegExp(String(pattern)).test("a1"));
```

### Lookbehind

-   Positive `(?<=...)`: Asserts that what precedes matches the pattern.
-   Negative `(?<!...)`: Asserts that what precedes does _not_ match.

#### Usage (TypeScript)

```typescript
import { simply } from "@thecyberlocal/strling";

const s = simply;
const pattern = s.merge(s.behind(s.letter()), s.digit());
// Assert that a letter precedes (lookbehind)
console.assert(new RegExp(String(pattern)).test("a1"));
```

---

## Logic

### Alternation

Matches one pattern OR another (`|`).

#### Usage (TypeScript)

```typescript
import { simply } from "@thecyberlocal/strling";

const s = simply;
const pattern = s.anyOf("cat", "dog");
// Match either 'cat' or 'dog'
console.assert(new RegExp(String(pattern)).test("I have a dog"));
```

---

## References

### Backreferences

Reference a previously captured group by index (`\1`) or name (`\k<name>`).

#### Usage (TypeScript)

```typescript
import { simply } from "@thecyberlocal/strling";

const s = simply;
const p = s.capture(s.letter(3));
const pattern = s.merge(p, s.lit("-"), s.backref(1));
// Backreference to the first numbered capture group
console.assert(new RegExp(String(pattern)).test("abc-abc"));
```

---

## Flags & Modifiers

Global flags that alter the behavior of the regex engine.

-   `i`: Case-insensitive
-   `m`: Multiline mode
-   `s`: Dotall (single line) mode
-   `x`: Extended mode (ignore whitespace)

#### Usage (TypeScript)

```typescript
import { simply } from "@thecyberlocal/strling";

const s = simply;
const pattern = s.merge(s.flag("i"), s.lit("abc"));
// Case-insensitive match (flag i)
console.assert(new RegExp(String(pattern)).test("ABC"));
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
%lang TypeScript
%engine pcre2
```

```text
%flags ims
%lang TypeScript
%engine js

# Directives set file-level defaults (flags/lang/engine)
```
