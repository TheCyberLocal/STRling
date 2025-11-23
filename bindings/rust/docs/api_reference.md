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
use strling_core::simply;
use strling_core::core::compiler::Compiler;
use strling_core::emitters::pcre2::PCRE2Emitter;

// Start of line and end of line: `^start$`
let flags = Flags::default();
let ast = simply::merge(vec![simply::start(), simply::literal("start"), simply::end()]);

let mut compiler = Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```
```

### Start/End of String

Matches the absolute beginning (`\A`) or end (`\z`) of the string, ignoring multiline mode.

#### Usage (Rust)

```rust
use strling_core::core::nodes::{Node, Sequence, Anchor, Group, Literal, Flags};
// Explicit AST for `^(hello)$` — anchored sequence with a capturing group around a literal
let flags = Flags::default();
let ast = Node::Sequence(Sequence { parts: vec![
	Node::Anchor(Anchor { at: "Start".to_string() }),
	Node::Group(Group { capturing: true, body: Box::new(Node::Literal(Literal { value: "hello".to_string() })), name: None, atomic: None }),
	Node::Anchor(Anchor { at: "End".to_string() }),
] });

let mut compiler = Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```

### Word Boundaries

Matches the position between a word character and a non-word character (`\\b`), or the inverse (`\B`).

#### Usage (Rust)

```rust
use strling_core::core::nodes::{Node, Sequence, Literal, Anchor, Flags};
// Word boundary (`\bword\b`) represented using boundary anchors + literal
let flags = Flags::default();
let ast = Node::Sequence(Sequence { parts: vec![
	Node::Anchor(Anchor { at: "WordBoundary".to_string() }),
	Node::Literal(Literal { value: "word".to_string() }),
	Node::Anchor(Anchor { at: "WordBoundary".to_string() }),
] });

let mut compiler = strling_core::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling_core::emitters::pcre2::PCRE2Emitter::new(flags);
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
use strling_core::simply;
use strling_core::core::compiler::Compiler;
use strling_core::emitters::pcre2::PCRE2Emitter;

// \d{3}
let flags = Flags::default();
let ast = simply::digit(3);

let mut compiler = strling_core::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling_core::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```
```

### Custom Classes & Ranges

Define a set of allowed characters (`[...]`) or a range (`a-z`).

#### Usage (Rust)

```rust
use strling_core::simply;
use strling_core::core::compiler::Compiler;
use strling_core::emitters::pcre2::PCRE2Emitter;

// Character class [abc]
let flags = Flags::default();
let ast = simply::any_of(&["a","b","c"]);

let mut compiler = strling_core::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling_core::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```
```

### Negated Classes

Match any character _not_ in the set (`[^...]`).

#### Usage (Rust)

```rust
use strling_core::core::nodes::{Node, Sequence, CharacterClass, ClassItem, ClassLiteral, Flags};
// Negated character class [^aeiou]
let flags = Flags::default();
let ast = Node::CharacterClass(CharacterClass { negated: true, items: vec![
	ClassItem::Char(ClassLiteral { ch: "a".to_string() }),
	ClassItem::Char(ClassLiteral { ch: "e".to_string() }),
	ClassItem::Char(ClassLiteral { ch: "i".to_string() }),
	ClassItem::Char(ClassLiteral { ch: "o".to_string() }),
	ClassItem::Char(ClassLiteral { ch: "u".to_string() }),
] });

let mut compiler = strling_core::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling_core::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```

### Unicode Properties

Match characters based on Unicode properties (`\\p{...}`), such as scripts, categories, or blocks. Unicode property escapes allow matching by Script (e.g. `\\p{Latin}`), General Category (e.g. `\\p{Lu}` for uppercase letters) or named blocks.

#### Usage (Rust)

```rust
use strling_core::core::nodes::{Node, Sequence, CharacterClass, ClassItem, ClassEscape, Flags};
// Unicode property escape \p{Lu}
let flags = Flags::default();
let ast = Node::CharacterClass(CharacterClass { negated: false, items: vec![
	ClassItem::Esc(ClassEscape { escape_type: "p".to_string(), property: Some("Lu".to_string()) }),
] });

let mut compiler = strling_core::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling_core::emitters::pcre2::PCRE2Emitter::new(flags);
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
use strling_core::core::nodes::{Node, Sequence, Literal, Flags};
// Construct an explicit AST representing a newline followed by 'end'
let flags = Flags::default();
let ast = Node::Sequence(Sequence { parts: vec![
	Node::Literal(Literal { value: "\n".to_string() }),
	Node::Literal(Literal { value: "end".to_string() }),
] });

let mut compiler = strling_core::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling_core::emitters::pcre2::PCRE2Emitter::new(flags);
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
use strling_core::core::nodes::{Node, Quantifier, QuantifierTarget, CharacterClass, ClassItem, ClassRange, MaxBound, Flags};
// [A-Za-z]+ -> a quantifier over a character class with two ranges
let flags = Flags::default();
let class_node = Node::CharacterClass(CharacterClass { negated: false, items: vec![
	ClassItem::Range(ClassRange { from_ch: "A".to_string(), to_ch: "Z".to_string() }),
	ClassItem::Range(ClassRange { from_ch: "a".to_string(), to_ch: "z".to_string() }),
] });

let ast = Node::Quantifier(Quantifier { target: QuantifierTarget { child: Box::new(class_node) }, min: 1, max: MaxBound::Infinite("Inf".to_string()), mode: "Greedy".to_string(), greedy: true, lazy: false, possessive: false });

let mut compiler = strling_core::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling_core::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```

### Lazy Quantifiers

Match as little as possible. Appending `?` to a quantifier (e.g., `*?`).

#### Usage (Rust)

```rust
use strling_core::core::nodes::{Node, Quantifier, QuantifierTarget, CharacterClass, ClassItem, ClassRange, MaxBound, Flags};
// [A-Za-z]{1,5}? -> lazy quantifier over letter ranges
let flags = Flags::default();
let class_node = Node::CharacterClass(CharacterClass { negated: false, items: vec![
	ClassItem::Range(ClassRange { from_ch: "A".to_string(), to_ch: "Z".to_string() }),
	ClassItem::Range(ClassRange { from_ch: "a".to_string(), to_ch: "z".to_string() }),
] });

let mut_ast = Node::Quantifier(Quantifier { target: QuantifierTarget { child: Box::new(class_node) }, min: 1, max: MaxBound::Finite(5), mode: "Lazy".to_string(), greedy: false, lazy: true, possessive: false });

let mut compiler = strling_core::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&mut_ast);
let emitter = strling_core::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```

### Possessive Quantifiers

Match as much as possible and **do not backtrack**. Appending `+` to a quantifier (e.g., `++`, `*+`).

> **Note:** This is a key performance feature in STRling.

#### Usage (Rust)

```rust
use strling_core::core::nodes::{Node, Quantifier, QuantifierTarget, CharacterClass, ClassItem, ClassEscape, MaxBound, Flags};
// \d++ -> possessive quantifier of \d shorthand
let flags = Flags::default();
let class_node = Node::CharacterClass(CharacterClass { negated: false, items: vec![
	ClassItem::Esc(ClassEscape { escape_type: "d".to_string(), property: None })
] });

let ast = Node::Quantifier(Quantifier { target: QuantifierTarget { child: Box::new(class_node) }, min: 1, max: MaxBound::Infinite("Inf".to_string()), mode: "Possessive".to_string(), greedy: false, lazy: false, possessive: true });

let mut compiler = strling_core::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling_core::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```

---

## Groups

### Capturing Groups

Standard groups `(...)` that capture the matched text.

#### Usage (Rust)

```rust
use strling_core::simply;
use strling_core::core::compiler::Compiler;
use strling_core::emitters::pcre2::PCRE2Emitter;

// (\d{3}) -> capturing group
let flags = Flags::default();
let ast = simply::capture(simply::digit(3));

let mut compiler = strling_core::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling_core::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```
```

### Named Groups

Capturing groups with a specific name `(?<name>...)` for easier extraction.

#### Usage (Rust)

```rust
use strling_core::core::nodes::{Node, Group, Quantifier, QuantifierTarget, CharacterClass, ClassItem, ClassEscape, MaxBound, Flags};
// (?<area>\d{3}) -> named capturing group
let flags = Flags::default();
let inner = Node::Quantifier(Quantifier { target: QuantifierTarget { child: Box::new(Node::CharacterClass(CharacterClass { negated: false, items: vec![
	ClassItem::Esc(ClassEscape { escape_type: "d".to_string(), property: None })
] })) }, min: 3, max: MaxBound::Finite(3), mode: "Greedy".to_string(), greedy: true, lazy: false, possessive: false });

let ast = Node::Group(Group { capturing: true, body: Box::new(inner), name: Some("area".to_string()), atomic: None });

let mut compiler = strling_core::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling_core::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```

### Non-Capturing Groups

Groups `(?:...)` that group logic without capturing text.

#### Usage (Rust)

```rust
use strling_core::core::nodes::{Node, Group, Quantifier, QuantifierTarget, CharacterClass, ClassItem, ClassEscape, MaxBound, Flags};
// (?:\d{3}) -> non-capturing group containing a quantifier over \d
let flags = Flags::default();
let inner = Node::Quantifier(Quantifier { target: QuantifierTarget { child: Box::new(Node::CharacterClass(CharacterClass { negated: false, items: vec![
	ClassItem::Esc(ClassEscape { escape_type: "d".to_string(), property: None })
] })) }, min: 3, max: MaxBound::Finite(3), mode: "Greedy".to_string(), greedy: true, lazy: false, possessive: false });

let ast = Node::Group(Group { capturing: false, body: Box::new(inner), name: None, atomic: None });

let mut compiler = strling_core::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling_core::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```

### Atomic Groups

Groups `(?>...)` that discard backtracking information once the group matches.

> **Note:** Useful for optimizing performance and preventing catastrophic backtracking.

#### Usage (Rust)

```rust
use strling_core::core::nodes::{Node, Group, Quantifier, QuantifierTarget, CharacterClass, ClassItem, ClassEscape, MaxBound, Flags};
// (?>\d+) -> atomic group around a quantifier
let flags = Flags::default();
let inner = Node::Quantifier(Quantifier { target: QuantifierTarget { child: Box::new(Node::CharacterClass(CharacterClass { negated: false, items: vec![
	ClassItem::Esc(ClassEscape { escape_type: "d".to_string(), property: None })
] })) }, min: 1, max: MaxBound::Infinite("Inf".to_string()), mode: "Greedy".to_string(), greedy: true, lazy: false, possessive: false });

let ast = Node::Group(Group { capturing: true, body: Box::new(inner), name: None, atomic: Some(true) });

let mut compiler = strling_core::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling_core::emitters::pcre2::PCRE2Emitter::new(flags);
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
use strling_core::core::nodes::{Node, Sequence, Literal, Lookahead, LookaroundBody, CharacterClass, ClassItem, ClassEscape, Flags};
// a(?=\d) -> sequence of literal 'a' followed by a lookahead asserting a digit
let flags = Flags::default();
let lookahead_body = LookaroundBody { body: Box::new(Node::CharacterClass(CharacterClass { negated: false, items: vec![
	ClassItem::Esc(ClassEscape { escape_type: "d".to_string(), property: None })
] })) };

let ast = Node::Sequence(Sequence { parts: vec![
	Node::Literal(Literal { value: "a".to_string() }),
	Node::Lookahead(lookahead_body),
] });

let mut compiler = strling_core::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling_core::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```

### Lookbehind

-   Positive `(?<=...)`: Asserts that what precedes matches the pattern.
-   Negative `(?<!...)`: Asserts that what precedes does _not_ match.

#### Usage (Rust)

```rust
use strling_core::core::nodes::{Node, Sequence, Literal, LookaroundBody, Flags};
// (?<=a)1 -> lookbehind asserting 'a' followed by literal '1'
let flags = Flags::default();
let ast = Node::Sequence(Sequence { parts: vec![
	Node::Lookbehind(LookaroundBody { body: Box::new(Node::Literal(Literal { value: "a".to_string() })) }),
	Node::Literal(Literal { value: "1".to_string() }),
] });

let mut compiler = strling_core::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling_core::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```

---

## Logic

### Alternation

Matches one pattern OR another (`|`).

#### Usage (Rust)

```rust
use strling_core::core::nodes::{Node, Alternation, Sequence, Literal, Flags};
// cat|dog -> alternation with two literal branches
let flags = Flags::default();
let left = Node::Sequence(Sequence { parts: vec![ Node::Literal(Literal { value: "cat".to_string() }) ] });
let right = Node::Sequence(Sequence { parts: vec![ Node::Literal(Literal { value: "dog".to_string() }) ] });

let ast = Node::Alternation(Alternation { branches: vec![ left, right ] });

let mut compiler = strling_core::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling_core::emitters::pcre2::PCRE2Emitter::new(flags);
println!("{}", emitter.emit(&result.ir));
```

---

## References

### Backreferences

Reference a previously captured group by index (`\\1`) or name (`\k<name>`).

#### Usage (Rust)

```rust
use strling_core::core::nodes::{Node, Sequence, Group, Literal, Backreference, Flags};
// (abc)\1 -> capturing group followed by a backreference to it
let flags = Flags::default();
let group = Node::Group(Group { capturing: true, body: Box::new(Node::Sequence(strling_core::core::nodes::Sequence { parts: vec![ Node::Literal(Literal { value: "abc".to_string() }) ] })), name: None, atomic: None });

let ast = Node::Sequence(Sequence { parts: vec![ group, Node::Backreference(Backreference { by_index: Some(1), by_name: None }) ] });

let mut compiler = strling_core::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling_core::emitters::pcre2::PCRE2Emitter::new(flags);
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
use strling_core::core::nodes::{Node, Sequence, Literal, Flags};
// (?i)abc -> flags set to case-insensitive, AST contains the literal sequence
let flags = Flags::from_letters("i");
let ast = Node::Sequence(Sequence { parts: vec![ Node::Literal(Literal { value: "abc".to_string() }) ] });

let mut compiler = strling_core::core::compiler::Compiler::new();
let result = compiler.compile_with_metadata(&ast);
let emitter = strling_core::emitters::pcre2::PCRE2Emitter::new(flags);
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
