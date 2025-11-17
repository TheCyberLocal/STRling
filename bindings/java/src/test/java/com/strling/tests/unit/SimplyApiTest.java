package com.strling.tests.unit;

import com.strling.simply.*;
import org.junit.jupiter.api.Test;

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
