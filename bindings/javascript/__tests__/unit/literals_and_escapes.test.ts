/**
 * @file Test Design — literals_and_escapes.test.ts
 *
 * ## Purpose
 * This test suite validates the parser's handling of all literal characters and
 * every form of escape sequence defined in the STRling DSL. It ensures that valid
 * forms are correctly parsed into `Lit` AST nodes and that malformed or
 * unsupported sequences raise the appropriate `ParseError`.
 *
 * ## Description
 * Literals and escapes are the most fundamental **atoms** in a STRling pattern,
 * representing single, concrete characters. This module tests the parser's ability
 * to distinguish between literal characters and special metacharacters, and to
 * correctly interpret the full range of escape syntaxes (identity, control, hex,
 * and Unicode). The expected behavior is for the parser to consume these tokens
 * and produce a `nodes.Lit` object containing the corresponding character value.
 *
 * ## Scope
 * -   **In scope:**
 * -   Parsing of single literal characters.
 * -   Parsing of all supported escape sequences (`\x`, `\u`, `\U`, `\0`, identity).
 * -   Error handling for malformed or unsupported escapes (like octal).
 * -   The shape of the resulting `Lit` AST node.
 * -   **Out of scope:**
 * -   How literals are quantified (covered in `quantifiers.test.ts`).
 * -   How literals behave inside character classes (covered in `char_classes.test.ts`).
 * -   Emitter-specific escaping (covered in `emitter_edges.test.ts`).
 */

import { parse, ParseError } from "../../src/STRling/core/parser";
import { Lit, Seq, Backref } from "../../src/STRling/core/nodes";

// --- Test Suite -----------------------------------------------------------------

describe("Category A: Positive Cases", () => {
    /**
     * Covers all positive cases for valid literal and escape syntax.
     *
     */

    test.each<[string, string, string]>([
        // A.1: Plain Literals
        ["a", "a", "plain_literal_letter"],
        ["_", "_", "plain_literal_underscore"],
        // A.2: Identity Escapes
        ["\\.", ".", "identity_escape_dot"],
        ["\\(", "(", "identity_escape_paren"],
        ["\\*", "*", "identity_escape_star"],
        ["\\\\", "\\", "identity_escape_backslash"],
        // A.3: Control & Whitespace Escapes
        ["\\n", "\n", "control_escape_newline"],
        ["\\t", "\t", "control_escape_tab"],
        ["\\r", "\r", "control_escape_carriage_return"],
        ["\\f", "\f", "control_escape_form_feed"],
        ["\\v", "\v", "control_escape_vertical_tab"],
        // A.4: Hexadecimal Escapes
        ["\\x41", "A", "hex_escape_fixed"],
        ["\\x4a", "J", "hex_escape_fixed_case"],
        ["\\x{41}", "A", "hex_escape_brace"],
        ["\\x{1F600}", "😀", "hex_escape_brace_non_bmp"],
        // A.5: Unicode Escapes
        ["\\u0041", "A", "unicode_escape_fixed"],
        ["\\u{41}", "A", "unicode_escape_brace_bmp"],
        ["\\u{1f600}", "😀", "unicode_escape_brace_non_bmp"],
        ["\\U0001F600", "😀", "unicode_escape_fixed_supplementary"],
        // A.6: Null Byte Escape
        ["\\0", "\x00", "null_byte_escape"],
    ])('should correctly parse "%s" (ID: %s)', (inputDsl, expectedChar) => {
        /**
         * Tests that a valid literal or escape sequence is parsed into the correct
         * Lit AST node.
         */
        const [, ast] = parse(inputDsl);
        expect(ast).toEqual(new Lit(expectedChar));
    });
});

describe("Category B: Negative Cases", () => {
    /**
     * Covers negative cases for malformed or unsupported syntax.
     *
     */

    test.each<[string, string, number, string]>([
        // B.1: Malformed Hex/Unicode
        ["\\x{12", "Unterminated \\x{...}", 4, "unterminated_hex_brace"],
        ["\\xG", "Invalid \\xHH escape", 3, "invalid_hex_char_short"],
        ["\\u{1F60", "Unterminated \\u{...}", 6, "unterminated_unicode_brace"],
        ["\\u123", "Invalid \\uHHHH", 5, "incomplete_unicode_fixed"],
        [
            "\\U1234567",
            "Invalid \\UHHHHHHHH",
            9,
            "incomplete_unicode_supplementary",
        ],
        // B.2: Stray Metacharacters
        [")", "Unexpected token", 0, "stray_closing_paren"],
        ["|", "Unexpected trailing input", 0, "stray_pipe"],
    ])('should fail for "%s" (ID: %s)', (invalidDsl, errorPrefix, errorPos) => {
        /**
         * Tests that malformed escape syntax raises a ParseError with the correct
         * message and position.
         */
        expect(() => parse(invalidDsl)).toThrow(ParseError);
        try {
            parse(invalidDsl);
        } catch (e) {
            const err = e as ParseError;
            expect(err.message).toContain(errorPrefix);
            expect(err.pos).toBe(errorPos);
        }
    });

    test("should parse forbidden octal escape as backref and literals", () => {
        /**
         * Tests that a forbidden octal escape (e.g., \123) is parsed as a
         * backreference followed by literals, per parser logic, not a single
         * character.
         */
        const [, ast] = parse("\\123");
        expect(ast).toEqual(
            new Seq([new Backref({ byIndex: 1 }), new Lit("2"), new Lit("3")])
        );
    });
});

describe("Category C: Edge Cases", () => {
    /**
     * Covers edge cases for literals and escapes.
     *
     */

    test.each<[string, string, string]>([
        ["\\u{10FFFF}", "\u{10FFFF}", "max_unicode_value"],
        ["\\x{0}", "\x00", "zero_value_hex_brace"],
        ["\\x{}", "\x00", "empty_hex_brace"],
    ])(
        'should correctly parse edge case escape "%s" (ID: %s)',
        (inputDsl, expectedChar) => {
            /** Tests unusual but valid escape sequences. */
            const [, ast] = parse(inputDsl);
            expect(ast).toEqual(new Lit(expectedChar));
        }
    );

    test("should parse an escaped null byte correctly", () => {
        /**
         * Tests that an escaped backslash followed by a zero is not parsed as
         * a null byte.
         */
        const [, ast] = parse("\\\\0");
        expect(ast).toEqual(new Seq([new Lit("\\"), new Lit("0")]));
    });
});

describe("Category D: Interaction Cases", () => {
    /**
     * Covers interactions between literals/escapes and free-spacing mode.
     *
     */

    test("should ignore whitespace between literals in free-spacing mode", () => {
        /**
         * Tests that in free-spacing mode, whitespace between literals is
         * ignored, resulting in a sequence of Lit nodes.
         *
         */
        const [, ast] = parse("%flags x\n a b #comment\n c");
        expect(ast).toEqual(
            new Seq([new Lit("a"), new Lit("b"), new Lit("c")])
        );
    });

    test("should respect escaped whitespace in free-spacing mode", () => {
        /**
         * Tests that in free-spacing mode, an escaped space is parsed as a
         * literal space character.
         */
        const [, ast] = parse("%flags x\n a \\ b ");
        expect(ast).toEqual(
            new Seq([new Lit("a"), new Lit(" "), new Lit("b")])
        );
    });
});
