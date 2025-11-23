# API Reference - C

[← Back to README](../README.md)

This document provides a comprehensive reference for the STRling API in **C**.

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

#### Usage (C)

```c
/* Start/End of line anchors */
STRlingASTNode* start = strling_ast_anchor_create("Start");
STRlingASTNode* end = strling_ast_anchor_create("End");
// attach into a sequence as needed, then free:
strling_ast_node_free(start);
strling_ast_node_free(end);
```

### Start/End of String

Matches the absolute beginning (`\A`) or end (`\z`) of the string, ignoring multiline mode.

#### Usage (C)

```c
/* Absolute string anchors */
STRlingASTNode* abs_start = strling_ast_anchor_create("AbsoluteStart");
STRlingASTNode* abs_end = strling_ast_anchor_create("AbsoluteEnd");
strling_ast_node_free(abs_start);
strling_ast_node_free(abs_end);
```

### Word Boundaries

Matches the position between a word character and a non-word character (`\b`), or the inverse (`\B`).

#### Usage (C)

```c
/* Word boundaries */
STRlingASTNode* wb = strling_ast_anchor_create("WordBoundary");
STRlingASTNode* nwb = strling_ast_anchor_create("NonWordBoundary");
strling_ast_node_free(wb);
strling_ast_node_free(nwb);
```

---

## Character Classes

### Built-in Classes

Standard shorthands for common character sets.

-   `\w`: Word characters (alphanumeric + underscore)
-   `\d`: Digits
-   `\s`: Whitespace
-   `.`: Any character (except newline)

#### Usage (C)

```c
/* Built-in shorthand (as class escapes) */
STRlingClassItem* dig = strling_class_escape_create("digit", NULL); // corresponds to \d inside a class
STRlingASTNode* cc = strling_ast_charclass_create(false, (STRlingClassItem*[]){dig}, 1);
strling_ast_node_free(cc);
```

### Custom Classes & Ranges

Define a set of allowed characters (`[...]`) or a range (`a-z`).

#### Usage (C)

```c
/* Custom char class and range */
STRlingClassItem* rng = strling_class_range_create("a", "z");
STRlingClassItem* lit = strling_class_literal_create("_");
STRlingASTNode* cc = strling_ast_charclass_create(false, (STRlingClassItem*[]){rng, lit}, 2);
strling_ast_node_free(cc);
```

### Negated Classes

Match any character _not_ in the set (`[^...]`).

#### Usage (C)

```c
/* Negated class */
STRlingClassItem* a = strling_class_literal_create("x");
STRlingASTNode* cc = strling_ast_charclass_create(true, (STRlingClassItem*[]){a}, 1); // [^x]
strling_ast_node_free(cc);
```

### Unicode Properties

Match characters based on Unicode properties (`\p{...}`), such as scripts, categories, or blocks. Unicode property escapes allow matching by Script (e.g. `\p{Latin}`), General Category (e.g. `\p{Lu}` for uppercase letters) or named blocks.

#### Usage (C)

```c
/* Unicode property inside a class */
STRlingClassItem* prop = strling_class_escape_create("unicode_property", "Latin");
STRlingASTNode* cc = strling_ast_charclass_create(false, (STRlingClassItem*[]){prop}, 1);
strling_ast_node_free(cc);
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

#### Usage (C)

```c
/* Control escapes inside character classes (as class-escapes) */
STRlingClassItem* nl = strling_class_escape_create("control", "n"); // newline in class
STRlingASTNode* cc = strling_ast_charclass_create(false, (STRlingClassItem*[]){nl}, 1);
strling_ast_node_free(cc);
```

### Hexadecimal & Unicode

Define characters by their code point.

-   `\\xHH`: 2-digit hexadecimal (e.g. `\\x0A`)
-   `\\x{...}`: braced hexadecimal code point (variable length, e.g. `\\x{1F}`)
-   `\\uHHHH`: 4-digit Unicode (e.g. `\\u00A9`)
-   `\\u{...}`: braced Unicode code point (variable length, e.g. `\\u{1F600}`)

#### Usage (C)

```c
/* Hex & Unicode escapes (in class items) */
STRlingClassItem* hx = strling_class_escape_create("hex", "0A"); //

STRlingClassItem* uni = strling_class_escape_create("unicode", "00A9"); // ©
STRlingASTNode* cc = strling_ast_charclass_create(false, (STRlingClassItem*[]){hx, uni}, 2);
strling_ast_node_free(cc);
```

---

## Quantifiers

### Greedy Quantifiers

Match as much as possible (standard behavior).

-   `*`: 0 or more
-   `+`: 1 or more
-   `?`: 0 or 1
-   `{n,m}`: Specific range

#### Usage (C)

```c
/* Greedy quantifier examples */
STRlingASTNode* lit = strling_ast_lit_create("a");
STRlingASTNode* q = strling_ast_quant_create(lit, 1, -1, "Greedy"); // a+
strling_ast_node_free(q);
```

### Lazy Quantifiers

Match as little as possible. Appending `?` to a quantifier (e.g., `*?`).

#### Usage (C)

```c
/* Lazy quantifier */
STRlingASTNode* lit = strling_ast_lit_create("a");
STRlingASTNode* q = strling_ast_quant_create(lit, 0, -1, "Lazy"); // a*?
strling_ast_node_free(q);
```

### Possessive Quantifiers

Match as much as possible and **do not backtrack**. Appending `+` to a quantifier (e.g., `++`, `*+`).

> **Note:** This is a key performance feature in STRling.

#### Usage (C)

```c
/* Possessive quantifier */
STRlingASTNode* lit = strling_ast_lit_create("a");
STRlingASTNode* q = strling_ast_quant_create(lit, 0, -1, "Possessive"); // a*+
strling_ast_node_free(q);
```

---

## Groups

### Capturing Groups

Standard groups `(...)` that capture the matched text.

#### Usage (C)

```c
/* Capturing group */
STRlingASTNode* body = strling_ast_lit_create("abc");
STRlingASTNode* g = strling_ast_group_create(true, body, NULL, false);
strling_ast_node_free(g);
```

### Named Groups

Capturing groups with a specific name `(?<name>...)` for easier extraction.

#### Usage (C)

```c
/* Named capturing group */
STRlingASTNode* body = strling_ast_lit_create("id");
STRlingASTNode* g = strling_ast_group_create(true, body, "myname", false);
strling_ast_node_free(g);
```

### Non-Capturing Groups

Groups `(?:...)` that group logic without capturing text.

#### Usage (C)

```c
/* Non-capturing group */
STRlingASTNode* body = strling_ast_lit_create("x+");
STRlingASTNode* g = strling_ast_group_create(false, body, NULL, false);
strling_ast_node_free(g);
```

### Atomic Groups

Groups `(?>...)` that discard backtracking information once the group matches.

> **Note:** Useful for optimizing performance and preventing catastrophic backtracking.

#### Usage (C)

```c
/* Atomic group */
STRlingASTNode* body = strling_ast_lit_create("a+");
STRlingASTNode* g = strling_ast_group_create(true, body, NULL, true);
strling_ast_node_free(g);
```

---

## Lookarounds

Zero-width assertions that match a group without consuming characters.

### Lookahead

-   Positive `(?=...)`: Asserts that what follows matches the pattern.
-   Negative `(?!...)`: Asserts that what follows does _not_ match.

#### Usage (C)

```c
/* Positive lookahead */
STRlingASTNode* body = strling_ast_lit_create("foo");
STRlingASTNode* look = strling_ast_look_create("Ahead", false, body); // (?=foo)
strling_ast_node_free(look);
```

### Lookbehind

-   Positive `(?<=...)`: Asserts that what precedes matches the pattern.
-   Negative `(?<!...)`: Asserts that what precedes does _not_ match.

#### Usage (C)

```c
/* Positive lookbehind */
STRlingASTNode* body = strling_ast_lit_create("bar");
STRlingASTNode* look = strling_ast_look_create("Behind", false, body); // (?<=bar)
strling_ast_node_free(look);
```

---

## Logic

### Alternation

Matches one pattern OR another (`|`).

#### Usage (C)

```c
/* Alternation */
STRlingASTNode* left = strling_ast_lit_create("a");
STRlingASTNode* right = strling_ast_lit_create("b");
STRlingASTNode* alt = strling_ast_alt_create((STRlingASTNode*[]){left,right}, 2);
strling_ast_node_free(alt);
```

---

## References

### Backreferences

Reference a previously captured group by index (`\1`) or name (`\k<name>`).

#### Usage (C)

```c
/* Backreferences */
// by index:
STRlingASTNode* br_idx = strling_ast_backref_create(1, NULL); // 
strling_ast_node_free(br_idx);
// by name:
STRlingASTNode* br_name = strling_ast_backref_create(-1, "groupName");
strling_ast_node_free(br_name);
```

---

## Flags & Modifiers

Global flags that alter the behavior of the regex engine.

-   `i`: Case-insensitive
-   `m`: Multiline mode
-   `s`: Dotall (single line) mode
-   `x`: Extended mode (ignore whitespace)

#### Usage (C)

```c
/* Flags object */
STRlingFlags* flags = strling_flags_create();
flags->ignoreCase = true; /* sets /i */
flags->multiline = true; /* sets /m */
// use when compiling, then free:
strling_flags_free(flags);
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
%lang C
%engine pcre2
```

```text
%flags imsx
%lang C
%engine pcre2
```
