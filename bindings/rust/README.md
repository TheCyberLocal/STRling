# STRling for Rust

[![Crates.io](https://img.shields.io/crates/v/strling_core)](https://crates.io/crates/strling_core)
[![Documentation](https://docs.rs/strling_core/badge.svg)](https://docs.rs/strling_core)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

STRling is a next-generation string pattern DSL and compiler for Rust. It provides a readable, beginner-friendly syntax for creating powerful regular expressions with instructional error handling.

## 🚀 Quick Start

Add this to your `Cargo.toml`:

```toml
[dependencies]
strling_core = "3.0.0-alpha"
```

## 📦 Project Structure

This Rust binding follows the same architectural principles as the Python and JavaScript bindings:

```
bindings/rust/
├── Cargo.toml           # Package manifest
├── src/
│   ├── lib.rs          # Main library entry point
│   └── core/           # Core data structures
│       ├── mod.rs      # Core module declaration
│       ├── nodes.rs    # AST node definitions
│       ├── ir.rs       # IR node definitions
│       └── errors.rs   # Error types
├── tests/              # Integration tests
└── docs/               # Documentation
```

## 🏗️ Status

This is an **alpha release**. The core data structures (AST nodes, IR nodes, and error types) have been ported from the normative Python binding. The Parser, Compiler, and Validator are not yet implemented.

### Implemented
- ✅ AST Node Definitions (`nodes.rs`)
- ✅ IR Node Definitions (`ir.rs`)
- ✅ Error Types (`errors.rs`)
- ✅ Serialization support via `serde`

### Planned
- ⏳ Parser
- ⏳ Compiler
- ⏳ Validator
- ⏳ Emitters (PCRE2, etc.)

## 🧪 Development

Build the project:
```bash
cargo build
```

Run tests:
```bash
cargo test
```

Run benchmarks:
```bash
cargo bench
```

Generate documentation:
```bash
cargo doc --open
```

## 📚 Documentation

For complete documentation on the STRling DSL and architecture, see the [main documentation](../../docs/index.md).

## 🌐 Other Bindings

- [Python](../python/README.md)
- [JavaScript](../javascript/README.md)

## 📝 License

MIT © TheCyberLocal
