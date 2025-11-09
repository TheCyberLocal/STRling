# STRling Python API Reference

**[← Back to Quick Start](../README.md)**

This document provides a comprehensive API reference for STRling in Python. For installation and quick start examples, see the [Quick Start Guide](../README.md).

---

## Table of Contents

- [Core API](#core-api)
  - [Pattern Compilation](#pattern-compilation)
  - [Pattern Matching](#pattern-matching)
- [Pattern Constructors](#pattern-constructors)
  - [Literals](#literals)
  - [Character Classes](#character-classes)
  - [Quantifiers](#quantifiers)
  - [Groups and Captures](#groups-and-captures)
  - [Lookarounds](#lookarounds)
  - [Anchors](#anchors)
  - [Backreferences](#backreferences)
- [Combinators](#combinators)
- [Advanced Features](#advanced-features)
- [Configuration](#configuration)
- [Error Handling](#error-handling)

---

## Core API

### Pattern Compilation

STRling patterns are Python objects that can be converted to regex strings using `str()`, then compiled using Python's built-in `re` module.

**Syntax:**
```python
from STRling import simply as s
import re

pattern_obj = s.digit(3)
regex_str = str(pattern_obj)
compiled = re.compile(regex_str)
```

**Parameters:**
- Pattern objects from `STRling.simply` module
- Standard Python `re` module flags (optional)

**Returns:** Python `re.Pattern` object

**Example:**
```python
from STRling import simply as s
import re

# Create a pattern for 3 digits
pattern = re.compile(str(s.digit(3)))
match = pattern.match("123")
print(match.group())  # "123"
```

### Pattern Matching

Once compiled, use standard Python `re.Pattern` methods for matching.

**Methods:**
- `match(string)` - Match at the beginning of the string
- `search(string)` - Search anywhere in the string
- `findall(string)` - Find all non-overlapping matches
- `finditer(string)` - Iterator over all matches
- `sub(replacement, string)` - Replace matches

**Example:**
```python
from STRling import simply as s
import re

pattern = re.compile(str(s.digit(min=1)), re.MULTILINE)
text = "123\n456\n789"

# Find all matches
matches = pattern.findall(text)  # ['123', '456', '789']
```

---

## Pattern Constructors

### Literals

Create patterns that match literal strings by passing strings to pattern functions or using them directly in `merge()`.

**Syntax:**
```python
from STRling import simply as s

# Literals in merge
pattern = s.merge("hello", " ", "world")
```

**Example:**
```python
from STRling import simply as s
import re

pattern = re.compile(str(s.merge("Hello", ", ", "World", "!")))
match = pattern.match("Hello, World!")
print(match.group())  # "Hello, World!"
```

### Character Classes

#### `digit(n)` - Match digits

Match a specific number of digits, or a range with `min` and `max` parameters.

**Syntax:**
```python
s.digit(n)           # Exactly n digits
s.digit(min=n)       # At least n digits
s.digit(max=n)       # At most n digits  
s.digit(min=n, max=m)  # Between n and m digits
```

**Parameters:**
- `n` (int) - Exact count of digits
- `min` (int) - Minimum count (optional)
- `max` (int) - Maximum count (optional)

**Example:**
```python
from STRling import simply as s
import re

# Exactly 3 digits
pattern1 = re.compile(str(s.digit(3)))
pattern1.match("123")  # Match

# At least 2, at most 4 digits
pattern2 = re.compile(str(s.digit(min=2, max=4)))
pattern2.match("12")    # Match
pattern2.match("1234")  # Match
pattern2.match("1")     # No match
```

#### `in_range(start, end)` - Match character range

Match any character in the specified range, with optional quantifiers.

**Syntax:**
```python
s.in_range(start, end)
s.in_range(start, end, min=n)
s.in_range(start, end, max=n)
s.in_range(start, end, min=n, max=m)
```

**Example:**
```python
from STRling import simply as s
import re

# 3-5 lowercase letters
pattern = re.compile(str(s.in_range("a", "z", min=3, max=5)))
pattern.match("abc")    # Match
pattern.match("abcde")  # Match
pattern.match("ab")     # No match
```

#### `in_chars(chars)` - Match any character in set

Match any single character from the provided set.

**Syntax:**
```python
s.in_chars(chars)
```

**Example:**
```python
from STRling import simply as s
import re

# Match space or hyphen
separator = re.compile(str(s.in_chars(" -")))
separator.match(" ")   # Match
separator.match("-")   # Match
separator.match("_")   # No match
```

#### `whitespace()` - Match whitespace

Match whitespace characters (spaces, tabs, newlines).

**Syntax:**
```python
s.whitespace()
s.whitespace(min=n)
s.whitespace(max=n)
```

**Example:**
```python
from STRling import simply as s
import re

# Match one or more whitespace
pattern = re.compile(str(s.whitespace(min=1)))
pattern.match("   ")    # Match
pattern.match("\t\n")   # Match
```

### Quantifiers

Control how many times a pattern should match.

**Available quantifiers:**
- `may(pattern)` - Optional (0 or 1)
- `many(pattern)` - One or more (1+)
- `any(pattern)` - Zero or more (0+)

**Syntax:**
```python
s.may(pattern)    # 0 or 1 occurrence
s.many(pattern)   # 1 or more occurrences
s.any(pattern)    # 0 or more occurrences
```

**Example:**
```python
from STRling import simply as s
import re

# Optional area code
pattern = s.merge(
    s.may(s.merge(s.digit(3), "-")),
    s.digit(3),
    "-",
    s.digit(4)
)
compiled = re.compile(str(pattern))

compiled.match("555-1234")      # Match
compiled.match("800-555-1234")  # Match
```

### Groups and Captures

#### Named groups

Capture parts of the match with a name for easy extraction.

**Syntax:**
```python
s.group(name, pattern)
```

**Example:**
```python
from STRling import simply as s
import re

pattern = s.merge(
    s.group("area", s.digit(3)),
    "-",
    s.group("exchange", s.digit(3)),
    "-",
    s.group("number", s.digit(4))
)

compiled = re.compile(str(pattern))
match = compiled.match("555-1234-5678")

print(match.group("area"))      # "555"
print(match.group("exchange"))  # "1234"
print(match.group("number"))    # "5678"
```

#### Non-capturing groups

Group patterns without capturing them (for applying quantifiers).

**Syntax:**
```python
# Groups in merge are non-capturing by default
s.merge(pattern1, pattern2)
```

**Example:**
```python
from STRling import simply as s
import re

# Group multiple patterns to apply quantifier
pattern = s.many(s.merge(s.digit(2), "-"))
compiled = re.compile(str(pattern))
compiled.match("12-34-56-")  # Match
```

### Lookarounds

#### Positive lookahead

Assert that a pattern follows without consuming it.

**Syntax:**
```python
s.ahead(pattern)
```

**Example:**
```python
from STRling import simply as s
import re

# Match word followed by colon (but don't include colon)
pattern = s.merge(s.in_range("a", "z", min=1), s.ahead(":"))
compiled = re.compile(str(pattern))

match = compiled.search("key: value")
print(match.group())  # "key" (colon not included)
```

#### Negative lookahead

Assert that a pattern does NOT follow.

**Syntax:**
```python
s.not_ahead(pattern)
```

**Example:**
```python
from STRling import simply as s
import re

# Match digits not followed by a letter
pattern = s.merge(s.digit(min=1), s.not_ahead(s.in_range("a", "z")))
compiled = re.compile(str(pattern))

compiled.search("123")    # Match
compiled.search("123abc") # No match
```

#### Positive lookbehind

Assert that a pattern precedes without consuming it.

**Syntax:**
```python
s.behind(pattern)
```

**Example:**
```python
from STRling import simply as s
import re

# Match digits preceded by a dollar sign
pattern = s.merge(s.behind("$"), s.digit(min=1))
compiled = re.compile(str(pattern))

match = compiled.search("$100")
print(match.group())  # "100" ($ not included)
```

#### Negative lookbehind

Assert that a pattern does NOT precede.

**Syntax:**
```python
s.not_behind(pattern)
```

**Example:**
```python
from STRling import simply as s
import re

# Match digits not preceded by a letter
pattern = s.merge(s.not_behind(s.in_range("a", "z")), s.digit(min=1))
compiled = re.compile(str(pattern))

compiled.search("123")  # Match
compiled.search("a123") # No match
```

### Anchors

Match at specific positions in the string.

**Available anchors:**
- `start()` - Start of string (or line in multiline mode)
- `end()` - End of string (or line in multiline mode)
- `word_boundary()` - Word boundary

**Syntax:**
```python
s.start()
s.end()
s.word_boundary()
```

**Example:**
```python
from STRling import simply as s
import re

# Match only if digits are at the start
pattern = s.merge(s.start(), s.digit(min=1))
compiled = re.compile(str(pattern))

compiled.match("123abc")  # Match
compiled.match("abc123")  # No match

# Match whole words only
word_pattern = s.merge(
    s.word_boundary(),
    "test",
    s.word_boundary()
)
word_compiled = re.compile(str(word_pattern))

word_compiled.search("test")     # Match
word_compiled.search("testing")  # No match
```

### Backreferences

Reference a previously captured group by name.

**Syntax:**
```python
s.backref(name)
```

**Example:**
```python
from STRling import simply as s
import re

# Match opening and closing HTML tags
pattern = s.merge(
    "<",
    s.group("tag", s.in_range("a", "z", min=1)),
    ">",
    s.many(s.in_range("a", "z", "A", "Z", " ")),  # Content
    "</",
    s.backref("tag"),  # Must match the opening tag
    ">"
)
compiled = re.compile(str(pattern))

compiled.match("<div>Hello World</div>")  # Match
compiled.match("<div>Hello World</span>") # No match
```

---

## Combinators

### `merge(*patterns)` - Concatenate patterns

Combine multiple patterns in sequence.

**Syntax:**
```python
s.merge(pattern1, pattern2, pattern3, ...)
```

**Example:**
```python
from STRling import simply as s
import re

# Build a phone number pattern
pattern = s.merge(
    s.digit(3),
    "-",
    s.digit(3),
    "-",
    s.digit(4)
)
compiled = re.compile(str(pattern))
compiled.match("555-123-4567")  # Match
```

### `either(*patterns)` - Alternation

Match any one of the provided patterns.

**Syntax:**
```python
s.either(pattern1, pattern2, pattern3, ...)
```

**Example:**
```python
from STRling import simply as s
import re

# Match yes or no
pattern = s.either("yes", "no")
compiled = re.compile(str(pattern))

compiled.match("yes")    # Match
compiled.match("no")     # Match
compiled.match("maybe")  # No match
```

---

## Advanced Features

### Custom Character Classes

Combine multiple character ranges and sets.

**Example:**
```python
from STRling import simply as s
import re

# Match alphanumeric characters
alphanum = s.either(
    s.in_range("a", "z"),
    s.in_range("A", "Z"),
    s.in_range("0", "9")
)
pattern = s.many(alphanum)
```

### Nested Patterns

STRling patterns can be nested arbitrarily deep.

**Example:**
```python
from STRling import simply as s

# Build complex patterns from smaller pieces
username = s.merge(
    s.in_range("a", "z"),
    s.many(s.either(s.in_range("a", "z"), s.digit(1), "_"))
)

domain = s.merge(
    s.in_range("a", "z", min=1),
    s.many(s.merge(s.may("."), s.in_range("a", "z", min=1)))
)

email = s.merge(username, "@", domain)
```

---

## Configuration

STRling patterns work with standard Python `re` module flags.

**Available options:**
- `re.IGNORECASE` / `re.I` - Case-insensitive matching
- `re.MULTILINE` / `re.M` - Make `^` and `$` match line boundaries
- `re.DOTALL` / `re.S` - Make `.` match newlines
- `re.VERBOSE` / `re.X` - Allow whitespace and comments in pattern
- `re.ASCII` / `re.A` - ASCII-only matching
- `re.LOCALE` / `re.L` - Locale-aware matching

**Example:**
```python
from STRling import simply as s
import re

pattern = s.in_range("a", "z", min=3)
compiled = re.compile(str(pattern), re.IGNORECASE)

compiled.match("abc")  # Match
compiled.match("ABC")  # Also match (case-insensitive)
```

---

## Error Handling

STRling provides instructional error messages when invalid patterns are constructed.

**Common errors:**

### SyntaxError

Raised when an invalid pattern is constructed.

**Example:**
```python
from STRling import simply as s

try:
    # Invalid: negative count
    pattern = s.digit(-1)
except ValueError as e:
    print(f"Error: {e}")
    # Error message explains the issue and how to fix it
```

### TypeError

Raised when incorrect types are passed to pattern constructors.

**Example:**
```python
from STRling import simply as s

try:
    # Invalid: string instead of integer
    pattern = s.digit("three")
except TypeError as e:
    print(f"Error: {e}")
```

---

## See Also

- **[Quick Start Guide](../README.md)**: Installation and basic usage
- **[Semantics Specification](../../../spec/grammar/semantics.md)**: Complete language reference
- **[Developer Hub](../../../docs/index.md)**: Architecture and contribution guides
- **[JavaScript API Reference](../../javascript/docs/api_reference.md)**: STRling for JavaScript
