package com.strling.tests.unit;

import com.strling.core.STRlingParseError;
import com.strling.core.HintEngine;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * @file Test Design — ErrorFormattingTest.java
 *
 * <h2>Purpose</h2>
 * Tests formatting of {@code STRlingParseError} and the behavior of the hint engine.
 * Ensures formatted errors include source context, caret positioning, and
 * that the hint engine returns contextual guidance where appropriate.
 */
public class ErrorFormattingTest {

    @Nested
    class STRlingParseErrorTests {

        @Test
        void simpleErrorWithoutText() {
            STRlingParseError err = new STRlingParseError("Test error", 5);
            assertTrue(err.toString().contains("Test error at position 5"));
        }

        @Test
        void errorWithTextAndHint() {
            String text = "(a|b))";
            String hint = "This ')' character does not have a matching opening '('. Did you mean to escape it with '\\)'?";
            STRlingParseError err = new STRlingParseError("Unmatched ')'", 5, text, hint);
            String formatted = err.toString();

            // Check that it contains the expected parts
            assertTrue(formatted.contains("STRling Parse Error: Unmatched ')'"));
            assertTrue(formatted.contains("> 1 | (a|b))"));
            assertTrue(formatted.contains("^"));
            assertTrue(formatted.contains("Hint:"));
            assertTrue(formatted.contains("does not have a matching opening '('"));
        }

        @Test
        void errorPositionIndicator() {
            String text = "abc def";
            STRlingParseError err = new STRlingParseError("Error at d", 4, text);
            String formatted = err.toString();

            // The caret should be under 'd' (position 4)
            String[] lines = formatted.split("\\r?\\n");
            for (String line : lines) {
                // Check if line contains the caret indicator (line with '|' followed by '^')
                if (line.contains("|") && line.contains("^") && line.indexOf('^') > line.indexOf('|')) {
                    // Find the index of the caret
                    int caretIndex = line.indexOf('^');
                    // Find the index of the start of the code (after "| ")
                    int codeStartIndex = line.indexOf('|') + 2;
                    int spacesBeforeCaret = caretIndex - codeStartIndex;
                    assertEquals(4, spacesBeforeCaret);
                    return;
                }
            }
            fail("Caret indicator line (starting with ' ^') not found in error output.");
        }

        @Test
        void multilineError() {
            String text = "abc\ndef\nghi";
            STRlingParseError err = new STRlingParseError("Error on line 2", 5, text);
            String formatted = err.toString();

            // Should show line 2
            assertTrue(formatted.contains("> 2 | def"));
        }

        @Test
        void toFormattedStringMethod() {
            STRlingParseError err = new STRlingParseError("Test", 0, "abc");
            assertEquals(err.toFormattedString(), err.toString());
        }
    }

    @Nested
    class HintEngineTests {

        @Test
        void unterminatedGroupHint() {
            String hint = HintEngine.getHint("Unterminated group", "(abc", 4);
            assertNotNull(hint);
            assertTrue(hint.contains("opened with '('"));
            assertTrue(hint.contains("Add a matching ')'"));
        }

        @Test
        void unterminatedCharacterClassHint() {
            String hint = HintEngine.getHint("Unterminated character class", "[abc", 4);
            assertNotNull(hint);
            assertTrue(hint.contains("opened with '['"));
            assertTrue(hint.contains("Add a matching ']'"));
        }

        @Test
        void unexpectedTokenHintClosingParen() {
            String hint = HintEngine.getHint("Unexpected token", "abc)", 3);
            assertNotNull(hint);
            assertTrue(hint.contains("does not have a matching opening '('"));
            assertTrue(hint.contains("escape it with '\\)'"));
        }

        @Test
        void cannotQuantifyAnchorHint() {
            String hint = HintEngine.getHint("Cannot quantify anchor", "^*", 1);
            assertNotNull(hint);
            assertTrue(hint.contains("Anchors"));
            assertTrue(hint.contains("match positions"));
            assertTrue(hint.contains("cannot be quantified"));
        }

        @Test
        void inlineModifiersHint() {
            String hint = HintEngine.getHint("Inline modifiers `(?imsx)` are not supported", "(?i)abc", 1);
            assertNotNull(hint);
            assertTrue(hint.contains("%flags"));
            assertTrue(hint.contains("directive"));
        }

        @Test
        void noHintForUnknownError() {
            String hint = HintEngine.getHint("Some unknown error message", "abc", 0);
            assertNull(hint);
        }
    }
}
