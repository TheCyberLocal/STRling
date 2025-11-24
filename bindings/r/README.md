# STRling - R Binding

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

Install directly from the GitHub repository (development build):

```r
# install.packages("devtools") # if you don't have devtools already
devtools::install_github("TheCyberLocal/STRling", subdir = "bindings/r")
```

## 📦 Usage

### Simply Fluent API (Recommended)

The **Simply API** provides a clean, functional interface for building STRling patterns using
Gold Standard naming conventions. This is the easiest way to use STRling in R:

```r
library(strling)

# Build a US Phone number pattern: ^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$
phone <- sl_merge(
  sl_start(),
  sl_capture(sl_digit(3)),
  sl_may(sl_any_of("-. ")),
  sl_capture(sl_digit(3)),
  sl_may(sl_any_of("-. ")),
  sl_capture(sl_digit(4)),
  sl_end()
)

# Compile the pattern to IR for inspection
ir <- sl_compile(phone)
print(ir)

# NOTE: An emitter (for example PCRE2) will convert the IR → a final regex string.
# For the canonical PCRE2 emitter the final emitted regex for the pattern above is:
# ^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$
```

**Simply API Functions:**
- `sl_start()` - Match start of line (^)
- `sl_end()` - Match end of line ($)
- `sl_digit(n)` - Match exactly n digits
- `sl_any_of(chars)` - Match any character in the string
- `sl_merge(...)` - Concatenate patterns sequentially
- `sl_capture(inner)` - Create a capturing group
- `sl_may(inner)` - Make a pattern optional (0 or 1)
- `sl_compile(pattern)` - Compile AST to IR

### Low-Level S3 Constructors

For advanced use cases, you can also build AST nodes directly using S3 constructors:

```r
library(strling)

# Build a STRling AST with S3 constructors (verbose approach)
phone <- strling_sequence(parts = list(
  strling_anchor("Start"),
  strling_group(
    strling_quantifier(
      strling_character_class(list(strling_class_escape("d"))),
      min = 3L, max = 3L
    ),
    capturing = TRUE
  ),
  strling_quantifier(
    strling_character_class(list(
      strling_class_literal("-"),
      strling_class_literal("."),
      strling_class_literal(" ")
    )),
    min = 0L, max = 1L
  ),
  strling_group(
    strling_quantifier(
      strling_character_class(list(strling_class_escape("d"))),
      min = 3L, max = 3L
    ),
    capturing = TRUE
  ),
  strling_quantifier(
    strling_character_class(list(
      strling_class_literal("-"),
      strling_class_literal("."),
      strling_class_literal(" ")
    )),
    min = 0L, max = 1L
  ),
  strling_group(
    strling_quantifier(
      strling_character_class(list(strling_class_escape("d"))),
      min = 4L, max = 4L
    ),
    capturing = TRUE
  ),
  strling_anchor("End")
))

# Compile the AST to IR
ir <- compile_ast(phone)
```

> **Note:** Both approaches compile to the optimized regex: `^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$`

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
