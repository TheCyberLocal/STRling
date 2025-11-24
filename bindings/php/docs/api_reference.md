# API Reference - PHP

[← Back to README](../README.md)

This document provides a comprehensive reference for the STRling API in **PHP**.

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

#### Usage (PHP)

```php
<?php
use STRling\Core\Nodes\{Anchor};

$start = new Anchor(at: '^');
$end   = new Anchor(at: '$');

// These nodes represent the start/end anchors (line-oriented)
```

### Start/End of String

Matches the absolute beginning (`\A`) or end (`\z`) of the string, ignoring multiline mode.

#### Usage (PHP)

```php
<?php
use STRling\Core\Nodes\Anchor;

$begin = new Anchor(at: '\\A');
$finish = new Anchor(at: '\\z');

// Absolute start/end of the string (ignore multiline)
```

### Word Boundaries

Matches the position between a word character and a non-word character (`\b`), or the inverse (`\B`).

#### Usage (PHP)

```php
<?php
use STRling\Core\Nodes\Anchor;

$wordBoundary = new Anchor(at: '\\b');
$notWordBoundary = new Anchor(at: '\\B');

// Word-boundary anchors
```

---

## Character Classes

### Built-in Classes

Standard shorthands for common character sets.

-   `\w`: Word characters (alphanumeric + underscore)
-   `\d`: Digits
-   `\s`: Whitespace
-   `.`: Any character (except newline)

#### Usage (PHP)

```php
<?php
use STRling\Core\Nodes\Escape;
use STRling\Core\Nodes\Quantifier;

// \d shorthand via Escape node; combine with Quantifier for repeating digits
$threeDigits = new Quantifier(target: new Escape(kind: 'digit'), min: 3, max: 3, greedy: true, lazy: false, possessive: false);
```

### Custom Classes & Ranges

Define a set of allowed characters (`[...]`) or a range (`a-z`).

#### Usage (PHP)

```php
<?php
use STRling\Core\Nodes\{CharacterClass, Range, Escape};

// Class containing a range and digits: [a-z0-9]
$class = new CharacterClass(false, [new Range('a', 'z'), new Escape(kind: 'digit')]);
```

### Negated Classes

Match any character _not_ in the set (`[^...]`).

#### Usage (PHP)

```php
<?php
use STRling\Core\Nodes\{CharacterClass, Literal};

// Negated class: [^aeiou]
$vowelsExcept = new CharacterClass(true, [new Literal('a'), new Literal('e'), new Literal('i'), new Literal('o'), new Literal('u')]);
```

### Unicode Properties

Match characters based on Unicode properties (`\p{...}`), such as scripts, categories, or blocks. Unicode property escapes allow matching by Script (e.g. `\p{Latin}`), General Category (e.g. `\p{Lu}` for uppercase letters) or named blocks.

#### Usage (PHP)

```php
<?php
use STRling\Core\Nodes\UnicodeProperty;

// Unicode property match for script / block
$latinLetters = new UnicodeProperty(value: 'Latin');
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

#### Usage (PHP)

```php
<?php
use STRling\Core\Nodes\Literal;

// Control characters as literals
$newline = new Literal("\n");
$tab = new Literal("\t");
```

### Hexadecimal & Unicode

Define characters by their code point.

-   `\\xHH`: 2-digit hexadecimal (e.g. `\\x0A`)
-   `\\x{...}`: braced hexadecimal code point (variable length, e.g. `\\x{1F}`)
-   `\\uHHHH`: 4-digit Unicode (e.g. `\\u00A9`)
-   `\\u{...}`: braced Unicode code point (variable length, e.g. `\\u{1F600}`)

#### Usage (PHP)

```php
<?php
use STRling\Core\Nodes\Literal;

// Raw hex/unicode escapes expressed as literals where appropriate in the AST
$hex = new Literal("\x0A");        // 2-digit hex
$unicode = new Literal("\u{1F600}"); // braced unicode codepoint
```

---

## Quantifiers

### Greedy Quantifiers

Match as much as possible (standard behavior).

-   `*`: 0 or more
-   `+`: 1 or more
-   `?`: 0 or 1
-   `{n,m}`: Specific range

#### Usage (PHP)

```php
<?php
use STRling\Core\Nodes\{Escape, Quantifier};

// Greedy quantifier: digits{2,4}
$greedy = new Quantifier(target: new Escape(kind: 'digit'), min: 2, max: 4, greedy: true, lazy: false, possessive: false);
```

### Lazy Quantifiers

Match as little as possible. Appending `?` to a quantifier (e.g., `*?`).

#### Usage (PHP)

```php
<?php
use STRling\Core\Nodes\{Escape, Quantifier};

// Lazy quantifier: .*?
$lazy = new Quantifier(target: new Escape(kind: 'word'), min: 0, max: 'inf', greedy: false, lazy: true, possessive: false);
```

### Possessive Quantifiers

Match as much as possible and **do not backtrack**. Appending `+` to a quantifier (e.g., `++`, `*+`).

> **Note:** This is a key performance feature in STRling.

#### Usage (PHP)

```php
<?php
use STRling\Core\Nodes\{Escape, Quantifier};

// Possessive quantifier: digits++
$possessive = new Quantifier(target: new Escape(kind: 'digit'), min: 1, max: 'inf', greedy: false, lazy: false, possessive: true);
```

---

## Groups

### Capturing Groups

Standard groups `(...)` that capture the matched text.

#### Usage (PHP)

```php
<?php
use STRling\Core\Nodes\{Group, Literal};

// Capturing group
$g = new Group(capturing: true, body: new Literal('abc'));
```

### Named Groups

Capturing groups with a specific name `(?<name>...)` for easier extraction.

#### Usage (PHP)

```php
<?php
use STRling\Core\Nodes\{Group, Literal};

// Named capturing group
$named = new Group(capturing: true, body: new Literal('year'), name: 'year');
```

### Non-Capturing Groups

Groups `(?:...)` that group logic without capturing text.

#### Usage (PHP)

```php
<?php
use STRling\Core\Nodes\{Group, Sequence, Literal};

// Non-capturing group
$noncap = new Group(capturing: false, body: new Sequence(parts: [new Literal('a'), new Literal('|'), new Literal('b')]));
```

### Atomic Groups

Groups `(?>...)` that discard backtracking information once the group matches.

> **Note:** Useful for optimizing performance and preventing catastrophic backtracking.

#### Usage (PHP)

```php
<?php
use STRling\Core\Nodes\{Group, Literal};

// Atomic group (no backtracking inside)
$atomic = new Group(capturing: true, body: new Literal('x+'), atomic: true);
```

---

## Lookarounds

Zero-width assertions that match a group without consuming characters.

### Lookahead

-   Positive `(?=...)`: Asserts that what follows matches the pattern.
-   Negative `(?!...)`: Asserts that what follows does _not_ match.

#### Usage (PHP)

```php
<?php
use STRling\Core\Nodes\{Lookahead, NegativeLookahead, Literal};

// Positive lookahead: (?=foo)
$ahead = new Lookahead(body: new Literal('foo'));

// Negative lookahead: (?!bar)
$notAhead = new NegativeLookahead(body: new Literal('bar'));
```

### Lookbehind

-   Positive `(?<=...)`: Asserts that what precedes matches the pattern.
-   Negative `(?<!...)`: Asserts that what precedes does _not_ match.

#### Usage (PHP)

```php
<?php
use STRling\Core\Nodes\{Lookbehind, NegativeLookbehind, Literal};

// Positive lookbehind: (?<=foo)
$behind = new Lookbehind(body: new Literal('foo'));

// Negative lookbehind: (?<!bar)
$notBehind = new NegativeLookbehind(body: new Literal('bar'));
```

---

## Logic

### Alternation

Matches one pattern OR another (`|`).

#### Usage (PHP)

```php
<?php
use STRling\Core\Nodes\{Alternation, Literal};

// Alternation: (cat|dog|bird)
$alts = new Alternation(alternatives: [new Literal('cat'), new Literal('dog'), new Literal('bird')]);
```

---

## References

### Backreferences

Reference a previously captured group by index (`\1`) or name (`\k<name>`).

#### Usage (PHP)

```php
<?php
use STRling\Core\Nodes\Backreference;

// By index: \1  — or by name: \k<name>
$byIndex = new Backreference(index: 1);
$byName  = new Backreference(name: 'area');
```

---

## Flags & Modifiers

Global flags that alter the behavior of the regex engine.

-   `i`: Case-insensitive
-   `m`: Multiline mode
-   `s`: Dotall (single line) mode
-   `x`: Extended mode (ignore whitespace)

#### Usage (PHP)

```php
<?php
use STRling\Core\Nodes\Flags;

// Construct flags programmatically or from letters
$flags = new Flags(ignoreCase: true, multiline: false, dotAll: false, unicode: false, extended: false);
$fromLetters = Flags::fromLetters('imsx');
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
%lang PHP
%engine pcre2
```

```php
<?php
// Directives are file-level hints (a patterns file top block) and are parsed
// as text directives — not as node objects in the binding.
```
