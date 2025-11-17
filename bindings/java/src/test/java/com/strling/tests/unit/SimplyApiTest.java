package com.strling.tests.unit;

import com.strling.simply.*;
import org.junit.jupiter.api.Disabled;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import java.util.regex.Matcher;

import static org.junit.jupiter.api.Assertions.*;
import static com.strling.simply.Lookarounds.*;
import static com.strling.simply.Static.*;
import static com.strling.simply.Constructors.*;

/**
 * @file Test Design — SimplyApiTest.java
 *
 * <h2>Purpose</h2>
 * This test suite validates the public-facing Simply API, ensuring all exported
 * functions and Pattern methods work correctly and produce expected regex patterns.
 * This provides comprehensive coverage of the user-facing DSL that developers
 * interact with directly.
 *
 * <h2>Description</h2>
 * The Simply API ({@code com.strling.simply}) is the primary interface for building regex
 * patterns. This suite tests all public functions across the {@code Sets}, {@code Constructors},
 * {@code Lookarounds}, {@code Static}, and {@code Pattern} modules to ensure they:
 * <ol>
 * <li>Accept valid inputs and produce correct patterns</li>
 * <li>Reject invalid inputs with instructional errors</li>
 * <li>Compose correctly with other API functions</li>
 * <li>Generate expected regex output</li>
 * </ol>
 *
 * <h2>Scope</h2>
 * <ul>
 * <li><strong>In scope:</strong></li>
 * <ul>
 * <li>All public functions in {@code simply.Sets}</li>
 * <li>All public functions in {@code simply.Constructors}</li>
 * <li>All public functions in {@code simply.Lookarounds}</li>
 * <li>All public functions in {@code simply.Static}</li>
 * <li>Public methods on the {@code Pattern} class</li>
 * <li>Integration between API functions</li>
 * <li>Error handling and validation</li>
 * </ul>
 * <li><strong>Out of scope:</strong></li>
 * <ul>
 * <li>Internal parser, compiler, and emitter logic (covered in other test files)</li>
 * <li>Low-level AST node manipulation</li>
 * <li>Performance testing</li>
 * </ul>
 * </ul>
 */
public class SimplyApiTest {

    // =========================================================================
    // Category A: Sets Module Tests (sets.py)
    // =========================================================================

    /**
     * Tests for character set functions: between, notBetween, inChars, notInChars
     */
    @Nested
    class CategoryASetsModuleTests {

        // -------------------------------------------------------------------------
        // A.1: notBetween() tests
        // -------------------------------------------------------------------------
        @Nested
        class A1_NotBetweenTests {
            @Test
            public void testNotBetweenWithSimpleDigitRange() {
                /** Test notBetween with simple digit range */
                Pattern pattern = Sets.notBetween(0, 9);
                String regex = pattern.toString();
                // Should match non-digits
                assertTrue(java.util.regex.Pattern.compile(regex).matcher("A").find());
                assertTrue(java.util.regex.Pattern.compile(regex).matcher(" ").find());
                assertFalse(java.util.regex.Pattern.compile(regex).matcher("5").find());
            }

            @Test
            public void testNotBetweenWithTypicalLowercaseLetterRange() {
                /** Test notBetween with typical lowercase letter range */
                Pattern pattern = Sets.notBetween("a", "z");
                String regex = pattern.toString();
                // Should match anything except lowercase letters
                assertTrue(java.util.regex.Pattern.compile(regex).matcher("A").find());
                assertTrue(java.util.regex.Pattern.compile(regex).matcher("5").find());
                assertTrue(java.util.regex.Pattern.compile(regex).matcher("!").find());
                assertFalse(java.util.regex.Pattern.compile(regex).matcher("m").find());
            }

            @Test
            public void testNotBetweenInteractingWithRepetition() {
                /** Test notBetween interacting with repetition */
                Pattern pattern = Sets.notBetween("a", "e", 2, 4);
                String regex = pattern.toString();
                // Should match 2-4 characters that are not a-e
                Matcher match = java.util.regex.Pattern.compile(regex).matcher("XYZ");
                assertTrue(match.find());
                assertEquals("XYZ", match.group());
            }

            @Test
            public void testNotBetweenWithSameStartAndEnd() {
                /** Test notBetween with same start and end */
                Pattern pattern = Sets.notBetween("a", "a");
                String regex = pattern.toString();
                // Should match everything except 'a'
                assertTrue(java.util.regex.Pattern.compile(regex).matcher("b").find());
                assertFalse(java.util.regex.Pattern.compile(regex).matcher("a").find());
            }

            @Test
            public void testNotBetweenWithUppercaseLetters() {
                /** Test notBetween with uppercase letters */
                Pattern pattern = Sets.notBetween("A", "Z");
                String regex = pattern.toString();
                // Should match anything except uppercase letters
                assertTrue(java.util.regex.Pattern.compile(regex).matcher("a").find());
                assertFalse(java.util.regex.Pattern.compile(regex).matcher("M").find());
            }

            @Test
            public void testNotBetweenRejectsInvalidRange() {
                /** Test notBetween rejects invalid range (start > end) */
                assertThrows(STRlingError.class, () -> Sets.notBetween(9, 0));
                try {
                    Sets.notBetween(9, 0);
                    fail("Should have thrown STRlingError");
                } catch (STRlingError e) {
                    assertTrue(e.getMessage().contains("start") || e.getMessage().contains("must not be greater"));
                }
            }

            @Test
            public void testNotBetweenRejectsMixedTypes() {
                /** Test notBetween rejects mixed types */
                assertThrows(STRlingError.class, () -> Sets.notBetween("a", 9));
                try {
                    Sets.notBetween("a", 9);
                    fail("Should have thrown STRlingError");
                } catch (STRlingError e) {
                    assertTrue(e.getMessage().contains("both be integers") || e.getMessage().contains("letters"));
                }
            }

            @Test
            public void testNotBetweenRejectsMixedCaseLetters() {
                /** Test notBetween rejects mixed case letters */
                assertThrows(STRlingError.class, () -> Sets.notBetween("a", "Z"));
                try {
                    Sets.notBetween("a", "Z");
                    fail("Should have thrown STRlingError");
                } catch (STRlingError e) {
                    assertTrue(e.getMessage().contains("same case"));
                }
            }
        }

        // -------------------------------------------------------------------------
        // A.2: inChars() tests
        // -------------------------------------------------------------------------
        @Nested
        class A2_InCharsTests {
            @Disabled("inChars() not yet implemented in Java Simply API")
            @Test
            public void testInCharsWithSimpleStringLiterals() {
                /** Test inChars with simple string literals */
            }

            @Disabled("inChars() not yet implemented in Java Simply API")
            @Test
            public void testInCharsWithMixedPatternTypes() {
                /** Test inChars with mixed pattern types */
            }

            @Disabled("inChars() not yet implemented in Java Simply API")
            @Test
            public void testInCharsUsedWithRepetition() {
                /** Test inChars used with repetition */
            }

            @Disabled("inChars() not yet implemented in Java Simply API")
            @Test
            public void testInCharsWithSingleCharacter() {
                /** Test inChars with single character */
            }

            @Disabled("inChars() not yet implemented in Java Simply API")
            @Test
            public void testInCharsRejectsCompositePatterns() {
                /** Test inChars rejects composite patterns */
            }
        }

        // -------------------------------------------------------------------------
        // A.3: notInChars() tests
        // -------------------------------------------------------------------------
        @Nested
        class A3_NotInCharsTests {
            @Disabled("notInChars() not yet implemented in Java Simply API")
            @Test
            public void testNotInCharsWithSimpleStringLiterals() {
                /** Test notInChars with simple string literals */
            }

            @Disabled("notInChars() not yet implemented in Java Simply API")
            @Test
            public void testNotInCharsExcludingDigitsAndLetters() {
                /** Test notInChars excluding digits and letters */
            }

            @Disabled("notInChars() not yet implemented in Java Simply API")
            @Test
            public void testNotInCharsInMergedPattern() {
                /** Test notInChars in a merged pattern */
            }
        }
    }

    // =========================================================================
    // Category B: Constructors Module Tests (constructors.py)
    // =========================================================================

    /**
     * Tests for pattern constructor functions: anyOf, merge
     */
    @Nested
    class CategoryBConstructorsModuleTests {

        // -------------------------------------------------------------------------
        // B.1: anyOf() tests
        // -------------------------------------------------------------------------
        @Nested
        class B1_AnyOfTests {
            @Disabled("anyOf() not yet implemented in Java Simply API")
            @Test
            public void testAnyOfWithSimpleStringAlternatives() {
                /** Test anyOf with simple string alternatives */
            }

            @Disabled("anyOf() not yet implemented in Java Simply API")
            @Test
            public void testAnyOfWithMixedPatternTypes() {
                /** Test anyOf with mixed pattern types */
            }

            @Disabled("anyOf() not yet implemented in Java Simply API")
            @Test
            public void testAnyOfUsedWithinMerge() {
                /** Test anyOf used within a merge */
            }

            @Disabled("anyOf() and group() not yet implemented in Java Simply API")
            @Test
            public void testAnyOfRejectsDuplicateNamedGroups() {
                /** Test anyOf rejects duplicate named groups */
            }
        }

        // -------------------------------------------------------------------------
        // B.2: merge() tests
        // -------------------------------------------------------------------------
        @Nested
        class B2_MergeTests {
            @Test
            public void testMergeWithSimpleStringLiterals() {
                /** Test merge with simple string literals */
                Pattern pattern = merge("hello", " ", "world");
                String regex = pattern.toString();
                // Should match exact sequence 'hello world'
                assertTrue(java.util.regex.Pattern.compile(regex).matcher("hello world").find());
                assertFalse(java.util.regex.Pattern.compile("^" + regex + "$").matcher("hello").find());
            }

            @Test
            public void testMergeWithComplexPatternComposition() {
                /** Test merge with complex pattern composition */
                Pattern areaCode = digit(3, null);
                Pattern separator = Pattern.lit("[-  ]"); // Using lit for character class pattern
                Pattern pattern = merge(areaCode, separator, digit(3, null), separator, digit(4, null));
                String regex = pattern.toString();
                // Should compile as valid regex
                assertDoesNotThrow(() -> java.util.regex.Pattern.compile(regex));
            }

            @Test
            public void testMergeWhereMergedPatternIsQuantified() {
                /** Test merge where merged pattern is quantified */
                Pattern word = merge(letter(1, 0));
                Pattern space = Pattern.lit(" ");
                Pattern pattern = merge(word, space.call(1, 0), word);
                String regex = pattern.toString();
                // Should compile as valid regex
                assertDoesNotThrow(() -> java.util.regex.Pattern.compile(regex));
            }

            @Disabled("group() not yet implemented in Java Simply API")
            @Test
            public void testMergeRejectsDuplicateNamedGroups() {
                /** Test merge rejects duplicate named groups */
            }
        }
    }

    // =========================================================================
    // Category C: Lookarounds Module Tests (lookarounds.py)
    // =========================================================================

    /**
     * Tests for lookaround functions: notAhead, notBehind, hasNot
     */
    @Nested
    class CategoryCLookaroundsModuleTests {

        // -------------------------------------------------------------------------
        // C.1: notAhead() tests
        // -------------------------------------------------------------------------
        @Nested
        class C1_NotAheadTests {
            @Test
            public void testNotAheadWithSimplePattern() {
                /**Test notAhead with simple pattern*/
                Pattern pattern = merge(digit(), notAhead(letter()));
                String regex = pattern.toString();
                // Should match digit NOT followed by letter
                assertTrue(java.util.regex.Pattern.compile(regex).matcher("56").find());
                assertTrue(java.util.regex.Pattern.compile(regex).matcher("5 ").find());
                assertFalse(java.util.regex.Pattern.compile(regex).matcher("5A").find());
            }

            @Test
            public void testNotAheadValidatingIdentifierEndings() {
                /**Test notAhead validating identifier endings*/
                // Match identifier not ending with '_tmp'
                Pattern identifier = merge(letter(), alphaNum(0, 0));
                Pattern pattern = merge(
                    identifier,
                    notAhead(merge("_tmp", end()))
                );
                String regex = pattern.toString();
                assertTrue(java.util.regex.Pattern.compile(regex).matcher("myvar").find());
            }

            @Test
            public void testNotAheadUsedWithWordBoundary() {
                /**Test notAhead used with word boundary*/
                Pattern pattern = merge(letter(1, 0), notAhead(digit()));
                String regex = pattern.toString();
                assertTrue(java.util.regex.Pattern.compile(regex).matcher("hello").find());
                // Should match 'test' but not continue into '123'
                Matcher match = java.util.regex.Pattern.compile(regex).matcher("test123");
                assertTrue(match.find());
            }
        }

        // -------------------------------------------------------------------------
        // C.2: notBehind() tests
        // -------------------------------------------------------------------------
        @Nested
        class C2_NotBehindTests {
            @Test
            public void testNotBehindWithSimplePattern() {
                /**Test notBehind with simple pattern*/
                Pattern pattern = merge(notBehind(digit()), letter());
                String regex = pattern.toString();
                // Should match letter NOT preceded by digit
                Matcher matcher = java.util.regex.Pattern.compile(regex).matcher("AB");
                assertTrue(matcher.find());
                assertEquals("A", matcher.group());
                Matcher match2 = java.util.regex.Pattern.compile(regex).matcher("5A");
                // The 'A' is preceded by '5', so shouldn't match at position 1
                assertTrue(!match2.find() || !match2.group().equals("A"));
            }

            @Test
            public void testNotBehindForMatchingWordsWithoutPrefix() {
                /**Test notBehind for matching words without prefix*/
                // Match 'possible' not preceded by 'im'
                Pattern pattern = merge(
                    notBehind(Pattern.lit("im")),
                    Pattern.lit("possible")
                );
                String regex = pattern.toString();
                assertTrue(java.util.regex.Pattern.compile(regex).matcher("possible").find());
            }

            @Test
            public void testNotBehindAtStartOfString() {
                /**Test notBehind at start of string*/
                Pattern pattern = merge(notBehind(start()), letter());
                String regex = pattern.toString();
                assertDoesNotThrow(() -> java.util.regex.Pattern.compile(regex));
            }
        }

        // -------------------------------------------------------------------------
        // C.3: hasNot() tests
        // -------------------------------------------------------------------------
        @Nested
        class C3_HasNotTests {
            @Test
            public void testHasNotCheckingForAbsenceOfDigits() {
                /**Test hasNot checking for absence of digits*/
                Pattern pattern = merge(hasNot(digit()), letter(1, 0));
                String regex = pattern.toString();
                // hasNot checks that pattern doesn't exist anywhere in remaining string
                assertTrue(java.util.regex.Pattern.compile("^" + regex).matcher("abcdef").find());
                assertFalse(java.util.regex.Pattern.compile("^" + regex).matcher("abc123").find());
            }

            @Test
            public void testHasNotForPasswordValidationNoSpaces() {
                /**Test hasNot for password validation (no spaces)*/
                Pattern noSpaces = hasNot(Pattern.lit(" "));
                Pattern pattern = merge(noSpaces, alphaNum(8, 0));
                String regex = pattern.toString();
                assertTrue(java.util.regex.Pattern.compile("^" + regex).matcher("password123").find());
                assertFalse(java.util.regex.Pattern.compile("^" + regex).matcher("pass word").find());
            }

            @Test
            public void testHasNotWithMultipleConstraints() {
                /**Test hasNot with multiple constraints*/
                Pattern noDigit = hasNot(digit());
                Pattern noSpecial = hasNot(specialChar());
                Pattern pattern = merge(noDigit, noSpecial, letter(5, 0));
                String regex = pattern.toString();
                assertTrue(java.util.regex.Pattern.compile("^" + regex).matcher("hello").find());
                assertFalse(java.util.regex.Pattern.compile("^" + regex).matcher("hello5").find());
                assertFalse(java.util.regex.Pattern.compile("^" + regex).matcher("hello!").find());
            }
        }
    }

    // =========================================================================
    // Category D: Static Module Tests (static.py)
    // =========================================================================

    /**
     * Tests for character class functions in static module
     */
    @Nested
    class CategoryDStaticModuleTests {

        // -------------------------------------------------------------------------
        // D.1: alphaNum() tests
        // -------------------------------------------------------------------------
        @Nested
        class D1_AlphaNumTests {
            @Test
            public void testAlphaNumMatchingSingleAlphanumericCharacter() {
                /** Test alphaNum matching single alphanumeric character */
                Pattern pattern = alphaNum();
                String regex = pattern.toString();
                assertTrue(java.util.regex.Pattern.compile(regex).matcher("A").find());
                assertTrue(java.util.regex.Pattern.compile(regex).matcher("5").find());
                assertTrue(java.util.regex.Pattern.compile(regex).matcher("z").find());
                assertFalse(java.util.regex.Pattern.compile(regex).matcher("@").find());
            }

            @Test
            public void testAlphaNumForUsernamePattern() {
                /** Test alphaNum for username pattern */
                Pattern pattern = alphaNum(3, 16);
                String regex = pattern.toString();
                assertTrue(java.util.regex.Pattern.compile("^" + regex).matcher("user123").find());
                assertTrue(java.util.regex.Pattern.compile("^" + regex).matcher("ABC").find());
                assertFalse(java.util.regex.Pattern.compile("^" + regex + "$").matcher("ab").find()); // Too short
            }

            @Test
            public void testAlphaNumInMergedPattern() {
                /** Test alphaNum in merged pattern */
                // Alphanumeric username starting with letter
                Pattern pattern = merge(letter(), alphaNum(0, 0));
                String regex = pattern.toString();
                assertTrue(java.util.regex.Pattern.compile("^" + regex).matcher("user123").find());
                assertFalse(java.util.regex.Pattern.compile("^" + regex).matcher("123user").find());
            }
        }

        // -------------------------------------------------------------------------
        // D.2: notAlphaNum() tests
        // -------------------------------------------------------------------------
        @Nested
        class D2_NotAlphaNumTests {
            @Disabled("notAlphaNum() not yet implemented in Java Simply API")
            @Test
            public void testNotAlphaNumMatchingNonAlphanumeric() {
                /** Test notAlphaNum matching non-alphanumeric */
            }

            @Disabled("notAlphaNum() not yet implemented in Java Simply API")
            @Test
            public void testNotAlphaNumForFindingDelimiters() {
                /** Test notAlphaNum for finding delimiters */
            }
        }

        // -------------------------------------------------------------------------
        // D.3: upper() tests
        // -------------------------------------------------------------------------
        @Nested
        class D3_UpperTests {
            @Disabled("upper() not yet implemented in Java Simply API")
            @Test
            public void testUpperMatchingUppercaseLetters() {
                /** Test upper matching uppercase letters */
            }

            @Disabled("upper() not yet implemented in Java Simply API")
            @Test
            public void testUpperForMatchingAcronyms() {
                /** Test upper for matching acronyms */
            }
        }

        // -------------------------------------------------------------------------
        // D.4: notUpper() tests
        // -------------------------------------------------------------------------
        @Nested
        class D4_NotUpperTests {
            @Disabled("notUpper() not yet implemented in Java Simply API")
            @Test
            public void testNotUpperMatchingNonUppercase() {
                /** Test notUpper matching non-uppercase */
            }
        }

        // -------------------------------------------------------------------------
        // D.5: notLower() tests
        // -------------------------------------------------------------------------
        @Nested
        class D5_NotLowerTests {
            @Disabled("notLower() not yet implemented in Java Simply API")
            @Test
            public void testNotLowerMatchingNonLowercase() {
                /** Test notLower matching non-lowercase */
            }
        }

        // -------------------------------------------------------------------------
        // D.6: notLetter() tests
        // -------------------------------------------------------------------------
        @Nested
        class D6_NotLetterTests {
            @Disabled("notLetter() not yet implemented in Java Simply API")
            @Test
            public void testNotLetterMatchingNonLetters() {
                /** Test notLetter matching non-letters */
            }
        }

        // -------------------------------------------------------------------------
        // D.7: notSpecialChar() tests
        // -------------------------------------------------------------------------
        @Nested
        class D7_NotSpecialCharTests {
            @Disabled("notSpecialChar() not yet implemented in Java Simply API")
            @Test
            public void testNotSpecialCharMatchingNonSpecialCharacters() {
                /** Test notSpecialChar matching non-special characters */
            }
        }

        // -------------------------------------------------------------------------
        // D.8: notHexDigit() tests
        // -------------------------------------------------------------------------
        @Nested
        class D8_NotHexDigitTests {
            @Disabled("notHexDigit() not yet implemented in Java Simply API")
            @Test
            public void testNotHexDigitMatchingNonHexCharacters() {
                /** Test notHexDigit matching non-hex characters */
            }
        }

        // -------------------------------------------------------------------------
        // D.9: notDigit() tests
        // -------------------------------------------------------------------------
        @Nested
        class D9_NotDigitTests {
            @Disabled("notDigit() not yet implemented in Java Simply API")
            @Test
            public void testNotDigitMatchingNonDigits() {
                /** Test notDigit matching non-digits */
            }
        }

        // -------------------------------------------------------------------------
        // D.10: notWhitespace() tests
        // -------------------------------------------------------------------------
        @Nested
        class D10_NotWhitespaceTests {
            @Disabled("notWhitespace() not yet implemented in Java Simply API")
            @Test
            public void testNotWhitespaceMatchingNonWhitespace() {
                /** Test notWhitespace matching non-whitespace */
            }
        }

        // -------------------------------------------------------------------------
        // D.11: notNewline() tests
        // -------------------------------------------------------------------------
        @Nested
        class D11_NotNewlineTests {
            @Disabled("notNewline() not yet implemented in Java Simply API")
            @Test
            public void testNotNewlineMatchingNonNewlineCharacters() {
                /** Test notNewline matching non-newline characters */
            }
        }

        // -------------------------------------------------------------------------
        // D.12: notBound() tests
        // -------------------------------------------------------------------------
        @Nested
        class D12_NotBoundTests {
            @Disabled("notBound() not yet implemented in Java Simply API")
            @Test
            public void testNotBoundMatchingNonBoundaryPositions() {
                /** Test notBound matching non-boundary positions */
            }
        }
    }

    // =========================================================================
    // Category E: Pattern Class Methods Tests (pattern.py)
    // =========================================================================

    /**
     * Tests for Pattern class methods: call, toString
     */
    @Nested
    class CategoryEPatternClassMethodsTests {

        // -------------------------------------------------------------------------
        // E.1: Pattern.call() tests (repetition)
        // -------------------------------------------------------------------------
        @Nested
        class E1_CallTests {
            @Test
            public void testPatternCallForSimpleRepetition() {
                /**Test Pattern.call for simple repetition*/
                Pattern pattern = Pattern.lit("d").call(3);
                String regex = pattern.toString();

                // Should have quantifier {3,3}
                assertTrue(regex.contains("{3,3}"));
                assertDoesNotThrow(() -> java.util.regex.Pattern.compile(regex));
            }

            @Test
            public void testPatternCallWithMinAndMax() {
                /**Test Pattern.call with min and max*/
                Pattern pattern = Pattern.lit("a").call(2, 4);
                String regex = pattern.toString();

                // Should have quantifier {2,4}
                assertTrue(regex.contains("{2,4}"));
                assertDoesNotThrow(() -> java.util.regex.Pattern.compile(regex));
            }

            @Test
            public void testPatternCallRejectsReassignmentOfRange() {
                /**Test Pattern.call rejects reassignment of range*/
                Pattern pattern = Pattern.lit("a").call(2, 3);

                // Attempting to call again should throw
                assertThrows(STRlingError.class, () -> {
                    pattern.call(4, 5);
                });
            }
        }

        // -------------------------------------------------------------------------
        // E.2: Pattern.toString() tests
        // -------------------------------------------------------------------------
        @Nested
        class E2_ToStringTests {
            @Test
            public void testPatternToStringProducesValidRegex() {
                /**Test Pattern.toString produces valid regex*/
                Pattern pattern = Pattern.lit("test");
                String regex = pattern.toString();

                // Should be a valid regex string
                assertNotNull(regex);
                assertTrue(regex.length() > 0);
                assertDoesNotThrow(() -> java.util.regex.Pattern.compile(regex));
            }

            @Test
            public void testPatternToStringWithQuantifier() {
                /**Test Pattern.toString with quantifier*/
                Pattern pattern = Pattern.lit("a").call(2, 4);
                String regex = pattern.toString();

                // Should produce valid regex that matches
                assertTrue(java.util.regex.Pattern.compile(regex).matcher("aa").find());
                assertTrue(java.util.regex.Pattern.compile(regex).matcher("aaaa").find());
                assertFalse(java.util.regex.Pattern.compile(regex).matcher("a").find());
            }
        }
    }
}
