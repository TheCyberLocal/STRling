# STRling - Rust Binding

Part of the [STRling Project](../..).

## 📦 Installation

```bash
cargo add strling_core
```

## 🚀 Usage

```rust
use strling_core::parse;
use strling_core::core::compiler::Compiler;
use strling_core::emitters::pcre2::PCRE2Emitter;

fn main() {
    // 1. Parse
    let (flags, ast) = parse("hello").unwrap();

    // 2. Compile
    let mut compiler = Compiler::new();
    let result = compiler.compile_with_metadata(&ast);

    // 3. Emit
    let emitter = PCRE2Emitter::new(flags);
    println!("{}", emitter.emit(&result.ir));
}
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
