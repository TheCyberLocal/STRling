# STRling Go Binding Documentation

This directory will contain documentation specific to the Go binding of STRling.

## Current Status

The Go binding is currently in development. The following components have been implemented:

### Core Architecture (Task 1 - Completed)

- **Module Structure**: Go module initialized at `github.com/thecyberlocal/strling/bindings/go`
- **Core Data Structures**: Complete port of foundational types from Python binding
  - `core/nodes.go`: AST node definitions
  - `core/ir.go`: Intermediate representation nodes
  - `core/errors.go`: Rich error handling with STRlingParseError

### Pending Implementation

- **Task 2**: Parser, Compiler, and comprehensive testing
- **Task 3**: CI/CD pipeline integration
- **Future Tasks**: Additional features and optimizations

## Package Structure

```
bindings/go/
├── strling.go          # Main public API
├── strling_test.go     # Test suite (native Go testing)
├── core/               # Core compiler components
│   ├── nodes.go        # AST node definitions
│   ├── ir.go           # IR node definitions
│   └── errors.go       # Error types and formatting
└── docs/               # Documentation (this directory)
```

## Development Notes

The Go binding follows idiomatic Go patterns:
- Interfaces for polymorphic behavior (Node, IROp)
- Exported types use PascalCase
- Comprehensive documentation comments
- Native Go error handling with the error interface

All code is fully documented with comments ported from the normative Python implementation.
