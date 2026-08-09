# STRling - Swift Binding

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

Add STRling to your `Package.swift` dependencies:

```swift
dependencies: [
    .package(url: "https://github.com/strling-lang/strling.git", from: "3.0.0")
]
```

Then add it to your target:

```swift
targets: [
    .target(
        name: "YourTarget",
        dependencies: ["STRling"]
    )
]
```

## 📦 Usage

Here is how to match a US Phone number (e.g., `555-0199`) using STRling in **Swift**:

```swift
import STRling
import Foundation

// Build the phone pattern using the Simply fluent API
// Match: ^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$
let phonePattern = Simply.merge(
    Simply.start(),                              // Start of line
    Simply.capture(Simply.digit(3)),             // 3 digits (area code)
    Simply.may(Simply.anyOf("-. ")),             // Optional separator
    Simply.capture(Simply.digit(3)),             // 3 digits (exchange)
    Simply.may(Simply.anyOf("-. ")),             // Optional separator
    Simply.capture(Simply.digit(4)),             // 4 digits (line number)
    Simply.end()                                 // End of line
)

// Compile to regex string and test
let regexString = try phonePattern.compile()
let regex = try NSRegularExpression(pattern: regexString)
let testString = "555-123-4567"
let range = NSRange(testString.startIndex..., in: testString)
let match = regex.firstMatch(in: testString, range: range)
print(match != nil) // true
```

> **Note:** This compiles to the optimized regex: `^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$`

## 🚀 Why STRling?

Regular Expressions are powerful but notorious for being "write-only" code. STRling solves this by treating Regex as **Software**, not a string.

-   **🧩 Composability:** Regex strings are hard to merge. STRling lets you build reusable components (e.g., `ip_address`, `email`) and safely compose them into larger patterns without breaking operator precedence or capturing groups.
-   **🛡️ Type Safety:** Catch syntax errors, invalid ranges, and incompatible flags at **compile time** inside your IDE, not at runtime when your app crashes.
-   **🧠 IntelliSense & Autocomplete:** Stop memorizing cryptic codes like `(?<=...)`. Use fluent, self-documenting methods like `Simply.lookBehind(...)` with full IDE discovery.
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
-   [**Project Hub**](https://github.com/strling-lang/strling/blob/main/README.md): The main STRling repository.
-   [**Specification**](https://github.com/strling-lang/strling/tree/main/spec): The core grammar and semantic specifications.

## 🌐 Connect

[![GitHub](https://img.shields.io/badge/GitHub-black?logo=github&logoColor=white)](https://github.com/strling-lang)

## 💖 Support

If you find STRling useful, consider starring the repository and contributing!
