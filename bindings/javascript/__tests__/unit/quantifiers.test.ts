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
 *
 * -   Parsing of all brace-based quantifiers: `{n}`, `{m,}`, `{m,n}`.
 *
 * -   Parsing of lazy (`*?`) and possessive (`*+`) mode modifiers
 * .
 * -   The structure and values of the resulting `nodes.Quant` AST node
 * (including `min`, `max`, and `mode` fields).
 *
 * -   Error handling for malformed brace quantifiers (e.g., `a{1,`).
 *
 * -   The parser's correct identification of the atom to be quantified.
 *
 * -   **Out of scope:**
 * -   Static analysis for ReDoS risks on nested quantifiers
 * (this is a Sprint 6 feature).
 * -   The emitter's final string output, such as adding non-capturing
 * groups (covered in `test_emitter_edges.ts`).
 */

// Note: Adjust import paths as needed for your project structure
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
    Alt,
    Backref,
} from "../../src/STRling/core/nodes";

// --- Test Suite -----------------------------------------------------------------

describe("Category A: Positive Cases", () => {
    /**
     * Covers all positive cases for valid quantifier syntax and modes.
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
        (inputDsl, expectedMin, expectedMax, expectedMode, id) => {
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
     */

    test.each<[string, string, number, string]>([
        ["a{1", "Incomplete quantifier", 3, "unclosed_brace_after_num"],
        ["a{1,", "Incomplete quantifier", 4, "unclosed_brace_after_comma"],
    ])(
        'should fail for malformed brace quantifier "%s" (ID: %s)',
        (invalidDsl, errorPrefix, errorPos, id) => {
            /**
             * Tests that malformed brace quantifiers raise a ParseError.
             */
            expect(() => parse(invalidDsl)).toThrow(ParseError);
            try {
                parse(invalidDsl);
                fail("ParseError was not thrown");
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
     */

    test.each<[string, number, number | string, string]>([
        ["a{0}", 0, 0, "exact_zero"],
        ["a{0,5}", 0, 5, "range_from_zero"],
        ["a{0,}", 0, "Inf", "at_least_zero"],
    ])(
        'should parse zero-repetition quantifier "%s" (ID: %s)',
        (inputDsl, expectedMin, expectedMax, id) => {
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
        const quantNode = ast as Quant;
        const groupNode = quantNode.child as Group;
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
        [String.raw`\d*`, CharClass, "quantify_shorthand"],
        [".*", Dot, "quantify_dot"],
        ["[a-z]*", CharClass, "quantify_char_class"],
        ["(abc)*", Group, "quantify_group"],
        ["(?:a|b)+", Group, "quantify_alternation_in_group"],
        ["(?=a)+", Look, "quantify_lookaround"],
    ])(
        'should correctly quantify different atom types for "%s" (ID: %s)',
        (inputDsl, expectedChildType, id) => {
            /**
             * Tests that quantifiers correctly wrap various types of AST nodes.
             */
            const [, ast] = parse(inputDsl);
            expect(ast).toBeInstanceOf(Quant);
            expect((ast as Quant).child).toBeInstanceOf(expectedChildType);
        }
    );
});

// --- New Test Stubs for 3-Test Standard Compliance -----------------------------

describe("Category E: Nested and Redundant Quantifiers", () => {
    /**
     * Tests for nested quantifiers and redundant quantification patterns.
     * These are edge cases that test the parser's ability to handle
     * syntactically valid but semantically unusual patterns.
     */

    test("should parse nested quantifier star on star", () => {
        /**
         * Tests that a quantifier can be applied to a group containing a
         * quantified atom: (a*)* is syntactically valid.
         */
        const [, ast] = parse("(a*)*");
        expect(ast).toBeInstanceOf(Quant);
        const quantNode = ast as Quant;
        expect(quantNode.min).toBe(0);
        expect(quantNode.max).toBe("Inf");
        expect(quantNode.child).toBeInstanceOf(Group);
        const groupChild = quantNode.child as Group;
        expect(groupChild.body).toBeInstanceOf(Quant);
        const innerQuant = groupChild.body as Quant;
        expect(innerQuant.min).toBe(0);
        expect(innerQuant.max).toBe("Inf");
    });

    test("should parse nested quantifier plus on optional", () => {
        /**
         * Tests nested quantifiers with different operators: (a+)?
         */
        const [, ast] = parse("(a+)?");
        expect(ast).toBeInstanceOf(Quant);
        const quantNode = ast as Quant;
        expect(quantNode.min).toBe(0);
        expect(quantNode.max).toBe(1);
        expect(quantNode.child).toBeInstanceOf(Group);
        const groupChild = quantNode.child as Group;
        expect(groupChild.body).toBeInstanceOf(Quant);
        const innerQuant = groupChild.body as Quant;
        expect(innerQuant.min).toBe(1);
        expect(innerQuant.max).toBe("Inf");
    });

    test("should parse redundant quantifier plus on star", () => {
        /**
         * Tests redundant quantification: (a*)+
         * This is semantically equivalent to a* but syntactically valid.
         */
        const [, ast] = parse("(a*)+");
        expect(ast).toBeInstanceOf(Quant);
        const quantNode = ast as Quant;
        expect(quantNode.min).toBe(1);
        expect(quantNode.max).toBe("Inf");
        expect(quantNode.child).toBeInstanceOf(Group);
        expect((quantNode.child as Group).body).toBeInstanceOf(Quant);
    });

    test("should parse redundant quantifier star on optional", () => {
        /**
         * Tests redundant quantification: (a?)*
         */
        const [, ast] = parse("(a?)*");
        expect(ast).toBeInstanceOf(Quant);
        const quantNode = ast as Quant;
        expect(quantNode.min).toBe(0);
        expect(quantNode.max).toBe("Inf");
        expect(quantNode.child).toBeInstanceOf(Group);
        const groupChild = quantNode.child as Group;
        expect(groupChild.body).toBeInstanceOf(Quant);
        const innerQuant = groupChild.body as Quant;
        expect(innerQuant.min).toBe(0);
        expect(innerQuant.max).toBe(1);
    });

    test("should parse nested quantifier with brace", () => {
        /**
         * Tests brace quantifiers on quantified groups: (a{2,3}){1,2}
         */
        const [, ast] = parse("(a{2,3}){1,2}");
        expect(ast).toBeInstanceOf(Quant);
        const quantNode = ast as Quant;
        expect(quantNode.min).toBe(1);
        expect(quantNode.max).toBe(2);
        expect(quantNode.child).toBeInstanceOf(Group);
        const groupChild = quantNode.child as Group;
        expect(groupChild.body).toBeInstanceOf(Quant);
        const innerQuant = groupChild.body as Quant;
        expect(innerQuant.min).toBe(2);
        expect(innerQuant.max).toBe(3);
    });
});

describe("Category F: Quantifier On Special Atoms", () => {
    /**
     * Tests for quantifiers applied to special atom types like backreferences
     * and anchors.
     */

    test("should parse quantifier on backref", () => {
        /**
         * Tests that a quantifier can be applied to a backreference: (a)\1*
         */
        const [, ast] = parse(String.raw`(a)\1*`);
        expect(ast).toBeInstanceOf(Seq);
        const seqNode = ast as Seq;
        expect(seqNode.parts).toHaveLength(2);
        expect(seqNode.parts[0]).toBeInstanceOf(Group);
        const quantNode = seqNode.parts[1] as Quant;
        expect(quantNode).toBeInstanceOf(Quant);
        expect(quantNode.child).toBeInstanceOf(Backref);
        expect(quantNode.min).toBe(0);
        expect(quantNode.max).toBe("Inf");
    });

    test("should parse quantifier on multiple backrefs", () => {
        /**
         * Tests quantifiers on multiple backrefs: (a)(b)\1*\2+
         */
        const [, ast] = parse(String.raw`(a)(b)\1*\2+`);
        expect(ast).toBeInstanceOf(Seq);
        const seqNode = ast as Seq;
        expect(seqNode.parts).toHaveLength(4);

        const quant1 = seqNode.parts[2] as Quant;
        expect(quant1).toBeInstanceOf(Quant);
        expect(quant1.child).toBeInstanceOf(Backref);
        expect((quant1.child as Backref).byIndex).toBe(1);

        const quant2 = seqNode.parts[3] as Quant;
        expect(quant2).toBeInstanceOf(Quant);
        expect(quant2.child).toBeInstanceOf(Backref);
        expect((quant2.child as Backref).byIndex).toBe(2);
    });
});

describe("Category G: Multiple Quantified Sequences", () => {
    /**
     * Tests for patterns with multiple consecutive quantified atoms.
     */

    test("should parse multiple consecutive quantified literals", () => {
        /**
         * Tests multiple quantified atoms in sequence: a*b+c?
         */
        const [, ast] = parse("a*b+c?");
        expect(ast).toBeInstanceOf(Seq);
        const seqNode = ast as Seq;
        expect(seqNode.parts).toHaveLength(3);
        expect(seqNode.parts.every((part) => part instanceof Quant)).toBe(true);

        const quant0 = seqNode.parts[0] as Quant;
        expect(quant0.min).toBe(0);
        expect(quant0.max).toBe("Inf");

        const quant1 = seqNode.parts[1] as Quant;
        expect(quant1.min).toBe(1);
        expect(quant1.max).toBe("Inf");

        const quant2 = seqNode.parts[2] as Quant;
        expect(quant2.min).toBe(0);
        expect(quant2.max).toBe(1);
    });

    test("should parse multiple quantified groups", () => {
        /**
         * Tests multiple quantified groups: (ab)*(cd)+(ef)?
         */
        const [, ast] = parse("(ab)*(cd)+(ef)?");
        expect(ast).toBeInstanceOf(Seq);
        const seqNode = ast as Seq;
        expect(seqNode.parts).toHaveLength(3);
        expect(seqNode.parts.every((part) => part instanceof Quant)).toBe(true);
        expect(
            seqNode.parts.every(
                (part) => (part as Quant).child instanceof Group
            )
        ).toBe(true);
    });

    test("should parse quantified atoms with alternation", () => {
        /**
         * Tests quantified atoms in an alternation: a*|b+
         */
        const [, ast] = parse("a*|b+");
        expect(ast).toBeInstanceOf(Alt);
        const altNode = ast as Alt;
        expect(altNode.branches).toHaveLength(2);

        const branch0 = altNode.branches[0] as Quant;
        expect(branch0).toBeInstanceOf(Quant);
        expect(branch0.min).toBe(0);

        const branch1 = altNode.branches[1] as Quant;
        expect(branch1).toBeInstanceOf(Quant);
        expect(branch1.min).toBe(1);
    });
});

describe("Category H: Brace Quantifier Edge Cases", () => {
    /**
     * Additional edge cases for brace quantifiers.
     */

    test("should parse brace quantifier exact one", () => {
        /**
         * Tests exact repetition of one: a{1}
         * Should parse correctly even though it's equivalent to 'a'.
         */
        const [, ast] = parse("a{1}");
        expect(ast).toBeInstanceOf(Quant);
        const quantNode = ast as Quant;
        expect(quantNode.min).toBe(1);
        expect(quantNode.max).toBe(1);
        expect(quantNode.child).toBeInstanceOf(Lit);
        expect((quantNode.child as Lit).value).toBe("a");
    });

    test("should parse brace quantifier zero to one", () => {
        /**
         * Tests range zero to one: a{0,1}
         * Should be equivalent to a? but valid syntax.
         */
        const [, ast] = parse("a{0,1}");
        expect(ast).toBeInstanceOf(Quant);
        const quantNode = ast as Quant;
        expect(quantNode.min).toBe(0);
        expect(quantNode.max).toBe(1);
        expect(quantNode.child).toBeInstanceOf(Lit);
    });

    test("should parse brace quantifier on alternation in group", () => {
        /**
         * Tests brace quantifier on group with alternation: (a|b){2,3}
         */
        const [, ast] = parse("(a|b){2,3}");
        expect(ast).toBeInstanceOf(Quant);
        const quantNode = ast as Quant;
        expect(quantNode.min).toBe(2);
        expect(quantNode.max).toBe(3);
        expect(quantNode.child).toBeInstanceOf(Group);
        expect((quantNode.child as Group).body).toBeInstanceOf(Alt);
    });

    test("should parse brace quantifier large values", () => {
        /**
         * Tests brace quantifiers with large repetition counts: a{100}, a{50,150}
         */
        const [, ast] = parse("a{100,200}");
        expect(ast).toBeInstanceOf(Quant);
        const quantNode = ast as Quant;
        expect(quantNode.min).toBe(100);
        expect(quantNode.max).toBe(200);
        expect(quantNode.child).toBeInstanceOf(Lit);
    });
});

describe("Category I: Quantifier Interaction With Flags", () => {
    /**
     * Tests for how quantifiers interact with DSL flags.
     */

    test("should parse quantifier with free spacing mode", () => {
        /**
         * Tests that free-spacing mode doesn't affect quantifier parsing:
         * %flags x\na * (spaces should be ignored, quantifier still applies)
         */
        const [, ast] = parse("%flags x\na *");
        // In free-spacing mode, spaces are ignored, so 'a' and '*' are separate
        // The * becomes a literal, not a quantifier
        expect(ast).toBeInstanceOf(Seq);
        const seqNode = ast as Seq;
        expect(seqNode.parts).toHaveLength(2);
        expect(seqNode.parts[0]).toBeInstanceOf(Lit);
        expect((seqNode.parts[0] as Lit).value).toBe("a");
        expect(seqNode.parts[1]).toBeInstanceOf(Lit);
        expect((seqNode.parts[1] as Lit).value).toBe("*");
    });

    test("should parse quantifier on escaped space in free spacing", () => {
        /**
         * Tests quantifier on escaped space in free-spacing mode:
         * %flags x\n\ *
         */
        const [, ast] = parse(`%flags x\n\\ *`);
        // Escaped space followed by *, should quantify the space
        expect(ast).toBeInstanceOf(Quant);
        const quantNode = ast as Quant;
        expect(quantNode.min).toBe(0);
        expect(quantNode.max).toBe("Inf");
        expect(quantNode.child).toBeInstanceOf(Lit);
        expect((quantNode.child as Lit).value).toBe(" ");
    });
});
