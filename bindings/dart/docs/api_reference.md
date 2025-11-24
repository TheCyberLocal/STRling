# API Reference - Dart

[← Back to README](../README.md)

This document provides a comprehensive reference for the STRling API in **Dart**.

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

#### Usage (Dart)

```dart
final Anchor start = Anchor('Start');
final Anchor end = Anchor('End');
```

### Start/End of String

Matches the absolute beginning (`\A`) or end (`\z`) of the string, ignoring multiline mode.

#### Usage (Dart)

```dart
final Anchor absoluteStart = Anchor('AbsoluteStart');
final Anchor absoluteEnd = Anchor('AbsoluteEnd');
final Anchor endBeforeFinalNewline = Anchor('EndBeforeFinalNewline');
```

### Word Boundaries

Matches the position between a word character and a non-word character (`\b`), or the inverse (`\B`).

#### Usage (Dart)

```dart
final Anchor wordBoundary = Anchor('WordBoundary');
final Anchor notWordBoundary = Anchor('NotWordBoundary');
```

---

## Character Classes

### Built-in Classes

Standard shorthands for common character sets.

-   `\w`: Word characters (alphanumeric + underscore)
-   `\d`: Digits
-   `\s`: Whitespace
-   `.`: Any character (except newline)

#### Usage (Dart)

```dart
final CharacterClass builtin = CharacterClass(
  negated: false,
  members: [
    Escape('word'),
    Escape('digit'),
    Escape('space'),
  ],
);
```

### Custom Classes & Ranges

Define a set of allowed characters (`[...]`) or a range (`a-z`).

#### Usage (Dart)

```dart
final CharacterClass custom = CharacterClass(
  negated: false,
  members: [
    Range(from: 'a', to: 'z'),
    Range(from: 'A', to: 'Z'),
    Range(from: '0', to: '9'),
    Literal('-'),
  ],
);
```

### Negated Classes

Match any character _not_ in the set (`[^...]`).

#### Usage (Dart)

```dart
final CharacterClass notVowels = CharacterClass(
  negated: true,
  members: [
    Literal('a'),
    Literal('e'),
    Literal('i'),
    Literal('o'),
    Literal('u'),
  ],
);
```

### Unicode Properties

Match characters based on Unicode properties (`\p{...}`), such as scripts, categories, or blocks. Unicode property escapes allow matching by Script (e.g. `\p{Latin}`), General Category (e.g. `\p{Lu}` for uppercase letters) or named blocks.

#### Usage (Dart)

```dart
final CharacterClass greek = CharacterClass(
  negated: false,
  members: [
    UnicodeProperty(value: 'Greek', negated: false),
  ],
);
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

#### Usage (Dart)

```dart
final Literal newline = Literal('\n');
final Literal tab = Literal('\t');
final Literal nullByte = Literal('\0');
```

### Hexadecimal & Unicode

Define characters by their code point.

-   `\\xHH`: 2-digit hexadecimal (e.g. `\\x0A`)
-   `\\x{...}`: braced hexadecimal code point (variable length, e.g. `\\x{1F}`)
-   `\\uHHHH`: 4-digit Unicode (e.g. `\\u00A9`)
-   `\\u{...}`: braced Unicode code point (variable length, e.g. `\\u{1F600}`)

#### Usage (Dart)

```dart
final Literal copyright = Literal('\u00A9');
final Literal smile = Literal('\u{1F600}');
```

---

## Quantifiers

### Greedy Quantifiers

Match as much as possible (standard behavior).

-   `*`: 0 or more
-   `+`: 1 or more
-   `?`: 0 or 1
-   `{n,m}`: Specific range

#### Usage (Dart)

```dart
final Quantifier oneOrMoreDigits = Quantifier(
  target: Escape('digit'),
  min: 1,
  max: null,
  greedy: true,
  lazy: false,
  possessive: false,
);
```

### Lazy Quantifiers

Match as little as possible. Appending `?` to a quantifier (e.g., `*?`).

#### Usage (Dart)

```dart
final Quantifier lazyMatch = Quantifier(
  target: CharacterClass(
    negated: false,
    members: [Literal('.')],
  ),
  min: 0,
  max: null,
  greedy: false,
  lazy: true,
  possessive: false,
);
```

### Possessive Quantifiers

Match as much as possible and **do not backtrack**. Appending `+` to a quantifier (e.g., `++`, `*+`).

> **Note:** This is a key performance feature in STRling.

#### Usage (Dart)

```dart
final Quantifier possessiveDigits = Quantifier(
  target: Escape('digit'),
  min: 1,
  max: null,
  greedy: false,
  lazy: false,
  possessive: true,
);
```

---

## Groups

### Capturing Groups

Standard groups `(...)` that capture the matched text.

#### Usage (Dart)

```dart
final Group captureArea = Group(
  capturing: true,
  body: Sequence([
    Quantifier(
      target: Escape('digit'),
      min: 3,
      max: 3,
      greedy: true,
      lazy: false,
      possessive: false,
    ),
  ]),
);
```

### Named Groups

Capturing groups with a specific name `(?<name>...)` for easier extraction.

#### Usage (Dart)

```dart
final Group namedArea = Group(
  capturing: true,
  name: 'area',
  body: Sequence([Escape('digit')]),
);
```

### Non-Capturing Groups

Groups `(?:...)` that group logic without capturing text.

#### Usage (Dart)

```dart
final Group nonCapture = Group(
  capturing: false,
  body: Sequence([Literal('x')]),
);
```

### Atomic Groups

Groups `(?>...)` that discard backtracking information once the group matches.

> **Note:** Useful for optimizing performance and preventing catastrophic backtracking.

#### Usage (Dart)

```dart
final Group atomic = Group(
  capturing: false,
  atomic: true,
  body: Sequence([
    Quantifier(
      target: Literal('a'),
      min: 1,
      max: null,
      greedy: true,
      lazy: false,
      possessive: false,
    ),
  ]),
);
```

---

## Lookarounds

Zero-width assertions that match a group without consuming characters.

### Lookahead

-   Positive `(?=...)`: Asserts that what follows matches the pattern.
-   Negative `(?!...)`: Asserts that what follows does _not_ match.

#### Usage (Dart)

```dart
final Lookaround lookahead = Lookaround(
  dir: 'Ahead',
  neg: false,
  body: Sequence([Literal('foo')]),
);

final Lookaround negative = Lookaround(
  dir: 'Ahead',
  neg: true,
  body: Sequence([Literal('bar')]),
);
```

### Lookbehind

-   Positive `(?<=...)`: Asserts that what precedes matches the pattern.
-   Negative `(?<!...)`: Asserts that what precedes does _not_ match.

#### Usage (Dart)

```dart
final Lookaround lookbehind = Lookaround(
  dir: 'Behind',
  neg: false,
  body: Sequence([Literal('prefix')]),
);

final Lookaround negativeBehind = Lookaround(
  dir: 'Behind',
  neg: true,
  body: Sequence([Literal('nope')]),
);
```

---

## Logic

### Alternation

Matches one pattern OR another (`|`).

#### Usage (Dart)

```dart
final Alternation choose = Alternation([
  Sequence([Literal('cat')]),
  Sequence([Literal('dog')]),
]);
```

---

## References

### Backreferences

Reference a previously captured group by index (`\1`) or name (`\k<name>`).

#### Usage (Dart)

```dart
final Backreference byIndex = Backreference(index: 1);
final Backreference byName = Backreference(name: 'area');
```

---

## Flags & Modifiers

Global flags that alter the behavior of the regex engine.

-   `i`: Case-insensitive
-   `m`: Multiline mode
-   `s`: Dotall (single line) mode
-   `x`: Extended mode (ignore whitespace)

#### Usage (Dart)

```dart
// Flags are not modelled identically across all bindings; some bindings
// expose a dedicated Flags object. This is a conceptual example:
final dynamic flags = /* Flags(ignoreCase: true, multiline: false) */ null;
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
%lang dart
%engine pcre2
```

```text
%flags imsux
%lang dart
%engine pcre2
```
