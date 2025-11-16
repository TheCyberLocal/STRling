/**
 * @file Test Design — flags_and_free_spacing.test.ts
 *
 * ## Purpose
 * This test suite validates the correct parsing of the `%flags` directive and the
 * behavioral changes it induces, particularly the free-spacing (`x`) mode. It
 * ensures that flags are correctly identified and stored in the `Flags` object
 * and that the parser correctly handles whitespace and comments when the
 * extended mode is active.
 *
 * ## Description
 * The `%flags` directive is a top-level command in a `.strl` file that modifies
 * the semantics of the entire pattern. This suite tests the parser's ability to
 * correctly consume this directive and apply its effects. The primary focus is
 * on the **`x` flag (extended/free-spacing mode)**, which dramatically alters
 * how the parser handles whitespace and comments. The tests will verify that the
 * parser correctly ignores insignificant characters outside of character classes
 * while treating them as literals inside character classes.
 *
 * ## Scope
 * -   **In scope:**
 * -   Parsing the `%flags` directive with single and multiple flags (`i`,
 * `m`, `s`, `u`, `x`).
 * -   Handling of various separators (commas, spaces) within the flag
 * list.
 * -   The parser's behavior in free-spacing mode: ignoring whitespace and
 * comments outside character classes.
 * -   The parser's behavior inside a character class when free-spacing mode
 * is active (i.e., treating whitespace and `#` as literals).
 *
 * -   The structure of the `Flags` object produced by the parser and its
 * serialization in the final artifact.
 * -   **Out of scope:**
 * -   The runtime *effect* of the `i`, `m`, `s`, and `u` flags on the regex
 * engine's matching behavior.
 * -   The parsing of other directives like `%engine` or `%lang`.
 *
 */

// Note: Adjust import paths as needed for your project structure
import { parse, ParseError } from "../../src/STRling/core/parser";
import {
    Flags,
    Seq,
    Lit,
    CharClass,
    ClassItem,
    ClassLiteral,
    Node, // Imported for type safety in test cases
} from "../../src/STRling/core/nodes";

// --- Test Suite -----------------------------------------------------------------

describe("Category A: Positive Cases", () => {
    /**
     * Covers all positive cases for parsing flags and applying free-spacing mode.
     */

    test.each<[string, Flags, string]>([
        ["%flags i", new Flags({ ignoreCase: true }), "single_flag"],
        [
            "%flags i, m, x",
            new Flags({ ignoreCase: true, multiline: true, extended: true }),
            "multiple_flags_with_commas",
        ],
        [
            "%flags u m s",
            new Flags({ unicode: true, multiline: true, dotAll: true }),
            "multiple_flags_with_spaces",
        ],
        [
            "%flags i,m s,u x",
            new Flags({
                ignoreCase: true,
                multiline: true,
                dotAll: true,
                unicode: true,
                extended: true,
            }),
            "multiple_flags_mixed_separators",
        ],
        [
            "  %flags i  ",
            new Flags({ ignoreCase: true }),
            "leading_trailing_whitespace",
        ],
    ])(
        'should parse flag directive "%s" correctly (ID: %s)',
        (inputDsl, expectedFlags, id) => {
            /**
             * Tests that the %flags directive is correctly parsed into a Flags object.
             */
            const [flags] = parse(inputDsl);
            expect(flags).toEqual(expectedFlags);
        }
    );

    test.each<[string, Seq, string]>([
        [
            "%flags x\na b c",
            new Seq([new Lit("a"), new Lit("b"), new Lit("c")]),
            "whitespace_is_ignored",
        ],
        [
            "%flags x\na # comment\n b",
            new Seq([new Lit("a"), new Lit("b")]),
            "comments_are_ignored",
        ],
        [
            `%flags x\na\\ b`,
            new Seq([new Lit("a"), new Lit(" "), new Lit("b")]),
            "escaped_whitespace_is_literal",
        ],
    ])(
        'should handle free-spacing mode for "%s" (ID: %s)',
        (inputDsl, expectedAst, id) => {
            /**
             * Tests that the parser correctly handles whitespace and comments when the
             * 'x' flag is active.
             */
            const [, ast] = parse(inputDsl);
            expect(ast).toEqual(expectedAst);
        }
    );
});

describe("Category B: Negative Cases", () => {
    /**
     * Covers lenient handling of malformed or unknown directives.
     */

    test.each<[string, string]>([
        ["%flags z", "unknown_flag"],
        ["%flagg i", "malformed_directive"],
    ])('should reject bad directive "%s" (ID: %s)', (inputDsl, id) => {
        /**
         * IEH audit requires unknown flags to be rejected. Expect a parse error.
         */
        expect(() => parse(inputDsl)).toThrow(ParseError);
    });
});

describe("Category C: Edge Cases", () => {
    /**
     * Covers edge cases for flag parsing and free-spacing mode.
     */

    test("should handle an empty flags directive", () => {
        /** Tests that an empty %flags directive results in default flags. */
        const [flags] = parse("%flags");
        expect(flags).toEqual(new Flags());
    });

    test("should reject a directive that appears after content", () => {
        /**
         * IEH audit requires directives appearing after pattern content to be
         * rejected. Expect a parse error indicating the directive must appear
         * at the start of the pattern.
         */
        expect(() => parse("a\n%flags i")).toThrow(ParseError);
    });

    test("should handle a pattern with only comments and whitespace", () => {
        /**
         * Tests that a pattern which becomes empty in free-spacing mode results
         * in an empty AST.
         */
        const [, ast] = parse("%flags x\n# comment\n  \n# another");
        expect(ast).toEqual(new Seq([]));
    });
});

describe("Category D: Interaction Cases", () => {
    /**
     * Covers the critical interaction between free-spacing mode and character classes.
     */

    test.each<[string, ClassItem[], string]>([
        [
            "%flags x\n[a b]",
            [
                new ClassLiteral("a"),
                new ClassLiteral(" "),
                new ClassLiteral("b"),
            ],
            "whitespace_is_literal_in_class",
        ],
        [
            "%flags x\n[a#b]",
            [
                new ClassLiteral("a"),
                new ClassLiteral("#"),
                new ClassLiteral("b"),
            ],
            "comment_char_is_literal_in_class",
        ],
    ])(
        'should disable free-spacing inside char class for "%s" (ID: %s)',
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
