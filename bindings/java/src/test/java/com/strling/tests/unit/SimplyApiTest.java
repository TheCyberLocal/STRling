package com.strling.tests.unit;

import com.strling.simply.Pattern;
import com.strling.simply.STRlingError;
import org.junit.jupiter.api.Test;

import java.util.regex.Matcher;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test suite for Simply API Pattern class.
 *
 * This test file validates the Pattern class methods and behavior,
 * ensuring correct compilation and error handling.
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
}
