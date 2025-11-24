# STRling - Perl Binding

> Part of the [STRling Project](https://github.com/TheCyberLocal/STRling/blob/main/README.md)

<table>
  <tr>
    <td style="padding: 10px;"><img src="https://raw.githubusercontent.com/TheCyberLocal/STRling/main/strling_logo.jpg" alt="STRling Logo" width="100" /></td>
    <td style="padding: 10px;">
      <strong>The Universal Regular Expression Compiler.</strong><br><br>
      STRling is a next-generation production-grade syntax designed to make Regex readable, maintainable, and robust. It abstracts the cryptic nature of raw regex strings into a clean, object-oriented, and strictly typed interface that compiles to standard PCRE2 (or native) patterns.
    </td>
  </tr>
</table>

## 💿 Installation

```bash
# install runtime dependencies for this binding from CPAN
cpanm --installdeps .

# or install the published distribution (if available)
cpanm STRling
```

## 📦 Usage

Here is how to match a US Phone number (e.g., `555-0199`) using STRling in **Perl**:

```perl
use strict;
use warnings;

# If you want to parse a DSL string into an AST and compile it:
use STRling::Core::Parser qw(parse);
use STRling::Core::Compiler;

my ($flags, $ast) = parse(
    "start capture(digit(3)) may(any_of('-', '.', ' ')) capture(digit(3)) may(any_of('-', '.', ' ')) capture(digit(4)) end"
);

# Or construct the same AST explicitly using Moo-based node constructors:
use STRling::Core::Nodes;

# Start of line.
# Match the area code (3 digits)
# Optional separator: [-. ]
# Match the central office code (3 digits)
# Optional separator: [-. ]
# Match the station number (4 digits)
# End of line.

my $phone_ast = STRling::Core::Nodes::Seq->new(parts => [
    STRling::Core::Nodes::Anchor->new(at => 'Start'),

    # Group 1: 3 digits
    STRling::Core::Nodes::Group->new(
        capturing => 1,
        body      => STRling::Core::Nodes::Quant->new(
            child => STRling::Core::Nodes::CharClass->new(negated => 0, items => [ STRling::Core::Nodes::ClassEscape->new(type => 'd') ]),
            min   => 3,
            max   => 3,
            mode  => 'Greedy',
        ),
    ),

    # Optional separator: [-. ]
    STRling::Core::Nodes::Quant->new(
        child => STRling::Core::Nodes::CharClass->new(
            negated => 0,
            items   => [
                STRling::Core::Nodes::ClassLiteral->new(ch => '-'),
                STRling::Core::Nodes::ClassLiteral->new(ch => '.'),
                STRling::Core::Nodes::ClassLiteral->new(ch => ' '),
            ]
        ),
        min  => 0,
        max  => 1,
        mode => 'Greedy',
    ),

    # Group 2: 3 digits
    STRling::Core::Nodes::Group->new(
        capturing => 1,
        body      => STRling::Core::Nodes::Quant->new(
            child => STRling::Core::Nodes::CharClass->new(negated => 0, items => [ STRling::Core::Nodes::ClassEscape->new(type => 'd') ]),
            min   => 3,
            max   => 3,
            mode  => 'Greedy',
        ),
    ),

    # Optional separator: [-. ]
    STRling::Core::Nodes::Quant->new(
        child => STRling::Core::Nodes::CharClass->new(
            negated => 0,
            items   => [
                STRling::Core::Nodes::ClassLiteral->new(ch => '-'),
                STRling::Core::Nodes::ClassLiteral->new(ch => '.'),
                STRling::Core::Nodes::ClassLiteral->new(ch => ' '),
            ]
        ),
        min  => 0,
        max  => 1,
        mode => 'Greedy',
    ),

    # Group 3: 4 digits
    STRling::Core::Nodes::Group->new(
        capturing => 1,
        body      => STRling::Core::Nodes::Quant->new(
            child => STRling::Core::Nodes::CharClass->new(negated => 0, items => [ STRling::Core::Nodes::ClassEscape->new(type => 'd') ]),
            min   => 4,
            max   => 4,
            mode  => 'Greedy',
        ),
    ),

    STRling::Core::Nodes::Anchor->new(at => 'End'),
]);

# Compile to the IR representation (emitters live in other bindings).
my $ir = STRling::Core::Compiler->compile($phone_ast);

# Note: the final regex emission is typically performed by a language emitter (e.g. TypeScript/Rust emitters).
```

> **Note:** This compiles to the optimized regex: `^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$`

## 🚀 Why STRling?

Regular Expressions are powerful but notorious for being "write-only" code. STRling solves this by treating Regex as **Software**, not a string.

-   **🧩 Composability:** Regex strings are hard to merge. STRling lets you build reusable components (e.g., `ip_address`, `email`) and safely compose them into larger patterns without breaking operator precedence or capturing groups.
-   **🛡️ Type Safety:** Catch syntax errors, invalid ranges, and incompatible flags at **compile time** inside your IDE, not at runtime when your app crashes.
-   **🧠 IntelliSense & Autocomplete:** Stop memorizing cryptic codes like `(?<=...)`. Use fluent, self-documenting methods like `simply.lookBehind(...)` with full IDE discovery.
-   **📖 Readability First:** Code is read far more often than it is written. STRling patterns describe _intent_, making them understandable to junior developers and future maintainers instantly.
-   **🌍 Polyglot Engine:** One mental model, 17 languages. Whether you are writing Rust, Python, or TypeScript, the syntax and behavior remain identical.

## 🏗️ Architecture

STRling follows a strict compiler pipeline architecture to ensure consistency across all ecosystems:

1.  **Parse**: `DSL -> AST` (Abstract Syntax Tree)
    -   Converts the human-readable STRling syntax into a structured tree.
2.  **Compile**: `AST -> IR` (Intermediate Representation)
    -   Transforms the AST into a target-agnostic intermediate representation, optimizing structures like literal sequences.
3.  **Emit**: `IR -> Target Regex`
    -   Generates the final, optimized regex string for the specific target engine (e.g., PCRE2, JS, Python `re`).

## 📚 Documentation

-   [**API Reference**](./docs/api_reference.md): Detailed documentation for this binding.
-   [**Project Hub**](https://github.com/TheCyberLocal/STRling/blob/main/README.md): The main STRling repository.
-   [**Specification**](https://github.com/TheCyberLocal/STRling/tree/main/spec): The core grammar and semantic specifications.

## 🌐 Connect

[![LinkedIn](https://img.shields.io/badge/LinkedIn-%230077B5.svg?logo=linkedin&logoColor=white)](https://linkedin.com/in/tzm01)
[![GitHub](https://img.shields.io/badge/GitHub-black?logo=github&logoColor=white)](https://github.com/TheCyberLocal)

## 💖 Support

If you find STRling useful, consider supporting the development:

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-%23FFDD00.svg?logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/thecyberlocal)
