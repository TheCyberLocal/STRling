# STRling Rust Binding Architecture

## Overview

This directory contains the Rust implementation of STRling, following the same architectural principles and data structures as the Python and JavaScript bindings.

## Design Principles

1. **Idiomatic Rust**: Uses modern Rust idioms including enums with variants, pattern matching, and the type system for safety.
2. **Serialization**: All data structures support serialization via `serde` for JSON export/import.
3. **Error Handling**: Custom error types implement the `std::error::Error` trait for proper error propagation.
4. **Documentation**: Comprehensive doc comments using `///` for all public APIs.

## Module Structure

### `core` Module

The core module contains the foundational data structures:

- **`nodes.rs`**: Abstract Syntax Tree (AST) node definitions
  - Directly represents the parsed structure of STRling patterns
  - Mirrors the source syntax before optimization
  - All nodes implement `NodeTrait` for serialization

- **`ir.rs`**: Intermediate Representation (IR) node definitions
  - Language-agnostic regex constructs
  - Optimized for transformation and analysis
  - All nodes implement `IROpTrait` for serialization

- **`errors.rs`**: Error type definitions
  - `STRlingParseError`: Rich error with position tracking
  - Instructional hints for error resolution
  - LSP diagnostic support for IDE integration

## Type Design

### AST Nodes

AST nodes use Rust enums to represent different node types:

```rust
pub enum Node {
    Alt(Alt),
    Seq(Seq),
    Lit(Lit),
    // ... other variants
}
```

This provides:
- Type safety through the compiler
- Exhaustive pattern matching
- Clear variant discrimination

### IR Nodes

Similarly, IR nodes use enums:

```rust
pub enum IROp {
    Alt(IRAlt),
    Seq(IRSeq),
    // ... other variants
}
```

### Serialization

All nodes can be serialized to JSON via the `to_dict()` method, which returns a `serde_json::Value`:

```rust
let node = Node::Lit(Lit { value: "hello".to_string() });
let json = node.to_dict();
// {"kind": "Lit", "value": "hello"}
```

## Error Handling

The `STRlingParseError` provides:
- Position tracking (line and column)
- Context display (showing the error in the source)
- Instructional hints
- LSP diagnostic format support

Example:
```rust
let error = STRlingParseError::new(
    "Unexpected character".to_string(),
    5,
    "hello world".to_string(),
    Some("Did you mean to escape this?".to_string())
);
println!("{}", error);
```

## Future Development

### Parser (Task 2)
- Tokenization
- Recursive descent parsing
- AST construction

### Compiler (Task 2)
- AST to IR transformation
- Optimization passes

### Validator (Task 2)
- Semantic validation
- Error detection

### Emitters (Task 3)
- PCRE2 output
- Other regex flavors

## Testing Strategy

Tests will be organized as:
- Unit tests in `src/` files using `#[cfg(test)]` modules
- Integration tests in `tests/` directory
- Benchmarks in `benches/` directory

## Contributing

When adding new features:
1. Follow the existing code style and patterns
2. Add comprehensive documentation
3. Include unit tests
4. Update this documentation as needed
