# STRling C Binding

This directory contains the C binding for STRling - a regex pattern compiler that transforms JSON AST representations into PCRE2-compatible regex patterns.

## Current Status

**Implementation Phase**: Minimal Viable Product (MVP)

The C binding currently provides:
- ✅ Public API definition (`include/strling.h`)
- ✅ Basic AST node structures (`src/core/nodes.[ch]`)
- ✅ IR node structures (`src/core/ir.[ch]`)
- ✅ Error handling (`src/core/errors.[ch]`)
- ✅ JSON AST parsing (using jansson)
- ✅ Basic PCRE2 pattern compilation for:
  - Literals
  - Anchors (Start/End)
  - Sequences
  - Dot (any character)
- ✅ Build system (Makefile)
- ✅ Basic integration test

## Building

### Prerequisites

- GCC or compatible C11 compiler
- jansson library (JSON parsing)
- cmocka library (for tests, optional)

On Ubuntu/Debian:
```bash
sudo apt-get install libjansson-dev libcmocka-dev
```

### Build the Library

```bash
make              # Build libstrling.a
make help         # Show all available targets
```

### Run Tests

```bash
make tests        # Build and run all tests
./tests/simple_test  # Run basic integration test
```

## API Overview

```c
#include <strling.h>

/* Compile JSON AST to PCRE2 pattern */
STRlingResult* result = strling_compile(json_string, flags);

if (result->error) {
    printf("Error: %s\n", result->error->message);
} else {
    printf("Pattern: %s\n", result->pattern);
}

strling_result_free(result);
```

## Test Suite Structure

### Specification Tests (`tests/unit/`, `tests/e2e/`)

The files in these directories are **specification documents** that define expected behavior using mock implementations. They:
- Demonstrate the intended API usage patterns
- Define expected outputs and error conditions
- Serve as documentation for implementers
- Are self-contained and test their own mock SUTs

**Note**: These specification tests cannot be run against the library directly as they contain their own implementations. They serve as the authoritative reference for what the library should do.

### Integration Tests (`tests/simple_test.c`)

Actual runnable tests that verify the library implementation:
- Test real API functions
- Verify JSON parsing and compilation
- Check error handling
- Validate output patterns

## Implementation Roadmap

### Completed ✅
- [x] Public API design
- [x] Core data structures (AST, IR, Error)
- [x] JSON parsing infrastructure
- [x] Basic node types (Literal, Anchor, Sequence, Dot)
- [x] Build system
- [x] Integration tests

### In Progress 🚧
- [ ] Character classes
- [ ] Quantifiers
- [ ] Groups and capturing
- [ ] Backreferences
- [ ] Lookarounds
- [ ] Alternation
- [ ] Escapes and Unicode support

### Planned 📋
- [ ] Complete PCRE2 emitter
- [ ] Flag handling (ignoreCase, multiline, etc.)
- [ ] Schema validation
- [ ] Comprehensive error messages
- [ ] Hint engine
- [ ] CLI integration
- [ ] Full test coverage (target: 581 tests)

## Architecture

```
bindings/c/
├── include/
│   └── strling.h          # Public API
├── src/
│   ├── strling.c          # API implementation
│   └── core/
│       ├── nodes.[ch]     # AST node definitions
│       ├── ir.[ch]        # IR node definitions
│       └── errors.[ch]    # Error handling
├── tests/
│   ├── simple_test.c      # Integration tests
│   ├── unit/              # Specification tests (doc)
│   └── e2e/               # E2E specification tests (doc)
└── Makefile
```

## Development

### Adding New Node Types

1. Define the node structure in `src/core/nodes.h`
2. Implement constructors/destructors in `src/core/nodes.c`
3. Add compilation logic in `compile_node_to_pcre2()` in `src/strling.c`
4. Add tests in `tests/simple_test.c`

### Testing

The simple test can be extended with new test cases:

```c
void test_my_feature() {
    const char* json = "{\"pattern\": {...}}";
    STRlingResult* result = strling_compile(json, NULL);
    assert(result->pattern != NULL);
    assert(strcmp(result->pattern, "expected") == 0);
    strling_result_free(result);
}
```

## Contributing

This implementation is part of the larger STRling project. See the root [README.md](../../README.md) for contribution guidelines.

## License

[See root LICENSE file]

## References

- [STRling Specification](../../spec/)
- [Python Implementation](../python/) (reference)
- [JavaScript Implementation](../javascript/) (reference)
