# STRling JavaScript API Reference

**[← Back to Quick Start](../README.md)**

This document provides a comprehensive API reference for STRling in JavaScript. For installation and quick start examples, see the [Quick Start Guide](../README.md).

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

STRling patterns are JavaScript objects that can be converted to regex strings using `.toString()`, then compiled using JavaScript's built-in `RegExp` constructor.

**Syntax:**
```javascript
import { simply as s } from "@thecyberlocal/strling";

const patternObj = s.digit(3);
const regexStr = patternObj.toString();
const compiled = new RegExp(regexStr);
```

**Parameters:**
- Pattern objects from `simply` module
- Standard JavaScript RegExp flags (optional)

**Returns:** JavaScript `RegExp` object

**Example:**
```javascript
import { simply as s } from "@thecyberlocal/strling";

// Create a pattern for 3 digits
const pattern = new RegExp(s.digit(3).toString());
const match = pattern.exec("123");
console.log(match[0]);  // "123"
```

### Pattern Matching

Once compiled, use standard JavaScript `RegExp` methods for matching.

**Methods:**
- `test(string)` - Test if pattern matches
- `exec(string)` - Execute match and return details
- `string.match(pattern)` - Find matches in string
- `string.matchAll(pattern)` - Iterator over all matches
- `string.replace(pattern, replacement)` - Replace matches

**Example:**
```javascript
import { simply as s } from "@thecyberlocal/strling";

const pattern = new RegExp(s.digit({ min: 1 }).toString(), "g");
const text = "123\n456\n789";

// Find all matches
const matches = text.match(pattern);  // ['123', '456', '789']
```

---

## Pattern Constructors

### Literals

Create patterns that match literal strings by passing strings to pattern functions or using them directly in `merge()`.

**Syntax:**
```javascript
import { simply as s } from "@thecyberlocal/strling";

// Literals in merge
const pattern = s.merge("hello", " ", "world");
```

**Example:**
```javascript
import { simply as s } from "@thecyberlocal/strling";

const pattern = new RegExp(s.merge("Hello", ", ", "World", "!").toString());
const match = pattern.exec("Hello, World!");
console.log(match[0]);  // "Hello, World!"
```

### Character Classes

#### `digit(n)` - Match digits

Match a specific number of digits, or a range with `min` and `max` options.

**Syntax:**
```javascript
s.digit(n)                    // Exactly n digits
s.digit({ min: n })           // At least n digits
s.digit({ max: n })           // At most n digits
s.digit({ min: n, max: m })   // Between n and m digits
```

**Parameters:**
- `n` (number) - Exact count of digits
- `options.min` (number) - Minimum count (optional)
- `options.max` (number) - Maximum count (optional)

**Example:**
```javascript
import { simply as s } from "@thecyberlocal/strling";

// Exactly 3 digits
const pattern1 = new RegExp(s.digit(3).toString());
pattern1.test("123");  // true

// At least 2, at most 4 digits
const pattern2 = new RegExp(s.digit({ min: 2, max: 4 }).toString());
pattern2.test("12");    // true
pattern2.test("1234");  // true
pattern2.test("1");     // false
```

#### `inRange(start, end)` - Match character range

Match any character in the specified range, with optional quantifiers.

**Syntax:**
```javascript
s.inRange(start, end)
s.inRange(start, end, { min: n })
s.inRange(start, end, { max: n })
s.inRange(start, end, { min: n, max: m })
```

**Example:**
```javascript
import { simply as s } from "@thecyberlocal/strling";

// 3-5 lowercase letters
const pattern = new RegExp(s.inRange("a", "z", { min: 3, max: 5 }).toString());
pattern.test("abc");    // true
pattern.test("abcde");  // true
pattern.test("ab");     // false
```

#### `inChars(chars)` - Match any character in set

Match any single character from the provided set.

**Syntax:**
```javascript
s.inChars(chars)
```

**Example:**
```javascript
import { simply as s } from "@thecyberlocal/strling";

// Match space or hyphen
const separator = new RegExp(s.inChars(" -").toString());
separator.test(" ");   // true
separator.test("-");   // true
separator.test("_");   // false
```

#### `whitespace()` - Match whitespace

Match whitespace characters (spaces, tabs, newlines).

**Syntax:**
```javascript
s.whitespace()
s.whitespace({ min: n })
s.whitespace({ max: n })
```

**Example:**
```javascript
import { simply as s } from "@thecyberlocal/strling";

// Match one or more whitespace
const pattern = new RegExp(s.whitespace({ min: 1 }).toString());
pattern.test("   ");    // true
pattern.test("\t\n");   // true
```

### Quantifiers

Control how many times a pattern should match.

**Available quantifiers:**
- `may(pattern)` - Optional (0 or 1)
- `many(pattern)` - One or more (1+)
- `any(pattern)` - Zero or more (0+)

**Syntax:**
```javascript
s.may(pattern)    // 0 or 1 occurrence
s.many(pattern)   // 1 or more occurrences
s.any(pattern)    // 0 or more occurrences
```

**Example:**
```javascript
import { simply as s } from "@thecyberlocal/strling";

// Optional area code
const pattern = s.merge(
    s.may(s.merge(s.digit(3), "-")),
    s.digit(3),
    "-",
    s.digit(4)
);
const compiled = new RegExp(pattern.toString());

compiled.test("555-1234");      // true
compiled.test("800-555-1234");  // true
```

### Groups and Captures

#### Named groups

Capture parts of the match with a name for easy extraction.

**Syntax:**
```javascript
s.group(name, pattern)
```

**Example:**
```javascript
import { simply as s } from "@thecyberlocal/strling";

const pattern = s.merge(
    s.group("area", s.digit(3)),
    "-",
    s.group("exchange", s.digit(3)),
    "-",
    s.group("number", s.digit(4))
);

const compiled = new RegExp(pattern.toString());
const match = compiled.exec("555-1234-5678");

console.log(match.groups.area);      // "555"
console.log(match.groups.exchange);  // "1234"
console.log(match.groups.number);    // "5678"
```

#### Non-capturing groups

Group patterns without capturing them (for applying quantifiers).

**Syntax:**
```javascript
// Groups in merge are non-capturing by default
s.merge(pattern1, pattern2)
```

**Example:**
```javascript
import { simply as s } from "@thecyberlocal/strling";

// Group multiple patterns to apply quantifier
const pattern = s.many(s.merge(s.digit(2), "-"));
const compiled = new RegExp(pattern.toString());
compiled.test("12-34-56-");  // true
```

### Lookarounds

#### Positive lookahead

Assert that a pattern follows without consuming it.

**Syntax:**
```javascript
s.ahead(pattern)
```

**Example:**
```javascript
import { simply as s } from "@thecyberlocal/strling";

// Match word followed by colon (but don't include colon)
const pattern = s.merge(s.inRange("a", "z", { min: 1 }), s.ahead(":"));
const compiled = new RegExp(pattern.toString());

const match = compiled.exec("key: value");
console.log(match[0]);  // "key" (colon not included)
```

#### Negative lookahead

Assert that a pattern does NOT follow.

**Syntax:**
```javascript
s.notAhead(pattern)
```

**Example:**
```javascript
import { simply as s } from "@thecyberlocal/strling";

// Match digits not followed by a letter
const pattern = s.merge(s.digit({ min: 1 }), s.notAhead(s.inRange("a", "z")));
const compiled = new RegExp(pattern.toString());

compiled.test("123");    // true
compiled.test("123abc"); // false
```

#### Positive lookbehind

Assert that a pattern precedes without consuming it.

**Syntax:**
```javascript
s.behind(pattern)
```

**Example:**
```javascript
import { simply as s } from "@thecyberlocal/strling";

// Match digits preceded by a dollar sign
const pattern = s.merge(s.behind("$"), s.digit({ min: 1 }));
const compiled = new RegExp(pattern.toString());

const match = compiled.exec("$100");
console.log(match[0]);  // "100" ($ not included)
```

#### Negative lookbehind

Assert that a pattern does NOT precede.

**Syntax:**
```javascript
s.notBehind(pattern)
```

**Example:**
```javascript
import { simply as s } from "@thecyberlocal/strling";

// Match digits not preceded by a letter
const pattern = s.merge(s.notBehind(s.inRange("a", "z")), s.digit({ min: 1 }));
const compiled = new RegExp(pattern.toString());

compiled.test("123");  // true
compiled.test("a123"); // false
```

### Anchors

Match at specific positions in the string.

**Available anchors:**
- `start()` - Start of string (or line in multiline mode)
- `end()` - End of string (or line in multiline mode)
- `wordBoundary()` - Word boundary

**Syntax:**
```javascript
s.start()
s.end()
s.wordBoundary()
```

**Example:**
```javascript
import { simply as s } from "@thecyberlocal/strling";

// Match only if digits are at the start
const pattern = s.merge(s.start(), s.digit({ min: 1 }));
const compiled = new RegExp(pattern.toString());

compiled.test("123abc");  // true
compiled.test("abc123");  // false

// Match whole words only
const wordPattern = s.merge(
    s.wordBoundary(),
    "test",
    s.wordBoundary()
);
const wordCompiled = new RegExp(wordPattern.toString());

wordCompiled.test("test");     // true
wordCompiled.test("testing");  // false
```

### Backreferences

Reference a previously captured group by name.

**Syntax:**
```javascript
s.backref(name)
```

**Example:**
```javascript
import { simply as s } from "@thecyberlocal/strling";

// Match opening and closing HTML tags
const pattern = s.merge(
    "<",
    s.group("tag", s.inRange("a", "z", { min: 1 })),
    ">",
    s.many(s.inRange("a", "z", "A", "Z", " ")),  // Content
    "</",
    s.backref("tag"),  // Must match the opening tag
    ">"
);
const compiled = new RegExp(pattern.toString());

compiled.test("<div>Hello World</div>");  // true
compiled.test("<div>Hello World</span>"); // false
```

---

## Combinators

### `merge(...patterns)` - Concatenate patterns

Combine multiple patterns in sequence.

**Syntax:**
```javascript
s.merge(pattern1, pattern2, pattern3, ...)
```

**Example:**
```javascript
import { simply as s } from "@thecyberlocal/strling";

// Build a phone number pattern
const pattern = s.merge(
    s.digit(3),
    "-",
    s.digit(3),
    "-",
    s.digit(4)
);
const compiled = new RegExp(pattern.toString());
compiled.test("555-123-4567");  // true
```

### `either(...patterns)` - Alternation

Match any one of the provided patterns.

**Syntax:**
```javascript
s.either(pattern1, pattern2, pattern3, ...)
```

**Example:**
```javascript
import { simply as s } from "@thecyberlocal/strling";

// Match yes or no
const pattern = s.either("yes", "no");
const compiled = new RegExp(pattern.toString());

compiled.test("yes");    // true
compiled.test("no");     // true
compiled.test("maybe");  // false
```

---

## Advanced Features

### Custom Character Classes

Combine multiple character ranges and sets.

**Example:**
```javascript
import { simply as s } from "@thecyberlocal/strling";

// Match alphanumeric characters
const alphanum = s.either(
    s.inRange("a", "z"),
    s.inRange("A", "Z"),
    s.inRange("0", "9")
);
const pattern = s.many(alphanum);
```

### Nested Patterns

STRling patterns can be nested arbitrarily deep.

**Example:**
```javascript
import { simply as s } from "@thecyberlocal/strling";

// Build complex patterns from smaller pieces
const username = s.merge(
    s.inRange("a", "z"),
    s.many(s.either(s.inRange("a", "z"), s.digit(1), "_"))
);

const domain = s.merge(
    s.inRange("a", "z", { min: 1 }),
    s.many(s.merge(s.may("."), s.inRange("a", "z", { min: 1 })))
);

const email = s.merge(username, "@", domain);
```

---

## Configuration

STRling patterns work with standard JavaScript RegExp flags.

**Available options:**
- `g` - Global search (find all matches)
- `i` - Case-insensitive matching
- `m` - Multiline mode (make `^` and `$` match line boundaries)
- `s` - Dotall mode (make `.` match newlines)
- `u` - Unicode mode
- `y` - Sticky mode

**Example:**
```javascript
import { simply as s } from "@thecyberlocal/strling";

const pattern = s.inRange("a", "z", { min: 3 });
const compiled = new RegExp(pattern.toString(), "i");

compiled.test("abc");  // true
compiled.test("ABC");  // true (case-insensitive)
```

---

## Error Handling

STRling provides instructional error messages when invalid patterns are constructed.

**Common errors:**

### SyntaxError

Thrown when an invalid pattern is constructed.

**Example:**
```javascript
import { simply as s } from "@thecyberlocal/strling";

try {
    // Invalid: negative count
    const pattern = s.digit(-1);
} catch (error) {
    console.error(`Error: ${error.message}`);
    // Error message explains the issue and how to fix it
}
```

### TypeError

Thrown when incorrect types are passed to pattern constructors.

**Example:**
```javascript
import { simply as s } from "@thecyberlocal/strling";

try {
    // Invalid: string instead of number
    const pattern = s.digit("three");
} catch (error) {
    console.error(`Error: ${error.message}`);
}
```

---

## See Also

- **[Quick Start Guide](../README.md)**: Installation and basic usage
- **[Semantics Specification](../../../spec/grammar/semantics.md)**: Complete language reference
- **[Developer Hub](../../../docs/index.md)**: Architecture and contribution guides
- **[Python API Reference](../../python/docs/api_reference.md)**: STRling for Python
