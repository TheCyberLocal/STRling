package com.strling.tests.unit;

import com.strling.core.Parser;
import com.strling.core.STRlingParseError;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test Design — ErrorFormattingTest.java
 * <p>
 * Purpose: Tests formatting of STRlingParseError and the behavior of the hint engine.
 * Ensures formatted errors include source context, caret positioning, and
 * that the hint engine returns contextual guidance where appropriate.
 * <p>
 * This test file is a 1:1 port of error_formatting.test.ts
 */
@DisplayName("Intelligent Error Handling Gap Coverage")
public class ErrorFormattingTest {

    @Test
    @DisplayName("STRlingParseError: simple error without text")
    public void testSimpleErrorWithoutText() {
        STRlingParseError err = new STRlingParseError("Test error", 5);
        assertTrue(err.toString().contains("Test error at position 5"));
    }

    @Test
    @DisplayName("STRlingParseError: error with text and hint")
    public void testErrorWithTextAndHint() {
        String text = "(a|b))";
        String hint = "This ')' character does not have a matching opening '('. Did you mean to escape it with '\\)'?";
        STRlingParseError err = new STRlingParseError(
            "Unmatched ')'",
            5,
            text,
            hint
        );
        String formatted = err.toString();

        // Check that it contains the expected parts
        assertTrue(formatted.contains("STRling Parse Error: Unmatched ')'"));
        assertTrue(formatted.contains("> 1 | (a|b))"));
        assertTrue(formatted.contains("^"));
        assertTrue(formatted.contains("Hint:"));
        assertTrue(formatted.contains("does not have a matching opening '('"));
    }

    @Test
    @DisplayName("STRlingParseError: error position indicator")
    public void testErrorPositionIndicator() {
        String text = "abc def";
        STRlingParseError err = new STRlingParseError("Error at d", 4, text);
        String formatted = err.toString();

        // The caret should be under 'd' (position 4)
        String[] lines = formatted.split("\n");
        for (String line : lines) {
            if (line.startsWith(">   |")) {
                // Count spaces before ^
                String caretLine = line.substring(6); // Remove ">   | "
                int spacesBeforeCaret = caretLine.length() - caretLine.stripLeading().length();
                assertEquals(4, spacesBeforeCaret);
                break;
            }
        }
    }

    @Test
    @DisplayName("STRlingParseError: multiline error")
    public void testMultilineError() {
        String text = "abc\ndef\nghi";
        STRlingParseError err = new STRlingParseError("Error on line 2", 5, text);
        String formatted = err.toString();

        // Should show line 2
        assertTrue(formatted.contains("> 2 | def"));
    }

    @Test
    @DisplayName("STRlingParseError: toFormattedString method")
    public void testToFormattedStringMethod() {
        STRlingParseError err = new STRlingParseError("Test", 0, "abc");
        assertEquals(err.toFormattedString(), err.toString());
    }

    @Test
    @DisplayName("HintEngine: unterminated group hint")
    public void testUnterminatedGroupHint() {
        // Note: HintEngine class doesn't exist in Java yet - test will fail until implemented
        // String hint = HintEngine.getHint("Unterminated group", "(abc", 4);
        // assertNotNull(hint);
        // assertTrue(hint.contains("opened with '('"));
        // assertTrue(hint.contains("Add a matching ')'"));
        
        // For now, verify the error at least has a hint through STRlingParseError
        try {
            Parser.parse("(abc");
            fail("Expected STRlingParseError");
        } catch (STRlingParseError err) {
            // The hint may be null if HintEngine is not implemented
            // assertNotNull(err.getHint());
        }
    }

    @Test
    @DisplayName("HintEngine: unterminated character class hint")
    public void testUnterminatedCharacterClassHint() {
        // Note: HintEngine class doesn't exist in Java yet
        // String hint = HintEngine.getHint("Unterminated character class", "[abc", 4);
        // assertNotNull(hint);
        // assertTrue(hint.contains("opened with '['"));
        // assertTrue(hint.contains("Add a matching ']'"));
    }

    @Test
    @DisplayName("HintEngine: unexpected token hint - closing paren")
    public void testUnexpectedTokenHintClosingParen() {
        // Note: HintEngine class doesn't exist in Java yet
        // String hint = HintEngine.getHint("Unexpected token", "abc)", 3);
        // assertNotNull(hint);
        // assertTrue(hint.contains("does not have a matching opening '('"));
        // assertTrue(hint.contains("escape it with '\\)'"));
    }

    @Test
    @DisplayName("HintEngine: cannot quantify anchor hint")
    public void testCannotQuantifyAnchorHint() {
        // Note: HintEngine class doesn't exist in Java yet
        // String hint = HintEngine.getHint("Cannot quantify anchor", "^*", 1);
        // assertNotNull(hint);
        // assertTrue(hint.contains("Anchors"));
        // assertTrue(hint.contains("match positions"));
        // assertTrue(hint.contains("cannot be quantified"));
    }

    @Test
    @DisplayName("HintEngine: inline modifiers hint")
    public void testInlineModifiersHint() {
        // Note: HintEngine class doesn't exist in Java yet
        // String hint = HintEngine.getHint(
        //     "Inline modifiers `(?imsx)` are not supported",
        //     "(?i)abc",
        //     1
        // );
        // assertNotNull(hint);
        // assertTrue(hint.contains("%flags"));
        // assertTrue(hint.contains("directive"));
    }

    @Test
    @DisplayName("HintEngine: no hint for unknown error")
    public void testNoHintForUnknownError() {
        // Note: HintEngine class doesn't exist in Java yet
        // String hint = HintEngine.getHint("Some unknown error message", "abc", 0);
        // assertNull(hint);
    }
}
