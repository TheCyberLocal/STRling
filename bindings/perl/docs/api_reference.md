# API Reference - Perl

[← Back to README](../README.md)

This document provides a comprehensive reference for the STRling API in **Perl**.

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

#### Usage (Perl)

```perl
use STRling::Core::Nodes;

my $pattern = STRling::Core::Nodes::Seq->new(parts => [
    STRling::Core::Nodes::Anchor->new(at => 'Start'),
    STRling::Core::Nodes::Lit->new(value => 'abc'),
    STRling::Core::Nodes::Anchor->new(at => 'End'),
]);
# Start of line.
# End of line.
```

### Start/End of String

Matches the absolute beginning (`\A`) or end (`\z`) of the string, ignoring multiline mode.

#### Usage (Perl)

```perl
use STRling::Core::Nodes;

# STRling's start()/end() anchor reflects line anchors in most engines; for absolute anchors, use directives or emitter options.
my $pattern = STRling::Core::Nodes::Seq->new(parts => [
    STRling::Core::Nodes::Anchor->new(at => 'AbsoluteStart'),
    STRling::Core::Nodes::Lit->new(value => 'hello'),
    STRling::Core::Nodes::Anchor->new(at => 'EndBeforeFinalNewline'),
]);
# Start of string.
# End of string.
```

### Word Boundaries

Matches the position between a word character and a non-word character (`\b`), or the inverse (`\B`).

#### Usage (Perl)

```perl
use STRling::Core::Nodes;

my $pattern = STRling::Core::Nodes::Seq->new(parts => [
    STRling::Core::Nodes::Anchor->new(at => 'Start'),
    STRling::Core::Nodes::Group->new(capturing => 1, body => STRling::Core::Nodes::ClassEscape->new(type => 'w')),
    STRling::Core::Nodes::Anchor->new(at => 'WordBoundary'),
    STRling::Core::Nodes::Group->new(capturing => 1, body => STRling::Core::Nodes::ClassEscape->new(type => 'd')),
    STRling::Core::Nodes::Anchor->new(at => 'End'),
]);
# Word boundary (\b) separates letters from digits
```

---

## Character Classes

### Built-in Classes

Standard shorthands for common character sets.

-   `\w`: Word characters (alphanumeric + underscore)
-   `\d`: Digits
-   `\s`: Whitespace
-   `.`: Any character (except newline)

#### Usage (Perl)

```perl
use STRling::Core::Nodes;

my $pattern = STRling::Core::Nodes::Seq->new(parts => [
    STRling::Core::Nodes::Anchor->new(at => 'Start'),
    STRling::Core::Nodes::Group->new(capturing => 1, body => STRling::Core::Nodes::Quant->new(child => STRling::Core::Nodes::CharClass->new(negated => 0, items => [ STRling::Core::Nodes::ClassEscape->new(type => 'd') ]), min => 3, max => 3, mode => 'Greedy')),
    STRling::Core::Nodes::Anchor->new(at => 'End'),
]);
# Match exactly 3 digits (\d{3})
```

### Custom Classes & Ranges

Define a set of allowed characters (`[...]`) or a range (`a-z`).

#### Usage (Perl)

```perl
use STRling::Core::Nodes;

my $pattern = STRling::Core::Nodes::Seq->new(parts => [
    STRling::Core::Nodes::Anchor->new(at => 'Start'),
    STRling::Core::Nodes::CharClass->new(negated => 0, items => [
        STRling::Core::Nodes::ClassLiteral->new(ch => 'a'),
        STRling::Core::Nodes::ClassLiteral->new(ch => 'b'),
        STRling::Core::Nodes::ClassLiteral->new(ch => 'c'),
    ]),
    STRling::Core::Nodes::Anchor->new(at => 'End'),
]);
# Match one of: a, b, or c (custom class)
```

### Negated Classes

Match any character _not_ in the set (`[^...]`).

#### Usage (Perl)

```perl
use STRling::Core::Nodes;

my $not_vowels = STRling::Core::Nodes::CharClass->new(
    negated => 1,
    items   => [ map { STRling::Core::Nodes::ClassLiteral->new(ch => $_) } qw(a e i o u) ]
);
my $pattern = STRling::Core::Nodes::Seq->new(parts => [
    STRling::Core::Nodes::Anchor->new(at => 'Start'),
    $not_vowels,
    STRling::Core::Nodes::Anchor->new(at => 'End'),
]);
# Match any character except vowels
```

### Unicode Properties

Match characters based on Unicode properties (`\p{...}`), such as scripts, categories, or blocks. Unicode property escapes allow matching by Script (e.g. `\p{Latin}`), General Category (e.g. `\p{Lu}` for uppercase letters) or named blocks.

#### Usage (Perl)

```perl
use STRling::Core::Nodes;

my $pattern = STRling::Core::Nodes::Seq->new(parts => [
    STRling::Core::Nodes::Anchor->new(at => 'Start'),
    STRling::Core::Nodes::CharClass->new(negated => 0, items => [ STRling::Core::Nodes::ClassEscape->new(type => 'p', property => 'Lu') ]),
    STRling::Core::Nodes::Anchor->new(at => 'End'),
]);
# Match a Unicode uppercase letter (\p{Lu})
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

#### Usage (Perl)

```perl
use STRling::Core::Nodes;

# Using a literal-style escape in a literal node
my $pattern_n = STRling::Core::Nodes::Seq->new(parts => [ STRling::Core::Nodes::Lit->new(value => "
"), STRling::Core::Nodes::Lit->new(value => 'end') ]);

# Using an explicit escape node is modeled via literals in the AST for many bindings
my $pattern_n2 = STRling::Core::Nodes::Seq->new(parts => [ STRling::Core::Nodes::Lit->new(value => "
"), STRling::Core::Nodes::Lit->new(value => 'end') ]);

# Both match a newline followed by 'end'
```

### Hexadecimal & Unicode

Define characters by their code point.

-   `\\xHH`: 2-digit hexadecimal (e.g. `\\x0A`)
-   `\\x{...}`: braced hexadecimal code point (variable length, e.g. `\\x{1F}`)
-   `\\uHHHH`: 4-digit Unicode (e.g. `\\u00A9`)
-   `\\u{...}`: braced Unicode code point (variable length, e.g. `\\u{1F600}`)

#### Usage (Perl)

```perl
use STRling::Core::Nodes;

my $pattern_hex = STRling::Core::Nodes::Seq->new(parts => [ STRling::Core::Nodes::Lit->new(value => "A"), STRling::Core::Nodes::Lit->new(value => 'end') ]);    # A -> 'A'
my $pattern_u   = STRling::Core::Nodes::Seq->new(parts => [ STRling::Core::Nodes::Lit->new(value => "A"), STRling::Core::Nodes::Lit->new(value => 'end') ]);    # A -> 'A'
my $pattern_braced = STRling::Core::Nodes::Seq->new(parts => [ STRling::Core::Nodes::Lit->new(value => "😀"), STRling::Core::Nodes::Lit->new(value => 'end') ]); # U+1F600 😀

# All three variants embed the codepoint into literals
```

---

## Quantifiers

### Greedy Quantifiers

Match as much as possible (standard behavior).

-   `*`: 0 or more
-   `+`: 1 or more
-   `?`: 0 or 1
-   `{n,m}`: Specific range

#### Usage (Perl)

```perl
use STRling::Core::Nodes;

# Match one or more word characters (greedy)
my $pattern = STRling::Core::Nodes::Seq->new(parts => [ STRling::Core::Nodes::Anchor->new(at => 'Start'), STRling::Core::Nodes::Quant->new(child => STRling::Core::Nodes::CharClass->new(negated => 0, items => [ STRling::Core::Nodes::ClassEscape->new(type => 'w') ]), min => 1, max => 'Inf', mode => 'Greedy'), STRling::Core::Nodes::Anchor->new(at => 'End') ]);
# Match one or more letters (greedy)
```

### Lazy Quantifiers

Match as little as possible. Appending `?` to a quantifier (e.g., `*?`).

#### Usage (Perl)

```perl
use STRling::Core::Nodes;

# Lazy quantifier: match between 1 and 5 word characters lazily
my $pattern = STRling::Core::Nodes::Quant->new(child => STRling::Core::Nodes::CharClass->new(negated => 0, items => [ STRling::Core::Nodes::ClassEscape->new(type => 'w') ]), min => 1, max => 5, mode => 'Lazy');
# Match between 1 and 5 characters lazily
```

### Possessive Quantifiers

Match as much as possible and **do not backtrack**. Appending `+` to a quantifier (e.g., `++`, `*+`).

> **Note:** This is a key performance feature in STRling.

#### Usage (Perl)

```perl
use STRling::Core::Nodes;

# Possessive quantifier avoids backtracking when supported
my $pattern = STRling::Core::Nodes::Quant->new(child => STRling::Core::Nodes::CharClass->new(negated => 0, items => [ STRling::Core::Nodes::ClassEscape->new(type => 'd') ]), min => 1, max => 'Inf', mode => 'Possessive');
# Match one or more digits possessively
```

---

## Groups

### Capturing Groups

Standard groups `(...)` that capture the matched text.

#### Usage (Perl)

```perl
use STRling::Core::Nodes;

my $pattern = STRling::Core::Nodes::Group->new(capturing => 1, body => STRling::Core::Nodes::Quant->new(child => STRling::Core::Nodes::CharClass->new(negated => 0, items => [ STRling::Core::Nodes::ClassEscape->new(type => 'w') ]), min => 3, max => 3, mode => 'Greedy'));
# Capture three letters for later extraction
```

### Named Groups

Capturing groups with a specific name `(?<name>...)` for easier extraction.

#### Usage (Perl)

```perl
use STRling::Core::Nodes;

my $pattern = STRling::Core::Nodes::Group->new(capturing => 1, name => 'area', body => STRling::Core::Nodes::Quant->new(child => STRling::Core::Nodes::CharClass->new(negated => 0, items => [ STRling::Core::Nodes::ClassEscape->new(type => 'd') ]), min => 3, max => 3, mode => 'Greedy'));
# Named group 'area' captures three digits
```

### Non-Capturing Groups

Groups `(?:...)` that group logic without capturing text.

#### Usage (Perl)

```perl
use STRling::Core::Nodes;

my $pattern = STRling::Core::Nodes::Seq->new(parts => [
    STRling::Core::Nodes::Anchor->new(at => 'Start'),
    STRling::Core::Nodes::Group->new(
        capturing => 0,
        body => STRling::Core::Nodes::Seq->new(parts => [
            STRling::Core::Nodes::Quant->new(child => STRling::Core::Nodes::CharClass->new(negated => 0, items => [ STRling::Core::Nodes::ClassEscape->new(type => 'd') ]), min => 3, max => 3, mode => 'Greedy')
        ])
    ),
    STRling::Core::Nodes::Anchor->new(at => 'End'),
]);
# Non-capturing grouping used for grouping logic without occupying capture slots
```

### Atomic Groups

Groups `(?>...)` that discard backtracking information once the group matches.

> **Note:** Useful for optimizing performance and preventing catastrophic backtracking.

#### Usage (Perl)

```perl
use STRling::Core::Nodes;

my $pattern = STRling::Core::Nodes::Group->new(capturing => 0, atomic => 1, body => STRling::Core::Nodes::Seq->new(parts => [ STRling::Core::Nodes::Quant->new(child => STRling::Core::Nodes::CharClass->new(negated => 0, items => [ STRling::Core::Nodes::ClassEscape->new(type => 'd') ]), min => 1, max => 'Inf', mode => 'Greedy'), STRling::Core::Nodes::Quant->new(child => STRling::Core::Nodes::CharClass->new(negated => 0, items => [ STRling::Core::Nodes::ClassEscape->new(type => 'w') ]), min => 1, max => 'Inf', mode => 'Greedy') ]));
# Atomic grouping prevents internal backtracking once matched
```

---

## Lookarounds

Zero-width assertions that match a group without consuming characters.

### Lookahead

-   Positive `(?=...)`: Asserts that what follows matches the pattern.
-   Negative `(?!...)`: Asserts that what follows does _not_ match.

#### Usage (Perl)

```perl
use STRling::Core::Nodes;

my $pattern = STRling::Core::Nodes::Seq->new(parts => [ STRling::Core::Nodes::ClassEscape->new(type => 'w'), STRling::Core::Nodes::Look->new(dir => 'Ahead', neg => 0, body => STRling::Core::Nodes::ClassEscape->new(type => 'd')) ]);
# Assert that a digit follows (lookahead)
```

### Lookbehind

-   Positive `(?<=...)`: Asserts that what precedes matches the pattern.
-   Negative `(?<!...)`: Asserts that what precedes does _not_ match.

#### Usage (Perl)

```perl
use STRling::Core::Nodes;

my $pattern = STRling::Core::Nodes::Seq->new(parts => [ STRling::Core::Nodes::Look->new(dir => 'Behind', neg => 0, body => STRling::Core::Nodes::ClassEscape->new(type => 'w')), STRling::Core::Nodes::ClassEscape->new(type => 'd') ]);
# Assert that a letter precedes (lookbehind)
```

---

## Logic

### Alternation

Matches one pattern OR another (`|`).

#### Usage (Perl)

```perl
use STRling::Core::Nodes;

my $pattern = STRling::Core::Nodes::Alt->new(branches => [ STRling::Core::Nodes::Lit->new(value => 'cat'), STRling::Core::Nodes::Lit->new(value => 'dog') ]);
# Match either 'cat' or 'dog'
```

---

## References

### Backreferences

Reference a previously captured group by index (`\1`) or name (`\k<name>`).

#### Usage (Perl)

```perl
use STRling::Core::Nodes;

my $p = STRling::Core::Nodes::Group->new(capturing => 1, body => STRling::Core::Nodes::Quant->new(child => STRling::Core::Nodes::CharClass->new(negated => 0, items => [ STRling::Core::Nodes::ClassEscape->new(type => 'w') ]), min => 3, max => 3, mode => 'Greedy'));
my $pattern = STRling::Core::Nodes::Seq->new(parts => [ $p, STRling::Core::Nodes::Lit->new(value => '-'), STRling::Core::Nodes::Backref->new(byIndex => 1) ]);
# Backreference to the first numbered capture group
```

---

## Flags & Modifiers

Global flags that alter the behavior of the regex engine.

-   `i`: Case-insensitive
-   `m`: Multiline mode
-   `s`: Dotall (single line) mode
-   `x`: Extended mode (ignore whitespace)

#### Usage (Perl)

```perl
use STRling::Core::Nodes;

# Build flags programmatically
my $flags = STRling::Core::Nodes::Flags->from_letters('ims');
# Case-insensitive, multiline and dotAll
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
%lang Perl
%engine pcre2
```

```text
%flags imsux
%lang Perl
%engine pcre2
```

```perl
# In Perl you can also parse directives inline at the top of a pattern file
my ($flags, $ast) = STRling::Core::Parser::parse("%flags imsux
start digit(3) '-' digit(4)");
```
