# API Reference - Python

[← Back to README](../README.md)

This document provides a comprehensive reference for the STRling API in **Python**.

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

#### Usage (Python)

```python
from STRling import simply as s
import re

pattern = s.merge(s.start(), s.lit('abc'), s.end())
# Start of line.
# End of line.
assert bool(re.match(str(pattern), 'abc'))
```

### Start/End of String

Matches the absolute beginning (`\A`) or end (`\z`) of the string, ignoring multiline mode.

#### Usage (Python)

```python
from STRling import simply as s
import re

# STRling's start()/end() anchor reflects line anchors in most engines; for absolute anchors, use directives or emitter options.
pattern = s.merge(s.start(), s.lit('hello'), s.end())
# Start of string.
# End of string.
assert bool(re.match(str(pattern), 'hello'))
```

### Word Boundaries

Matches the position between a word character and a non-word character (`\b`), or the inverse (`\B`).

#### Usage (Python)

```python
from STRling import simply as s
import re

pattern = s.merge(s.start(), s.capture(s.letter()), s.bound(), s.capture(s.digit()), s.end())
# Word boundary () separates letters from digits
assert bool(re.search(str(pattern),'A1'))
```

---

## Character Classes

### Built-in Classes

Standard shorthands for common character sets.

-   `\w`: Word characters (alphanumeric + underscore)
-   `\d`: Digits
-   `\s`: Whitespace
-   `.`: Any character (except newline)

#### Usage (Python)

```python
from STRling import simply as s
import re

pattern = s.merge(s.start(), s.capture(s.digit(3)), s.end())
# Match exactly 3 digits (\d{3})
assert bool(re.search(str(pattern), '123'))
```

### Custom Classes & Ranges

Define a set of allowed characters (`[...]`) or a range (`a-z`).

#### Usage (Python)

```python
from STRling import simply as s
import re

pattern = s.merge(s.start(), s.any_of(s.lit('a'), s.lit('b'), s.lit('c')), s.end())
# Match one of: a, b, or c (custom class)
assert bool(re.search(str(pattern), 'a'))
```

### Negated Classes

Match any character _not_ in the set (`[^...]`).

#### Usage (Python)

```python
from STRling import simply as s
import re

not_vowels = s.not_in_chars('aeiou')
pattern = s.merge(s.start(), not_vowels, s.end())
# Match any character except vowels
assert bool(re.search(str(pattern), 'z'))
```

### Unicode Properties

Match characters based on Unicode properties (`\p{...}`), such as scripts, categories, or blocks. Unicode property escapes allow matching by Script (e.g. `\p{Latin}`), General Category (e.g. `\p{Lu}` for uppercase letters) or named blocks.

#### Usage (Python)

```python
from STRling import simply as s
import re

pattern = s.merge(s.start(), s.char_property('Lu'), s.end())
# Match a Unicode uppercase letter (\p{Lu})
assert bool(re.search(str(pattern), 'A'))
```

### Escape Sequences

Represent special characters like newlines, tabs, or unicode values.

### Control Characters

-   `\\n`: Newline
-   `\\r`: Carriage Return
-   `\\t`: Tab
-   `\\0`: Null Byte

#### Usage (Python)

```python
from STRling import simply as s
import re

# Using literal-style escapes
pattern_n = s.merge(s.lit("\n"), s.lit("end"))
# Using the escape helper
pattern_n2 = s.merge(s.escape("n"), s.lit("end"))

assert bool(re.search(str(pattern_n), "\nend"))
assert bool(re.search(str(pattern_n2), "\nend"))
```

### Hexadecimal & Unicode

-   `\\xHH`: 2-digit Hex
-   `\\x{...}`: Hex code point
-   `\\uHHHH`: 4-digit Unicode
-   `\\u{...}`: Unicode code point

#### Usage (Python)

```python
from STRling import simply as s
import re

pattern_hex = s.merge(s.lit("\x41"), s.lit("end"))    # \x41 -> 'A'
pattern_u = s.merge(s.lit("\u0041"), s.lit("end"))     # \u0041 -> 'A'
pattern_braced = s.merge(s.lit("\U0001F600"), s.lit("end")) # U+1F600 😀

assert bool(re.search(str(pattern_hex), "Aend"))
assert bool(re.search(str(pattern_u), "Aend"))
assert bool(re.search(str(pattern_braced), "😀end"))
```

---

## Quantifiers

### Greedy Quantifiers

Match as much as possible (standard behavior).

-   `*`: 0 or more
-   `+`: 1 or more
-   `?`: 0 or 1
-   `{n,m}`: Specific range

#### Usage (Python)

```python
from STRling import simply as s
import re

pattern = s.merge(s.start(), s.letter(1,0), s.end())
# Match one or more letters (greedy)
assert bool(re.search(str(pattern), 'abc'))
```

### Lazy Quantifiers

Match as little as possible. Appending `?` to a quantifier (e.g., `*?`).

#### Usage (Python)

```python
from STRling import simply as s
import re

# Use .rep() with min and max for lazy quantifiers where supported by emitter
pattern = s.merge(s.start(), s.letter().rep(1, 5).lazy(), s.end())
# Match between 1 and 5 letters lazily
assert bool(re.search(str(pattern), 'x'))
```

### Possessive Quantifiers

Match as much as possible and **do not backtrack**. Appending `+` to a quantifier (e.g., `++`, `*+`).

> **Note:** This is a key performance feature in STRling.

#### Usage (Python)

```python
from STRling import simply as s
import re

# Possessive quantifiers avoid backtracking when supported
pattern = s.merge(s.start(), s.digit().rep(1,0).possessive(), s.end())
# Match one or more digits possessively
assert bool(re.search(str(pattern), '12345'))
```

---

## Groups

### Capturing Groups

Standard groups `(...)` that capture the matched text.

#### Usage (Python)

```python
from STRling import simply as s
import re

pattern = s.capture(s.letter(3))
# Capture three letters for later extraction
assert re.match(str(pattern),'abc').group(1)=='abc'
```

### Named Groups

Capturing groups with a specific name `(?<name>...)` for easier extraction.

#### Usage (Python)

```python
from STRling import simply as s
import re

pattern = s.group('area', s.digit(3))
# Named group 'area' captures three digits
match = re.search(str(pattern),'123')
assert match and match.group('area')=='123'
```

### Non-Capturing Groups

Groups `(?:...)` that group logic without capturing text.

#### Usage (Python)

```python
from STRling import simply as s
import re

pattern = s.merge(s.start(), s.merge(s.digit(3)).non_capture(), s.end())
# Non-capturing grouping used for grouping logic without occupying capture slots
assert bool(re.search(str(pattern),'123'))
```

### Atomic Groups

Groups `(?>...)` that discard backtracking information once the group matches.

> **Note:** Useful for optimizing performance and preventing catastrophic backtracking.

#### Usage (Python)

```python
from STRling import simply as s
import re

pattern = s.atomic(s.merge(s.digit(1,0), s.letter(1,0)))
# Atomic grouping prevents internal backtracking once matched
assert bool(re.search(str(pattern),'1a'))
```

---

## Lookarounds

Zero-width assertions that match a group without consuming characters.

### Lookahead

-   Positive `(?=...)`: Asserts that what follows matches the pattern.
-   Negative `(?!...)`: Asserts that what follows does _not_ match.

#### Usage (Python)

```python
from STRling import simply as s
import re

pattern = s.merge(s.letter(), s.ahead(s.digit()))
# Assert that a digit follows (lookahead)
assert bool(re.search(str(pattern),'a1'))
```

### Lookbehind

-   Positive `(?<=...)`: Asserts that what precedes matches the pattern.
-   Negative `(?<!...)`: Asserts that what precedes does _not_ match.

#### Usage (Python)

```python
from STRling import simply as s
import re

pattern = s.merge(s.behind(s.letter()), s.digit())
# Assert that a letter precedes (lookbehind)
assert bool(re.search(str(pattern),'a1'))
```

---

## Logic

### Alternation

Matches one pattern OR another (`|`).

#### Usage (Python)

```python
from STRling import simply as s
import re

pattern = s.any_of('cat','dog')
# Match either 'cat' or 'dog'
assert bool(re.search(str(pattern),'I have a dog'))
```

---

## References

### Backreferences

Reference a previously captured group by index (`\1`) or name (`\k<name>`).

#### Usage (Python)

```python
from STRling import simply as s
import re

p = s.capture(s.letter(3))
pattern = s.merge(p, s.lit('-'), s.backref(1))
# Backreference to the first numbered capture group
assert bool(re.search(str(pattern),'abc-abc'))
```

---

## Flags & Modifiers

Global flags that alter the behavior of the regex engine.

-   `i`: Case-insensitive
-   `m`: Multiline mode
-   `s`: Dotall (single line) mode
-   `x`: Extended mode (ignore whitespace)

#### Usage (Python)

```python
from STRling import simply as s
import re

pattern = s.merge(s.flag('i'), s.lit('abc'))
# Case-insensitive match (flag i)
assert bool(re.search(str(pattern),'ABC'))
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
%lang Python
%engine pcre2
```

```text
%flags ims
%lang Python
%engine pcre2

# Directives set file-level defaults (flags/lang/engine)
```
