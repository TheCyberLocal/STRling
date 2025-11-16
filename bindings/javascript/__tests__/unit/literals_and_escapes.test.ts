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
 *
 * -   Parsing of all supported escape sequences (`\x`, `\u`, `\U`, `\0`, identity).
 *
 * -   Error handling for malformed or unsupported escapes (like octal).
 *
 * -   The shape of the resulting `Lit` AST node.
 *
 * -   **Out of scope:**
 * -   How literals are quantified (covered in `quantifiers.test.ts`).
 *
 * -   How literals behave inside character classes (covered in `char_classes.test.ts`).
 *
 * -   Emitter-specific escaping (covered in `emitter_edges.test.ts`).
 */

// Note: Adjust import paths as needed for your project structure
import { parse, ParseError } from "../../src/STRling/core/parser";
import {
    Lit,
    Seq,
    Backref,
    Node,
    Quant,
    Alt,
    Group,
} from "../../src/STRling/core/nodes";

// --- Test Suite -----------------------------------------------------------------

describe("Category A: Positive Cases", () => {
    /**
     * Covers all positive cases for valid literal and escape syntax.
     */

    test.each<[string, Node, string]>([
        // A.1: Plain Literals
        ["a", new Lit("a"), "plain_literal_letter"],
        ["_", new Lit("_"), "plain_literal_underscore"],
        // A.2: Identity Escapes
        [String.raw`\.`, new Lit("."), "identity_escape_dot"],
        [String.raw`\(`, new Lit("("), "identity_escape_paren"],
        [String.raw`\*`, new Lit("*"), "identity_escape_star"],
        // Note: The Python test `r"\\\\"` is parsed as a Lit("\\\\") due to Python's r-string.
        // The equivalent DSL input `\\\\` (two backslashes) parses to a Lit("\\").
        // To match the Python test's *intent* (a literal `\\` string), the DSL must be `\\\\`.
        // But to match the Python test's *output* (Lit("\\\\")), the DSL must be `\\\\\\`.
        // We will match the Python test's *output AST* which means the input string must be `\\\\`.
        [String.raw`\\\\`, new Lit("\\\\"), "identity_escape_backslash"],
        // A.3: Control & Whitespace Escapes
        [String.raw`\n`, new Lit("\n"), "control_escape_newline"],
        [String.raw`\t`, new Lit("\t"), "control_escape_tab"],
        [String.raw`\r`, new Lit("\r"), "control_escape_carriage_return"],
        [String.raw`\f`, new Lit("\f"), "control_escape_form_feed"],
        [String.raw`\v`, new Lit("\v"), "control_escape_vertical_tab"],
        // A.4: Hexadecimal Escapes
        [String.raw`\x41`, new Lit("A"), "hex_escape_fixed"],
        [String.raw`\x4a`, new Lit("J"), "hex_escape_fixed_case"],
        [String.raw`\x{41}`, new Lit("A"), "hex_escape_brace"],
        [String.raw`\x{1F600}`, new Lit("😀"), "hex_escape_brace_non_bmp"],
        // A.5: Unicode Escapes
        [String.raw`\u0041`, new Lit("A"), "unicode_escape_fixed"],
        [String.raw`\u{41}`, new Lit("A"), "unicode_escape_brace_bmp"],
        [String.raw`\u{1f600}`, new Lit("😀"), "unicode_escape_brace_non_bmp"],
        [String.raw`\U0001F600`, new Lit("😀"), "unicode_escape_fixed_supplementary"],
        // A.6: Null Byte Escape
        [String.raw`\0`, new Lit("\x00"), "null_byte_escape"],
    ])(
        'should parse "%s" (ID: %s)',
        (inputDsl, expectedAst, id) => {
            /**
             * Tests that a valid literal or escape sequence is parsed into the correct
             * Lit AST node.
             */
            const [, ast] = parse(inputDsl);
            expect(ast).toEqual(expectedAst);
        }
    );
});

describe("Category B: Negative Cases", () => {
    /**
     * Covers negative cases for malformed or unsupported syntax.
     */

    test.each<[string, string, number, string]>([
        // B.1: Malformed Hex/Unicode
        [String.raw`\x{12`, "Unterminated \\x{...}", 0, "unterminated_hex_brace"],
        [String.raw`\xG`, "Invalid \\xHH escape", 0, "invalid_hex_char_short"],
        [String.raw`\u{1F60`, "Unterminated \\u{...}", 0, "unterminated_unicode_brace"],
        [String.raw`\u123`, "Invalid \\uHHHH", 0, "incomplete_unicode_fixed"],
        [String.raw`\U1234567`, "Invalid \\UHHHHHHHH", 0, "incomplete_unicode_supplementary"],
        // B.2: Stray Metacharacters
            [")", "Unmatched ')'", 0, "stray_closing_paren"],
        ["|", "Alternation lacks left-hand side", 0, "stray_pipe"],
    ])(
        'should fail for "%s" (ID: %s)',
        (invalidDsl, errorPrefix, errorPos, id) => {
            /**
             * Tests that malformed escape syntax raises a ParseError with the correct
             * message and position.
             */
            expect(() => parse(invalidDsl)).toThrow(ParseError);
            try {
                parse(invalidDsl);
                fail("ParseError was not thrown");
            } catch (e) {
                const err = e as ParseError;
                if (id === "stray_closing_paren") {
                    expect(err.message).toBe("Unmatched ')'");
                } else {
                    expect(err.message).toContain(errorPrefix);
                }
                expect(err.pos).toBe(errorPos);
            }
        }
    );

    test("should fail for forbidden octal escape (undefined backreference)", () => {
        /**
         * Tests that a forbidden octal escape (e.g., \123) with no groups defined
         * raises a ParseError for undefined backreference.
         */
        expect(() => parse(String.raw`\123`)).toThrow(ParseError);
        expect(() => parse(String.raw`\123`)).toThrow(
            /Backreference to undefined group/
        );
    });
});

describe("Category C: Edge Cases", () => {
    /**
     * Covers edge cases for literals and escapes.
     */

    test.each<[string, string, string]>([
        [String.raw`\u{10FFFF}`, "\u{10FFFF}", "max_unicode_value"],
        [String.raw`\x{0}`, "\x00", "zero_value_hex_brace"],
        [String.raw`\x{}`, "\x00", "empty_hex_brace"],
    ])(
        'should correctly parse edge case escape "%s" (ID: %s)',
        (inputDsl, expectedChar, id) => {
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
        const [, ast] = parse(String.raw`\\\\0`);
        expect(ast).toEqual(new Seq([new Lit("\\\\"), new Lit("0")]));
    });
});

describe("Category D: Interaction Cases", () => {
    /**
     * Covers interactions between literals/escapes and free-spacing mode.
     */

    test("should ignore whitespace between literals in free-spacing mode", () => {
        /**
         * Tests that in free-spacing mode, whitespace between literals is
         * ignored, resulting in a sequence of Lit nodes.
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
        const [, ast] = parse(`%flags x\n a \\ b `);
        expect(ast).toEqual(
            new Seq([new Lit("a"), new Lit(" "), new Lit("b")])
        );
    });
});

// --- New Test Stubs for 3-Test Standard Compliance -----------------------------

describe("Category E: Literal Sequences And Coalescing", () => {
    /**
     * Tests for sequences of literals and how the parser handles coalescing.
     */

    test("should parse multiple plain literals in sequence", () => {
        /**
         * Tests sequence of plain literals: abc
         * Should parse as single Lit("abc").
         */
        const [, ast] = parse("abc");
        expect(ast).toBeInstanceOf(Lit);
        expect((ast as Lit).value).toBe("abc");
    });

    test("should parse literals with escaped metachar sequence", () => {
        /**
         * Tests literals mixed with escaped metachars: a\*b\+c
         */
        const [, ast] = parse(String.raw`a\*b\+c`);
        expect(ast).toBeInstanceOf(Lit);
        expect((ast as Lit).value).toBe("a*b+c");
    });

    test("should parse sequence of only escapes", () => {
        /**
         * Tests sequence of only escape sequences: \n\t\r
         */
        const [, ast] = parse(String.raw`\n\t\r`);
        expect(ast).toBeInstanceOf(Seq);
        // Verify all parts are Lit nodes
        for (const part of (ast as Seq).parts) {
            expect(part).toBeInstanceOf(Lit);
        }
    });

    test("should parse mixed escape types in sequence", () => {
        /**
         * Tests mixed escape types in sequence: \x41\u0042\n
         * Hex, Unicode, and control escapes together.
         */
        const [, ast] = parse(String.raw`\x41\u0042\n`);
        // The parser may coalesce these into Lit or Seq
        expect(ast).toBeInstanceOf(Node); // Base check
        if (ast instanceof Seq) {
            // Verify all parts are Lit nodes
            for (const part of ast.parts) {
                expect(part).toBeInstanceOf(Lit);
            }
        } else {
            expect(ast).toBeInstanceOf(Lit);
        }
    });
});

describe("Category F: Escape Interactions", () => {
    /**
     * Tests for interactions between different escape types and literals.
     */

    test("should parse literal after control escape", () => {
        /**
         * Tests literal after control escape: \na (newline followed by 'a')
         */
        const [, ast] = parse(String.raw`\na`);
        expect(ast).toBeInstanceOf(Seq);
        const seqNode = ast as Seq;
        expect(seqNode.parts).toHaveLength(2);
        expect(seqNode.parts[0]).toBeInstanceOf(Lit);
        expect((seqNode.parts[0] as Lit).value).toBe("\n");
        expect(seqNode.parts[1]).toBeInstanceOf(Lit);
        expect((seqNode.parts[1] as Lit).value).toBe("a");
    });

    test("should parse literal after hex escape", () => {
        /**
         * Tests literal after hex escape: \x41b (A followed by 'b')
         */
        const [, ast] = parse(String.raw`\x41b`);
        expect(ast).toBeInstanceOf(Lit);
        expect((ast as Lit).value).toBe("Ab");
    });

    test("should parse escape after escape", () => {
        /**
         * Tests escape after escape: \n\t (newline followed by tab)
         * Already covered but confirming.
         */
        const [, ast] = parse(String.raw`\n\t`);
        expect(ast).toBeInstanceOf(Seq);
        // Verify all parts are Lit nodes
        for (const part of (ast as Seq).parts) {
            expect(part).toBeInstanceOf(Lit);
        }
    });

    test("should parse identity escape after literal", () => {
        /**
         * Tests identity escape after literal: a\* ('a' followed by '*')
         */
        const [, ast] = parse(String.raw`a\*`);
        expect(ast).toBeInstanceOf(Lit);
        expect((ast as Lit).value).toBe("a*");
    });
});

describe("Category G: Backslash Escape Combinations", () => {
    /**
     * Tests for various backslash escape combinations.
     */

    test("should parse double backslash", () => {
        /**
         * Tests double backslash: \\
         * Should parse as single backslash character.
         */
        const [, ast] = parse(String.raw`\\`);
        expect(ast).toBeInstanceOf(Lit);
        expect((ast as Lit).value).toBe("\\");
    });

    test("should parse quadruple backslash", () => {
        /**
         * Tests quadruple backslash: \\\\
         * Should parse as two backslash characters.
         */
        const [, ast] = parse(String.raw`\\\\`);
        expect(ast).toBeInstanceOf(Lit);
        expect((ast as Lit).value).toBe("\\\\");
    });

    test("should parse backslash before literal", () => {
        /**
         * Tests backslash followed by non-metachar: \\a
         * Should parse as backslash followed by 'a'.
         */
        const [, ast] = parse(String.raw`\\a`);
        expect(ast).toBeInstanceOf(Lit);
        expect((ast as Lit).value).toBe("\\a");
    });
});

describe("Category H: Escape Edge Cases Expanded", () => {
    /**
     * Additional edge cases for escape sequences.
     */

    test("should parse hex escape min value", () => {
        /**
         * Tests minimum hex value: \x00
         */
        const [, ast] = parse(String.raw`\x00`);
        expect(ast).toBeInstanceOf(Lit);
        expect((ast as Lit).value).toBe("\x00");
    });

    test("should parse hex escape max value", () => {
        /**
         * Tests maximum single-byte hex value: \xFF
         */
        const [, ast] = parse(String.raw`\xFF`);
        expect(ast).toBeInstanceOf(Lit);
        expect((ast as Lit).value).toBe("\xFF");
    });

    test("should parse unicode escape BMP boundary", () => {
        /**
         * Tests Unicode at BMP boundary: \uFFFF
         */
        const [, ast] = parse(String.raw`\uFFFF`);
        expect(ast).toBeInstanceOf(Lit);
        expect((ast as Lit).value).toBe("\uFFFF");
    });

    test("should parse unicode escape supplementary plane", () => {
        /**
         * Tests Unicode in supplementary plane: \U00010000
         * First character outside BMP.
         */
        const [, ast] = parse(String.raw`\U00010000`);
        expect(ast).toBeInstanceOf(Lit);
        expect((ast as Lit).value).toBe("\u{10000}");
    });
});

describe("Category I: Octal And Backref Disambiguation", () => {
    /**
     * Tests for the parser's handling of octal-like sequences and
     * their disambiguation with backreferences.
     */

    test("should raise error for single digit backslash with no groups", () => {
        /**
         * Tests that \1 with no groups raises backreference error, not octal.
         */
        expect(() => parse(String.raw`\1`)).toThrow(ParseError);
        expect(() => parse(String.raw`\1`)).toThrow(
            /Backreference to undefined group/
        );
    });

    test("should parse two digit sequence with one group", () => {
        /**
         * Tests (a)\12: should be backref \1 followed by literal '2'.
         */
        const [, ast] = parse(String.raw`(a)\12`);
        expect(ast).toBeInstanceOf(Seq);
        const seqNode = ast as Seq;
        expect(seqNode.parts).toHaveLength(3);
        expect(seqNode.parts[0]).toBeInstanceOf(Group);
        expect(seqNode.parts[1]).toBeInstanceOf(Backref);
        expect((seqNode.parts[1] as Backref).byIndex).toBe(1);
        expect(seqNode.parts[2]).toBeInstanceOf(Lit);
        expect((seqNode.parts[2] as Lit).value).toBe("2");
    });

    test("should raise error for three digit sequence (undefined backref)", () => {
        /**
         * Tests \123 parsing behavior (backref or error).
         */
        expect(() => parse(String.raw`\123`)).toThrow(ParseError);
        expect(() => parse(String.raw`\123`)).toThrow(
            /Backreference to undefined group/
        );
    });
});

describe("Category J: Literals In Complex Contexts", () => {
    /**
     * Tests for literal behavior in complex syntactic contexts.
     */

    test("should parse literal between quantifiers", () => {
        /**
         * Tests literal between quantified atoms: a*Xb+
         */
        const [, ast] = parse("a*Xb+");
        expect(ast).toBeInstanceOf(Seq);
        const seqNode = ast as Seq;
        expect(seqNode.parts).toHaveLength(3);
        expect(seqNode.parts[0]).toBeInstanceOf(Quant);
        expect(seqNode.parts[1]).toBeInstanceOf(Lit);
        expect((seqNode.parts[1] as Lit).value).toBe("X");
        expect(seqNode.parts[2]).toBeInstanceOf(Quant);
    });

    test("should parse literal in alternation", () => {
        /**
         * Tests literal in alternation: a|b|c
         */
        const [, ast] = parse("a|b|c");
        expect(ast).toBeInstanceOf(Alt);
        const altNode = ast as Alt;
        expect(altNode.branches).toHaveLength(3);
        expect(altNode.branches[0]).toBeInstanceOf(Lit);
        expect((altNode.branches[0] as Lit).value).toBe("a");
        expect(altNode.branches[1]).toBeInstanceOf(Lit);
        expect((altNode.branches[1] as Lit).value).toBe("b");
        expect(altNode.branches[2]).toBeInstanceOf(Lit);
        expect((altNode.branches[2] as Lit).value).toBe("c");
    });

    test("should parse escaped literal in group", () => {
        /**
         * Tests escaped literal inside group: (\*)
         */
        const [, ast] = parse(String.raw`(\*)`);
        expect(ast).toBeInstanceOf(Group);
        const groupNode = ast as Group;
        expect(groupNode.capturing).toBe(true);
        expect(groupNode.body).toBeInstanceOf(Lit);
        expect((groupNode.body as Lit).value).toBe("*");
    });
});
