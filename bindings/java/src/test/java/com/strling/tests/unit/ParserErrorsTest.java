package com.strling.tests.unit;

import com.strling.core.Parser;
import com.strling.core.STRlingParseError;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test Parser Error Messages - Comprehensive Validation of Rich Error Output
 * <p>
 * This test suite validates that the parser produces rich, instructional error
 * messages in the "Visionary State" format with:
 * - Context line showing the error location
 * - Caret (^) pointing to the exact position
 * - Helpful hints explaining how to fix the error
 * <p>
 * These tests intentionally pass invalid syntax to ensure the error messages
 * are helpful and educational.
 * <p>
 * This is a 1:1 port of parser_errors.test.ts
 */
public class ParserErrorsTest {

    @Nested
    @DisplayName("Rich Error Formatting")
    class RichErrorFormatting {
        
        @Test
        @DisplayName("unmatched closing paren shows visionary format")
        public void testUnmatchedClosingParenShowsVisionaryFormat() {
            assertThrows(STRlingParseError.class, () -> Parser.parse("(a|b))"));
            
            try {
                Parser.parse("(a|b))");
                fail("Expected STRlingParseError");
            } catch (STRlingParseError err) {
                String formatted = err.toString();
                
                // Check all components of visionary format
                assertTrue(formatted.contains("STRling Parse Error:"));
                assertTrue(formatted.contains("Unmatched ')'"));
                assertTrue(formatted.contains("> 1 | (a|b))"));
                assertTrue(formatted.contains("^"));
                assertTrue(formatted.contains("Hint:"));
                assertTrue(formatted.contains("Did you mean to escape it"));
            }
        }

        @Test
        @DisplayName("unterminated group shows helpful hint")
        public void testUnterminatedGroupShowsHelpfulHint() {
            try {
                Parser.parse("(abc");
                fail("Expected STRlingParseError");
            } catch (STRlingParseError err) {
                assertNotNull(err.getHint());
                assertTrue(err.getHint().contains("opened with '('"));
                assertTrue(err.getHint().contains("Add a matching ')'"));
            }
        }

        @Test
        @DisplayName("error on second line shows correct line number")
        public void testErrorOnSecondLineShowsCorrectLineNumber() {
            String pattern = "abc\n(def";
            try {
                Parser.parse(pattern);
                fail("Expected STRlingParseError");
            } catch (STRlingParseError error) {
                String formatted = error.toString();
                assertTrue(formatted.contains("> 2 |")); // Should show line 2
                assertTrue(formatted.contains("(def"));
            }
        }

        @Test
        @DisplayName("caret points to exact position")
        public void testCaretPointsToExactPosition() {
            try {
                Parser.parse("abc)");
                fail("Expected STRlingParseError");
            } catch (STRlingParseError error) {
                String formatted = error.toString();
                String[] lines = formatted.split("\n");
                
                // Find the line with the caret
                for (String line : lines) {
                    if (line.startsWith(">   |")) {
                        String caretLine = line.substring(6); // Remove ">   | "
                        // Caret should be at position 3 (under ')')
                        assertEquals("^", caretLine.trim());
                        int spaces = caretLine.length() - caretLine.stripLeading().length();
                        assertEquals(3, spaces);
                    }
                }
            }
        }
    }

    @Nested
    @DisplayName("Specific Error Hints")
    class SpecificErrorHints {
        
        @Test
        @DisplayName("alternation no lhs hint")
        public void testAlternationNoLhsHint() {
            try {
                Parser.parse("|abc");
                fail("Expected STRlingParseError");
            } catch (STRlingParseError err) {
                assertTrue(err.getErrorMessage().contains("Alternation lacks left-hand side"));
                assertNotNull(err.getHint());
                assertTrue(err.getHint().contains("expression on the left side"));
            }
        }

        @Test
        @DisplayName("alternation no rhs hint")
        public void testAlternationNoRhsHint() {
            try {
                Parser.parse("abc|");
                fail("Expected STRlingParseError");
            } catch (STRlingParseError err) {
                assertTrue(err.getErrorMessage().contains("Alternation lacks right-hand side"));
                assertNotNull(err.getHint());
                assertTrue(err.getHint().contains("expression on the right side"));
            }
        }

        @Test
        @DisplayName("unterminated char class hint")
        public void testUnterminatedCharClassHint() {
            try {
                Parser.parse("[abc");
                fail("Expected STRlingParseError");
            } catch (STRlingParseError err) {
                assertTrue(err.getErrorMessage().contains("Unterminated character class"));
                assertNotNull(err.getHint());
                assertTrue(err.getHint().contains("opened with '['"));
                assertTrue(err.getHint().contains("Add a matching ']'"));
            }
        }

        @Test
        @DisplayName("cannot quantify anchor hint")
        public void testCannotQuantifyAnchorHint() {
            try {
                Parser.parse("^*");
                fail("Expected STRlingParseError");
            } catch (STRlingParseError err) {
                assertTrue(err.getErrorMessage().contains("Cannot quantify anchor"));
                assertNotNull(err.getHint());
                assertTrue(err.getHint().contains("Anchors"));
                assertTrue(err.getHint().contains("match positions"));
            }
        }

        @Test
        @DisplayName("invalid hex escape hint")
        public void testInvalidHexEscapeHint() {
            try {
                Parser.parse("\\xGG");
                fail("Expected STRlingParseError");
            } catch (STRlingParseError err) {
                assertTrue(err.getErrorMessage().contains("Invalid \\xHH escape"));
                assertNotNull(err.getHint());
                assertTrue(err.getHint().contains("hexadecimal digits"));
            }
        }

        @Test
        @DisplayName("undefined backref hint")
        public void testUndefinedBackrefHint() {
            try {
                Parser.parse("\\1abc");
                fail("Expected STRlingParseError");
            } catch (STRlingParseError err) {
                assertTrue(err.getErrorMessage().contains("Backreference to undefined group"));
                assertNotNull(err.getHint());
                assertTrue(err.getHint().contains("previously captured groups"));
                assertTrue(err.getHint().contains("forward references"));
            }
        }

        @Test
        @DisplayName("duplicate group name hint")
        public void testDuplicateGroupNameHint() {
            try {
                Parser.parse("(?<name>a)(?<name>b)");
                fail("Expected STRlingParseError");
            } catch (STRlingParseError err) {
                assertTrue(err.getErrorMessage().contains("Duplicate group name"));
                assertNotNull(err.getHint());
                assertTrue(err.getHint().contains("unique name"));
            }
        }

        @Test
        @DisplayName("inline modifiers hint")
        public void testInlineModifiersHint() {
            try {
                Parser.parse("(?i)abc");
                fail("Expected STRlingParseError");
            } catch (STRlingParseError err) {
                assertTrue(err.getErrorMessage().contains("Inline modifiers"));
                assertNotNull(err.getHint());
                assertTrue(err.getHint().contains("%flags"));
                assertTrue(err.getHint().contains("directive"));
            }
        }

        @Test
        @DisplayName("unterminated unicode property hint")
        public void testUnterminatedUnicodePropertyHint() {
            try {
                Parser.parse("[\\p{Letter");
                fail("Expected STRlingParseError");
            } catch (STRlingParseError err) {
                assertTrue(err.getErrorMessage().contains("Unterminated \\p{...}"));
                assertNotNull(err.getHint());
                assertTrue(err.getHint().contains("syntax \\p{Property}"));
            }
        }
    }

    @Nested
    @DisplayName("Complex Error Scenarios")
    class ComplexErrorScenarios {
        
        @Test
        @DisplayName("nested groups error shows outermost")
        public void testNestedGroupsErrorShowsOutermost() {
            try {
                Parser.parse("((abc");
                fail("Expected STRlingParseError");
            } catch (STRlingParseError err) {
                assertTrue(err.getErrorMessage().contains("Unterminated group"));
            }
        }

        @Test
        @DisplayName("error in alternation branch")
        public void testErrorInAlternationBranch() {
            try {
                Parser.parse("a|(b");
                fail("Expected STRlingParseError");
            } catch (STRlingParseError err) {
                assertTrue(err.getErrorMessage().contains("Unterminated group"));
                // Position should point to the end where ')' is expected
                assertEquals(4, err.getPos());
            }
        }

        @Test
        @DisplayName("error with free spacing mode")
        public void testErrorWithFreeSpacingMode() {
            String pattern = "%flags x\n(abc\n  def";
            try {
                Parser.parse(pattern);
                fail("Expected STRlingParseError");
            } catch (STRlingParseError err) {
                assertNotNull(err.getHint());
            }
        }

        @Test
        @DisplayName("error position accuracy")
        public void testErrorPositionAccuracy() {
            try {
                Parser.parse("abc{2,");
                fail("Expected STRlingParseError");
            } catch (STRlingParseError err) {
                assertTrue(err.getErrorMessage().contains("Incomplete quantifier"));
                // Position should be at the end where '}' is expected
                assertEquals(6, err.getPos());
            }
        }
    }

    @Nested
    @DisplayName("Error Backward Compatibility")
    class ErrorBackwardCompatibility {
        
        @Test
        @DisplayName("error has message attribute")
        public void testErrorHasMessageAttribute() {
            try {
                Parser.parse("(");
                fail("Expected STRlingParseError");
            } catch (STRlingParseError err) {
                assertNotNull(err.getErrorMessage());
                assertEquals("Unterminated group", err.getErrorMessage());
            }
        }

        @Test
        @DisplayName("error has pos attribute")
        public void testErrorHasPosAttribute() {
            try {
                Parser.parse("abc)");
                fail("Expected STRlingParseError");
            } catch (STRlingParseError err) {
                assertTrue(err.getPos() >= 0);
                assertEquals(3, err.getPos());
            }
        }

        @Test
        @DisplayName("error string contains position")
        public void testErrorStringContainsPosition() {
            try {
                Parser.parse(")");
                fail("Expected STRlingParseError");
            } catch (STRlingParseError error) {
                String formatted = error.toString();
                // Should contain position information in the formatted output
                assertTrue(formatted.contains(">")); // Line markers
                assertTrue(formatted.contains("^")); // Caret pointer
            }
        }
    }
}
