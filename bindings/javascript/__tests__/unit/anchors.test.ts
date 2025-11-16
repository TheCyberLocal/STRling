/**
 * @file Test Design — anchors.test.ts
 *
 * ## Purpose
 * This test suite validates the correct parsing of all anchor tokens (^, $, \b, \B, etc.).
 * It ensures that each anchor is correctly mapped to a corresponding Anchor AST node
 * with the proper type and that its parsing is unaffected by flags or surrounding
 * constructs.
 *
 * ## Description
 * Anchors are zero-width assertions that do not consume characters but instead
 * match a specific **position** within the input string, such as the start of a
 * line or a boundary between a word and a space. This suite tests the parser's
 * ability to correctly identify all supported core and extension anchors and
 * produce the corresponding `nodes.Anchor` AST object.
 *
 * ## Scope
 * -   **In scope:**
 * -   Parsing of core line anchors (`^`, `$`) and word boundary anchors
 * (`\b`, `\B`).
 * -   Parsing of non-core, engine-specific absolute anchors (`\A`, `\Z`, `\z`).
 *
 * -   The structure and `at` value of the resulting `nodes.Anchor` AST node.
 *
 * -   How anchors are parsed when placed at the start, middle, or end of a sequence.
 *
 * -   Ensuring the parser's output for `^` and `$` is consistent regardless
 * of the multiline (`m`) flag's presence.
 * -   **Out of scope:**
 * -   The runtime *behavioral change* of `^` and `$` when the `m` flag is
 * active (this is an emitter/engine concern).
 * -   Quantification of anchors.
 * -   The behavior of `\b` inside a character class, where it represents a
 * backspace literal (covered in `char_classes.test.ts`).
 */

// Note: Adjust the import paths based on your project's directory structure.
import { parse, ParseError } from "../../src/STRling/core/parser";
import {
    Node,
    Anchor,
    Seq,
    Group,
    Look,
    Lit,
    Quant,
    Alt,
    Dot,
    CharClass,
} from "../../src/STRling/core/nodes";

// --- Test Suite -----------------------------------------------------------------

describe("Category A: Positive Cases", () => {
    /**
     * Covers all positive cases for valid anchor syntax. These tests verify
     * that each anchor token is parsed into the correct Anchor node with the
     * expected `at` value.
     */

    test.each([
        // A.1: Core Line Anchors
        ["^", "Start", "line_start"],
        ["$", "End", "line_end"],
        // A.2: Core Word Boundary Anchors
        [String.raw`\b`, "WordBoundary", "word_boundary"],
        [String.raw`\B`, "NotWordBoundary", "not_word_boundary"],
        // A.3: Absolute Anchors (Extension Features)
        [String.raw`\A`, "AbsoluteStart", "absolute_start_ext"],
        [String.raw`\Z`, "EndBeforeFinalNewline", "end_before_newline_ext"],
    ])("should parse anchor '%s' (ID: %s)", (inputDsl, expectedAtValue, id) => {
        /**
         * Tests that each individual anchor token is parsed into the correct
         * Anchor AST node.
         */
        const [, ast] = parse(inputDsl);
        expect(ast).toBeInstanceOf(Anchor);
        expect((ast as Anchor).at).toBe(expectedAtValue);
    });
});

describe("Category B: Negative Cases", () => {
    /**
     * This category is intentionally empty. Anchors are single, unambiguous
     * tokens, and there are no anchor-specific parse errors. Invalid escape
     * sequences are handled by the literal/escape parser and are tested in
     * that suite.
     */
});

describe("Category C: Edge Cases", () => {
    /**
     * Covers edge cases related to the position and combination of anchors.
     */

    test("should parse a pattern with only anchors", () => {
        /**
         * Tests that a pattern containing multiple anchors is parsed into a
         * correct sequence of Anchor nodes.
         */
        const [, ast] = parse(String.raw`^\A\b$`);
        expect(ast).toBeInstanceOf(Seq);
        const seqNode = ast as Seq;

        expect(seqNode.parts).toHaveLength(4);
        // Add type check to inform the type checker
        expect(seqNode.parts.every((part) => part instanceof Anchor)).toBe(
            true
        );
        const atValues = seqNode.parts.map((part) => (part as Anchor).at);
        expect(atValues).toEqual([
            "Start",
            "AbsoluteStart",
            "WordBoundary",
            "End",
        ]);
    });

    test.each([
        [String.raw`^a`, 0, "Start", "at_start"],
        [String.raw`a\bb`, 1, "WordBoundary", "in_middle"],
        [String.raw`ab$`, 1, "End", "at_end"],
    ])(
        "should parse anchors in different positions (ID: %s)",
        (inputDsl, expectedPosition, expectedAtValue, id) => {
            /**
             * Tests that anchors are correctly parsed as part of a sequence at
             * various positions.
             */
            const [, ast] = parse(inputDsl);
            expect(ast).toBeInstanceOf(Seq);
            const seqNode = ast as Seq;
            const anchorNode = seqNode.parts[expectedPosition];
            expect(anchorNode).toBeInstanceOf(Anchor);
            expect((anchorNode as Anchor).at).toBe(expectedAtValue);
        }
    );
});

describe("Category D: Interaction Cases", () => {
    /**
     * Covers how anchors interact with other DSL features, such as flags
     * and grouping constructs.
     */

    test("should not change the parsed AST when multiline flag is present", () => {
        /**
         * A critical test to ensure the parser's output for `^` and `$` is
         * identical regardless of the multiline flag. The flag's semantic
         * effect is a runtime concern for the regex engine.
         */
        const [, astNoM] = parse("^a$");
        const [, astWithM] = parse("%flags m\n^a$");

        expect(astWithM).toEqual(astNoM);

        // Add specific checks to help the type checker and be explicit
        expect(astNoM).toBeInstanceOf(Seq);
        const seqNode = astNoM as Seq;
        expect(seqNode.parts[0]).toBeInstanceOf(Anchor);
        expect(seqNode.parts[2]).toBeInstanceOf(Anchor);
        expect((seqNode.parts[0] as Anchor).at).toBe("Start");
        expect((seqNode.parts[2] as Anchor).at).toBe("End");
    });

    // Define a type for the constructor of Node subclasses for cleaner type hinting
    type NodeConstructor = new (...args: any[]) => Group | Look;

    test.each<[string, NodeConstructor, string, string]>([
        [String.raw`(^a)`, Group, "Start", "in_capturing_group"],
        [String.raw`(?:a\b)`, Group, "WordBoundary", "in_noncapturing_group"],
        [String.raw`(?=a$)`, Look, "End", "in_lookahead"],
        [String.raw`(?<=^a)`, Look, "Start", "in_lookbehind"],
    ])(
        "should parse anchors inside groups and lookarounds (ID: %s)",
        (inputDsl, containerType, expectedAtValue, id) => {
            /**
             * Tests that anchors are correctly parsed when nested inside other
             * syntactic constructs.
             */
            const [, ast] = parse(inputDsl);
            expect(ast).toBeInstanceOf(containerType);

            // Add type check for the container before accessing `.body`
            const containerNode = ast as Group | Look;

            // The anchor may be part of a sequence inside the container, find it
            let anchorNode: Node | null = null;
            if (containerNode.body instanceof Seq) {
                // Find the anchor in the sequence
                for (const part of containerNode.body.parts) {
                    if (part instanceof Anchor) {
                        anchorNode = part;
                        break;
                    }
                }
            } else if (containerNode.body instanceof Anchor) {
                // Direct anchor
                anchorNode = containerNode.body;
            }

            if (!anchorNode) {
                throw new Error(
                    `No anchor found in sequence: ${containerNode.body}`
                );
            }

            expect(anchorNode).toBeInstanceOf(Anchor);
            expect((anchorNode as Anchor).at).toBe(expectedAtValue);
        }
    );
});

// --- New Test Stubs for 3-Test Standard Compliance -----------------------------

describe("Category E: Anchors in Complex Sequences", () => {
    /**
     * Tests for anchors in complex sequences with quantified atoms.
     */

    test("should parse anchor between quantified atoms", () => {
        /**
         * Tests anchor between quantified atoms: a*^b+
         * The ^ anchor appears between two quantified literals.
         */
        const [, ast] = parse("a*^b+");
        expect(ast).toBeInstanceOf(Seq);
        const seqNode = ast as Seq;
        expect(seqNode.parts).toHaveLength(3);
        expect(seqNode.parts[0]).toBeInstanceOf(Quant);
        expect(seqNode.parts[1]).toBeInstanceOf(Anchor);
        expect((seqNode.parts[1] as Anchor).at).toBe("Start");
        expect(seqNode.parts[2]).toBeInstanceOf(Quant);
    });

    test("should parse anchor after quantified group", () => {
        /**
         * Tests anchor after quantified group: (ab)*$
         */
        const [, ast] = parse("(ab)*$");
        expect(ast).toBeInstanceOf(Seq);
        const seqNode = ast as Seq;
        expect(seqNode.parts).toHaveLength(2);
        expect(seqNode.parts[0]).toBeInstanceOf(Quant);
        expect(seqNode.parts[1]).toBeInstanceOf(Anchor);
        expect((seqNode.parts[1] as Anchor).at).toBe("End");
    });

    test("should parse multiple anchors of same type", () => {
        /**
         * Tests multiple same anchors: ^^
         * Edge case: semantically redundant but syntactically valid.
         */
        const [, ast] = parse("^^");
        expect(ast).toBeInstanceOf(Seq);
        const seqNode = ast as Seq;
        expect(seqNode.parts).toHaveLength(2);
        expect(seqNode.parts[0]).toBeInstanceOf(Anchor);
        expect((seqNode.parts[0] as Anchor).at).toBe("Start");
        expect(seqNode.parts[1]).toBeInstanceOf(Anchor);
        expect((seqNode.parts[1] as Anchor).at).toBe("Start");
    });

    test("should parse multiple end anchors", () => {
        /**
         * Tests multiple end anchors: $$
         */
        const [, ast] = parse("$$");
        expect(ast).toBeInstanceOf(Seq);
        const seqNode = ast as Seq;
        expect(seqNode.parts).toHaveLength(2);
        expect(seqNode.parts[0]).toBeInstanceOf(Anchor);
        expect((seqNode.parts[0] as Anchor).at).toBe("End");
        expect(seqNode.parts[1]).toBeInstanceOf(Anchor);
        expect((seqNode.parts[1] as Anchor).at).toBe("End");
    });
});

describe("Category F: Anchors in Alternation", () => {
    /**
     * Tests for anchors used in alternation patterns.
     */

    test("should parse anchor in alternation branch", () => {
        /**
         * Tests anchor in one branch of alternation: ^a|b$
         * Parses as (^a)|(b$).
         */
        const [, ast] = parse("^a|b$");
        expect(ast).toBeInstanceOf(Alt);
        const altNode = ast as Alt;
        expect(altNode.branches).toHaveLength(2);
        // First branch: ^a
        const branch0 = altNode.branches[0] as Seq;
        expect(branch0).toBeInstanceOf(Seq);
        expect(branch0.parts).toHaveLength(2);
        expect(branch0.parts[0]).toBeInstanceOf(Anchor);
        expect((branch0.parts[0] as Anchor).at).toBe("Start");
        expect(branch0.parts[1]).toBeInstanceOf(Lit);
        // Second branch: b$
        const branch1 = altNode.branches[1] as Seq;
        expect(branch1).toBeInstanceOf(Seq);
        expect(branch1.parts).toHaveLength(2);
        expect(branch1.parts[0]).toBeInstanceOf(Lit);
        expect(branch1.parts[1]).toBeInstanceOf(Anchor);
        expect((branch1.parts[1] as Anchor).at).toBe("End");
    });

    test("should parse anchors in group alternation", () => {
        /**
         * Tests anchors in grouped alternation: (^|$)
         */
        const [, ast] = parse("(^|$)");
        expect(ast).toBeInstanceOf(Group);
        const groupNode = ast as Group;
        expect(groupNode.capturing).toBe(true);
        expect(groupNode.body).toBeInstanceOf(Alt);
        const altBody = groupNode.body as Alt;
        expect(altBody.branches).toHaveLength(2);
        expect(altBody.branches[0]).toBeInstanceOf(Anchor);
        expect((altBody.branches[0] as Anchor).at).toBe("Start");
        expect(altBody.branches[1]).toBeInstanceOf(Anchor);
        expect((altBody.branches[1] as Anchor).at).toBe("End");
    });

    test("should parse word boundary in alternation", () => {
        /**
         * Tests word boundary in alternation: \ba|\bb
         */
        const [, ast] = parse(String.raw`\ba|\bb`);
        expect(ast).toBeInstanceOf(Alt);
        const altNode = ast as Alt;
        expect(altNode.branches).toHaveLength(2);
        // First branch: \ba
        const branch0 = altNode.branches[0] as Seq;
        expect(branch0).toBeInstanceOf(Seq);
        expect(branch0.parts).toHaveLength(2);
        expect(branch0.parts[0]).toBeInstanceOf(Anchor);
        expect((branch0.parts[0] as Anchor).at).toBe("WordBoundary");
        // Second branch: \bb
        const branch1 = altNode.branches[1] as Seq;
        expect(branch1).toBeInstanceOf(Seq);
        expect(branch1.parts).toHaveLength(2);
        expect(branch1.parts[0]).toBeInstanceOf(Anchor);
        expect((branch1.parts[0] as Anchor).at).toBe("WordBoundary");
    });
});

describe("Category G: Anchors in Atomic Groups", () => {
    /**
     * Tests for anchors inside atomic groups.
     */

    test("should parse start anchor in atomic group", () => {
        /**
         * Tests start anchor in atomic group: (?>^a)
         */
        const [, ast] = parse("(?>^a)");
        expect(ast).toBeInstanceOf(Group);
        const groupNode = ast as Group;
        expect(groupNode.atomic).toBe(true);
        expect(groupNode.body).toBeInstanceOf(Seq);
        const seqBody = groupNode.body as Seq;
        expect(seqBody.parts).toHaveLength(2);
        expect(seqBody.parts[0]).toBeInstanceOf(Anchor);
        expect((seqBody.parts[0] as Anchor).at).toBe("Start");
        expect(seqBody.parts[1]).toBeInstanceOf(Lit);
    });

    test("should parse end anchor in atomic group", () => {
        /**
         * Tests end anchor in atomic group: (?>a$)
         */
        const [, ast] = parse("(?>a$)");
        expect(ast).toBeInstanceOf(Group);
        const groupNode = ast as Group;
        expect(groupNode.atomic).toBe(true);
        expect(groupNode.body).toBeInstanceOf(Seq);
        const seqBody = groupNode.body as Seq;
        expect(seqBody.parts).toHaveLength(2);
        expect(seqBody.parts[0]).toBeInstanceOf(Lit);
        expect(seqBody.parts[1]).toBeInstanceOf(Anchor);
        expect((seqBody.parts[1] as Anchor).at).toBe("End");
    });

    test("should parse word boundary in atomic group", () => {
        /**
         * Tests word boundary in atomic group: (?>\ba)
         */
        const [, ast] = parse(String.raw`(?>\ba)`);
        expect(ast).toBeInstanceOf(Group);
        const groupNode = ast as Group;
        expect(groupNode.atomic).toBe(true);
        expect(groupNode.body).toBeInstanceOf(Seq);
        const seqBody = groupNode.body as Seq;
        expect(seqBody.parts).toHaveLength(2);
        expect(seqBody.parts[0]).toBeInstanceOf(Anchor);
        expect((seqBody.parts[0] as Anchor).at).toBe("WordBoundary");
        expect(seqBody.parts[1]).toBeInstanceOf(Lit);
    });
});

describe("Category H: Word Boundary Edge Cases", () => {
    /**
     * Tests for word boundary anchors in various contexts.
     */

    test("should parse word boundary with non-word character", () => {
        /**
         * Tests word boundary with non-word character: \b.\b
         * The dot matches any character, boundaries on both sides.
         */
        const [, ast] = parse(String.raw`\b.\b`);
        expect(ast).toBeInstanceOf(Seq);
        const seqNode = ast as Seq;
        expect(seqNode.parts).toHaveLength(3);
        expect(seqNode.parts[0]).toBeInstanceOf(Anchor);
        expect((seqNode.parts[0] as Anchor).at).toBe("WordBoundary");
        expect(seqNode.parts[1]).toBeInstanceOf(Dot);
        expect(seqNode.parts[2]).toBeInstanceOf(Anchor);
        expect((seqNode.parts[2] as Anchor).at).toBe("WordBoundary");
    });

    test("should parse word boundary with digit", () => {
        /**
         * Tests word boundary with digit: \b\d\b
         */
        const [, ast] = parse(String.raw`\b\d\b`);
        expect(ast).toBeInstanceOf(Seq);
        const seqNode = ast as Seq;
        expect(seqNode.parts).toHaveLength(3);
        expect(seqNode.parts[0]).toBeInstanceOf(Anchor);
        expect((seqNode.parts[0] as Anchor).at).toBe("WordBoundary");
        expect(seqNode.parts[1]).toBeInstanceOf(CharClass);
        expect(seqNode.parts[2]).toBeInstanceOf(Anchor);
        expect((seqNode.parts[2] as Anchor).at).toBe("WordBoundary");
    });

    test("should parse not-word-boundary usage", () => {
        /**
         * Tests not-word-boundary: \Ba\B
         */
        const [, ast] = parse(String.raw`\Ba\B`);
        expect(ast).toBeInstanceOf(Seq);
        const seqNode = ast as Seq;
        expect(seqNode.parts).toHaveLength(3);
        expect(seqNode.parts[0]).toBeInstanceOf(Anchor);
        expect((seqNode.parts[0] as Anchor).at).toBe("NotWordBoundary");
        expect(seqNode.parts[1]).toBeInstanceOf(Lit);
        expect((seqNode.parts[1] as Lit).value).toBe("a");
        expect(seqNode.parts[2]).toBeInstanceOf(Anchor);
        expect((seqNode.parts[2] as Anchor).at).toBe("NotWordBoundary");
    });
});

describe("Category I: Multiple Anchor Types", () => {
    /**
     * Tests for patterns combining different anchor types.
     */

    test("should parse start and end anchors", () => {
        /**
         * Tests both start and end anchors: ^abc$
         * Already covered but confirming as typical case.
         */
        const [, ast] = parse("^abc$");
        expect(ast).toBeInstanceOf(Seq);
        const seqNode = ast as Seq;
        expect(seqNode.parts).toHaveLength(3);
        expect(seqNode.parts[0]).toBeInstanceOf(Anchor);
        expect((seqNode.parts[0] as Anchor).at).toBe("Start");
        expect(seqNode.parts[1]).toBeInstanceOf(Lit);
        expect((seqNode.parts[1] as Lit).value).toBe("abc");
        expect(seqNode.parts[2]).toBeInstanceOf(Anchor);
        expect((seqNode.parts[2] as Anchor).at).toBe("End");
    });

    test("should parse absolute and line anchors", () => {
        /** The trailing `\z` is an unknown escape sequence and must raise */
        expect(() => parse(String.raw`\A^abc$\z`)).toThrow(ParseError);
        expect(() => parse(String.raw`\A^abc$\z`)).toThrow(
            /Unknown escape sequence \\z/
        );
    });

    test("should treat lowercase \\z as unknown escape", () => {
        expect(() => parse(String.raw`\z`)).toThrow(ParseError);
        expect(() => parse(String.raw`\z`)).toThrow(
            /Unknown escape sequence \\z/
        );
    });

    test("should parse word boundaries and line anchors", () => {
        /**
         * Tests word boundaries with line anchors: ^\ba\b$
         */
        const [, ast] = parse(String.raw`^\ba\b$`);
        expect(ast).toBeInstanceOf(Seq);
        const seqNode = ast as Seq;
        expect(seqNode.parts).toHaveLength(5);
        expect(seqNode.parts[0]).toBeInstanceOf(Anchor);
        expect((seqNode.parts[0] as Anchor).at).toBe("Start");
        expect(seqNode.parts[1]).toBeInstanceOf(Anchor);
        expect((seqNode.parts[1] as Anchor).at).toBe("WordBoundary");
        expect(seqNode.parts[2]).toBeInstanceOf(Lit);
        expect((seqNode.parts[2] as Lit).value).toBe("a");
        expect(seqNode.parts[3]).toBeInstanceOf(Anchor);
        expect((seqNode.parts[3] as Anchor).at).toBe("WordBoundary");
        expect(seqNode.parts[4]).toBeInstanceOf(Anchor);
        expect((seqNode.parts[4] as Anchor).at).toBe("End");
    });
});

describe("Category J: Anchors with Quantifiers", () => {
    /**
     * Tests confirming that anchors themselves cannot be quantified.
     */

    test("should raise error for anchor quantified directly (^*_)", () => {
        /**
         * Tests that ^* raises an error (cannot quantify anchor).
         */
        expect(() => parse("^*")).toThrow(ParseError);
        expect(() => parse("^*")).toThrow(/Cannot quantify anchor/);
    });

    test("should raise error for end anchor followed by quantifier ($+)", () => {
        /**
         * Tests $+ raises an error (cannot quantify anchor).
         */
        expect(() => parse("$+")).toThrow(ParseError);
        expect(() => parse("$+")).toThrow(/Cannot quantify anchor/);
    });
});
