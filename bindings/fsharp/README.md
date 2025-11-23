# STRling - F# Binding

Part of the [STRling Project](../..).

## 📦 Installation

```bash
dotnet add package STRling
```

## 🚀 Usage

```fsharp
open STRling

// Assuming inputAst is a Node
let ir = Compiler.compile inputAst
```

## 📚 Documentation

See the [API Reference](docs/api_reference.md) for detailed documentation.

## ✨ Features

-   **Clean Syntax**: Write regex in a readable, object-oriented way.
-   **Type Safety**: Catch errors at compile time (where applicable).
-   **Polyglot**: Consistent API across all supported languages.
-   **Standard Features**:
    -   Quantifiers (Greedy, Lazy)
    -   Groups (Capturing, Non-capturing, Named)
    -   Character Classes
    -   Anchors
    -   Lookarounds (Positive/Negative Lookahead/Lookbehind)
