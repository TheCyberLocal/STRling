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
import { Lit, Seq, Backref, Group, Look, Quant } from "../../src/STRling/core/nodes";

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
        ["\\x{12", "Unterminated \\x{...}", 0, "unterminated_hex_brace"],
        ["\\xG", "Invalid \\xHH escape", 0, "invalid_hex_char_short"],
        ["\\u{1F60", "Unterminated \\u{...}", 0, "unterminated_unicode_brace"],
        ["\\u123", "Invalid \\uHHHH", 0, "incomplete_unicode_fixed"],
        [
            "\\U1234567",
            "Invalid \\UHHHHHHHH",
            0,
            "incomplete_unicode_supplementary",
        ],
        // B.2: Stray Metacharacters
        [")", "Unexpected trailing input", 0, "stray_closing_paren"],
        ["|", "Alternation lacks left-hand side", 0, "stray_pipe"],
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

    test("should fail for forbidden octal escape with no groups", () => {
        /**
         * Tests that a forbidden octal escape (e.g., \123) with no groups defined
         * raises a ParseError for undefined backreference.
         */
        expect(() => parse("\\123")).toThrow(ParseError);
        try {
            parse("\\123");
        } catch (e) {
            const err = e as ParseError;
            expect(err.message).toContain("Backreference to undefined group");
        }
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

// --- New Test Categories for 3-Test Standard Compliance ------------------------

describe('Category E: Literal Sequences And Coalescing', () => {
  test('should parse consecutive literals as sequence', () => {
    const [, ast] = parse('abc');
    expect(ast).toBeInstanceOf(Lit);
    expect((ast as Lit).value).toBe('abc');
  });

  test('should coalesce adjacent literal strings', () => {
    const [, ast] = parse('hello world');
    expect(ast).toBeInstanceOf(Lit);
    expect((ast as Lit).value).toBe('hello world');
  });

  test('should handle escaped chars in sequences', () => {
    const [, ast] = parse('a\\tb\\nc');
    expect(ast).toBeInstanceOf(Seq);
    const seqNode = ast as Seq;
    expect(seqNode.parts).toHaveLength(3);
    expect(seqNode.parts[0]).toBeInstanceOf(Lit);
    expect((seqNode.parts[0] as Lit).value).toBe('a\tb');
    expect(seqNode.parts[1]).toBeInstanceOf(Lit);
    expect((seqNode.parts[1] as Lit).value).toBe('\n');
    expect(seqNode.parts[2]).toBeInstanceOf(Lit);
    expect((seqNode.parts[2] as Lit).value).toBe('c');
  });
});

describe('Category F: Escape Interactions', () => {
  test('should parse escape followed by quantifier', () => {
    const [, ast] = parse('\\d+');
    expect(ast).toBeInstanceOf(Quant);
    const quantNode = ast as Quant;
    expect(quantNode.child.constructor.name).toBe('CharClass');
  });

  test('should parse escaped backslash followed by literal', () => {
    const [, ast] = parse('\\\\a');
    expect(ast).toBeInstanceOf(Lit);
    expect((ast as Lit).value).toBe('\\a');
  });

  test('should parse multiple escape sequences', () => {
    const [, ast] = parse('\\n\\r\\t');
    expect(ast).toBeInstanceOf(Seq);
    const seqNode = ast as Seq;
    expect(seqNode.parts).toHaveLength(2);
    expect(seqNode.parts[0]).toBeInstanceOf(Lit);
    expect((seqNode.parts[0] as Lit).value).toBe('\n');
    expect(seqNode.parts[1]).toBeInstanceOf(Lit);
    expect((seqNode.parts[1] as Lit).value).toBe('\r\t');
  });
});

describe('Category G: Backslash Escape Combinations', () => {
  test.each<[string, string, string]>([
    ['\\n', '\n', 'newline'],
    ['\\r', '\r', 'carriage_return'],
    ['\\t', '\t', 'tab'],
    ['\\f', '\f', 'form_feed'],
    ['\\v', '\v', 'vertical_tab'],
  ])('should parse backslash escape %s (ID: %s)', (inputDsl, expectedValue) => {
    const [, ast] = parse(inputDsl);
    expect(ast).toBeInstanceOf(Lit);
    expect((ast as Lit).value).toBe(expectedValue);
  });
});

describe('Category H: Escape Edge Cases Expanded', () => {
  test('should parse hex escape lowercase', () => {
    const [, ast] = parse('\\x41');
    expect(ast).toBeInstanceOf(Lit);
    expect((ast as Lit).value).toBe('A');
  });

  test('should parse unicode escape', () => {
    const [, ast] = parse('\\u0041');
    expect(ast).toBeInstanceOf(Lit);
    expect((ast as Lit).value).toBe('A');
  });

  test('should parse extended hex escape', () => {
    const [, ast] = parse('\\x{41}');
    expect(ast).toBeInstanceOf(Lit);
    expect((ast as Lit).value).toBe('A');
  });
});

describe('Category I: Octal And Backref Disambiguation', () => {
  test('should parse null byte as literal', () => {
    const [, ast] = parse('\\0');
    expect(ast).toBeInstanceOf(Lit);
    expect((ast as Lit).value).toBe('\x00');
  });

  test('should raise error for two-digit octal (treated as undefined backref)', () => {
    expect(() => parse('\\77')).toThrow(ParseError);
  });

  test('should raise error for three-digit octal (treated as undefined backref)', () => {
    expect(() => parse('\\101')).toThrow(ParseError);
  });
});

describe('Category J: Literals In Complex Contexts', () => {
  test('should parse literal in group', () => {
    const [, ast] = parse('(abc)');
    expect(ast).toBeInstanceOf(Group);
    const groupNode = ast as Group;
    expect(groupNode.body).toBeInstanceOf(Lit);
    expect((groupNode.body as Lit).value).toBe('abc');
  });

  test('should parse literal in lookahead', () => {
    const [, ast] = parse('(?=test)');
    expect(ast).toBeInstanceOf(Look);
    const lookNode = ast as Look;
    expect(lookNode.body).toBeInstanceOf(Lit);
    expect((lookNode.body as Lit).value).toBe('test');
  });

  test('should parse literal in alternation', () => {
    const [, ast] = parse('abc|def');
    expect(ast.constructor.name).toBe('Alt');
    const altNode = ast as any;
    expect(altNode.branches[0]).toBeInstanceOf(Lit);
    expect((altNode.branches[0] as Lit).value).toBe('abc');
    expect(altNode.branches[1]).toBeInstanceOf(Lit);
    expect((altNode.branches[1] as Lit).value).toBe('def');
  });
});

// --- Additional Literal Test Cases for Parity ------------------------


// --- Additional tests to reach parity with Python ------------------------

