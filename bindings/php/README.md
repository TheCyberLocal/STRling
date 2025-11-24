# STRling - PHP Binding

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

Install via Composer (PHP 8.2+):

```bash
composer require thecyberlocal/strling
```

## 📦 Usage

### Simply API (Recommended)

Here is how to match a US Phone number (e.g., `555-0199`) using the **Simply API** in **PHP (8.2+)**:

```php
<?php

use STRling\Simply;

// Build the pattern using the Simply API with static methods
$phone = Simply::merge(
    Simply::start(),
    Simply::capture(Simply::digit(3)),
    Simply::may(Simply::inChars("-. ")),
    Simply::capture(Simply::digit(3)),
    Simply::may(Simply::inChars("-. ")),
    Simply::capture(Simply::digit(4)),
    Simply::end()
);

// Compile to IR (intermediate representation)
$ir = $phone->compile();
echo $ir . PHP_EOL;

// Expected output: JSON IR representing the pattern
// Final regex: ^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$
```

> **Note:** The Simply API provides a clean, composable interface for building patterns with **structural identity**—using `Simply::capture($inner)` instead of `$inner->capture()`. Method names are inspired by Python/TypeScript but may differ (e.g., `inChars` for character classes in PHP vs. `in_chars` in Python/TypeScript).

### Low-Level AST API

For advanced use cases, you can build patterns directly using the AST Node classes:

```php
<?php

use STRling\Compiler;
use STRling\Core\Nodes\{Sequence, Anchor, Literal, Quantifier, Group, CharacterClass, Escape};

// Build the AST using PHP 8.2 readonly node classes and named arguments
$area = new Group(
  capturing: true,
  body: new Quantifier(
    target: new Escape(kind: 'digit'),
    min: 3,
    max: 3,
    greedy: true,
    lazy: false,
    possessive: false
  )
);

// Match optional separator [-. ]?
$sep = new Quantifier(
  target: new CharacterClass(false, [new Literal('-'), new Literal('.'), new Literal(' ')]),
  min: 0,
  max: 1,
  greedy: true,
  lazy: false,
  possessive: false
);

// Match the next 3 digits
$prefix = new Group(
  capturing: true,
  body: new Quantifier(
    target: new Escape(kind: 'digit'),
    min: 3,
    max: 3,
    greedy: true,
    lazy: false,
    possessive: false
  )
);

// Match the final 4 digits
$line = new Group(
  capturing: true,
  body: new Quantifier(
    target: new Escape(kind: 'digit'),
    min: 4,
    max: 4,
    greedy: true,
    lazy: false,
    possessive: false
  )
);

$ast = new Sequence(parts: [
  new Anchor(at: 'Start'),
  $area,
  $sep,
  $prefix,
  $sep,
  $line,
  new Anchor(at: 'End'),
]);

// Compiler compiles the Node AST into an intermediate representation (IR).
$compiler = new Compiler();
$ir = $compiler->compile($ast);

// For demonstration we JSON-encode the IR so it's human readable.
echo json_encode($ir, JSON_PRETTY_PRINT) . PHP_EOL;

// Expected (semantic) shape: the Compiler will transform our node graph into an
// IR tree. A downstream emitter (e.g., PCRE2 emitter) will generate the
// final regex string from that IR. Example final regex: ^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$
```

> **Note:** Both approaches compile to the same optimized regex: `^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$`

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
