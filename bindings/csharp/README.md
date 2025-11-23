# STRling - C# Binding

Part of the [STRling Project](../..).

## 📦 Installation

```bash
dotnet add package STRling
```

## 🚀 Usage

```csharp
using Strling.Core;

// 1. Parse
var (flags, ast) = Parser.Parse("hello");

// 2. Compile
var compiler = new Compiler();
var ir = compiler.Compile(ast);

Console.WriteLine(ir);
```

## 📚 Documentation

See the [API Reference](docs/api_reference.md) for detailed documentation.

## ✨ Features

*   **Clean Syntax**: Write regex in a readable, object-oriented way.
*   **Type Safety**: Catch errors at compile time (where applicable).
*   **Polyglot**: Consistent API across all supported languages.
*   **Standard Features**:
    *   Quantifiers (Greedy, Lazy)
    *   Groups (Capturing, Non-capturing, Named)
    *   Character Classes
    *   Anchors
    *   Lookarounds (Positive/Negative Lookahead/Lookbehind)
