/**
 * @file Test Design — quantifiers.test.ts
 *
 * ## Purpose
 * This test suite validates the correct parsing of all quantifier forms (`*`, `+`,
 * `?`, `{m,n}`) and modes (Greedy, Lazy, Possessive). It ensures quantifiers
 * correctly bind to their preceding atom, generate the proper `Quant` AST node,
 * and that malformed quantifier syntax raises the appropriate `ParseError`.
 *
 * ## Description
 * Quantifiers specify the number of times a preceding atom can occur in a
 * pattern. This test suite covers the full syntactic and semantic range of this
 * feature. It verifies that the parser correctly interprets the different
 * quantifier syntaxes and their greedy (default), lazy (`?` suffix), and
 * possessive (`+` suffix) variants. A key focus is testing operator
 * precedence—ensuring that a quantifier correctly associates with a single
 * preceding atom (like a literal, group, or class) rather than an entire
 * sequence.
 *
 * ## Scope
 * -   **In scope:**
 * -   Parsing of all standard quantifiers: `*`, `+`, `?`.
 * -   Parsing of all brace-based quantifiers: `{n}`, `{m,}`, `{m,n}`.
 * -   Parsing of lazy (`*?`) and possessive (`*+`) mode modifiers.
 * -   The structure and values of the resulting `nodes.Quant` AST node
 * (including `min`, `max`, and `mode` fields).
 * -   Error handling for malformed brace quantifiers (e.g., `a{1,`).
 * -   The parser's correct identification of the atom to be quantified.
 * -   **Out of scope:**
 * -   Static analysis for ReDoS risks on nested quantifiers
 * (this is a Sprint 6 feature).
 * -   The emitter's final string output, such as adding non-capturing
 * groups (covered in `test_emitter_edges.ts`).
 */

import { parse, ParseError } from "../../src/STRling/core/parser";
import {
    Node,
    Quant,
    Lit,
    Seq,
    Dot,
    CharClass,
    Group,
    Look,
    Anchor,
} from "../../src/STRling/core/nodes";

// --- Test Suite -----------------------------------------------------------------

describe("Category A: Positive Cases", () => {
    /**
     * Covers all positive cases for valid quantifier syntax and modes.
     *
     */
    test.each<[string, number, number | string, string, string]>([
        // A.1: Star Quantifier
        ["a*", 0, "Inf", "Greedy", "star_greedy"],
        ["a*?", 0, "Inf", "Lazy", "star_lazy"],
        ["a*+", 0, "Inf", "Possessive", "star_possessive"],
        // A.2: Plus Quantifier
        ["a+", 1, "Inf", "Greedy", "plus_greedy"],
        ["a+?", 1, "Inf", "Lazy", "plus_lazy"],
        ["a++", 1, "Inf", "Possessive", "plus_possessive"],
        // A.3: Optional Quantifier
        ["a?", 0, 1, "Greedy", "optional_greedy"],
        ["a??", 0, 1, "Lazy", "optional_lazy"],
        ["a?+", 0, 1, "Possessive", "optional_possessive"],
        // A.4: Exact Repetition
        ["a{3}", 3, 3, "Greedy", "brace_exact_greedy"],
        ["a{3}?", 3, 3, "Lazy", "brace_exact_lazy"],
        ["a{3}+", 3, 3, "Possessive", "brace_exact_possessive"],
        // A.5: At-Least Repetition
        ["a{3,}", 3, "Inf", "Greedy", "brace_at_least_greedy"],
        ["a{3,}?", 3, "Inf", "Lazy", "brace_at_least_lazy"],
        ["a{3,}+", 3, "Inf", "Possessive", "brace_at_least_possessive"],
        // A.6: Range Repetition
        ["a{3,5}", 3, 5, "Greedy", "brace_range_greedy"],
        ["a{3,5}?", 3, 5, "Lazy", "brace_range_lazy"],
        ["a{3,5}+", 3, 5, "Possessive", "brace_range_possessive"],
    ])(
        'should parse quantifier "%s" correctly (ID: %s)',
        (inputDsl, expectedMin, expectedMax, expectedMode) => {
            /**
             * Tests that all quantifier forms and modes are parsed into a Quant node
             * with the correct min, max, and mode attributes.
             */
            const [, ast] = parse(inputDsl);
            expect(ast).toBeInstanceOf(Quant);
            const quantNode = ast as Quant;
            expect(quantNode.min).toBe(expectedMin);
            expect(quantNode.max).toBe(expectedMax);
            expect(quantNode.mode).toBe(expectedMode);
            expect(quantNode.child).toBeInstanceOf(Lit);
        }
    );
});

describe("Category B: Negative Cases", () => {
    /**
     * Covers negative cases for malformed quantifier syntax.
     *
     */
    test.each<[string, string, number, string]>([
        ["a{", "Unterminated {n}", 2, "unclosed_brace"],
        ["a{1", "Unterminated {n}", 3, "unclosed_brace_after_num"],
        ["a{1,", "Unterminated {m,n}", 4, "unclosed_brace_after_comma"],
    ])(
        'should fail for malformed brace quantifier "%s" (ID: %s)',
        (invalidDsl, errorPrefix, errorPos) => {
            /**
             * Tests that malformed brace quantifiers raise a ParseError.
             *
             */
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

    test("should parse a malformed brace quantifier as a literal", () => {
        /**
         * Tests that a brace construct invalid as a quantifier (e.g., '{,5}')
         * is parsed as a literal string.
         */
        const [, ast] = parse("a{,5}");
        expect(ast).toEqual(new Seq([new Lit("a"), new Lit("{,5}")]));
    });
});

describe("Category C: Edge Cases", () => {
    /**
     * Covers edge cases for quantifiers.
     *
     */
    test.each<[string, number, number | string, string]>([
        ["a{0}", 0, 0, "exact_zero"],
        ["a{0,5}", 0, 5, "range_from_zero"],
        ["a{0,}", 0, "Inf", "at_least_zero"],
    ])(
        'should parse zero-repetition quantifier "%s" (ID: %s)',
        (inputDsl, expectedMin, expectedMax) => {
            /** Tests that quantifiers with zero values are parsed correctly. */
            const [, ast] = parse(inputDsl);
            expect(ast).toBeInstanceOf(Quant);
            const quantNode = ast as Quant;
            expect(quantNode.min).toBe(expectedMin);
            expect(quantNode.max).toBe(expectedMax);
        }
    );

    test("should apply a quantifier to an empty group", () => {
        /** Tests that a quantifier can be applied to an empty group. */
        const [, ast] = parse("(?:)*");
        expect(ast).toBeInstanceOf(Quant);
        const groupNode = (ast as Quant).child as Group;
        expect(groupNode.capturing).toBe(false);
        expect(groupNode.body).toEqual(new Seq([]));
    });

    test("should not apply a quantifier to an anchor", () => {
        /**
         * Tests that a quantifier correctly applies to the atom before an anchor,
         * not the anchor itself.
         */
        const [, ast] = parse("a?^");
        expect(ast).toBeInstanceOf(Seq);
        const seqNode = ast as Seq;
        const quantNode = seqNode.parts[0] as Quant;
        const anchorNode = seqNode.parts[1] as Anchor;
        expect(quantNode.child).toEqual(new Lit("a"));
        expect(anchorNode.at).toBe("Start");
    });
});

describe("Category D: Interaction Cases", () => {
    /**
     * Covers the interaction of quantifiers with different atoms and sequences.
     *
     */
    test("should demonstrate correct quantifier precedence", () => {
        /**
         * A critical test to ensure a quantifier binds only to the immediately
         * preceding atom, not the whole sequence.
         */
        const [, ast] = parse("ab*");
        expect(ast).toEqual(
            new Seq([new Lit("a"), new Quant(new Lit("b"), 0, "Inf", "Greedy")])
        );
    });

    // Define a type for the constructor of Node subclasses for cleaner type hinting
    type NodeConstructor = new (...args: any[]) => Node;

    test.each<[string, NodeConstructor, string]>([
        ["\\d*", CharClass, "quantify_shorthand"],
        [".*", Dot, "quantify_dot"],
        ["[a-z]*", CharClass, "quantify_char_class"],
        ["(abc)*", Group, "quantify_group"],
        ["(?:a|b)+", Group, "quantify_alternation_in_group"],
        ["(?=a)+", Look, "quantify_lookaround"],
    ])(
        'should correctly quantify different atom types for "%s" (ID: %s)',
        (inputDsl, expectedChildType) => {
            /**
             * Tests that quantifiers correctly wrap various types of AST nodes.
             *
             */
            const [, ast] = parse(inputDsl);
            expect(ast).toBeInstanceOf(Quant);
            expect((ast as Quant).child).toBeInstanceOf(expectedChildType);
        }
    );
});
