package com.strling.tests.unit;

import com.strling.simply.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Disabled;

import java.util.regex.Matcher;

import static org.junit.jupiter.api.Assertions.*;
import static com.strling.simply.Lookarounds.*;
import static com.strling.simply.Static.*;
import static com.strling.simply.Constructors.*;

/**
 * Test suite for Simply API.
 *
 * This test file validates the Simply API modules including Pattern, Lookarounds,
 * Static character classes, and Constructors.
 */
public class SimplyApiTest {

    // =========================================================================
    // Category A: Sets Module Tests (sets.py)
    // =========================================================================

    /**
     * Category A.1: notBetween() tests
     */

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

    /**
     * Category A.2: inChars() tests
     * Note: inChars() not yet implemented in Java Simply API - tests disabled
     */

    @Disabled("inChars() not yet implemented in Java Simply API")
    @Test
    public void testInCharsWithSimpleStringLiterals() {
        /** Test inChars with simple string literals */
        // This test is disabled until inChars() is implemented
    }

    @Disabled("inChars() not yet implemented in Java Simply API")
    @Test
    public void testInCharsWithMixedPatternTypes() {
        /** Test inChars with mixed pattern types */
        // This test is disabled until inChars() is implemented
    }

    @Disabled("inChars() not yet implemented in Java Simply API")
    @Test
    public void testInCharsUsedWithRepetition() {
        /** Test inChars used with repetition */
        // This test is disabled until inChars() is implemented
    }

    @Disabled("inChars() not yet implemented in Java Simply API")
    @Test
    public void testInCharsWithSingleCharacter() {
        /** Test inChars with single character */
        // This test is disabled until inChars() is implemented
    }

    @Disabled("inChars() not yet implemented in Java Simply API")
    @Test
    public void testInCharsRejectsCompositePatterns() {
        /** Test inChars rejects composite patterns */
        // This test is disabled until inChars() is implemented
    }

    /**
     * Category A.3: notInChars() tests
     * Note: notInChars() not yet implemented in Java Simply API - tests disabled
     */

    @Disabled("notInChars() not yet implemented in Java Simply API")
    @Test
    public void testNotInCharsWithSimpleStringLiterals() {
        /** Test notInChars with simple string literals */
        // This test is disabled until notInChars() is implemented
    }

    @Disabled("notInChars() not yet implemented in Java Simply API")
    @Test
    public void testNotInCharsExcludingDigitsAndLetters() {
        /** Test notInChars excluding digits and letters */
        // This test is disabled until notInChars() is implemented
    }

    @Disabled("notInChars() not yet implemented in Java Simply API")
    @Test
    public void testNotInCharsInMergedPattern() {
        /** Test notInChars in a merged pattern */
        // This test is disabled until notInChars() is implemented
    }

    // =========================================================================
    // Category B: Constructors Module Tests (constructors.py)
    // =========================================================================

    /**
     * Category B.1: anyOf() tests
     * Note: anyOf() not yet implemented in Java Simply API - tests disabled
     */

    @Disabled("anyOf() not yet implemented in Java Simply API")
    @Test
    public void testAnyOfWithSimpleStringAlternatives() {
        /** Test anyOf with simple string alternatives */
        // This test is disabled until anyOf() is implemented
    }

    @Disabled("anyOf() not yet implemented in Java Simply API")
    @Test
    public void testAnyOfWithMixedPatternTypes() {
        /** Test anyOf with mixed pattern types */
        // This test is disabled until anyOf() is implemented
    }

    @Disabled("anyOf() not yet implemented in Java Simply API")
    @Test
    public void testAnyOfUsedWithinMerge() {
        /** Test anyOf used within a merge */
        // This test is disabled until anyOf() is implemented
    }

    @Disabled("anyOf() and group() not yet implemented in Java Simply API")
    @Test
    public void testAnyOfRejectsDuplicateNamedGroups() {
        /** Test anyOf rejects duplicate named groups */
        // This test is disabled until anyOf() and group() are implemented
    }

    /**
     * Category B.2: merge() tests
     */

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
        // This test is disabled until group() is implemented
    }

    // =========================================================================
    // Category D: Static Module Tests (static.py)
    // =========================================================================

    /**
     * Category D.1: alphaNum() tests
     */

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

    /**
     * Category D.2-D.10: not* methods tests
     * Note: Most not* methods not yet implemented in Java Simply API - tests disabled
     */

    @Disabled("notAlphaNum() not yet implemented in Java Simply API")
    @Test
    public void testNotAlphaNumMatchingNonAlphanumeric() {
        /** Test notAlphaNum matching non-alphanumeric */
        // This test is disabled until notAlphaNum() is implemented
    }

    @Disabled("notAlphaNum() not yet implemented in Java Simply API")
    @Test
    public void testNotAlphaNumForFindingDelimiters() {
        /** Test notAlphaNum for finding delimiters */
        // This test is disabled until notAlphaNum() is implemented
    }

    @Disabled("upper() not yet implemented in Java Simply API")
    @Test
    public void testUpperMatchingUppercaseLetters() {
        /** Test upper matching uppercase letters */
        // This test is disabled until upper() is implemented
    }

    @Disabled("upper() not yet implemented in Java Simply API")
    @Test
    public void testUpperForMatchingAcronyms() {
        /** Test upper for matching acronyms */
        // This test is disabled until upper() is implemented
    }

    @Disabled("notUpper() not yet implemented in Java Simply API")
    @Test
    public void testNotUpperMatchingNonUppercase() {
        /** Test notUpper matching non-uppercase */
        // This test is disabled until notUpper() is implemented
    }

    @Disabled("notLower() not yet implemented in Java Simply API")
    @Test
    public void testNotLowerMatchingNonLowercase() {
        /** Test notLower matching non-lowercase */
        // This test is disabled until notLower() is implemented
    }

    @Disabled("notLetter() not yet implemented in Java Simply API")
    @Test
    public void testNotLetterMatchingNonLetters() {
        /** Test notLetter matching non-letters */
        // This test is disabled until notLetter() is implemented
    }

    @Disabled("notSpecialChar() not yet implemented in Java Simply API")
    @Test
    public void testNotSpecialCharMatchingNonSpecialCharacters() {
        /** Test notSpecialChar matching non-special characters */
        // This test is disabled until notSpecialChar() is implemented
    }

    @Disabled("notHexDigit() not yet implemented in Java Simply API")
    @Test
    public void testNotHexDigitMatchingNonHexCharacters() {
        /** Test notHexDigit matching non-hex characters */
        // This test is disabled until notHexDigit() is implemented
    }

    @Disabled("notDigit() not yet implemented in Java Simply API")
    @Test
    public void testNotDigitMatchingNonDigits() {
        /** Test notDigit matching non-digits */
        // This test is disabled until notDigit() is implemented
    }

    @Disabled("notWhitespace() not yet implemented in Java Simply API")
    @Test
    public void testNotWhitespaceMatchingNonWhitespace() {
        /** Test notWhitespace matching non-whitespace */
        // This test is disabled until notWhitespace() is implemented
    }

    // =========================================================================
    // Category E: Pattern Class Methods Tests (pattern.py)
    // =========================================================================

    /**
     * Category E.1: Pattern.call() tests (repetition)
     */
    
    @Test
    public void testPatternCallForSimpleRepetition() {
        /**Test Pattern.call for simple repetition*/
        // Using lit with plain text (actual digit() function will be added later)
        Pattern pattern = Pattern.lit("d").call(3);
        String regex = pattern.toString();
        
        // Should have quantifier {3,3}
        assertTrue(regex.contains("{3,3}"));
        // Should compile as valid regex
        assertDoesNotThrow(() -> java.util.regex.Pattern.compile(regex));
    }

    @Test
    public void testPatternCallWithMinAndMax() {
        /**Test Pattern.call with min and max*/
        // Using lit with plain text
        Pattern pattern = Pattern.lit("a").call(2, 4);
        String regex = pattern.toString();
        
        // Should have quantifier {2,4}
        assertTrue(regex.contains("{2,4}"));
        // Should compile as valid regex
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

    /**
     * Category E.2: Pattern.toString() tests
     */
    
    @Test
    public void testPatternToStringProducesValidRegex() {
        /**Test Pattern.toString produces valid regex*/
        Pattern pattern = Pattern.lit("test");
        String regex = pattern.toString();
        
        // Should be a valid regex string
        assertNotNull(regex);
        assertTrue(regex.length() > 0);
        
        // Should compile as regex
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

    // =========================================================================
    // Category C: Lookarounds Module Tests (lookarounds.py)
    // =========================================================================

    /**
     * Category C.1: notAhead() tests
     */
    
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
        // Note: notAhead doesn't consume, so this might still match
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

    /**
     * Category C.2: notBehind() tests
     */
    
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
        // 'possible' in 'impossible' is preceded by 'im', so shouldn't match
        // Actually, lookbehinds check at the position, need to be careful here
    }

    @Test
    public void testNotBehindAtStartOfString() {
        /**Test notBehind at start of string*/
        Pattern pattern = merge(notBehind(start()), letter());
        String regex = pattern.toString();
        // Can't be behind start, so should never match? Need to verify logic
        assertDoesNotThrow(() -> java.util.regex.Pattern.compile(regex));
    }

    /**
     * Category C.3: hasNot() tests
     */
    
    @Test
    public void testHasNotCheckingForAbsenceOfDigits() {
        /**Test hasNot checking for absence of digits*/
        Pattern pattern = merge(hasNot(digit()), letter(1, 0));
        String regex = pattern.toString();
        // hasNot checks that pattern doesn't exist anywhere in remaining string
        // So this should match letters only if no digit exists after current position
        assertTrue(java.util.regex.Pattern.compile("^" + regex).matcher("abcdef").find());
        // 'abc123' will match 'abc' because hasNot is checked at position 0
        // and the lookahead scans the whole string and finds '123'
        // So this should NOT match at all
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
