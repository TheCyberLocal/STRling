# Next Steps for Test Parity Completion

## Current Status
- **Completed**: 306/581 tests (53%)
- **Remaining**: 275 tests across 5 files

## Files Completed (12/17)
✅ All E2E tests (116 tests)
✅ 9 unit test files with perfect parity

## Immediate Next Steps

### 1. QuantifiersTest.java (+34 tests)
**Current**: 15 tests (8 parameterized + 7 individual)  
**Target**: 49 tests

**What to Add** (based on JavaScript test file):

**Expand Parameterized Tests:**
- Category A (quantifierCases): Add missing modes
  - Plus lazy: `a+?`
  - Plus possessive: `a++`
  - Optional lazy: `a??`
  - Optional possessive: `a?+`
  - Exact lazy/possessive: `a{3}?`, `a{3}+`
  - At-least lazy/possessive: `a{3,}?`, `a{3,}+`
  - Range lazy/possessive: `a{3,5}?`, `a{3,5}+`

**Add New Individual Tests:**
- Category C (Edge Cases):
  - testZeroRangeQuantifier (`a{0,5}`)
  - testAtLeastZeroQuantifier (`a{0,}`)
  - testQuantifierOnEmptyGroup (already exists)
  - testQuantifierVsAnchorPrecedence (`a?^`)

- Category D (Interaction):
  - testQuantifierPrecedence (already exists)
  - testQuantifyCharClass (`[a-z]*`)
  - testQuantifyDot (`.*`)
  - testQuantifyGroup (`(abc)*`)
  - testQuantifyAlternationInGroup (`(?:a|b)+`)
  - testQuantifyLookaround (`(?=a)+`)

- Category E (Nested Quantifiers):
  - testNestedStarOnStar (`(a*)*`)
  - testNestedPlusOnOptional (`(a+)?`)
  - testRedundantPlusOnStar (`(a*)+`)
  - testRedundantStarOnOptional (`(a?)*`)
  - testNestedBraceQuantifier (`(a{2,3}){1,2}`)

- Category F (Special Atoms):
  - testQuantifierOnBackref (`(a)\1*`)
  - testQuantifierOnMultipleBackrefs (`(a)(b)\1*\2+`)

- Category G (Multiple Sequences):
  - testMultipleConsecutiveQuantifiedLiterals (`a*b+c?`)
  - testMultipleQuantifiedGroups (`(ab)*(cd)+(ef)?`)
  - testQuantifiedAtomsInAlternation (`a*|b+`)

- Category H (Brace Edge Cases):
  - testBraceExactOne (`a{1}`)
  - testBraceZeroToOne (`a{0,1}`)
  - testBraceOnAlternationInGroup (`(a|b){2,3}`)
  - testBraceLargeValues (`a{100,200}`)

- Category I (Flags Interaction):
  - testQuantifierWithFreeSpacingMode (`%flags x\na *`)
  - testQuantifierOnEscapedSpaceInFreeSpacing (`%flags x\n\ *`)

**Reference**: `bindings/javascript/__tests__/unit/quantifiers.test.ts`

### 2. LiteralsAndEscapesTest.java (+36 tests)
**Current**: 19 tests  
**Target**: 55 tests  
**Reference**: `bindings/javascript/__tests__/unit/literals_and_escapes.test.ts`

### 3. CharClassesTest.java (+37 tests)
**Current**: 10 tests  
**Target**: 47 tests  
**Reference**: `bindings/javascript/__tests__/unit/char_classes.test.ts`

### 4. GroupsBackrefsLookaroundsTest.java (+38 tests)
**Current**: 13 tests  
**Target**: 51 tests  
**Reference**: `bindings/javascript/__tests__/unit/groups_backrefs_lookarounds.test.ts`

### 5. SimplyApiTest.java (+40 tests)
**Current**: 14 tests  
**Target**: 54 tests  
**Reference**: `bindings/javascript/__tests__/unit/simply_api.test.ts`

## Implementation Process

For each file:

1. **Audit JavaScript tests**
   ```bash
   cd bindings/javascript
   npm test -- <testname> --verbose 2>&1 | grep "✓"
   ```

2. **Map test.each blocks**
   - Count array items
   - Create corresponding @ParameterizedTest with @MethodSource
   - Or create individual @Test methods for 1:1 parity

3. **Implement test logic**
   - Translate TypeScript assertions to JUnit
   - Convert JS structures to Java
   - Use existing test patterns as templates

4. **Verify**
   ```bash
   cd bindings/java
   mvn test -Dtest=ClassName 2>&1 | grep "Tests run:"
   ```

5. **Update guide**
   - Mark file as complete
   - Update test counts
   - Run full suite: `mvn test 2>&1 | grep "Tests run:"`

## Estimated Timeline

| File | Tests | Est. Time | Cumulative |
|------|-------|-----------|------------|
| QuantifiersTest | +34 | 3-4 hours | 340 tests |
| LiteralsAndEscapesTest | +36 | 3-4 hours | 376 tests |
| CharClassesTest | +37 | 3-4 hours | 413 tests |
| GroupsBackrefsLookaroundsTest | +38 | 3-4 hours | 451 tests |
| SimplyApiTest | +40 | 4-5 hours | 491 tests |

**Total Remaining**: 15-21 hours of focused implementation work

## Success Criteria

- [ ] All 17 test files exist ✅ (Complete)
- [ ] Test count per file matches JavaScript exactly (12/17 complete)
- [ ] Total test count: 581
- [ ] All tests compile successfully
- [ ] Implementation guide updated
- [ ] Final metrics report delivered
