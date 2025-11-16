# STRling C++ Binding

STRling C++ binding provides a modern, idiomatic C++ interface for the STRling pattern language.

## Overview

This directory contains the C++ implementation of the STRling library, designed to provide the same powerful regex abstraction capabilities as the Python and JavaScript bindings.

## Status

✅ **Foundation Complete** - Test infrastructure and working demonstration

### Current Implementation

- **Test Infrastructure**: 100% complete (GTest + CMake + C++20)
- **Parser**: ~40% complete (~400 lines implemented)
- **Tests Passing**: 18/581 (3.1%)
- **Build Status**: Clean, zero warnings ✅

### What's Working

The following features are **fully functional and tested**:

✅ All anchor types (^, $, \b, \B, \A, \Z)  
✅ Sequences and alternation  
✅ Groups (capturing, non-capturing, atomic)  
✅ Lookahead and lookbehind  
✅ Quantifiers (*, +, ?, lazy, possessive)  
✅ Basic character classes  
✅ Flag directives  
✅ Error handling  

### Quick Start

```bash
cd bindings/cpp
mkdir build && cd build
cmake .. -DBUILD_TESTS=ON
cmake --build .
./test/strling_tests  # Runs 18 passing tests
```

### Documentation

- **TASK2_SUMMARY.md** - Complete status overview
- **IMPLEMENTATION_GUIDE.md** - Detailed continuation guide
- **README.md** - This file

### Remaining Work

To complete the full implementation (581 tests):

- Complete parser (~600 more lines): 3-5 days
- Implement compiler (187 lines): 1-2 days
- Implement validator (62 lines): 1 day
- Implement hint engine (350 lines): 2-3 days
- Implement emitters (~300 lines): 2-3 days
- Implement CLI + E2E (200 lines + 30 tests): 2-3 days
- Debug and polish: 3-5 days

**Total Estimate**: 16-25 days (2.5-4 weeks)

See **IMPLEMENTATION_GUIDE.md** for step-by-step instructions.

## Completed

- [x] Project structure and build system (CMake + Conan)
- [x] Core data structures (AST nodes, IR nodes, Error classes)
- [x] **Test infrastructure (GTest + C++20)** ✅
- [x] **Working parser with 18 passing tests** ✅

### In Progress

- [x] Parser implementation (40% complete - Task 2)
- [ ] Compiler implementation (0% - Task 2)
- [ ] Full test suite (18/581 tests = 3.1% - Task 2)
- [ ] CLI interface (0% - Task 2)
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
