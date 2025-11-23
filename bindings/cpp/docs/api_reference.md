# API Reference - C++ (C++17)

[← Back to README](../README.md)

This document provides a comprehensive reference for the STRling API in **C++ (C++17)**.

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

#### Usage (C++)

```cpp
#include "strling/ast.hpp"
#include "strling/compiler.hpp"
#include <memory>
#include <iostream>

using namespace strling;
using namespace strling::ast;

// Start/End of line anchors
auto start = std::make_unique<Anchor>();
start->kind = "Start";

auto end = std::make_unique<Anchor>();
end->kind = "End";

// Put them in a sequence
auto seq = std::make_unique<Sequence>();
seq->items.push_back(std::move(start));
seq->items.push_back(std::move(end));

auto ir = strling::compile(seq);
std::cout << "IR: " << ir->to_json().dump() << "\n";
```

### Start/End of String

Matches the absolute beginning (`\A`) or end (`\z`) of the string, ignoring multiline mode.

#### Usage (C++)

```cpp
#include "strling/ast.hpp"
#include "strling/compiler.hpp"
#include <memory>

using namespace strling;
using namespace strling::ast;

// Absolute string anchors
auto abs_start = std::make_unique<Anchor>();
abs_start->kind = "AbsoluteStart";

auto abs_end = std::make_unique<Anchor>();
abs_end->kind = "AbsoluteEnd";

auto seq = std::make_unique<Sequence>();
seq->items.push_back(std::move(abs_start));
seq->items.push_back(std::move(abs_end));

auto ir = strling::compile(seq);
```

### Word Boundaries

Matches the position between a word character and a non-word character (`\b`), or the inverse (`\B`).

#### Usage (C++)

```cpp
#include "strling/ast.hpp"
#include "strling/compiler.hpp"
#include <memory>

using namespace strling;
using namespace strling::ast;

// Word boundaries
auto wb = std::make_unique<Anchor>();
wb->kind = "WordBoundary";

auto nwb = std::make_unique<Anchor>();
nwb->kind = "NonWordBoundary";

auto seq = std::make_unique<Sequence>();
seq->items.push_back(std::move(wb));
seq->items.push_back(std::move(nwb));

auto ir = strling::compile(seq);
```

---

## Character Classes

### Built-in Classes

Standard shorthands for common character sets.

-   `\w`: Word characters (alphanumeric + underscore)
-   `\d`: Digits
-   `\s`: Whitespace
-   `.`: Any character (except newline)

#### Usage (C++)

```cpp
#include "strling/ast.hpp"
#include "strling/compiler.hpp"
#include <memory>

using namespace strling;
using namespace strling::ast;

// Built-in shorthand (as class members / escapes)
auto digitEscape = std::make_unique<Escape>();
digitEscape->kind = "digit"; // corresponds to \d inside a class

auto cc = std::make_unique<CharacterClass>();
cc->members.push_back(std::move(digitEscape));

auto ir = strling::compile(cc);
```

### Custom Classes & Ranges

Define a set of allowed characters (`[...]`) or a range (`a-z`).

#### Usage (C++)

```cpp
#include "strling/ast.hpp"
#include "strling/compiler.hpp"
#include <memory>

using namespace strling;
using namespace strling::ast;

// Custom char class and range
auto rng = std::make_unique<Range>();
rng->from = "a"; rng->to = "z";

auto lit = std::make_unique<Literal>();
lit->value = "_";

auto cc = std::make_unique<CharacterClass>();
cc->members.push_back(std::move(rng));
cc->members.push_back(std::move(lit));

auto ir = strling::compile(cc);
```

### Negated Classes

Match any character _not_ in the set (`[^...]`).

#### Usage (C++)

```cpp
#include "strling/ast.hpp"
#include "strling/compiler.hpp"
#include <memory>

using namespace strling;
using namespace strling::ast;

// Negated class
auto lit = std::make_unique<Literal>();
lit->value = "x";

auto cc = std::make_unique<CharacterClass>();
cc->negated = true; // [^x]
cc->members.push_back(std::move(lit));

auto ir = strling::compile(cc);
```

### Unicode Properties

Match characters based on Unicode properties (`\p{...}`), such as scripts, categories, or blocks. Unicode property escapes allow matching by Script (e.g. `\p{Latin}`), General Category (e.g. `\p{Lu}` for uppercase letters) or named blocks.

#### Usage (C++)

```cpp
#include "strling/ast.hpp"
#include "strling/compiler.hpp"
#include <memory>

using namespace strling;
using namespace strling::ast;

// Unicode property inside a class
auto prop = std::make_unique<UnicodeProperty>();
prop->value = "Latin";
prop->negated = false;

auto cc = std::make_unique<CharacterClass>();
cc->members.push_back(std::move(prop));

auto ir = strling::compile(cc);
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

#### Usage (C++)

```cpp
#include "strling/ast.hpp"
#include "strling/compiler.hpp"
#include <memory>

using namespace strling;
using namespace strling::ast;

// Control escape inside a character class
auto nl = std::make_unique<Escape>();
nl->kind = "control:n"; // newline control escape

auto cc = std::make_unique<CharacterClass>();
cc->members.push_back(std::move(nl));

auto ir = strling::compile(cc);
```

### Hexadecimal & Unicode

Define characters by their code point.

-   `\\xHH`: 2-digit hexadecimal (e.g. `\\x0A`)
-   `\\x{...}`: braced hexadecimal code point (variable length, e.g. `\\x{1F}`)
-   `\\uHHHH`: 4-digit Unicode (e.g. `\\u00A9`)
-   `\\u{...}`: braced Unicode code point (variable length, e.g. `\\u{1F600}`)

#### Usage (C++)

```cpp
#include "strling/ast.hpp"
#include "strling/compiler.hpp"
#include <memory>

using namespace strling;
using namespace strling::ast;

// Hex & Unicode escapes (in class items)
auto hx = std::make_unique<Escape>();
hx->kind = "hex:0A"; // \x0A

auto uni = std::make_unique<Escape>();
uni->kind = "unicode:00A9"; // ©

auto cc = std::make_unique<CharacterClass>();
cc->members.push_back(std::move(hx));
cc->members.push_back(std::move(uni));

auto ir = strling::compile(cc);
```

---

## Quantifiers

### Greedy Quantifiers

Match as much as possible (standard behavior).

-   `*`: 0 or more
-   `+`: 1 or more
-   `?`: 0 or 1
-   `{n,m}`: Specific range

#### Usage (C++)

```cpp
#include "strling/ast.hpp"
#include "strling/compiler.hpp"
#include <memory>

using namespace strling;
using namespace strling::ast;

// Greedy quantifier example: a+
auto lit = std::make_unique<Literal>();
lit->value = "a";

auto q = std::make_unique<Quantifier>();
q->child = std::move(lit);
q->min = 1; q->max = -1; q->greedy = true; // a+

auto ir = strling::compile(q);
```

### Lazy Quantifiers

Match as little as possible. Appending `?` to a quantifier (e.g., `*?`).

#### Usage (C++)

```cpp
#include "strling/ast.hpp"
#include "strling/compiler.hpp"
#include <memory>

using namespace strling;
using namespace strling::ast;

// Lazy quantifier: a*?
auto lit = std::make_unique<Literal>();
lit->value = "a";

auto q = std::make_unique<Quantifier>();
q->child = std::move(lit);
q->min = 0; q->max = -1; q->greedy = false; // lazy

auto ir = strling::compile(q);
```

### Possessive Quantifiers

Match as much as possible and **do not backtrack**. Appending `+` to a quantifier (e.g., `++`, `*+`).

> **Note:** This is a key performance feature in STRling.

#### Usage (C++)

```cpp
#include "strling/ast.hpp"
#include "strling/compiler.hpp"
#include <memory>

using namespace strling;
using namespace strling::ast;

// Possessive quantifier: a*+
auto lit = std::make_unique<Literal>();
lit->value = "a";

auto q = std::make_unique<Quantifier>();
q->child = std::move(lit);
q->min = 0; q->max = -1; q->greedy = true; q->possessive = true; // possessive

auto ir = strling::compile(q);
```

---

## Groups

### Capturing Groups

Standard groups `(...)` that capture the matched text.

#### Usage (C++)

```cpp
#include "strling/ast.hpp"
#include "strling/compiler.hpp"
#include <memory>

using namespace strling;
using namespace strling::ast;

// Capturing group
auto body = std::make_unique<Literal>();
body->value = "abc";

auto g = std::make_unique<Group>();
g->capturing = true;
g->child = std::move(body);

auto ir = strling::compile(g);
```

### Named Groups

Capturing groups with a specific name `(?<name>...)` for easier extraction.

#### Usage (C++)

```cpp
#include "strling/ast.hpp"
#include "strling/compiler.hpp"
#include <memory>
#include <string>

using namespace strling;
using namespace strling::ast;

// Named capturing group
auto body = std::make_unique<Literal>();
body->value = "id";

auto g = std::make_unique<Group>();
g->capturing = true;
g->name = std::optional<std::string>("myname");
g->child = std::move(body);

auto ir = strling::compile(g);
```

### Non-Capturing Groups

Groups `(?:...)` that group logic without capturing text.

#### Usage (C++)

```cpp
#include "strling/ast.hpp"
#include "strling/compiler.hpp"
#include <memory>

using namespace strling;
using namespace strling::ast;

// Non-capturing group
auto body = std::make_unique<Literal>();
body->value = "x+";

auto g = std::make_unique<Group>();
g->capturing = false;
g->child = std::move(body);

auto ir = strling::compile(g);
```

### Atomic Groups

Groups `(?>...)` that discard backtracking information once the group matches.

> **Note:** Useful for optimizing performance and preventing catastrophic backtracking.

#### Usage (C++)

```cpp
#include "strling/ast.hpp"
#include "strling/compiler.hpp"
#include <memory>

using namespace strling;
using namespace strling::ast;

// Atomic group
auto body = std::make_unique<Literal>();
body->value = "a+";

auto g = std::make_unique<Group>();
g->capturing = true;
g->atomic = true;
g->child = std::move(body);

auto ir = strling::compile(g);
```

---

## Lookarounds

Zero-width assertions that match a group without consuming characters.

### Lookahead

-   Positive `(?=...)`: Asserts that what follows matches the pattern.
-   Negative `(?!...)`: Asserts that what follows does _not_ match.

#### Usage (C++)

```cpp
#include "strling/ast.hpp"
#include "strling/compiler.hpp"
#include <memory>

using namespace strling;
using namespace strling::ast;

// Positive lookahead (?=foo)
auto body = std::make_unique<Literal>();
body->value = "foo";

auto look = std::make_unique<Lookahead>();
look->child = std::move(body);
look->positive = true;

auto ir = strling::compile(look);
```

### Lookbehind

-   Positive `(?<=...)`: Asserts that what precedes matches the pattern.
-   Negative `(?<!...)`: Asserts that what precedes does _not_ match.

#### Usage (C++)

```cpp
#include "strling/ast.hpp"
#include "strling/compiler.hpp"
#include <memory>

using namespace strling;
using namespace strling::ast;

// Positive lookbehind (?<=bar)
auto body = std::make_unique<Literal>();
body->value = "bar";

auto look = std::make_unique<Lookbehind>();
look->child = std::move(body);
look->positive = true;

auto ir = strling::compile(look);
```

---

## Logic

### Alternation

Matches one pattern OR another (`|`).

#### Usage (C++)

```cpp
#include "strling/ast.hpp"
#include "strling/compiler.hpp"
#include <memory>

using namespace strling;
using namespace strling::ast;

// Alternation (a|b)
auto left = std::make_unique<Literal>();
left->value = "a";

auto right = std::make_unique<Literal>();
right->value = "b";

auto alt = std::make_unique<Alternation>();
alt->items.push_back(std::move(left));
alt->items.push_back(std::move(right));

auto ir = strling::compile(alt);
```

---

## References

### Backreferences

Reference a previously captured group by index (`\1`) or name (`\k<name>`).

#### Usage (C++)

```cpp
#include "strling/ast.hpp"
#include "strling/compiler.hpp"
#include <memory>
#include <string>

using namespace strling;
using namespace strling::ast;

// Backreference by index
auto br_idx = std::make_unique<Backreference>();
br_idx->index = 1; // \1

// Backreference by name
auto br_name = std::make_unique<Backreference>();
br_name->name = std::optional<std::string>("groupName"); // \k<groupName>

auto seq = std::make_unique<Sequence>();
seq->items.push_back(std::move(br_idx));
seq->items.push_back(std::move(br_name));

auto ir = strling::compile(seq);
```

---

## Flags & Modifiers

Global flags that alter the behavior of the regex engine.

-   `i`: Case-insensitive
-   `m`: Multiline mode
-   `s`: Dotall (single line) mode
-   `x`: Extended mode (ignore whitespace)

#### Usage (C++)

```cpp
#include "strling/core/nodes.hpp"
#include <string>
#include <iostream>

using namespace strling::core;

// Flags object
Flags flags;
flags.ignoreCase = true; // /i
flags.multiline = true;  // /m

// Flags are commonly produced by parsing a directives block and passed into
// downstream compilation/parsing stages where applicable.
std::cout << "ignoreCase=" << flags.ignoreCase << " multiline=" << flags.multiline << "\n";
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
%lang C++
%engine pcre2
```

```text
%flags imsux
%lang C++
%engine pcre2
```
