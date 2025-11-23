# STRling - Go Binding

Part of the [STRling Project](../..).

## 📦 Installation

```bash
go get github.com/thecyberlocal/strling/bindings/go
```

## 🚀 Usage

```go
package main

import (
    "fmt"
    "github.com/thecyberlocal/strling/bindings/go/core"
    "github.com/thecyberlocal/strling/bindings/go/emitters"
)

func main() {
    // 1. Parse
    flags, ast, _ := core.Parse("hello")

    // 2. Compile
    compiler := core.NewCompiler()
    ir := compiler.Compile(ast)

    // 3. Emit
    regex := emitters.Emit(ir, flags)
    fmt.Println(regex)
}
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
