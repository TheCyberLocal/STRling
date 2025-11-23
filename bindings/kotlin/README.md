# STRling - Kotlin Binding

Part of the [STRling Project](../..).

## 📦 Installation

```kotlin
implementation("com.strling:strling:0.1.0")
```

## 🚀 Usage

```kotlin
import strling.core.Compiler
import strling.core.Node

// Assuming inputAst is a Node
val ir = Compiler.compile(inputAst)
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
