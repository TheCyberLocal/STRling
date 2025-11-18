# C++ Binding Implementation Guide

## Overview

This guide documents the partial implementation of Task 2: Full Test Suite Porting and Core Logic Implementation. It provides context for continuing the work.

## Current Status

### ✅ Completed (Phase 1)
- **Test Infrastructure**: Full GTest integration with CMake
- **Directory Structure**: All necessary directories created
- **Build System**: C++20 support, automatic dependency fetching
- **Working Demonstration**: 18 passing tests from anchors.test.ts

### Test Progress
- **Current**: 18 tests passing
- **Target**: 581 tests (from JavaScript binding)
- **Completion**: 3.1%

### Code Progress
- **Parser**: ~400 lines implemented (~40% complete)
- **Compiler**: Not started (need 187 lines from Python)
- **Validator**: Not started (need 62 lines from Python)
- **Hint Engine**: Not started (need 350 lines from Python)
- **Emitters**: Not started
- **CLI**: Not started

## Architecture

### Files Created

```
bindings/cpp/
├── include/strling/core/
│   └── parser.hpp          ✅ Complete API definition
├── src/core/
│   └── parser.cpp          ⚠️  Partial implementation (~40%)
├── test/
│   ├── CMakeLists.txt      ✅ Full GTest setup
│   └── unit/
│       └── anchors_test.cpp ⚠️  18/31 tests (58%)
└── CMakeLists.txt          ✅ Updated for C++20
```

### Dependencies
- **Google Test v1.14.0**: Auto-fetched by CMake
- **nlohmann/json v3.11.3**: Auto-fetched for CLI/JSON needs

## Implementation Pattern

### Test Porting Pattern

JavaScript test:
```javascript
test("should parse anchor", () => {
    const [, ast] = parse("^");
    expect(ast).toBeInstanceOf(Anchor);
    expect((ast as Anchor).at).toBe("Start");
});
```

C++ equivalent:
```cpp
TEST(TestSuite, TestName) {
    auto [flags, ast] = parse("^");
    Anchor* anchor = dynamic_cast<Anchor*>(ast.get());
    ASSERT_NE(anchor, nullptr);
    EXPECT_EQ(anchor->at, "Start");
}
```

### Key Differences
- Use `auto [flags, ast]` for structured bindings
- Use `dynamic_cast` instead of `instanceof`
- Use `ASSERT_NE` for null checks before `EXPECT_EQ`
- Use raw string literals `R"(...)"` for strings with backslashes
- GTest `EXPECT_THROW` takes only 2 args (statement, exception type)

## Parser Implementation

### What's Implemented

✅ **Core Parsing**
- Cursor with position tracking
- Directive parsing (%flags)
- Alternation (`|`)
- Sequences (concatenation)
- Atoms (literals, anchors, etc.)

✅ **Anchors**
- Line anchors: `^`, `$`
- Word boundaries: `\b`, `\B`
- Absolute anchors: `\A`, `\Z`
- Error handling for quantified anchors

✅ **Groups**
- Capturing: `(...)`
- Non-capturing: `(?:...)`
- Atomic: `(?>...)`
- Lookahead: `(?=...)`, `(?!...)`
- Lookbehind: `(?<=...)`, `(?<!...)`

✅ **Quantifiers**
- Basic: `*`, `+`, `?`
- Modes: greedy, lazy (`?`), possessive (`+`)
- Error handling for invalid quantifiers

⚠️ **Partial**
- Character classes `[...]` (basic support)
- Escape sequences (basic support)
- Literal parsing

❌ **Not Implemented**
- Named groups `(?<name>...)`
- Range quantifiers `{m,n}`
- Unicode escapes `\p{...}`, `\P{...}`
- Comprehensive escape handling
- Full character class features

### Parser Methods Reference

```cpp
class Parser {
    NodePtr parse();              // Main entry point
    NodePtr parse_alt();          // Alternation |
    NodePtr parse_seq();          // Sequence (concatenation)
    NodePtr parse_atom();         // Single atom
    NodePtr parse_anchor();       // ^, $, \b, etc.
    NodePtr parse_group();        // (...) and variants
    NodePtr parse_class();        // [...]
    NodePtr parse_literal();      // Literals and escapes
    NodePtr parse_escape();       // \n, \d, etc.
    NodePtr parse_quantifier();   // *, +, ?, {m,n}
};
```

## Test Suite Breakdown

### Unit Tests (14 files, ~551 tests)

| File | Tests | Status | Priority |
|------|-------|--------|----------|
| anchors.test.ts | 31 | 18/31 (58%) | Continue |
| char_classes.test.ts | 31 | 0 | Next |
| quantifiers.test.ts | 29 | 0 | High |
| literals_and_escapes.test.ts | 35 | 0 | High |
| groups_backrefs_lookarounds.test.ts | 39 | 0 | Medium |
| flags_and_free_spacing.test.ts | 7 | 0 | Low |
| errors.test.ts | 10 | 0 | Medium |
| parser_errors.test.ts | 24 | 0 | Medium |
| error_formatting.test.ts | 14 | 0 | Low |
| schema_validation.test.ts | 8 | 0 | Low |
| ir_compiler.test.ts | 37 | 0 | High |
| emitter_edges.test.ts | 21 | 0 | High |
| ieh_audit_gaps.test.ts | 33 | 0 | Medium |
| simply_api.test.ts | 81 | 0 | High |

### E2E Tests (3 files, ~30 tests)

| File | Tests | Status | Requires |
|------|-------|--------|----------|
| pcre2_emitter.test.ts | 10 | 0 | Emitter + CLI |
| e2e_combinatorial.test.ts | 11 | 0 | Full stack |
| cli_smoke.test.ts | 9 | 0 | CLI interface |

## Next Steps Guide

### Step 1: Complete Anchors (13 remaining tests)

Review `bindings/javascript/__tests__/unit/anchors.test.ts` lines 217-535 for:
- Category E: Anchors in Complex Sequences (4 tests)
- Category F: Anchors in Alternation (3 tests)
- Category G: Anchors in Atomic Groups (3 tests)
- Category H: Word Boundary Edge Cases (3 tests)

Add these to `test/unit/anchors_test.cpp` following the existing pattern.

### Step 2: Port Character Classes

Create `test/unit/char_classes_test.cpp`:
```cpp
#include <gtest/gtest.h>
#include "strling/core/parser.hpp"
#include "strling/core/nodes.hpp"

using namespace strling::core;

TEST(CharClassesPositive, ParseSimpleClass) {
    auto [flags, ast] = parse("[abc]");
    CharClass* cc = dynamic_cast<CharClass*>(ast.get());
    ASSERT_NE(cc, nullptr);
    EXPECT_FALSE(cc->negated);
    EXPECT_EQ(cc->items.size(), 3);
}
// ... more tests
```

Review source: `bindings/javascript/__tests__/unit/char_classes.test.ts`

Enhance `Parser::parse_class()` to handle:
- Ranges: `[a-z]`, `[0-9]`
- Negation: `[^abc]`
- Escapes: `[\n\t]`, `[\d\w\s]`
- Special chars: `[-]`, `[]]`, `[^]`
- Nested brackets

### Step 3: Port Quantifiers

Create `test/unit/quantifiers_test.cpp`

Enhance `Parser::parse_quantifier()` to handle:
- Range quantifiers: `{3}`, `{2,5}`, `{3,}`
- Edge cases: `{0,0}`, `{0,1}` vs `?`
- Invalid patterns: `{,5}`, `{5,2}`

Reference: `bindings/python/src/STRling/core/parser.py` lines 600-700 (approx)

### Step 4: Implement Compiler

Create `include/strling/core/compiler.hpp` and `src/core/compiler.cpp`

Port from: `bindings/python/src/STRling/core/compiler.py`

Key methods:
```cpp
class Compiler {
    dict compile_with_metadata(NodePtr root);
    IROp _lower(NodePtr node);      // AST -> IR
    IROp _normalize(IROp ir);       // Optimize IR
    void _analyze_features(IROp ir); // Detect features
};
```

Create `test/unit/ir_compiler_test.cpp` to test compilation.

### Step 5: Implement Emitters

Create `include/strling/emitters/pcre2.hpp` and `src/emitters/pcre2.cpp`

Port from: `bindings/python/src/STRling/emitters/pcre2.py`

Test with: `test/e2e/pcre2_emitter_test.cpp`

### Step 6: Implement CLI

Create `src/strling_cli/main.cpp`:
```cpp
#include <iostream>
#include <nlohmann/json.hpp>
#include "strling/core/parser.hpp"
#include "strling/core/compiler.hpp"
#include "strling/emitters/pcre2.hpp"

int main(int argc, char** argv) {
    // Parse args
    // Read pattern
    // Emit diagnostics as JSON (LSP format)
    return 0;
}
```

Reference: `bindings/python/src/STRling/cli_server.py`

Add to CMakeLists.txt:
```cmake
add_executable(strling_cli src/strling_cli/main.cpp)
target_link_libraries(strling_cli PRIVATE strling nlohmann_json::nlohmann_json)
```

## Building and Testing

### Build with Tests
```bash
cd bindings/cpp
rm -rf build
mkdir build && cd build
cmake .. -DBUILD_TESTS=ON
cmake --build .
```

### Run Tests
```bash
# All tests
./test/strling_tests

# With CTest
ctest --verbose

# Single test suite
./test/strling_tests --gtest_filter=AnchorsPositive.*

# Count passing tests
./test/strling_tests --gtest_list_tests | wc -l
```

### Debug Build
```bash
cmake .. -DBUILD_TESTS=ON -DCMAKE_BUILD_TYPE=Debug
cmake --build .
```

## Reference Documentation

### JavaScript Test Suite
- Location: `bindings/javascript/__tests__/`
- Run with: `cd bindings/javascript && npm test`
- Total: 581 tests across 17 files

### Python Implementation (Reference)
- Parser: `bindings/python/src/STRling/core/parser.py` (1,035 lines)
- Compiler: `bindings/python/src/STRling/core/compiler.py` (187 lines)
- Validator: `bindings/python/src/STRling/core/validator.py` (62 lines)
- Hint Engine: `bindings/python/src/STRling/core/hint_engine.py` (350 lines)
- Errors: `bindings/python/src/STRling/core/errors.py` (190 lines)
- CLI: `bindings/python/src/STRling/cli_server.py` (200 lines)

### Existing C++ Infrastructure
- Nodes: `include/strling/core/nodes.hpp` ✅ Complete
- IR: `include/strling/core/ir.hpp` ✅ Complete
- Errors: `include/strling/core/strling_parse_error.hpp` ✅ Complete

## Common Pitfalls

1. **Constructor Order**: C++ constructors must match header order exactly
2. **Dynamic Cast**: Always check result before use: `ASSERT_NE(ptr, nullptr)`
3. **Move Semantics**: Use `std::move()` for `unique_ptr` transfers
4. **Raw Strings**: Use `R"(...)"` for patterns with backslashes
5. **GTest Macros**: `EXPECT_THROW` is 2 args, not 3 like try-catch
6. **Optional**: Use `std::optional<>` for optional fields, not null pointers

## Estimated Effort

| Phase | Lines of Code | Tests | Time Estimate |
|-------|---------------|-------|---------------|
| Complete Parser | ~600 more | ~300 tests | 3-5 days |
| Compiler | ~200 | ~40 tests | 1-2 days |
| Validator | ~80 | ~20 tests | 1 day |
| Hint Engine | ~400 | ~50 tests | 2-3 days |
| Emitters | ~300 | ~30 tests | 2-3 days |
| CLI + E2E | ~200 | ~100 tests | 2-3 days |
| **Total** | **~1,780** | **~540** | **11-17 days** |

*Plus 3-5 days for debugging, polish, and test fixes = **2-3 weeks total***

## Success Criteria

From the original task requirements:

- [x] Test framework integrated (GTest)
- [x] Core logic files created (parser.cpp, etc.)
- [ ] strling_cli executable implemented
- [ ] All unit tests pass (currently 18/551)
- [ ] All E2E tests pass (currently 0/30)
- [ ] **Test Parity**: 581 tests match JavaScript count
- [ ] All code properly commented with Doxygen

## Contact / Questions

If continuing this work, review:
1. This guide for context
2. Python implementation for reference logic
3. JavaScript tests for expected behavior
4. Existing passing tests for C++ patterns

The infrastructure is solid and the pattern is clear. It's primarily a matter of:
1. Porting test cases one file at a time
2. Enhancing parser/compiler to pass those tests
3. Repeating until complete
