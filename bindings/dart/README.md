# STRling - Dart Binding

> Part of the [STRling Project](https://github.com/strling-lang/strling/blob/main/README.md)

<table>
  <tr>
    <td style="padding: 10px;"><img src="https://raw.githubusercontent.com/strling-lang/.github/refs/heads/main/strling_silver_bell.png" alt="STRling Logo" width="100" /></td>
    <td style="padding: 10px;">
      <strong>The Universal Regular Expression Compiler.</strong><br><br>
      STRling is a next-generation production-grade syntax designed to make Regex readable, maintainable, and robust. It abstracts the cryptic nature of raw regex strings into a clean, object-oriented, and strictly typed interface that compiles to standard PCRE2 (or native) patterns.
    </td>
  </tr>
</table>

## 💿 Installation

Add the official STRling Dart package to your project using pub:

```bash
dart pub add strling
```

## 📦 Usage

Here is how to match a US Phone number (e.g., `555-0199`) using STRling in **Dart**:

```dart
import 'package:strling/simply.dart';

// Build a pattern for ^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$
final usPhonePattern = Simply.merge([
  Simply.start(),
  Simply.digit(3, 3).asCapture(),       // Area code
  Simply.inChars('-. ').may(),      // Optional separator
  Simply.digit(3, 3).asCapture(),       // Prefix
  Simply.inChars('-. ').may(),      // Optional separator
  Simply.digit(4, 4).asCapture(),       // Line number
  Simply.end(),
]);

// Get the intermediate representation (IR)
final ir = usPhonePattern.toIR();

// The IR can be passed to emitters in downstream tooling to generate
// concrete regular expression strings for different regex engines.
```

> **Note:** This compiles to the optimized regex: `^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$`

### Alternative: Using Raw AST Nodes

For advanced use cases, you can still construct patterns using raw AST nodes:

```dart
import 'package:strling/strling.dart';

final Node usPhoneAst = Sequence([
  Anchor('Start'),
  Group(
    capturing: true,
    body: Quantifier(
      target: CharacterClass(negated: false, members: [Escape('digit')]),
      min: 3,
      max: 3,
      greedy: true,
      lazy: false,
      possessive: false,
    ),
  ),
  Quantifier(
    target: CharacterClass(
      negated: false,
      members: [Literal('-'), Literal('.'), Literal(' ')],
    ),
    min: 0,
    max: 1,
    greedy: true,
    lazy: false,
    possessive: false,
  ),
  // ... pattern continues for remaining groups and separators
  Anchor('End'),
]);
```

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

-   [**API Reference**](./doc/api_reference.md): Detailed documentation for this binding.
-   [**Project Hub**](https://github.com/strling-lang/strling/blob/main/README.md): The main STRling repository.
-   [**Specification**](https://github.com/strling-lang/strling/tree/main/spec): The core grammar and semantic specifications.

## 🌐 Connect

[![GitHub](https://img.shields.io/badge/GitHub-black?logo=github&logoColor=white)](https://github.com/strling-lang)

## 💖 Support

If you find STRling useful, consider starring the repository and contributing!
