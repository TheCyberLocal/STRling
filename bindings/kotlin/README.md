# STRling - Kotlin Binding

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

Add STRling as a Gradle dependency (Kotlin DSL):

```kotlin
repositories {
    mavenCentral()
}

dependencies {
    // artifact coordinates (group:artifact:version)
    implementation("com.strling:strling-kotlin:3.0.0")
}
```

## 📦 Usage

> **Migration status:** this README describes the historical Kotlin package
> surface. Its local parser/compiler output is compatibility evidence, not the
> canonical STRling 4.0 compiler boundary.

Here is how to match a US Phone number (e.g., `555-0199`) using STRling's **Simply API** in Kotlin:

```kotlin
import strling.Simply

// Build a US phone number pattern: ^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$
// Start of line
// Match the area code (3 digits, captured)
// Optional separator: [-. ]
// Match the central office code (3 digits, captured)
// Optional separator: [-. ]
// Match the station number (4 digits, captured)
// End of line
val phonePattern = Simply.merge(
    Simply.start(),
    Simply.capture(Simply.digit(3)),
    Simply.may(Simply.anyOf("-. ")),
    Simply.capture(Simply.digit(3)),
    Simply.may(Simply.anyOf("-. ")),
    Simply.capture(Simply.digit(4)),
    Simply.end()
)

// `phonePattern` belongs to the historical package-local model. Its emitted
// regex is compatibility output until this binding uses the canonical adapter.
```

### Textual authoring

Semantic STRling is the flagship textual language. The historical Kotlin string
parser does not implement `strling.semantic@1.0.0`, so its former builder-like
string example is intentionally omitted. Use the Simply API above for
programmatic intent; use the canonical Semantic frontend through the repository
kernel until the Kotlin adapter migration is complete. Regex-compatible text is
an import/compatibility surface, not Semantic STRling.

### Simply API Features

The Simply API provides a fluent, chainable interface for building regex patterns:

**Static Patterns:**

```kotlin
Simply.start()        // Start anchor (^)
Simply.end()          // End anchor ($)
Simply.digit(3)       // Exactly 3 digits
Simply.letter(2, 5)   // 2 to 5 letters
Simply.alphaNum()     // Single alphanumeric character
Simply.whitespace()   // Single whitespace character
Simply.literal("abc") // Literal text
```

**Character Sets:**

```kotlin
Simply.between('a', 'z')  // Lowercase letters
Simply.between(0, 9)      // Digits
Simply.anyOf("-. ")       // Any of: -, ., or space
```

**Constructors:**

```kotlin
Simply.merge(p1, p2, p3)  // Concatenate patterns
Simply.may(p1)            // Optional pattern (0 or 1)
Simply.capture(p1)        // Numbered capture group
Simply.group("name", p1)  // Named capture group
Simply.anyOf(p1, p2)      // Alternation (p1 OR p2)
```

**Fluent Methods:**

```kotlin
pattern.may()             // Make pattern optional
pattern.repeat(2, 5)      // Repeat 2-5 times
pattern.asCapture()       // Wrap in capture group
pattern.asGroup("name")   // Wrap in named group
pattern.lazy()            // Make quantifier lazy (non-greedy)
```

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
