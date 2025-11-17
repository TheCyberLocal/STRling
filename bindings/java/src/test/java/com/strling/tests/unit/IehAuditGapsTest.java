package com.strling.tests.unit;

import com.strling.core.Parser;
import com.strling.core.STRlingParseError;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test Design — IehAuditGapsTest.java
 * <p>
 * Purpose: Tests coverage for the Intelligent Error Handling (IEH) audit gaps. This
 * suite verifies that parser validation and the hint engine provide
 * context-aware, instructional error messages for the audit's critical
 * findings and that valid inputs remain accepted.
 * <p>
 * Description: Each test maps to one or more audit gaps and asserts both that invalid
 * inputs raise a STRlingParseError containing an actionable hint, and
 * that valid inputs continue to parse successfully.
 * <p>
 * This is a 1:1 port of ieh_audit_gaps.test.ts
 */
@DisplayName("Intelligent Error Handling Gap Coverage")
public class IehAuditGapsTest {

    @Nested
    @DisplayName("Group name validation")
    class GroupNameValidation {
        
        @Test
        @DisplayName("group name cannot start with digit")
        public void testGroupNameCannotStartWithDigit() {
            assertThrows(STRlingParseError.class, () -> Parser.parse("(?<1a>)"));
            try {
                Parser.parse("(?<1a>)");
            } catch (STRlingParseError e) {
                assertTrue(e.getErrorMessage().matches(".*Invalid group name.*"));
                assertNotNull(e.getHint());
                assertTrue(e.getHint().matches(".*IDENTIFIER.*"));
            }
        }

        @Test
        @DisplayName("group name cannot be empty")
        public void testGroupNameCannotBeEmpty() {
            assertThrows(STRlingParseError.class, () -> Parser.parse("(?<>)"));
            try {
                Parser.parse("(?<>)");
            } catch (STRlingParseError e) {
                assertTrue(e.getErrorMessage().matches(".*Invalid group name.*"));
                assertNotNull(e.getHint());
            }
        }

        @Test
        @DisplayName("group name cannot contain hyphens")
        public void testGroupNameCannotContainHyphens() {
            assertThrows(STRlingParseError.class, () -> Parser.parse("(?<name-bad>)"));
            try {
                Parser.parse("(?<name-bad>)");
            } catch (STRlingParseError e) {
                assertTrue(e.getErrorMessage().matches(".*Invalid group name.*"));
                assertNotNull(e.getHint());
                assertTrue(e.getHint().matches(".*IDENTIFIER.*"));
            }
        }
    }

    @Nested
    @DisplayName("Quantifier range validation")
    class QuantifierRangeValidation {
        
        @Test
        @DisplayName("quantifier range min cannot exceed max")
        public void testQuantifierRangeMinCannotExceedMax() {
            assertThrows(STRlingParseError.class, () -> Parser.parse("a{5,2}"));
            try {
                Parser.parse("a{5,2}");
            } catch (STRlingParseError e) {
                assertTrue(e.getErrorMessage().matches(".*Invalid quantifier range.*"));
                assertNotNull(e.getHint());
                assertTrue(e.getHint().matches(".*(m.*<=.*n|m <= n|m ≤ n).*"));
            }
        }
    }

    @Nested
    @DisplayName("Character class range validation")
    class CharacterClassRangeValidation {
        
        @Test
        @DisplayName("reversed letter ranges are rejected")
        public void testReversedLetterRangesAreRejected() {
            assertThrows(STRlingParseError.class, () -> Parser.parse("[z-a]"));
            try {
                Parser.parse("[z-a]");
            } catch (STRlingParseError e) {
                assertTrue(e.getErrorMessage().matches(".*Invalid character range.*"));
                assertNotNull(e.getHint());
            }
        }

        @Test
        @DisplayName("reversed digit ranges are rejected")
        public void testReversedDigitRangesAreRejected() {
            assertThrows(STRlingParseError.class, () -> Parser.parse("[9-0]"));
            try {
                Parser.parse("[9-0]");
            } catch (STRlingParseError e) {
                assertTrue(e.getErrorMessage().matches(".*Invalid character range.*"));
                assertNotNull(e.getHint());
            }
        }
    }

    @Nested
    @DisplayName("Empty alternation validation")
    class EmptyAlternationValidation {
        
        @Test
        @DisplayName("empty alternation branch is rejected")
        public void testEmptyAlternationBranchIsRejected() {
            assertThrows(STRlingParseError.class, () -> Parser.parse("a||b"));
            try {
                Parser.parse("a||b");
            } catch (STRlingParseError e) {
                assertTrue(e.getErrorMessage().matches(".*Empty alternation.*"));
                assertNotNull(e.getHint());
                assertTrue(e.getHint().matches(".*a\\|b.*"));
            }
        }
    }

    @Nested
    @DisplayName("Flag directive validation")
    class FlagDirectiveValidation {
        
        @Test
        @DisplayName("invalid flag letters are rejected")
        public void testInvalidFlagLettersAreRejected() {
            assertThrows(STRlingParseError.class, () -> Parser.parse("%flags foo"));
            try {
                Parser.parse("%flags foo");
            } catch (STRlingParseError e) {
                assertTrue(e.getErrorMessage().matches(".*Invalid flag.*"));
                assertNotNull(e.getHint());
                assertTrue(e.getHint().matches(".*i.*"));
                assertTrue(e.getHint().matches(".*m.*"));
            }
        }

        @Test
        @DisplayName("directive after pattern is rejected")
        public void testDirectiveAfterPatternIsRejected() {
            assertThrows(STRlingParseError.class, () -> Parser.parse("abc%flags i"));
            try {
                Parser.parse("abc%flags i");
            } catch (STRlingParseError e) {
                assertTrue(e.getErrorMessage().matches(".*Directive after pattern.*"));
                assertNotNull(e.getHint());
                assertTrue(e.getHint().matches(".*start of the pattern.*"));
            }
        }
    }

    @Nested
    @DisplayName("Incomplete named backref hint")
    class IncompleteNamedBackrefHint {
        
        @Test
        @DisplayName("incomplete named backref has hint")
        public void testIncompleteNamedBackrefHasHint() {
            assertThrows(STRlingParseError.class, () -> Parser.parse("\\k"));
            try {
                Parser.parse("\\k");
            } catch (STRlingParseError e) {
                assertTrue(e.getErrorMessage().matches(".*Expected '<' after \\\\k.*"));
                assertNotNull(e.getHint());
                assertTrue(e.getHint().matches(".*\\\\k<name>.*"));
            }
        }
    }

    @Nested
    @DisplayName("Context-aware quantifier hints")
    class ContextAwareQuantifierHints {
        
        @Test
        @DisplayName("plus quantifier hint mentions plus")
        public void testPlusQuantifierHintMentionsPlus() {
            assertThrows(STRlingParseError.class, () -> Parser.parse("+"));
            try {
                Parser.parse("+");
            } catch (STRlingParseError e) {
                assertNotNull(e.getHint());
                assertTrue(e.getHint().matches(".*'\\+'.*"));
            }
        }

        @Test
        @DisplayName("question quantifier hint mentions question")
        public void testQuestionQuantifierHintMentionsQuestion() {
            assertThrows(STRlingParseError.class, () -> Parser.parse("?"));
            try {
                Parser.parse("?");
            } catch (STRlingParseError e) {
                assertNotNull(e.getHint());
                assertTrue(e.getHint().matches(".*'\\?'.*"));
            }
        }

        @Test
        @DisplayName("brace quantifier hint mentions brace")
        public void testBraceQuantifierHintMentionsBrace() {
            assertThrows(STRlingParseError.class, () -> Parser.parse("{5}"));
            try {
                Parser.parse("{5}");
            } catch (STRlingParseError e) {
                assertNotNull(e.getHint());
                assertTrue(e.getHint().matches(".*'\\{'.*"));
            }
        }
    }

    @Nested
    @DisplayName("Context-aware escape hints")
    class ContextAwareEscapeHints {
        
        @Test
        @DisplayName("unknown escape \\q has dynamic hint")
        public void testUnknownEscapeQHasDynamicHint() {
            assertThrows(STRlingParseError.class, () -> Parser.parse("\\q"));
            try {
                Parser.parse("\\q");
            } catch (STRlingParseError e) {
                assertNotNull(e.getHint());
                assertTrue(e.getHint().matches(".*(\\\\q|q).*"));
            }
        }

        @Test
        @DisplayName("unknown escape \\z suggests \\Z")
        public void testUnknownEscapeZSuggestsZ() {
            assertThrows(STRlingParseError.class, () -> Parser.parse("\\z"));
            try {
                Parser.parse("\\z");
            } catch (STRlingParseError e) {
                assertNotNull(e.getHint());
                assertTrue(e.getHint().matches(".*\\\\z.*"));
                assertTrue(e.getHint().matches(".*\\\\Z.*"));
            }
        }
    }

    @Nested
    @DisplayName("Valid patterns still work")
    class ValidPatternsStillWork {
        
        @Test
        @DisplayName("valid group names still work")
        public void testValidGroupNamesStillWork() {
            assertDoesNotThrow(() -> Parser.parse("(?<name>abc)"));
            assertDoesNotThrow(() -> Parser.parse("(?<_name>abc)"));
            assertDoesNotThrow(() -> Parser.parse("(?<name123>abc)"));
            assertDoesNotThrow(() -> Parser.parse("(?<Name_123>abc)"));
        }

        @Test
        @DisplayName("valid quantifier ranges still work")
        public void testValidQuantifierRangesStillWork() {
            assertDoesNotThrow(() -> Parser.parse("a{2,5}"));
            assertDoesNotThrow(() -> Parser.parse("a{2,2}"));
            assertDoesNotThrow(() -> Parser.parse("a{0,10}"));
        }

        @Test
        @DisplayName("valid character ranges still work")
        public void testValidCharacterRangesStillWork() {
            assertDoesNotThrow(() -> Parser.parse("[a-z]"));
            assertDoesNotThrow(() -> Parser.parse("[0-9]"));
            assertDoesNotThrow(() -> Parser.parse("[A-Z]"));
        }

        @Test
        @DisplayName("single alternation still works")
        public void testSingleAlternationStillWorks() {
            assertDoesNotThrow(() -> Parser.parse("a|b"));
            assertDoesNotThrow(() -> Parser.parse("a|b|c"));
        }

        @Test
        @DisplayName("valid flags still work")
        public void testValidFlagsStillWork() {
            assertDoesNotThrow(() -> Parser.parse("%flags i\nabc"));
            assertDoesNotThrow(() -> Parser.parse("%flags imsux\nabc"));
        }

        @Test
        @DisplayName("brace quantifier rejects non-digits")
        public void testBraceQuantifierRejectsNonDigits() {
            assertThrows(STRlingParseError.class, () -> Parser.parse("a{foo}"));
            try {
                Parser.parse("a{foo}");
            } catch (STRlingParseError e) {
                assertNotNull(e.getHint());
                assertTrue(e.getHint().matches(".*(digit|number|digits).*"));
            }
        }

        @Test
        @DisplayName("unterminated brace quantifier reports hint")
        public void testUnterminatedBraceQuantifierReportsHint() {
            assertThrows(STRlingParseError.class, () -> Parser.parse("a{5"));
            try {
                Parser.parse("a{5");
            } catch (STRlingParseError e) {
                assertNotNull(e.getHint());
                assertTrue(e.getHint().matches(".*(closing '\\}'|Unterminated brace).*"));
            }
        }

        @Test
        @DisplayName("empty character class reports hint")
        public void testEmptyCharacterClassReportsHint() {
            assertThrows(STRlingParseError.class, () -> Parser.parse("[]"));
            try {
                Parser.parse("[]");
            } catch (STRlingParseError e) {
                assertNotNull(e.getHint());
                assertTrue(e.getHint().matches(".*(empty|add characters).*"));
            }
        }
    }
}
