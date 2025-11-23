# STRling - TypeScript Binding

Part of the [STRling Project](../..).

## 📦 Installation

```bash
npm install @thecyberlocal/strling
```

## 🚀 Usage

```typescript
import { parse, Compiler } from "@thecyberlocal/strling";

// 1. Parse
const [flags, node] = parse("hello");

// 2. Compile
const compiler = new Compiler();
const ir = compiler.compile(node);

console.log(ir);
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
