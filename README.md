# STRling

<table>
  <tr>
    <td style="padding: 10px;"><img src="https://raw.githubusercontent.com/strling-lang/.github/refs/heads/main/strling_silver_bell.png" alt="STRling Logo" /></td>
    <td style="padding: 10px;">
      <strong>The Universal Regular Expression Compiler.</strong><br><br>
      STRling is a next-generation production-grade syntax designed to make Regex readable, maintainable, and robust. It abstracts the cryptic nature of raw regex strings into a clean, object-oriented, and strictly typed interface that compiles to standard PCRE2 (or native) patterns.
    </td>
  </tr>
</table>

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

## ⚙️ Quick Start

Use the root CLI as the canonical setup and test entry point:

```bash
# Discover available bindings and current tool availability
./strling list

# Bootstrap every binding end-to-end
./strling bootstrap all

# Or target a single binding
./strling bootstrap python

# Re-run tests without reinstalling dependencies
./strling test all

# Run the established quality and certification aggregates
./strling check
./strling certify
```

The CLI will create the Python binding virtual environment automatically and will attempt best-effort prerequisite installation for missing language toolchains when the current package manager is supported.
See [Toolchains and Quality Commands](docs/toolchains.md) for governed versions,
component scoping, explicit incomplete capabilities, and JSON automation output.

## 📦 Distribution Channels

STRling supports multiple integration paths depending on the binding and ecosystem:

-   **Registry-Distributed:** Python on PyPI and TypeScript on npm.
-   **Git/Module-Delivered:** Go via `go get github.com/strling-lang/strling/bindings/go`.
-   **Source-Integrated / Manual Build:** C++, C, Rust, and Swift for teams integrating directly from repository source or binding-local build tooling.

## 📚 Documentation

-   [**Developer Documentation Hub**](docs/index.md): Architecture, testing standards, and contribution guidelines.
-   [**Toolchains and Quality Commands**](docs/toolchains.md): Canonical quality operations and deterministic environment policy.
-   [**Specification**](spec/README.md): The core grammar and semantic specifications.

## 🌐 Connect

[![GitHub](https://img.shields.io/badge/GitHub-black?logo=github&logoColor=white)](https://github.com/strling-lang)

## 💖 Support

If you find STRling useful, consider starring the repository and contributing!
