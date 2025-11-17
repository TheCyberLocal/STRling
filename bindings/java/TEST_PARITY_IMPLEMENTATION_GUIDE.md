# Java Test Suite Parity Implementation Guide

## Current Status (As of 2025-11-17)

### Overall Progress
- **Target**: 581 tests (matching JavaScript SSOT)
- **Current**: 306 tests
- **Remaining**: 275 tests (53% complete)

### Completed Files (12/17 files - 71% file parity)

#### E2E Tests (100% Complete)
- ✅ **CliSmokeTest**: 6/6 tests
- ✅ **E2ECombinatorialTest**: 90/90 tests
- ✅ **PCRE2EmitterTest**: 20/20 tests

#### Unit Tests (100% Complete)
- ✅ **AnchorsTest**: 34/34 tests
- ✅ **CompilerTest**: 40/40 tests *(recently completed)*
- ✅ **EmitterEdgesTest**: 36/36 tests
- ✅ **ErrorFormattingTest**: 11/11 tests
- ✅ **ErrorsTest**: 20/20 tests
- ✅ **FlagsAndFreeSpacingTest**: 15/15 tests
- ✅ **IehAuditGapsTest**: 23/23 tests
- ✅ **ParserErrorsTest**: 20/20 tests
- ✅ **ValidatorTest** (schema_validation): 10/10 tests

### Files Requiring Implementation (5 files, 275 tests)

| File | Current | Target | Gap | Priority |
|------|---------|--------|-----|----------|
| QuantifiersTest.java | 15 | 49 | **+34** | High |
| LiteralsAndEscapesTest.java | 19 | 55 | **+36** | High |
| CharClassesTest.java | 10 | 47 | **+37** | High |
| GroupsBackrefsLookaroundsTest.java | 13 | 51 | **+38** | High |
| SimplyApiTest.java | 14 | 54 | **+40** | High |

## Implementation Approach

### ✅ 1. CompilerTest.java (+16 tests) - COMPLETED

Added missing Categories E, F, G, H, I, J from JavaScript test suite:

**Category E: Deeply Nested Alternations (3 tests)**
- testFlattenThreeLevelNestedAlternation
- testFuseSequencesWithinAlternation
- testMixedAlternationAndSequenceNesting

**Category F: Complex Sequence Normalization (3 tests)**
- testFlattenDeeplyNestedSequences
- testSequenceWithNonLiteralInMiddle
- testNormalizeEmptySequence

**Category G: Literal Fusion Edge Cases (3 tests)**
- testFuseLiteralsWithEscapedChars
- testFuseUnicodeLiterals
- testNotFuseAcrossNonLiterals

**Category H: Quantifier Normalization (3 tests)**
- testUnwrapQuantifierOfSingleItemSequence
- testPreserveQuantifierOfEmptySequence
- testPreserveNestedQuantifiers

**Category I: Feature Detection Comprehensive (2 tests)**
- testDetectUnicodeProperties
- testDetectMultipleFeaturesInOnePattern

**Category J: Alternation Normalization Edge Cases (3 tests)**
- testUnwrapAlternationWithSingleBranch
- testPreserveAlternationWithEmptyBranches
- testFlattenAlternationsNestedAtDifferentDepths

Reference: `bindings/javascript/__tests__/unit/ir_compiler.test.ts`

**Status**: ✅ Complete - 40/40 tests (1 expected failure due to upstream gap)

### 2. QuantifiersTest.java (+34 tests)

Currently has 15 tests via parameterized tests. JavaScript has 49 individual test cases covering:
- Basic quantifiers (*, +, ?, {n}, {n,m})
- Edge cases (zero quantifiers, max limits)
- Greedy vs lazy vs possessive modes
- Quantifier interactions
- Error cases

Reference: `bindings/javascript/__tests__/unit/quantifiers.test.ts`

### 3. LiteralsAndEscapesTest.java (+36 tests)

Currently has 19 tests. JavaScript has 55 covering:
- Literal metacharacter escaping
- Unicode escapes (\u, \x, \x{})
- Character escapes (\n, \t, \r, etc.)
- Octal and hex escapes
- Edge cases and error handling

Reference: `bindings/javascript/__tests__/unit/literals_and_escapes.test.ts`

### 4. CharClassesTest.java (+37 tests)

Currently has 10 tests. JavaScript has 47 covering:
- Basic character classes [abc]
- Ranges [a-z], [0-9]
- Negated classes [^abc]
- Predefined classes (\d, \w, \s, etc.)
- Unicode property escapes (\p{L}, \p{N}, etc.)
- Complex nested classes
- Edge cases (empty classes, invalid ranges)

Reference: `bindings/javascript/__tests__/unit/char_classes.test.ts`

### 5. GroupsBackrefsLookaroundsTest.java (+38 tests)

Currently has 13 tests. JavaScript has 51 covering:
- Capturing groups (numbered and named)
- Non-capturing groups (?:)
- Atomic groups (?>)
- Lookahead (?=) and (?!)
- Lookbehind (?<=) and (?<!)
- Backreferences (\1, \2, \k<name>)
- Group interactions and nesting
- Error cases

Reference: `bindings/javascript/__tests__/unit/groups_backrefs_lookarounds.test.ts`

### 6. SimplyApiTest.java (+40 tests)

Currently has 14 tests. JavaScript has 54 covering all Simply API modules:
- Sets module (notBetween, inChars, notInChars)
- Constructors module
- Lookarounds module
- Static module
- Pattern class methods
- API composition and integration
- Error handling for invalid inputs

Reference: `bindings/javascript/__tests__/unit/simply_api.test.ts`

## Step-by-Step Implementation Process

### For Each Test File:

1. **Read JavaScript Source**
   - Open corresponding `.test.ts` file
   - Identify all test cases (including test.each expansions)
   - Document test names, inputs, and expected outputs

2. **Map to Java**
   - Use `@Test` for individual test cases
   - Use `@ParameterizedTest` with `@MethodSource` for test.each blocks
   - Maintain exact test count parity

3. **Implement Test Logic**
   - Translate TypeScript assertions to JUnit assertions
   - Convert test data structures from JS to Java
   - Handle any API differences between bindings

4. **Verify Compilation**
   ```bash
   cd bindings/java
   mvn test-compile
   ```

5. **Run Tests**
   ```bash
   mvn test -Dtest=FileName
   ```
   Note: Some tests may fail due to upstream implementation gaps - this is acceptable.

6. **Verify Count**
   - Ensure test count matches JavaScript exactly
   - Check `mvn test` output for "Tests run" count

## Testing Guidelines

### Acceptable Test Failures
Per requirements, tests may fail due to:
- Missing features in Java core implementation
- Bugs in Java emitter
- Incomplete Simply API implementation

**Goal**: Structural completeness, not all tests passing

### Test Organization
- Keep test structure parallel to JavaScript
- Use descriptive test method names
- Group related tests with `@Nested` classes when appropriate
- Add JavaDoc comments matching JavaScript test descriptions

## Progress Tracking

After implementing each file, update this document and run:

```bash
mvn test 2>&1 | grep "Tests run:"
```

Record the total in the progress table above.

## Estimated Effort

| File | Tests to Add | Est. Time | Status |
|------|--------------|-----------|--------|
| CompilerTest | 16 | 1-2 hours | ✅ DONE |
| QuantifiersTest | 34 | 3-4 hours | ⏭️ NEXT |
| LiteralsAndEscapesTest | 36 | 3-4 hours | Pending |
| CharClassesTest | 37 | 3-4 hours | Pending |
| GroupsBackrefsLookaroundsTest | 38 | 3-4 hours | Pending |
| SimplyApiTest | 40 | 4-5 hours | Pending |
| **Total** | **201** | **17-23 hours** | **16 of 201 done** |

## Resources

### Reference Files
- JavaScript SSOT: `bindings/javascript/__tests__/`
- Java Tests: `bindings/java/src/test/java/com/strling/tests/`
- Completed examples: `EmitterEdgesTest.java`, `FlagsAndFreeSpacingTest.java`

### Build Commands
```bash
# Compile tests
mvn test-compile

# Run all tests
mvn test

# Run specific test file
mvn test -Dtest=ClassName

# Count tests
mvn test 2>&1 | grep "Tests run:"
```

## Next Steps

1. Implement CompilerTest (+16 tests) - smallest remaining gap
2. Move to larger files in priority order
3. Update this guide after each completion
4. Final verification: ensure 581 total tests

## Acceptance Criteria

- [ ] All 17 test files exist ✅ (Already complete)
- [ ] Test count per file matches JavaScript exactly
- [ ] Total test count: 581
- [ ] All tests compile successfully
- [ ] No changes outside `bindings/java/src/test/` directory
- [ ] Final metrics report with test counts per file
