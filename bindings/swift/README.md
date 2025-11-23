# STRling - Swift Binding

Part of the [STRling Project](../..).

## 📦 Installation

```swift
.package(url: "https://github.com/TheCyberLocal/STRling.git", from: "0.1.0")
```

## 🚀 Usage

```swift
import STRling

let compiler = Compiler()
// Assuming input_ast is a Node
let ir = try compiler.compile(node: input_ast)
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
