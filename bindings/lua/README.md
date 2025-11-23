# STRling - Lua Binding

Part of the [STRling Project](../..).

## 📦 Installation

```bash
luarocks install strling
```

## 🚀 Usage

```lua
local strling = require("strling")

-- Assuming input_ast is a table
local ir = strling.compile(input_ast)
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
