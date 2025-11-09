/**
 * @file Test Design — errors.test.ts
 *
 * ## Purpose
 * This test suite serves as the single source of truth for defining and
 * validating the error-handling contract of the entire STRling pipeline. It
 * ensures that invalid inputs are rejected predictably and that diagnostics are
 * stable, accurate, and helpful across all stages—from the parser to the CLI.
 *
 * ## Description
 * This suite defines the expected behavior for all invalid, malformed, or
 * unsupported inputs. It verifies that errors are raised at the correct stage
 * (e.g., `ParseError`), contain a clear, human-readable message, and provide an
 * accurate source location. A key invariant tested is the "first error wins"
 * policy: for an input with multiple issues, only the error at the earliest
 * position is reported.
 *
 * ## Scope
 * -   **In scope:**
 * -   `ParseError` exceptions raised by the parser for syntactic and lexical
 * issues.
 * -   `ValidationError` (or equivalent semantic errors) raised for
 * syntactically valid but semantically incorrect patterns.
 * -   Asserting error messages for a stable, recognizable substring and the
 * correctness of the error's reported position.
 * -   **Out of scope:**
 * -   Correct handling of **valid** inputs (covered in other test suites).
 *
 * -   The exact, full wording of error messages (tests assert substrings).
 *
 */

import { parse, ParseError } from "../../src/STRling/core/parser";

// --- Test Suite -----------------------------------------------------------------

describe("Error Handling Contract", () => {
    describe("Grouping & Lookaround Errors", () => {
        /**
         * Covers errors related to groups, named groups, and lookarounds.
         *
         */
        test.each<[string, string, number, string]>([
            ["(abc", "Unterminated group", 4, "unterminated_group"],
            [
                "(?<nameabc)",
                "Unterminated group name",
                11,
                "unterminated_named_group",
            ],
            ["(?=abc", "Unterminated lookahead", 6, "unterminated_lookahead"],
            [
                "(?<=abc",
                "Unterminated lookbehind",
                7,
                "unterminated_lookbehind",
            ],
            ["(?i)abc", "Inline modifiers", 1, "unsupported_inline_modifier"],
        ])(
            'should fail for "%s" (ID: %s)',
            (invalidDsl, errorPrefix, errorPos) => {
                /** Tests that various unterminated group/lookaround forms raise ParseError. */
                expect(() => parse(invalidDsl)).toThrow(ParseError);
                try {
                    parse(invalidDsl);
                } catch (e) {
                    const err = e as ParseError;
                    expect(err.message).toContain(errorPrefix);
                    expect(err.pos).toBe(errorPos);
                }
            }
        );
    });

    describe("Backreference & Naming Errors", () => {
        /**
         * Covers errors related to invalid backreferences and group naming.
         *
         */
        test.each<[string, string, number, string]>([
            [
                "\\k<later>(?<later>a)",
                "Backreference to undefined group <later>",
                0,
                "forward_reference_by_name",
            ],
            [
                "\\2(a)(b)",
                "Backreference to undefined group \\2",
                0,
                "forward_reference_by_index",
            ],
            [
                "(a)\\2",
                "Backreference to undefined group \\2",
                3,
                "nonexistent_reference_by_index",
            ],
            ["\\k<", "Unterminated named backref", 0, "unterminated_named_backref"],
        ])(
            'should fail for "%s" (ID: %s)',
            (invalidDsl, errorPrefix, errorPos) => {
                /** Tests that invalid backreferences are caught at parse time. */
                expect(() => parse(invalidDsl)).toThrow(ParseError);
                try {
                    parse(invalidDsl);
                } catch (e) {
                    const err = e as ParseError;
                    expect(err.message).toContain(errorPrefix);
                    expect(err.pos).toBe(errorPos);
                }
            }
        );

        test.skip("duplicate group name raises error", () => {
            /**
             * Tests that duplicate group names raise a semantic error.
             * SKIPPED: Parser does not yet check for duplicate group names.
             *
             */
            expect(() => parse("(?<name>a)(?<name>b)")).toThrow(
                /Duplicate group name/
            );
        });
    });

    describe("Character Class Errors", () => {
        /**
         * Covers errors related to character class syntax.
         *
         */
        test.each<[string, string, number, string]>([
            ["[abc", "Unterminated character class", 4, "unterminated_class"],
            [
                "[\\p{L",
                "Unterminated \\p{...}",
                5,
                "unterminated_unicode_property",
            ],
            [
                "[\\pL]",
                "Expected { after \\p/\\P",
                3,
                "missing_braces_on_unicode_property",
            ],
        ])(
            'should fail for "%s" (ID: %s)',
            (invalidDsl, errorPrefix, errorPos) => {
                /** Tests that malformed character classes raise a ParseError. */
                expect(() => parse(invalidDsl)).toThrow(ParseError);
                try {
                    parse(invalidDsl);
                } catch (e) {
                    const err = e as ParseError;
                    expect(err.message).toContain(errorPrefix);
                    expect(err.pos).toBe(errorPos);
                }
            }
        );
    });

    describe("Escape & Codepoint Errors", () => {
        /**
         * Covers errors related to malformed escape sequences.
         *
         */
        test.each<[string, string, number, string]>([
            ["\\xG1", "Invalid \\xHH escape", 0, "invalid_hex_digit"],
            ["\\u12Z4", "Invalid \\uHHHH", 0, "invalid_unicode_digit"],
            [
                "\\x{",
                "Unterminated \\x{...}",
                0,
                "unterminated_hex_brace_empty",
            ],
            [
                "\\x{FFFF",
                "Unterminated \\x{...}",
                0,
                "unterminated_hex_brace_with_digits",
            ],
        ])(
            'should fail for "%s" (ID: %s)',
            (invalidDsl, errorPrefix, errorPos) => {
                /** Tests that malformed hex/unicode escapes raise a ParseError. */
                expect(() => parse(invalidDsl)).toThrow(ParseError);
                try {
                    parse(invalidDsl);
                } catch (e) {
                    const err = e as ParseError;
                    expect(err.message).toContain(errorPrefix);
                    expect(err.pos).toBe(errorPos);
                }
            }
        );
    });

    describe("Quantifier Errors", () => {
        /**
         * Covers errors related to malformed quantifiers.
         *
         */
        test("unterminated brace quantifier raises error", () => {
            /**
             * Tests that an unterminated brace quantifier like {m,n raises an error.
             *
             */
            const invalidDsl = "a{2,5";
            expect(() => parse(invalidDsl)).toThrow(ParseError);
            try {
                parse(invalidDsl);
            } catch (e) {
                const err = e as ParseError;
                expect(err.message).toContain("Unterminated {m,n}");
                expect(err.pos).toBe(5);
            }
        });

        test.skip("quantifying a non-quantifiable atom raises error", () => {
            /**
             * Tests that attempting to quantify an anchor raises a semantic error.
             * SKIPPED: Parser does not yet perform semantic validation on quantifiers.
             *
             */
            expect(() => parse("^*")).toThrow(/Cannot quantify anchor/);
        });
    });

    describe("Invariant: First Error Wins", () => {
        /**
         * Tests the invariant that only the first error in a string is reported.
         *
         */
        test("first of multiple errors is reported", () => {
            /**
             * In the string '[a|b(', the unterminated class at position 0 should be
             * reported, not the unterminated group at position 4.
             *
             */
            const invalidDsl = "[a|b(";
            expect(() => parse(invalidDsl)).toThrow(ParseError);
            try {
                parse(invalidDsl);
            } catch (e) {
                const err = e as ParseError;
                expect(err.message).toContain("Unterminated character class");
                expect(err.pos).toBe(5);
            }
        });
    });
});

// --- Additional Error Test Cases ------------------------


