# [TEMPLATE] Binding API Reference

**[← Back to Quick Start](../README.md)**

---

**INSTRUCTIONS FOR USING THIS TEMPLATE:**

This is a master template for creating language-specific API reference documentation. When creating a new binding API reference:

1. Copy this file to `bindings/{language}/docs/api_reference.md`
2. Replace all placeholder text in `[BRACKETS]` with language-specific content
3. Maintain the exact heading structure shown here
4. Include working code examples in the appropriate language
5. Link back to the binding's README.md at the top
6. Ensure all examples are tested and functional

Delete these instructions when creating the actual API reference.

---

# STRling [LANGUAGE] API Reference

This document provides a comprehensive API reference for STRling in [LANGUAGE]. For installation and quick start examples, see the [Quick Start Guide](../README.md).

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

[Explain how to compile STRling patterns to regex in this language]

**Syntax:**
```[language]
[Code example showing pattern compilation]
```

**Parameters:**
- `pattern` - [Description]
- `flags` - [Description]

**Returns:** [Description]

**Raises/Throws:** [Description]

**Example:**
```[language]
[Working example code]
```

### Pattern Matching

[Explain how to use compiled patterns for matching]

**Methods:**
- [Method 1]: [Description]
- [Method 2]: [Description]

**Example:**
```[language]
[Working example code]
```

---

## Pattern Constructors

### Literals

[Explain how to create literal string patterns]

**Syntax:**
```[language]
[Code example]
```

**Example:**
```[language]
[Working example showing literal matching]
```

### Character Classes

#### `digit(n)` - Match digits

[Explain the digit() function and its parameters]

**Syntax:**
```[language]
[Code example]
```

**Parameters:**
- `n` / `min` - [Description]
- `max` - [Description]

**Example:**
```[language]
[Working example]
```

#### `in_range(start, end)` - Match character range

[Explain character range matching]

**Syntax:**
```[language]
[Code example]
```

**Example:**
```[language]
[Working example]
```

#### `in_chars(chars)` - Match any character in set

[Explain character set matching]

**Syntax:**
```[language]
[Code example]
```

**Example:**
```[language]
[Working example]
```

#### `whitespace()` - Match whitespace

[Explain whitespace matching]

**Syntax:**
```[language]
[Code example]
```

**Example:**
```[language]
[Working example]
```

### Quantifiers

[Explain how quantifiers work in this language]

**Available quantifiers:**
- `may(pattern)` - Optional (0 or 1)
- `many(pattern)` - One or more (1+)
- `any(pattern)` - Zero or more (0+)

**Syntax:**
```[language]
[Code example showing quantifiers]
```

**Example:**
```[language]
[Working example]
```

### Groups and Captures

#### Named groups

[Explain named capture groups]

**Syntax:**
```[language]
[Code example]
```

**Example:**
```[language]
[Working example showing group extraction]
```

#### Non-capturing groups

[Explain non-capturing groups]

**Syntax:**
```[language]
[Code example]
```

**Example:**
```[language]
[Working example]
```

### Lookarounds

#### Positive lookahead

[Explain positive lookahead]

**Syntax:**
```[language]
[Code example]
```

**Example:**
```[language]
[Working example]
```

#### Negative lookahead

[Explain negative lookahead]

**Syntax:**
```[language]
[Code example]
```

**Example:**
```[language]
[Working example]
```

#### Positive lookbehind

[Explain positive lookbehind]

**Syntax:**
```[language]
[Code example]
```

**Example:**
```[language]
[Working example]
```

#### Negative lookbehind

[Explain negative lookbehind]

**Syntax:**
```[language]
[Code example]
```

**Example:**
```[language]
[Working example]
```

### Anchors

[Explain anchors for matching positions]

**Available anchors:**
- `start()` - Start of string
- `end()` - End of string
- `word_boundary()` - Word boundary

**Syntax:**
```[language]
[Code example]
```

**Example:**
```[language]
[Working example]
```

### Backreferences

[Explain how to reference previously captured groups]

**Syntax:**
```[language]
[Code example]
```

**Example:**
```[language]
[Working example showing backreference]
```

---

## Combinators

### `merge(*patterns)` - Concatenate patterns

[Explain pattern concatenation]

**Syntax:**
```[language]
[Code example]
```

**Example:**
```[language]
[Working example]
```

### `either(*patterns)` - Alternation

[Explain pattern alternation]

**Syntax:**
```[language]
[Code example]
```

**Example:**
```[language]
[Working example]
```

---

## Advanced Features

[Document any language-specific advanced features or optimizations]

---

## Configuration

[Explain how to configure STRling behavior in this language]

**Available options:**
- [Option 1]: [Description]
- [Option 2]: [Description]

**Example:**
```[language]
[Configuration example]
```

---

## Error Handling

[Explain the error handling approach in this language]

**Common errors:**

### SyntaxError

[When this occurs and how to handle it]

**Example:**
```[language]
[Error handling example]
```

### [Other errors specific to this language]

[Explanations and examples]

---

## See Also

- **[Quick Start Guide](../README.md)**: Installation and basic usage
- **[Semantics Specification](../../../spec/grammar/semantics.md)**: Complete language reference
- **[Developer Hub](../../../docs/index.md)**: Architecture and contribution guides
