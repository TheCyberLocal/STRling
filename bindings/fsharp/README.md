# STRling - F# Binding

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

Install via NuGet:

```bash
dotnet add package STRling.FSharp
```

## 📦 Usage

> **Migration status:** this README describes the historical F# package surface.
> Its local parser/compiler output is compatibility evidence, not the canonical
> STRling 4.0 compiler boundary.

### Historical Simply API

Here is how to match a US Phone number (e.g., `555-0199`) using STRling's **Simply API** in **F#**:

```fsharp
open STRling.Simply

// Build a US phone number pattern: ^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$
let phone =
    merge [
        start ()
        capture (digit 3)
        may (anyOf "-. ")
        capture (digit 3)
        may (anyOf "-. ")
        capture (digit 4)
        end' ()
    ]

// Historical package-local compatibility output
let regex = phone |> compile
printfn "%s" regex
// Output: ^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$
```

### Textual authoring

Semantic STRling is the flagship textual language. The historical F# string
parser does not implement `strling.semantic@1.0.0`, so its former builder-like
string example is intentionally omitted. Use the Simply API above for
programmatic intent; use the canonical Semantic frontend through the repository
kernel until the F# adapter migration is complete. Regex-compatible text is an
import/compatibility surface, not Semantic STRling.

## 🚀 Why STRling?

Regular Expressions are powerful but notorious for being "write-only" code. STRling solves this by treating Regex as **Software**, not a string.

-   **🧩 Composability:** Regex strings are hard to merge. STRling lets you build reusable components (e.g., `ip_address`, `email`) and safely compose them into larger patterns without breaking operator precedence or capturing groups.
-   **🛡️ Type Safety:** Catch syntax errors, invalid ranges, and incompatible flags at **compile time** inside your IDE, not at runtime when your app crashes.
-   **🧠 IntelliSense & Autocomplete:** Stop memorizing cryptic codes like `(?<=...)`. Use fluent, self-documenting methods like `simply.lookBehind(...)` with full IDE discovery.
-   **📖 Readability First:** Code is read far more often than it is written. STRling patterns describe _intent_, making them understandable to junior developers and future maintainers instantly.
-   **🌍 Shared semantics:** Host APIs may be idiomatic, while equivalent requests converge through one canonical semantic model.

## 🏗️ Architecture

STRling 4.0 uses one canonical pipeline: Semantic STRling, Simply requests, and
explicit regex-compatible imports lower to canonical Semantic IR; the Rust
kernel performs semantic analysis, portability planning, and target emission
under an exact profile. Host bindings are adapters that serialize requests and
preserve canonical results and structured diagnostics. Until this binding is
migrated to that adapter boundary, its local compiler remains historical
compatibility behavior only.

## 📚 Documentation

-   [**API Reference**](./docs/api_reference.md): Detailed documentation for this binding.
-   [**Project Hub**](https://github.com/strling-lang/strling/blob/main/README.md): The main STRling repository.
-   [**Specification**](https://github.com/strling-lang/strling/tree/main/spec): The core grammar and semantic specifications.

## 🌐 Connect

[![GitHub](https://img.shields.io/badge/GitHub-black?logo=github&logoColor=white)](https://github.com/strling-lang)

## 💖 Support

If you find STRling useful, consider starring the repository and contributing!
