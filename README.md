# STRling Project Overview

<table>
  <tr>
    <td style="padding: 10px;"><img src="./strling_logo.jpg" alt="" /></td>
    <td style="padding: 10px;">
      <strong>A universal, polyglot regular expression compiler.</strong><br><br>
      STRling is a next-generation production-grade syntax designed as a user interface for writing powerful regular expressions (RegEx) with an object-oriented approach and instructional error handling. It abstracts the cryptic nature of raw regex into a clean, readable, and powerful interface, maintaining full compatibility with standard regex engines.
    </td>
  </tr>
</table>

## 🏗️ Architecture

STRling follows a strict compiler pipeline architecture to ensure consistency across all languages:

1.  **Parse**: `DSL -> AST` (Abstract Syntax Tree)
    -   Converts the human-readable STRling syntax into a structured tree.
2.  **Compile**: `AST -> IR` (Intermediate Representation)
    -   Transforms the AST into a target-agnostic intermediate representation.
3.  **Emit**: `IR -> Target Regex`
    -   Generates the final regex string for the specific target engine (e.g., PCRE2, JS, Python re).

## 🌍 Language Bindings

STRling is available in **17 languages**. Select a binding to view installation and usage instructions.

| Language       | Binding                                              | Status         |
| :------------- | :--------------------------------------------------- | :------------- |
| **C**          | [bindings/c](bindings/c/README.md)                   | 🚧 Development |
| **C++**        | [bindings/cpp](bindings/cpp/README.md)               | 🚧 Development |
| **C#**         | [bindings/csharp](bindings/csharp/README.md)         | 🚧 Development |
| **Dart**       | [bindings/dart](bindings/dart/README.md)             | 🚧 Development |
| **F#**         | [bindings/fsharp](bindings/fsharp/README.md)         | 🚧 Development |
| **Go**         | [bindings/go](bindings/go/README.md)                 | 🚧 Development |
| **Java**       | [bindings/java](bindings/java/README.md)             | 🚧 Development |
| **Kotlin**     | [bindings/kotlin](bindings/kotlin/README.md)         | 🚧 Development |
| **Lua**        | [bindings/lua](bindings/lua/README.md)               | 🚧 Development |
| **Perl**       | [bindings/perl](bindings/perl/README.md)             | 🚧 Development |
| **PHP**        | [bindings/php](bindings/php/README.md)               | 🚧 Development |
| **Python**     | [bindings/python](bindings/python/README.md)         | ✅ Stable      |
| **R**          | [bindings/r](bindings/r/README.md)                   | 🚧 Development |
| **Ruby**       | [bindings/ruby](bindings/ruby/README.md)             | 🚧 Development |
| **Rust**       | [bindings/rust](bindings/rust/README.md)             | 🧪 Alpha       |
| **Swift**      | [bindings/swift](bindings/swift/README.md)           | 🚧 Development |
| **TypeScript** | [bindings/typescript](bindings/typescript/README.md) | ✅ Stable      |

## 📚 Documentation

-   [**Developer Documentation Hub**](docs/index.md): Architecture, testing standards, and contribution guidelines.
-   [**Specification**](spec/README.md): The core grammar and semantic specifications.
-   [**Release Process**](docs/releasing.md): How to release new versions.
-   [**Contributing**](CONTRIBUTING.md): How to get involved.

## 🌐 Socials

[![LinkedIn](https://img.shields.io/badge/LinkedIn-%230077B5.svg?logo=linkedin&logoColor=white)](https://linkedin.com/in/tzm01)
[![GitHub](https://img.shields.io/badge/GitHub-black?logo=github&logoColor=white)](https://github.com/TheCyberLocal)
[![PyPI](https://img.shields.io/badge/PyPI-3776AB?logo=pypi&logoColor=white)](https://pypi.org/user/TheCyberLocal/)
[![npm](https://img.shields.io/badge/npm-%23FFFFFF.svg?logo=npm&logoColor=D00000)](https://www.npmjs.com/~thecyberlocal)

## 💖 Support

If you find STRling useful, consider [buying me a coffee](https://buymeacoffee.com/thecyberlocal).
