# STRling - R Binding

Part of the [STRling Project](../..).

## 📦 Installation

```r
install.packages("strling")
```

## 🚀 Usage

```r
library(strling)

# Assuming input_ast is a list structure
ast <- hydrate_ast(input_ast)
ir <- compile_ast(ast)
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
