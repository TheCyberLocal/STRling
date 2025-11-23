# API Reference - Rust

[← Back to README](../README.md)

This document provides a comprehensive reference for the STRling API in **Rust**.

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

#### Usage (Rust)

```rust
use strling::simply;
use strling::core::compiler::Compiler;
use strling::emitters::pcre2::PCRE2Emitter;

// Start of line and end of line: `^start$`
let flags = Flags::default();
let ast = simply::merge(vec![simply::start(), simply::literal("start"), simply::end()]);

let mut compiler = Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```

### Start/End of String

Matches the absolute beginning (`\A`) or end (`\z`) of the string, ignoring multiline mode.

#### Usage (Rust)

```rust
use strling::simply;
// `^(hello)$` using the simply builder helpers
let flags = Flags::default();
let ast = simply::merge(vec![
	simply::start(),
	simply::capture(simply::literal("hello")),
	simply::end(),
]);

let mut compiler = Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```

### Word Boundaries

Matches the position between a word character and a non-word character (`\\b`), or the inverse (`\B`).

#### Usage (Rust)

```rust
use strling::simply;
// Word boundary (`\bword\b`) using simply helpers
let flags = Flags::default();
let ast = simply::merge(vec![
	simply::word_boundary(),
	simply::literal("word"),
	simply::word_boundary(),
]);

let mut compiler = strling::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```

---

## Character Classes

### Built-in Classes

Standard shorthands for common character sets.

-   `\w`: Word characters (alphanumeric + underscore)
-   `\\d`: Digits
-   `\s`: Whitespace
-   `.`: Any character (except newline)

#### Usage (Rust)

```rust
use strling::simply;
use strling::core::compiler::Compiler;
use strling::emitters::pcre2::PCRE2Emitter;

// \d{3}
let flags = Flags::default();
let ast = simply::digit(3);

let mut compiler = strling::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```

### Custom Classes & Ranges

Define a set of allowed characters (`[...]`) or a range (`a-z`).

#### Usage (Rust)

```rust
use strling::simply;
use strling::core::compiler::Compiler;
use strling::emitters::pcre2::PCRE2Emitter;

// Character class [abc]
let flags = Flags::default();
let ast = simply::any_of(&["a","b","c"]);

let mut compiler = strling::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```

### Negated Classes

Match any character _not_ in the set (`[^...]`).

#### Usage (Rust)

```rust
use strling::simply;
// Negated character class [^aeiou]
let flags = Flags::default();
let ast = simply::not_any_of(&["a","e","i","o","u"]);

let mut compiler = strling::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```

### Unicode Properties

Match characters based on Unicode properties (`\\p{...}`), such as scripts, categories, or blocks. Unicode property escapes allow matching by Script (e.g. `\\p{Latin}`), General Category (e.g. `\\p{Lu}` for uppercase letters) or named blocks.

#### Usage (Rust)

```rust
use strling::simply;
// Unicode property escape \p{Lu}
let flags = Flags::default();
let ast = simply::prop("Lu");

let mut compiler = strling::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```

### Escape Sequences

Escape sequences let you represent special characters, control characters, numeric code escapes, and shorthand character classes. STRling supports a range of commonly used escapes (identity, control, hex, unicode, shorthand, and null) and documents engine behavior for invalid or forbidden sequences.

#### Common escapes

-   Identity and literal escapes: `\`, `\.`
-   Control characters: `\n`, `\r`, `\t`, `\f`, `\v`
-   Null byte: `\0`
-   Hex escapes: `\xHH` and `\x{HH}`
-   Unicode escapes: `\uHHHH`, `\UHHHHHHHH`, and `\u{H...}`
-   Shorthand classes inside and outside classes: `\\d`, `\w`, `\s`, `\\b`, `\B`

#### Usage (Rust)

```rust
use strling::simply;
// Construct `\n` followed by `end` using helpers
let flags = Flags::default();
let ast = simply::merge(vec![simply::escape("n"), simply::literal("end")]);

let mut compiler = strling::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```

---

## Quantifiers

### Greedy Quantifiers

Match as much as possible (standard behavior).

-   `*`: 0 or more
-   `+`: 1 or more
-   `?`: 0 or 1
-   `{n,m}`: Specific range

#### Usage (Rust)

```rust
use strling::simply;
// [A-Za-z]+ -> a quantifier over a character class with two ranges
let flags = Flags::default();
let class_node = simply::ranges(&[("A","Z"),("a","z")]);
let ast = simply::repeat_greedy(class_node, 1, None);

let mut compiler = strling::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```

### Lazy Quantifiers

Match as little as possible. Appending `?` to a quantifier (e.g., `*?`).

#### Usage (Rust)

```rust
use strling::simply;
// [A-Za-z]{1,5}? -> lazy quantifier over letter ranges
let flags = Flags::default();
let class_node = simply::ranges(&[("A","Z"),("a","z")]);
let mut_ast = simply::repeat_lazy(class_node, 1, Some(5));

let mut compiler = strling::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&mut_ast);
let emitter = strling::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```

### Possessive Quantifiers

Match as much as possible and **do not backtrack**. Appending `+` to a quantifier (e.g., `++`, `*+`).

> **Note:** This is a key performance feature in STRling.

#### Usage (Rust)

```rust
use strling::simply;
// \d++ -> possessive quantifier of \d shorthand
let flags = Flags::default();
let ast = simply::repeat_possessive(class_escape("d"), 1, None);

let mut compiler = strling::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```

---

## Groups

### Capturing Groups

Standard groups `(...)` that capture the matched text.

#### Usage (Rust)

```rust
use strling::simply;
use strling::core::compiler::Compiler;
use strling::emitters::pcre2::PCRE2Emitter;

// (\d{3}) -> capturing group
let flags = Flags::default();
let ast = simply::capture(simply::digit(3));

let mut compiler = strling::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```

### Named Groups

Capturing groups with a specific name `(?<name>...)` for easier extraction.

#### Usage (Rust)

```rust
use strling::simply;
use strling::Flags;
// (?<area>\d{3}) -> named capturing group
let flags = Flags::default();
let inner = simply::digit(3);

let ast = simply::named_capture("area", inner);

let mut compiler = strling::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```

### Non-Capturing Groups

Groups `(?:...)` that group logic without capturing text.

#### Usage (Rust)

```rust
use strling::simply;
// (?:\d{3}) -> non-capturing group containing a quantifier over \d
let flags = Flags::default();
let inner = simply::digit(3);
let ast = simply::non_capturing(inner);

let mut compiler = strling::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```

### Atomic Groups

Groups `(?>...)` that discard backtracking information once the group matches.

> **Note:** Useful for optimizing performance and preventing catastrophic backtracking.

#### Usage (Rust)

```rust
use strling::simply;
// (?>\d+) -> atomic group around a quantifier
let flags = Flags::default();
let inner = simply::repeat_greedy(class_escape("d"), 1, None);
let ast = simply::atomic(inner);

let mut compiler = strling::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```

---

## Lookarounds

Zero-width assertions that match a group without consuming characters.

### Lookahead

-   Positive `(?=...)`: Asserts that what follows matches the pattern.
-   Negative `(?!...)`: Asserts that what follows does _not_ match.

#### Usage (Rust)

```rust
use strling::simply;
// a(?=\d) -> sequence of literal 'a' followed by a lookahead asserting a digit
let flags = Flags::default();
let ast = simply::merge(vec![ simply::literal("a"), simply::look_ahead(class_escape("d")) ]);

let mut compiler = strling::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```

### Lookbehind

-   Positive `(?<=...)`: Asserts that what precedes matches the pattern.
-   Negative `(?<!...)`: Asserts that what precedes does _not_ match.

#### Usage (Rust)

```rust
use strling::simply;
// (?<=a)1 -> lookbehind asserting 'a' followed by literal '1'
let flags = Flags::default();
let ast = simply::merge(vec![ simply::look_behind(simply::literal("a")), simply::literal("1") ]);

let mut compiler = strling::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```

---

## Logic

### Alternation

Matches one pattern OR another (`|`).

#### Usage (Rust)

```rust
use strling::simply;
// cat|dog -> alternation with two literal branches
let flags = Flags::default();
let ast = simply::either(simply::literal("cat"), simply::literal("dog"));

let mut compiler = strling::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```

---

## References

### Backreferences

Reference a previously captured group by index (`\\1`) or name (`\k<name>`).

#### Usage (Rust)

```rust
use strling::simply;
// (abc)\1 -> capturing group followed by a backreference to it
let flags = Flags::default();
let ast = simply::merge(vec![ simply::capture(simply::literal("abc")), simply::backref_index(1) ]);

let mut compiler = strling::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```

---

## Flags & Modifiers

Global flags that alter the behavior of the regex engine.

-   `i`: Case-insensitive
-   `m`: Multiline mode
-   `s`: Dotall (single line) mode
-   `x`: Extended mode (ignore whitespace)

#### Usage (Rust)

```rust
use strling::simply;
// (?i)abc -> flags set to case-insensitive, AST contains the literal sequence
let flags = simply::flag("i");
let ast = simply::literal("abc");

let mut compiler = strling::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
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
%lang Rust
%engine pcre2
```

```text
%flags ims
%lang Rust
%engine pcre2

# Directives set file-level defaults (flags/lang/engine)
```
