package com.strling.tests.unit;

import com.strling.core.Parser;
import com.strling.core.STRlingParseError;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test Parser Error Messages - Comprehensive Validation of Rich Error Output
 *
 * This test suite validates that the parser produces rich, instructional error
 * messages in the "Visionary State" format with:
 * - Context line showing the error location
 * - Caret (^) pointing to the exact position
 * - Helpful hints explaining how to fix the error
 *
 * These tests intentionally pass invalid syntax to ensure the error messages
 * are helpful and educational.
 */
public class ParserErrorsTest {

    @Nested
    class RichErrorFormatting {

        @Test
        void unmatchedClosingParenShowsVisionaryFormat() {
            try {
                Parser.parse("(a|b))");
                fail("Expected STRlingParseError");
            } catch (STRlingParseError err) {
                String formatted = err.toString();
                
                // Check all components of visionary format
                assertTrue(formatted.contains("STRling Parse Error:"), "Missing error title");
                assertTrue(formatted.contains("Unmatched ')'"), "Missing error message");
                assertTrue(formatted.contains("> 1 | (a|b))"), "Missing context line");
                assertTrue(formatted.contains("^"), "Missing caret");
                assertTrue(formatted.contains("Hint:"), "Missing hint prefix");
                assertTrue(formatted.contains("Did you mean to escape it"), "Missing specific hint text");
            }
        }

        @Test
        void unterminatedGroupShowsHelpfulHint() {
            try {
                Parser.parse("(abc");
                fail("Expected STRlingParseError");
            } catch (STRlingParseError err) {
                assertNotNull(err.getHint(), "Hint should not be null");
                assertTrue(err.getHint().contains("opened with '('"), "Hint content mismatch");
                assertTrue(err.getHint().contains("Add a matching ')'"), "Hint content mismatch");
            }
        }

        @Test
        void errorOnSecondLineShowsCorrectLineNumber() {
            String pattern = "abc\n(def";
            try {
                Parser.parse(pattern);
                fail("Expected STRlingParseError");
            } catch (STRlingParseError err) {
                String formatted = err.toString();
                assertTrue(formatted.contains("> 2 |"), "Should show line 2");
                assertTrue(formatted.contains("(def"), "Should show line 2 content");
            }
        }

        @Test
        void caretPointsToExactPosition() {
            try {
                Parser.parse("abc)");
                fail("Expected STRlingParseError");
            } catch (STRlingParseError err) {
                String formatted = err.toString();
                String[] lines = formatted.split("\\r?\\n");
                
                boolean caretLineFound = false;
                for (String line : lines) {
                    // Check if line contains the caret indicator (line with '|' followed by '^')
                    if (line.contains("|") && line.contains("^") && line.indexOf('^') > line.indexOf('|')) {
                        caretLineFound = true;
                        // Find the index of the caret
                        int caretIndex = line.indexOf('^');
                        // Find the index of the start of the code (after "| ")
                        int codeStartIndex = line.indexOf('|') + 2;
                        int spacesBeforeCaret = caretIndex - codeStartIndex;
                        
                        // Caret should be at position 3 (under ')')
                        assertEquals(3, spacesBeforeCaret, "Caret is not at the correct position");
                        break;
                    }
                }
                assertTrue(caretLineFound, "Caret indicator line (starting with ' ^') not found");
            }
        }
    }

    @Nested
    class SpecificErrorHints {

        private void assertErrorAndHint(String dsl, String msg, String hint) {
            try {
                Parser.parse(dsl);
                fail("Expected STRlingParseError for: " + dsl);
            } catch (STRlingParseError err) {
                if (msg != null) {
                    assertTrue(err.getMessage().contains(msg), "Error message mismatch. Was: " + err.getMessage());
                }
                if (hint != null) {
                    assertNotNull(err.getHint(), "Hint should not be null");
                    assertTrue(err.getHint().contains(hint), "Hint content mismatch. Was: " + err.getHint());
                }
            }
        }

        @Test
        void alternationNoLhsHint() {
            assertErrorAndHint("|abc", "Alternation lacks left-hand side", "expression on the left side");
        }

        @Test
        void alternationNoRhsHint() {
            assertErrorAndHint("abc|", "Alternation lacks right-hand side", "expression on the right side");
        }

        @Test
        void unterminatedCharClassHint() {
            assertErrorAndHint("[abc", "Unterminated character class", "opened with '['");
        }

        @Test
        void cannotQuantifyAnchorHint() {
            assertErrorAndHint("^*", "Cannot quantify anchor", "match positions");
        }

        @Test
        void invalidHexEscapeHint() {
            assertErrorAndHint("\\xGG", "Invalid \\xHH escape", "hexadecimal digits");
        }

        @Test
        void undefinedBackrefHint() {
            assertErrorAndHint("\\1abc", "Backreference to undefined group", "previously captured groups");
        }

        @Test
        void duplicateGroupNameHint() {
            assertErrorAndHint("(?<name>a)(?<name>b)", "Duplicate group name", "unique name");
        }

        @Test
        void inlineModifiersHint() {
            assertErrorAndHint("(?i)abc", "Inline modifiers", "%flags");
        }

        @Test
        void unterminatedUnicodePropertyHint() {
            assertErrorAndHint("[\\p{Letter", "Unterminated \\p{...}", "syntax \\p{Property}");
        }
    }

    @Nested
    class ComplexErrorScenarios {

        @Test
        void nestedGroupsErrorShowsOutermost() {
            // The error is "Unterminated group", the hint clarifies
            STRlingParseError e = assertThrows(STRlingParseError.class, () -> Parser.parse("((abc"));
            assertTrue(e.getMessage().contains("Unterminated group"));
        }

        @Test
        void errorInAlternationBranch() {
            STRlingParseError e = assertThrows(STRlingParseError.class, () -> Parser.parse("a|(b"));
            assertTrue(e.getMessage().contains("Unterminated group"));
            // Position should point to the end where ')' is expected
            assertEquals(4, e.getPos());
        }

        @Test
        void errorWithFreeSpacingMode() {
            String pattern = "%flags x\n(abc\n  def";
            STRlingParseError e = assertThrows(STRlingParseError.class, () -> Parser.parse(pattern));
            assertNotNull(e.getHint(), "Hint should not be null even in free-spacing mode");
        }

        @Test
        void errorPositionAccuracy() {
            STRlingParseError e = assertThrows(STRlingParseError.class, () -> Parser.parse("abc{2,"));
            assertTrue(e.getMessage().contains("Incomplete quantifier"));
            // Position should be at the end where '}' is expected
            assertEquals(6, e.getPos());
        }
    }

    @Nested
    class ErrorBackwardCompatibility {

        @Test
        void errorHasMessageAttribute() {
            try {
                Parser.parse("(");
                fail("Expected STRlingParseError");
            } catch (STRlingParseError err) {
                assertNotNull(err.getMessage());
                assertEquals("Unterminated group", err.getMessage());
            }
        }

        @Test
        void errorHasPosAttribute() {
            try {
                Parser.parse("abc)");
                fail("Expected STRlingParseError");
            } catch (STRlingParseError err) {
                assertNotNull(err.getPos());
                assertEquals(3, err.getPos());
            }
        }

        @Test
        void errorStringContainsPosition() {
            try {
                Parser.parse(")");
                fail("Expected STRlingParseError");
            } catch (STRlingParseError err) {
                String formatted = err.toString();
                // Should contain position information in the formatted output
                assertTrue(formatted.contains(">"), "Missing line marker");
                assertTrue(formatted.contains("^"), "Missing caret pointer");
            }
        }
    }
}
