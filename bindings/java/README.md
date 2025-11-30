# STRling - Java Binding

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
cd bindings/java
mvn clean install
```

## 📦 Usage

Here is how to match a US Phone number (e.g., `555-0199`) using STRling in **Java**:

```java
import static com.strling.simply.Simply.*;

import com.strling.simply.Pattern;
import com.strling.simply.Simply;

// Build the phone pattern using the Simply fluent API
// Match: ^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$
Pattern phonePattern = merge(
    start(),                  // Start of line
    capture(digit(3)),        // 3 digits (area code)
    may(anyOf("-. ")),        // Optional separator
    capture(digit(3)),        // 3 digits (exchange)
    may(anyOf("-. ")),        // Optional separator
    capture(digit(4)),        // 4 digits (line number)
    end()                     // End of line
);

// Compile to regex string
Simply compiler = new Simply();
String regex = compiler.build(phonePattern);
System.out.println(regex);  // ^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$
```

> **Note:** This compiles to the optimized regex: `^(\d{3})[\-. ]?(\d{3})[\-. ]?(\d{4})$`

### Zero Boilerplate

The Simply API eliminates verbose constructor calls. Compare the old verbose style:

```java
// ❌ Old verbose style (NOT recommended)
Nodes.Node phoneAst = new Nodes.Seq(List.of(
  new Nodes.Anchor("Start"),
  new Nodes.Group(true, new Nodes.Quant(
    new Nodes.CharClass(false, List.of(new Nodes.ClassEscape("d"))),
    3, 3, "Greedy"
  )),
  // ... many more lines
));
```

With the modern fluent API:

```java
// ✅ Modern fluent style (recommended)
Pattern phonePattern = merge(
    start(),
    capture(digit(3)),
    may(anyOf("-", ".", " ")),
    capture(digit(3)),
    may(anyOf("-", ".", " ")),
    capture(digit(4)),
    end()
);
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
