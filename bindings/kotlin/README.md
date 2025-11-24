# STRling - Kotlin Binding

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

Add STRling as a Gradle dependency (Kotlin DSL):

```kotlin
repositories {
    mavenCentral()
}

dependencies {
    // artifact coordinates (group:artifact:version)
    implementation("com.strling:strling-kotlin:3.0.0-alpha")
}
```

## 📦 Usage

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

// `phonePattern` is a Pattern object wrapping a STRling AST node.
// Use the binding's compiler/emitter to convert the AST into a target
// regex string (PCRE2 / Kotlin/JVM compatible) before using it with
// Kotlin's Regex class at runtime.
```

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
pattern.optional()        // Make pattern optional
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
