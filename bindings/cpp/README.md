# STRling - C++ Binding

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

{Installation_Command}

## 📦 Usage

Here is how to match a US Phone number (e.g., `555-0199`) using STRling in **C++ (C++17)**:

```cpp
#include <iostream>
#include <memory>
#include <vector>
#include "strling/ast.hpp"
#include "strling/compiler.hpp"

using namespace strling;
using namespace strling::ast;

// Build a small phone-number AST — comments match the Python example exactly
// Start of line.
// Match the area code (3 digits)
// Optional separator: [-. ]
// Match the central office code (3 digits)
// Optional separator: [-. ]
// Match the station number (4 digits)
// End of line.

auto ast = std::make_unique<Sequence>();
{
  auto* seq = static_cast<Sequence*>(ast.get());

  // Start anchor
  auto start = std::make_unique<Anchor>();
  start->kind = "Start";
  seq->items.push_back(std::move(start));

  // Match the area code (3 digits)
  auto area_group = std::make_unique<Group>();
  area_group->capturing = true;
  auto area_q = std::make_unique<Quantifier>();
  area_q->child = std::make_unique<Literal>();
  static_cast<Literal*>(area_q->child.get())->value = "\\d";
  area_q->min = 3;
  area_q->max = 3;
  area_q->greedy = true;
  area_group->child = std::move(area_q);
  seq->items.push_back(std::move(area_group));

  // Optional separator: [-. ]
  auto sep_class = std::make_unique<CharacterClass>();
  sep_class->negated = false;
  sep_class->members.push_back(std::make_unique<Literal>());
  static_cast<Literal*>(sep_class->members.back().get())->value = "-";
  sep_class->members.push_back(std::make_unique<Literal>());
  static_cast<Literal*>(sep_class->members.back().get())->value = ".";
  sep_class->members.push_back(std::make_unique<Literal>());
  static_cast<Literal*>(sep_class->members.back().get())->value = " ";

  auto opt_sep = std::make_unique<Quantifier>();
  opt_sep->child = std::move(sep_class);
  opt_sep->min = 0;
  opt_sep->max = 1;
  seq->items.push_back(std::move(opt_sep));

  // Match the central office code (3 digits)
  auto central_group = std::make_unique<Group>();
  central_group->capturing = true;
  auto central_q = std::make_unique<Quantifier>();
  central_q->child = std::make_unique<Literal>();
  static_cast<Literal*>(central_q->child.get())->value = "\\d";
  central_q->min = 3;
  central_q->max = 3;
  central_q->greedy = true;
  central_group->child = std::move(central_q);
  seq->items.push_back(std::move(central_group));

  // Optional separator: [-. ]
  auto sep_class_b = std::make_unique<CharacterClass>();
  sep_class_b->members.push_back(std::make_unique<Literal>());
  static_cast<Literal*>(sep_class_b->members.back().get())->value = "-";
  sep_class_b->members.push_back(std::make_unique<Literal>());
  static_cast<Literal*>(sep_class_b->members.back().get())->value = ".";
  sep_class_b->members.push_back(std::make_unique<Literal>());
  static_cast<Literal*>(sep_class_b->members.back().get())->value = " ";

  auto opt_sep_b = std::make_unique<Quantifier>();
  opt_sep_b->child = std::move(sep_class_b);
  opt_sep_b->min = 0;
  opt_sep_b->max = 1;
  seq->items.push_back(std::move(opt_sep_b));

  // Match the station number (4 digits)
  auto station_group = std::make_unique<Group>();
  station_group->capturing = true;
  auto station_q = std::make_unique<Quantifier>();
  station_q->child = std::make_unique<Literal>();
  static_cast<Literal*>(station_q->child.get())->value = "\\d";
  station_q->min = 4;
  station_q->max = 4;
  station_q->greedy = true;
  station_group->child = std::move(station_q);
  seq->items.push_back(std::move(station_group));

  // End anchor
  auto end = std::make_unique<Anchor>();
  end->kind = "End";
  seq->items.push_back(std::move(end));
}

// Compile the AST into the IR
auto ir = strling::compile(ast);
std::cout << "Compiled IR type: " << ir->to_json().dump() << "\n";
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
