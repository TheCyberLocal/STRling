# STRling C++ Binding

STRling C++ binding provides a modern, idiomatic C++ interface for the STRling pattern language.

## Overview

This directory contains the C++ implementation of the STRling library, designed to provide the same powerful regex abstraction capabilities as the Python and JavaScript bindings.

## Status

⚠️ **Work in Progress** - This binding is currently under development.

### Completed

- [x] Project structure and build system (CMake + Conan)
- [x] Core data structures (AST nodes, IR nodes, Error classes)

### In Progress

- [ ] Parser implementation (Task 2)
- [ ] Compiler implementation (Task 2)
- [ ] Test suite with GTest (Task 2)
- [ ] CI/CD integration (Task 3)

## Building

### Prerequisites

- CMake 3.15 or higher
- C++17 compatible compiler (GCC 7+, Clang 5+, MSVC 2017+)
- Conan package manager (optional, for dependency management)

### Build with CMake

```bash
mkdir build
cd build
cmake ..
cmake --build .
```

### Build with Conan

```bash
conan install . --build=missing
conan build .
```

### Build with Tests

```bash
mkdir build
cd build
cmake .. -DBUILD_TESTS=ON
cmake --build .
ctest
```

## Project Structure

```
bindings/cpp/
├── CMakeLists.txt          # Root CMake build configuration
├── conanfile.py            # Conan package recipe
├── include/strling/        # Public headers
│   ├── strling.hpp         # Main API header
│   └── core/               # Core module headers
│       ├── nodes.hpp       # AST node definitions
│       ├── ir.hpp          # IR node definitions
│       └── strling_parse_error.hpp  # Error classes
├── src/core/               # Implementation files
│   ├── nodes.cpp           # AST node implementations
│   ├── ir.cpp              # IR node implementations
│   └── strling_parse_error.cpp      # Error class implementations
├── test/                   # Test suite (GTest)
└── docs/                   # Documentation
```

## Architecture

The C++ binding follows the same architecture as the Python and JavaScript bindings:

1. **Parser**: Parses STRling pattern syntax into an Abstract Syntax Tree (AST)
2. **AST Nodes**: Represent the syntactic structure of patterns
3. **Compiler**: Transforms AST into Intermediate Representation (IR)
4. **IR Nodes**: Language-agnostic representation of regex operations
5. **Emitters**: Convert IR to target regex flavors (e.g., PCRE2)

## Usage (Coming Soon)

```cpp
#include <strling/strling.hpp>

int main() {
    // Example usage will be added in Task 2
    return 0;
}
```

## Contributing

See the main [Developer Documentation](../../docs/index.md) for contribution guidelines.

## License

MIT License - See LICENSE file for details
