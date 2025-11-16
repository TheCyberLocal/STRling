/**
 * @file Test Design — char_classes.test.ts
 *
 * ## Purpose
 * This test suite validates the correct parsing of character classes, ensuring
 * all forms—including literals, ranges, shorthands, and Unicode properties—are
 * correctly transformed into `CharClass` AST nodes. It also verifies that
 * negation, edge cases involving special characters, and invalid syntax are
 * handled according to the DSL's semantics.
 *
 * ## Description
 * Character classes (`[...]`) are a fundamental feature of the STRling DSL,
 * allowing a pattern to match any single character from a specified set. This
 * suite tests the parser's ability to correctly handle the various components
 * that can make up these sets: literal characters, character ranges (`a-z`),
 * shorthand escapes (`\d`, `\w`), and Unicode property escapes (`\p{L}`). It also
 * ensures that class-level negation (`[^...]`) and the special rules for
 * metacharacters (`-`, `]`, `^`) within classes are parsed correctly.
 *
 * ## Scope
 * -   **In scope:**
 * -   Parsing of positive `[abc]` and negative `[^abc]` character classes.
 * -   Parsing of character ranges (`[a-z]`, `[0-9]`) and their validation.
 * -   Parsing of all supported shorthand (`\d`, `\s`, `\w` and their negated
 * counterparts) and Unicode property (`\p{...}`, `\P{...}`) escapes
 * within a class.
 * -   The special syntactic rules for `]`, `-`, `^`, and escapes like `\b`
 * when they appear inside a class.
 * -   Error handling for malformed classes (e.g., unterminated `[` or invalid
 * ranges `[z-a]`).
 * -   The structure of the resulting `nodes.CharClass` AST node and its list
 * of `items`.
 * -   **Out of scope:**
 * -   Quantification of an entire character class (covered in
 * `quantifiers.test.ts`).
 * -   The behavior of character classes within groups or lookarounds.
 * -   Emitter-specific optimizations or translations (covered in
 * `emitter_edges.test.ts`).
 */

// Note: Adjust import paths as needed for your project structure
import { parse, ParseError } from "../../src/STRling/core/parser";
import {
    CharClass,
    ClassItem,
    ClassLiteral,
    ClassRange,
    ClassEscape,
    Seq,
} from "../../src/STRling/core/nodes";

// --- Test Suite -----------------------------------------------------------------

describe("Category A: Positive Cases", () => {
    /**
     * Covers all positive cases for valid character class syntax.
     */

    test.each<[string, boolean, ClassItem[], string]>([
        // A.1: Basic Classes
        [
            "[abc]",
            false,
            [
                new ClassLiteral("a"),
                new ClassLiteral("b"),
                new ClassLiteral("c"),
            ],
            "simple_class",
        ],
        [
            "[^abc]",
            true,
            [
                new ClassLiteral("a"),
                new ClassLiteral("b"),
                new ClassLiteral("c"),
            ],
            "negated_simple_class",
        ],
        // A.2: Ranges
        ["[a-z]", false, [new ClassRange("a", "z")], "range_lowercase"],
        [
            "[A-Za-z0-9]",
            false,
            [
                new ClassRange("A", "Z"),
                new ClassRange("a", "z"),
                new ClassRange("0", "9"),
            ],
            "range_alphanum",
        ],
        // A.3: Shorthand Escapes
        [
            String.raw`[\d\s\w]`,
            false,
            [new ClassEscape("d"), new ClassEscape("s"), new ClassEscape("w")],
            "shorthand_positive",
        ],
        [
            String.raw`[\D\S\W]`,
            false,
            [new ClassEscape("D"), new ClassEscape("S"), new ClassEscape("W")],
            "shorthand_negated",
        ],
        // A.4: Unicode Property Escapes
        [
            String.raw`[\p{L}]`,
            false,
            [new ClassEscape("p", "L")],
            "unicode_property_short",
        ],
        [
            String.raw`[\p{Letter}]`,
            false,
            [new ClassEscape("p", "Letter")],
            "unicode_property_long",
        ],
        [
            String.raw`[\P{Number}]`,
            false,
            [new ClassEscape("P", "Number")],
            "unicode_property_negated",
        ],
        [
            String.raw`[\p{Script=Greek}]`,
            false,
            [new ClassEscape("p", "Script=Greek")],
            "unicode_property_with_value",
        ],
        // A.5: Special Character Handling
        [
            "[]a]",
            false,
            [new ClassLiteral("]"), new ClassLiteral("a")],
            "special_char_bracket_at_start",
        ],
        [
            "[^]a]",
            true,
            [new ClassLiteral("]"), new ClassLiteral("a")],
            "special_char_bracket_at_start_negated",
        ],
        [
            "[-az]",
            false,
            [
                new ClassLiteral("-"),
                new ClassLiteral("a"),
                new ClassLiteral("z"),
            ],
            "special_char_hyphen_at_start",
        ],
        [
            "[az-]",
            false,
            [
                new ClassLiteral("a"),
                new ClassLiteral("z"),
                new ClassLiteral("-"),
            ],
            "special_char_hyphen_at_end",
        ],
        [
            "[a^b]",
            false,
            [
                new ClassLiteral("a"),
                new ClassLiteral("^"),
                new ClassLiteral("b"),
            ],
            "special_char_caret_in_middle",
        ],
        [
            String.raw`[\b]`,
            false,
            [new ClassLiteral("\x08")],
            "special_char_backspace_escape",
        ], // \b is backspace inside class
    ])(
        "should parse valid char class '%s' (ID: %s)",
        (inputDsl, expectedNegated, expectedItems, id) => {
            /**
             * Tests that various valid character classes are parsed into the correct
             * CharClass AST node with the expected items.
             */
            const [, ast] = parse(inputDsl);
            expect(ast).toBeInstanceOf(CharClass);
            const ccNode = ast as CharClass;
            expect(ccNode.negated).toBe(expectedNegated);
            expect(ccNode.items).toEqual(expectedItems);
        }
    );
});

describe("Category B: Negative Cases", () => {
    /**
     * Covers all negative cases for malformed character class syntax.
     */

    test.each<[string, string, number, string]>([
        // B.1: Unterminated classes
        ["[abc", "Unterminated character class", 4, "unterminated_class"],
        ["[", "Unterminated character class", 1, "unterminated_empty_class"],
        [
            "[^",
            "Unterminated character class",
            2,
            "unterminated_negated_empty_class",
        ],
        // B.2: Malformed Unicode properties (Error positions match Python source)
        [
            String.raw`[\p{L`,
            "Unterminated \\p{...}",
            1,
            "unterminated_unicode_property",
        ],
        [
            String.raw`[\pL]`,
            "Expected { after \\p/\\P",
            1,
            "missing_braces_on_unicode_property",
        ],
    ])(
        "should fail to parse '%s' (ID: %s)",
        (invalidDsl, errorMessagePrefix, errorPosition, id) => {
            /**
             * Tests that invalid character class syntax raises a ParseError with the
             * correct message and position.
             */
            try {
                parse(invalidDsl);
                // This line should not be reached
                fail(
                    `Expected parse to throw ParseError for input: ${invalidDsl}`
                );
            } catch (e) {
                expect(e).toBeInstanceOf(ParseError);
                const err = e as ParseError;
                // We check for inclusion to avoid strict matching on platform-specific escape chars (e.g., \\\\ vs \\)
                expect(err.message).toContain(errorMessagePrefix);
                expect(err.pos).toBe(errorPosition);
            }
        }
    );
});

describe("Category C: Edge Cases", () => {
    /**
     * Covers edge cases for character class parsing.
     */

    test.each<[string, ClassItem[], string]>([
        [
            String.raw`[a\-c]`,
            [
                new ClassLiteral("a"),
                new ClassLiteral("-"),
                new ClassLiteral("c"),
            ],
            "escaped_hyphen_is_literal",
        ],
        [
            String.raw`[\x41-\x5A]`,
            [new ClassRange("A", "Z")],
            "range_with_escaped_endpoints",
        ],
        [
            String.raw`[\n\t\d]`,
            [
                new ClassLiteral("\n"),
                new ClassLiteral("\t"),
                new ClassEscape("d"),
            ],
            "class_with_only_escapes",
        ],
    ])(
        "should correctly parse edge case class '%s' (ID: %s)",
        (inputDsl, expectedItems, id) => {
            /**
             * Tests unusual but valid character class constructs.
             */
            const [, ast] = parse(inputDsl);
            expect(ast).toBeInstanceOf(CharClass);
            expect((ast as CharClass).items).toEqual(expectedItems);
        }
    );
});

describe("Category D: Interaction Cases", () => {
    /**
     * Covers how character classes interact with other DSL features, specifically
     * the free-spacing mode flag.
     */

    test.each<[string, ClassItem[], string]>([
        [
            "%flags x\n[a b]",
            [
                new ClassLiteral("a"),
                new ClassLiteral(" "),
                new ClassLiteral("b"),
            ],
            "whitespace_is_literal",
        ],
        [
            "%flags x\n[a#b]",
            [
                new ClassLiteral("a"),
                new ClassLiteral("#"),
                new ClassLiteral("b"),
            ],
            "comment_char_is_literal",
        ],
    ])(
        "should handle '%s' in free-spacing mode (ID: %s)",
        (inputDsl, expectedItems, id) => {
            /**
             * Tests that in free-spacing mode, whitespace and '#' are treated as
             * literal characters inside a class, per the specification.
             */
            const [, ast] = parse(inputDsl);
            expect(ast).toBeInstanceOf(CharClass);
            expect((ast as CharClass).items).toEqual(expectedItems);
        }
    );
});

// --- New Test Stubs for 3-Test Standard Compliance -----------------------------

describe("Category E: Minimal Char Classes", () => {
    /**
     * Tests for character classes with minimal content.
     */

    test("should parse single literal in class", () => {
        /**
         * Tests character class with single literal: [a]
         */
        const [, ast] = parse("[a]");
        expect(ast).toBeInstanceOf(CharClass);
        const ccNode = ast as CharClass;
        expect(ccNode.negated).toBe(false);
        expect(ccNode.items).toHaveLength(1);
        expect(ccNode.items[0]).toBeInstanceOf(ClassLiteral);
        expect((ccNode.items[0] as ClassLiteral).ch).toBe("a");
    });

    test("should parse single literal negated class", () => {
        /**
         * Tests negated class with single literal: [^x]
         */
        const [, ast] = parse("[^x]");
        expect(ast).toBeInstanceOf(CharClass);
        const ccNode = ast as CharClass;
        expect(ccNode.negated).toBe(true);
        expect(ccNode.items).toHaveLength(1);
        expect(ccNode.items[0]).toBeInstanceOf(ClassLiteral);
        expect((ccNode.items[0] as ClassLiteral).ch).toBe("x");
    });

    test("should parse single range in class", () => {
        /**
         * Tests class with only a single range: [a-z]
         * Already exists but validating explicit simple case.
         */
        const [, ast] = parse("[a-z]");
        expect(ast).toBeInstanceOf(CharClass);
        const ccNode = ast as CharClass;
        expect(ccNode.negated).toBe(false);
        expect(ccNode.items).toHaveLength(1);
        expect(ccNode.items[0]).toBeInstanceOf(ClassRange);
        expect((ccNode.items[0] as ClassRange).fromCh).toBe("a");
        expect((ccNode.items[0] as ClassRange).toCh).toBe("z");
    });
});

describe("Category F: Escaped Metachars In Classes", () => {
    /**
     * Tests for escaped metacharacters inside character classes.
     */

    test("should parse escaped dot in class", () => {
        /**
         * Tests escaped dot in class: [\.]
         * The dot should be literal, not a wildcard.
         */
        const [, ast] = parse(String.raw`[\.]`);
        expect(ast).toBeInstanceOf(CharClass);
        const ccNode = ast as CharClass;
        expect(ccNode.items).toHaveLength(1);
        expect(ccNode.items[0]).toBeInstanceOf(ClassLiteral);
        expect((ccNode.items[0] as ClassLiteral).ch).toBe(".");
    });

    test("should parse escaped star in class", () => {
        /**
         * Tests escaped star in class: [\*]
         */
        const [, ast] = parse(String.raw`[\*]`);
        expect(ast).toBeInstanceOf(CharClass);
        const ccNode = ast as CharClass;
        expect(ccNode.items).toHaveLength(1);
        expect(ccNode.items[0]).toBeInstanceOf(ClassLiteral);
        expect((ccNode.items[0] as ClassLiteral).ch).toBe("*");
    });

    test("should parse escaped plus in class", () => {
        /**
         * Tests escaped plus in class: [\+]
         */
        const [, ast] = parse(String.raw`[\+]`);
        expect(ast).toBeInstanceOf(CharClass);
        const ccNode = ast as CharClass;
        expect(ccNode.items).toHaveLength(1);
        expect(ccNode.items[0]).toBeInstanceOf(ClassLiteral);
        expect((ccNode.items[0] as ClassLiteral).ch).toBe("+");
    });

    test("should parse multiple escaped metachars", () => {
        /**
         * Tests multiple escaped metacharacters: [\.\*\+\?]
         */
        const [, ast] = parse(String.raw`[\.\*\+\?]`);
        expect(ast).toBeInstanceOf(CharClass);
        const ccNode = ast as CharClass;
        expect(ccNode.items).toHaveLength(4);
        expect(ccNode.items.every((item) => item instanceof ClassLiteral)).toBe(
            true
        );
        const chars = ccNode.items.map((item) => (item as ClassLiteral).ch);
        expect(chars).toEqual([".", "*", "+", "?"]);
    });

    test("should parse escaped backslash in class", () => {
        /**
         * Tests escaped backslash in class: [\\]
         */
        const [, ast] = parse(String.raw`[\\]`);
        expect(ast).toBeInstanceOf(CharClass);
        const ccNode = ast as CharClass;
        expect(ccNode.items).toHaveLength(1);
        expect(ccNode.items[0]).toBeInstanceOf(ClassLiteral);
        expect((ccNode.items[0] as ClassLiteral).ch).toBe("\\");
    });
});

describe("Category G: Complex Range Combinations", () => {
    /**
     * Tests for character classes with complex range combinations.
     */

    test("should parse multiple non-overlapping ranges", () => {
        /**
         * Tests multiple separate ranges: [a-zA-Z0-9]
         * Already covered but validating as typical case.
         */
        const [, ast] = parse("[a-zA-Z0-9]");
        expect(ast).toBeInstanceOf(CharClass);
        const ccNode = ast as CharClass;
        expect(ccNode.items).toHaveLength(3);
        expect(ccNode.items[0]).toBeInstanceOf(ClassRange);
        expect((ccNode.items[0] as ClassRange).fromCh).toBe("a");
        expect((ccNode.items[0] as ClassRange).toCh).toBe("z");
        expect(ccNode.items[1]).toBeInstanceOf(ClassRange);
        expect((ccNode.items[1] as ClassRange).fromCh).toBe("A");
        expect((ccNode.items[1] as ClassRange).toCh).toBe("Z");
        expect(ccNode.items[2]).toBeInstanceOf(ClassRange);
        expect((ccNode.items[2] as ClassRange).fromCh).toBe("0");
        expect((ccNode.items[2] as ClassRange).toCh).toBe("9");
    });

    test("should parse range with literals mixed", () => {
        /**
         * Tests ranges mixed with literals: [a-z_0-9-]
         */
        const [, ast] = parse("[a-z_0-9-]");
        expect(ast).toBeInstanceOf(CharClass);
        const ccNode = ast as CharClass;
        expect(ccNode.items).toHaveLength(4);
        expect(ccNode.items[0]).toBeInstanceOf(ClassRange);
        expect((ccNode.items[0] as ClassRange).fromCh).toBe("a");
        expect((ccNode.items[0] as ClassRange).toCh).toBe("z");
        expect(ccNode.items[1]).toBeInstanceOf(ClassLiteral);
        expect((ccNode.items[1] as ClassLiteral).ch).toBe("_");
        expect(ccNode.items[2]).toBeInstanceOf(ClassRange);
        expect((ccNode.items[2] as ClassRange).fromCh).toBe("0");
        expect((ccNode.items[2] as ClassRange).toCh).toBe("9");
        expect(ccNode.items[3]).toBeInstanceOf(ClassLiteral);
        expect((ccNode.items[3] as ClassLiteral).ch).toBe("-");
    });

    test("should parse adjacent ranges", () => {
        /**
         * Tests adjacent character ranges: [a-z][A-Z]
         * Note: This is two separate classes, not one.
         */
        const [, ast] = parse("[a-z][A-Z]");
        expect(ast).toBeInstanceOf(Seq);
        const seqNode = ast as Seq;
        expect(seqNode.parts).toHaveLength(2);

        const part1 = seqNode.parts[0] as CharClass;
        expect(part1).toBeInstanceOf(CharClass);
        expect(part1.items).toHaveLength(1);
        expect(part1.items[0]).toBeInstanceOf(ClassRange);

        const part2 = seqNode.parts[1] as CharClass;
        expect(part2).toBeInstanceOf(CharClass);
        expect(part2.items).toHaveLength(1);
        expect(part2.items[0]).toBeInstanceOf(ClassRange);
    });
});

describe("Category H: Unicode Property Combinations", () => {
    /**
     * Tests for combinations of Unicode property escapes.
     */

    test("should parse multiple unicode properties", () => {
        /**
         * Tests multiple Unicode properties in one class: [\p{L}\p{N}]
         */
        const [, ast] = parse(String.raw`[\p{L}\p{N}]`);
        expect(ast).toBeInstanceOf(CharClass);
        const ccNode = ast as CharClass;
        expect(ccNode.items).toHaveLength(2);
        expect(ccNode.items[0]).toBeInstanceOf(ClassEscape);
        expect((ccNode.items[0] as ClassEscape).type).toBe("p");
        expect((ccNode.items[0] as ClassEscape).property).toBe("L");
        expect(ccNode.items[1]).toBeInstanceOf(ClassEscape);
        expect((ccNode.items[1] as ClassEscape).type).toBe("p");
        expect((ccNode.items[1] as ClassEscape).property).toBe("N");
    });

    test("should parse unicode property with literals", () => {
        /**
         * Tests Unicode property mixed with literals: [\p{L}abc]
         */
        const [, ast] = parse(String.raw`[\p{L}abc]`);
        expect(ast).toBeInstanceOf(CharClass);
        const ccNode = ast as CharClass;
        expect(ccNode.items).toHaveLength(4);
        expect(ccNode.items[0]).toBeInstanceOf(ClassEscape);
        expect((ccNode.items[0] as ClassEscape).type).toBe("p");
        expect(ccNode.items[1]).toBeInstanceOf(ClassLiteral);
        expect((ccNode.items[1] as ClassLiteral).ch).toBe("a");
        expect(ccNode.items[2]).toBeInstanceOf(ClassLiteral);
        expect((ccNode.items[2] as ClassLiteral).ch).toBe("b");
        expect(ccNode.items[3]).toBeInstanceOf(ClassLiteral);
        expect((ccNode.items[3] as ClassLiteral).ch).toBe("c");
    });

    test("should parse unicode property with range", () => {
        /**
         * Tests Unicode property mixed with range: [\p{L}0-9]
         */
        const [, ast] = parse(String.raw`[\p{L}0-9]`);
        expect(ast).toBeInstanceOf(CharClass);
        const ccNode = ast as CharClass;
        expect(ccNode.items).toHaveLength(2);
        expect(ccNode.items[0]).toBeInstanceOf(ClassEscape);
        expect((ccNode.items[0] as ClassEscape).type).toBe("p");
        expect((ccNode.items[0] as ClassEscape).property).toBe("L");
        expect(ccNode.items[1]).toBeInstanceOf(ClassRange);
        expect((ccNode.items[1] as ClassRange).fromCh).toBe("0");
        expect((ccNode.items[1] as ClassRange).toCh).toBe("9");
    });

    test("should parse negated unicode property in class", () => {
        /**
         * Tests negated Unicode property: [\P{L}]
         * Already exists but confirming coverage.
         */
        const [, ast] = parse(String.raw`[\P{L}]`);
        expect(ast).toBeInstanceOf(CharClass);
        const ccNode = ast as CharClass;
        expect(ccNode.negated).toBe(false); // The class itself is not negated
        expect(ccNode.items).toHaveLength(1);
        expect(ccNode.items[0]).toBeInstanceOf(ClassEscape);
        expect((ccNode.items[0] as ClassEscape).type).toBe("P"); // P is the negated property
        expect((ccNode.items[0] as ClassEscape).property).toBe("L");
    });
});

describe("Category I: Negated Class Variations", () => {
    /**
     * Tests for negated character classes with various contents.
     */

    test("should parse negated class with range", () => {
        /**
         * Tests negated class with range: [^a-z]
         */
        const [, ast] = parse("[^a-z]");
        expect(ast).toBeInstanceOf(CharClass);
        const ccNode = ast as CharClass;
        expect(ccNode.negated).toBe(true);
        expect(ccNode.items).toHaveLength(1);
        expect(ccNode.items[0]).toBeInstanceOf(ClassRange);
        expect((ccNode.items[0] as ClassRange).fromCh).toBe("a");
        expect((ccNode.items[0] as ClassRange).toCh).toBe("z");
    });

    test("should parse negated class with shorthand", () => {
        /**
         * Tests negated class with shorthand: [^\d\s]
         */
        const [, ast] = parse(String.raw`[^\d\s]`);
        expect(ast).toBeInstanceOf(CharClass);
        const ccNode = ast as CharClass;
        expect(ccNode.negated).toBe(true);
        expect(ccNode.items).toHaveLength(2);
        expect(ccNode.items[0]).toBeInstanceOf(ClassEscape);
        expect((ccNode.items[0] as ClassEscape).type).toBe("d");
        expect(ccNode.items[1]).toBeInstanceOf(ClassEscape);
        expect((ccNode.items[1] as ClassEscape).type).toBe("s");
    });

    test("should parse negated class with unicode property", () => {
        /**
         * Tests negated class with Unicode property: [^\p{L}]
         */
        const [, ast] = parse(String.raw`[^\p{L}]`);
        expect(ast).toBeInstanceOf(CharClass);
        const ccNode = ast as CharClass;
        expect(ccNode.negated).toBe(true);
        expect(ccNode.items).toHaveLength(1);
        expect(ccNode.items[0]).toBeInstanceOf(ClassEscape);
        expect((ccNode.items[0] as ClassEscape).type).toBe("p");
        expect((ccNode.items[0] as ClassEscape).property).toBe("L");
    });
});

describe("Category J: Char Class Error Cases", () => {
    /**
     * Additional error cases for character classes.
     */

    test("should raise error for truly empty class", () => {
        /**
         * Tests that [] without the special ] handling raises an error.
         * Note: []a] is valid (] is literal), but [] alone should error.
         */
        expect(() => parse("[]")).toThrow(ParseError);
        expect(() => parse("[]")).toThrow("Unterminated character class");
    });

    test("should reject reversed range [z-a] as invalid", () => {
        /**
         * Per IEH audit, reversed character ranges (e.g., [z-a]) are invalid
         * and should be reported as a parse error.
         */
        expect(() => parse("[z-a]")).toThrow(ParseError);
        expect(() => parse("[z-a]")).toThrow(/Invalid character range/);
    });

    test("should parse incomplete range at end as literal", () => {
        /**
         * Tests incomplete range at class end: [a-]
         * This is valid (hyphen is literal), confirm behavior.
         */
        const [, ast] = parse("[a-]");
        expect(ast).toBeInstanceOf(CharClass);
        const ccNode = ast as CharClass;
        expect(ccNode.items).toHaveLength(2);
        expect(ccNode.items[0]).toBeInstanceOf(ClassLiteral);
        expect((ccNode.items[0] as ClassLiteral).ch).toBe("a");
        expect(ccNode.items[1]).toBeInstanceOf(ClassLiteral);
        expect((ccNode.items[1] as ClassLiteral).ch).toBe("-");
    });
});
