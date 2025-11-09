/**
 * @file Test Design — test_groups_backrefs_lookarounds.ts
 *
 * ## Purpose
 * This test suite validates the parser's handling of all grouping constructs,
 * backreferences, and lookarounds. It ensures that different group types are
 * parsed correctly into their corresponding AST nodes, that backreferences are
 * validated against defined groups, that lookarounds are constructed properly,
 * and that all syntactic errors raise the correct `ParseError`.
 *
 * ## Description
 * Groups, backreferences, and lookarounds are the primary features for defining
 * structure and context within a pattern.
 * -   **Groups** `(...)` are used to create sub-patterns, apply quantifiers to
 * sequences, and capture text for later use.
 * -   **Backreferences** `\1`, `\k<name>` match the exact text previously
 * captured by a group.
 * -   **Lookarounds** `(?=...)`, `(?<=...)`, etc., are zero-width assertions that
 * check for patterns before or after the current position without consuming
 * characters.
 *
 * This suite verifies that the parser correctly implements the rich syntax and
 * validation rules for these powerful features.
 *
 * ## Scope
 * -   **In scope:**
 * -   Parsing of all group types: capturing `()`, non-capturing `(?:...)`,
 * named `(?<name>...)`, and atomic `(?>...)`.
 * -   Parsing of numeric (`\1`) and named (`\k<name>`) backreferences.
 *
 * -   Validation of backreferences (e.g., ensuring no forward references).
 *
 * -   Parsing of all four lookaround types: positive/negative lookahead and
 * positive/negative lookbehind.
 * -   Error handling for unterminated constructs and invalid backreferences.
 *
 * -   The structure of the resulting `nodes.Group`, `nodes.Backref`, and
 * `nodes.Look` AST nodes.
 * -   **Out of scope:**
 * -   Quantification of these constructs (covered in `quantifiers.test.ts`).
 *
 * -   Semantic validation of lookbehind contents (e.g., the fixed-length
 * requirement).
 * -   Emitter-specific syntax transformations (e.g., Python's `(?P<name>...)`).
 */

// Note: Adjust import paths as needed for your project structure
import { parse, ParseError } from "../../src/STRling/core/parser";
import {
    Group,
    Backref,
    Look,
    Seq,
    Lit,
    Quant,
    Alt,
    Node,
} from "../../src/STRling/core/nodes";

// --- Test Suite -----------------------------------------------------------------

describe("Category A: Positive Cases", () => {
    /**
     * Covers all positive cases for valid group, backreference, and lookaround syntax.
     */

    test.each<[string, boolean, string | null, boolean | null, string]>([
        ["(a)", true, null, null, "capturing"],
        ["(?:a)", false, null, null, "non_capturing"],
        ["(?<name>a)", true, "name", null, "named_capturing"],
        ["(?>a)", false, null, true, "atomic_ext"],
    ])(
        'should parse group type for "%s" (ID: %s)',
        (inputDsl, expectedCapturing, expectedName, expectedAtomic, id) => {
            /** Tests that various group types are parsed with the correct attributes. */
            const [, ast] = parse(inputDsl);
            expect(ast).toBeInstanceOf(Group);
            const groupNode = ast as Group;
            expect(groupNode.capturing).toBe(expectedCapturing);
            expect(groupNode.name).toBe(expectedName);
            expect(groupNode.atomic).toBe(expectedAtomic);
            expect(groupNode.body).toBeInstanceOf(Lit);
        }
    );

    test.each<[string, Backref, string]>([
        [String.raw`(a)\1`, new Backref({ byIndex: 1 }), "numeric_backref"],
        [
            String.raw`(?<A>a)\k<A>`,
            new Backref({ byName: "A" }),
            "named_backref",
        ],
    ])(
        'should parse backreference for "%s" (ID: %s)',
        (inputDsl, expectedBackref, id) => {
            /** Tests that valid backreferences are parsed into the correct Backref node. */
            const [, ast] = parse(inputDsl);
            expect(ast).toBeInstanceOf(Seq);
            expect((ast as Seq).parts[1]).toEqual(expectedBackref);
        }
    );

    test.each<[string, string, boolean, string]>([
        ["a(?=b)", "Ahead", false, "lookahead_pos"],
        ["a(?!b)", "Ahead", true, "lookahead_neg"],
        ["(?<=a)b", "Behind", false, "lookbehind_pos"],
        ["(?<!a)b", "Behind", true, "lookbehind_neg"],
    ])(
        'should parse lookaround for "%s" (ID: %s)',
        (inputDsl, expectedDir, expectedNeg, id) => {
            /** Tests that all four lookaround types are parsed correctly. */
            const [, ast] = parse(inputDsl);
            expect(ast).toBeInstanceOf(Seq);
            const seqNode = ast as Seq;
            const lookNode = (
                expectedDir === "Ahead" ? seqNode.parts[1] : seqNode.parts[0]
            ) as Look;
            expect(lookNode).toBeInstanceOf(Look);
            expect(lookNode.dir).toBe(expectedDir);
            expect(lookNode.neg).toBe(expectedNeg);
        }
    );
});

describe("Category B: Negative Cases", () => {
    /**
     * Covers all negative cases for malformed or invalid syntax.
     */

    test.each<[string, string, number, string]>([
        // B.1: Unterminated constructs
        ["(a", "Unterminated group", 2, "unterminated_group"],
        ["(?<name", "Unterminated group name", 7, "unterminated_named_group"],
        ["(?=a", "Unterminated lookahead", 4, "unterminated_lookahead"],
        [
            String.raw`\k<A`,
            "Unterminated named backref",
            0,
            "unterminated_named_backref",
        ],
        // B.2: Invalid backreferences
        [
            String.raw`\k<A>(?<A>a)`,
            "Backreference to undefined group <A>",
            0,
            "forward_ref_by_name",
        ],
        [
            String.raw`\2(a)(b)`,
            "Backreference to undefined group \\2",
            0,
            "forward_ref_by_index",
        ],
        [
            String.raw`(a)\2`,
            "Backreference to undefined group \\2",
            3,
            "nonexistent_ref_by_index",
        ],
        // B.3: Invalid syntax
        ["(?i)a", "Inline modifiers", 1, "disallowed_inline_modifier"],
    ])(
        'should fail for "%s" (ID: %s)',
        (invalidDsl, errorPrefix, errorPos, id) => {
            /**
             * Tests that invalid syntax for groups and backrefs raises a ParseError.
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

    test("duplicate group name raises error", () => {
        /**
         * Tests that duplicate group names raise a semantic error.
         */
        expect(() => parse("(?<a>x)(?<a>y)")).toThrow(ParseError);
        expect(() => parse("(?<a>x)(?<a>y)")).toThrow(/Duplicate group name/);
    });
});

describe("Category C: Edge Cases", () => {
    /**
     * Covers edge cases for groups and backreferences.
     */

    test.each<[string, boolean, string | null, string]>([
        ["()", true, null, "empty_capturing"],
        ["(?:)", false, null, "empty_noncapturing"],
        ["(?<A>)", true, "A", "empty_named"],
    ])(
        'should parse empty group for "%s" (ID: %s)',
        (inputDsl, expectedCapturing, expectedName, id) => {
            /** Tests that empty groups parse into a Group node with an empty body. */
            const [, ast] = parse(inputDsl);
            expect(ast).toBeInstanceOf(Group);
            const groupNode = ast as Group;
            expect(groupNode.capturing).toBe(expectedCapturing);
            expect(groupNode.name).toBe(expectedName);
            expect(groupNode.body).toEqual(new Seq([]));
        }
    );

    test("backreference to an optional group should be valid syntax", () => {
        /**
         * Tests that a backreference to an optional group is syntactically valid.
         */
        const [, ast] = parse(String.raw`(a)?\1`);
        expect(ast).toBeInstanceOf(Seq);
        const seqNode = ast as Seq;
        const quantNode = seqNode.parts[0] as Quant;
        expect(quantNode).toBeInstanceOf(Quant);
        expect(quantNode.child).toBeInstanceOf(Group);
        expect(seqNode.parts[1]).toEqual(new Backref({ byIndex: 1 }));
    });

    test("should parse \\0 as a null byte, not a backreference", () => {
        /**
         * Tests that \0 is parsed as a literal null byte, not backreference 0.
         */
        const [, ast] = parse(String.raw`\0`);
        expect(ast).toEqual(new Lit("\x00"));
    });
});

describe("Category D: Interaction Cases", () => {
    /**
     * Covers interactions between groups, lookarounds, and other DSL features.
     */

    test("should handle a backreference inside a lookaround", () => {
        /**
         * Tests that a backreference can refer to a group defined before a lookaround.
         */
        const [, ast] = parse(String.raw`(?<A>a)(?=\k<A>)`);
        expect(ast).toBeInstanceOf(Seq);
        const seqNode = ast as Seq;
        expect(seqNode.parts[0]).toBeInstanceOf(Group);
        const lookNode = seqNode.parts[1] as Look;
        expect(lookNode.body).toBeInstanceOf(Backref);
        expect((lookNode.body as Backref).byName).toBe("A");
    });

    test("should handle free-spacing mode inside groups", () => {
        /**
         * Tests that free-spacing and comments work correctly inside groups.
         */
        const [, ast] = parse("%flags x\n(?<name> a #comment\n b)");
        expect(ast).toBeInstanceOf(Group);
        const groupNode = ast as Group;
        expect(groupNode.name).toBe("name");
        expect(groupNode.body).toEqual(new Seq([new Lit("a"), new Lit("b")]));
    });
});

// --- New Test Stubs for 3-Test Standard Compliance -----------------------------

describe("Category E: Nested Groups", () => {
    /**
     * Tests for nested groups of the same and different types.
     * Validates that the parser correctly handles deep nesting.
     */

    test("should parse nested capturing groups", () => {
        /**
         * Tests nested capturing groups: ((a))
         */
        const [, ast] = parse("((a))");
        expect(ast).toBeInstanceOf(Group);
        const group1 = ast as Group;
        expect(group1.capturing).toBe(true);
        expect(group1.body).toBeInstanceOf(Group);
        const group2 = group1.body as Group;
        expect(group2.capturing).toBe(true);
        expect(group2.body).toBeInstanceOf(Lit);
        expect((group2.body as Lit).value).toBe("a");
    });

    test("should parse nested non-capturing groups", () => {
        /**
         * Tests nested non-capturing groups: (?:(?:a))
         */
        const [, ast] = parse("(?:(?:a))");
        expect(ast).toBeInstanceOf(Group);
        const group1 = ast as Group;
        expect(group1.capturing).toBe(false);
        expect(group1.body).toBeInstanceOf(Group);
        const group2 = group1.body as Group;
        expect(group2.capturing).toBe(false);
        expect(group2.body).toBeInstanceOf(Lit);
        expect((group2.body as Lit).value).toBe("a");
    });

    test("should parse nested atomic groups", () => {
        /**
         * Tests nested atomic groups: (?>(?>(a)))
         */
        const [, ast] = parse("(?>(?>(a)))");
        expect(ast).toBeInstanceOf(Group);
        const group1 = ast as Group;
        expect(group1.atomic).toBe(true);
        expect(group1.body).toBeInstanceOf(Group);
        const group2 = group1.body as Group;
        expect(group2.atomic).toBe(true);
        expect(group2.body).toBeInstanceOf(Group);
        const group3 = group2.body as Group;
        expect(group3.capturing).toBe(true);
        expect(group3.body).toBeInstanceOf(Lit);
    });

    test("should parse capturing group inside non-capturing", () => {
        /**
         * Tests capturing group inside non-capturing: (?:(a))
         */
        const [, ast] = parse("(?:(a))");
        expect(ast).toBeInstanceOf(Group);
        const group1 = ast as Group;
        expect(group1.capturing).toBe(false);
        expect(group1.body).toBeInstanceOf(Group);
        const group2 = group1.body as Group;
        expect(group2.capturing).toBe(true);
        expect(group2.body).toBeInstanceOf(Lit);
        expect((group2.body as Lit).value).toBe("a");
    });

    test("should parse named group inside capturing", () => {
        /**
         * Tests named group inside capturing: ((?<name>a))
         */
        const [, ast] = parse("((?<name>a))");
        expect(ast).toBeInstanceOf(Group);
        const group1 = ast as Group;
        expect(group1.capturing).toBe(true);
        expect(group1.name).toBeNull();
        expect(group1.body).toBeInstanceOf(Group);
        const group2 = group1.body as Group;
        expect(group2.capturing).toBe(true);
        expect(group2.name).toBe("name");
        expect(group2.body).toBeInstanceOf(Lit);
    });

    test("should parse atomic group inside non-capturing", () => {
        /**
         * Tests atomic group inside non-capturing: (?:(?>a))
         */
        const [, ast] = parse("(?:(?>a))");
        expect(ast).toBeInstanceOf(Group);
        const group1 = ast as Group;
        expect(group1.capturing).toBe(false);
        expect(group1.body).toBeInstanceOf(Group);
        const group2 = group1.body as Group;
        expect(group2.atomic).toBe(true);
        expect(group2.body).toBeInstanceOf(Lit);
        expect((group2.body as Lit).value).toBe("a");
    });

    test("should parse deeply nested groups (3+ levels)", () => {
        /**
         * Tests deeply nested groups (3+ levels): ((?:(?<x>(?>a))))
         */
        const [, ast] = parse("((?:(?<x>(?>a))))");
        expect(ast).toBeInstanceOf(Group);
        const level1 = ast as Group;
        expect(level1.capturing).toBe(true);
        // Level 2
        expect(level1.body).toBeInstanceOf(Group);
        const level2 = level1.body as Group;
        expect(level2.capturing).toBe(false);
        // Level 3
        expect(level2.body).toBeInstanceOf(Group);
        const level3 = level2.body as Group;
        expect(level3.capturing).toBe(true);
        expect(level3.name).toBe("x");
        // Level 4
        expect(level3.body).toBeInstanceOf(Group);
        const level4 = level3.body as Group;
        expect(level4.atomic).toBe(true);
        expect(level4.body).toBeInstanceOf(Lit);
    });
});

describe("Category F: Lookaround With Complex Content", () => {
    /**
     * Tests for lookarounds containing complex patterns like alternations
     * and nested lookarounds.
     */

    test("should parse lookahead with alternation", () => {
        /**
         * Tests positive lookahead with alternation: (?=a|b)
         */
        const [, ast] = parse("(?=a|b)");
        expect(ast).toBeInstanceOf(Look);
        const lookNode = ast as Look;
        expect(lookNode.dir).toBe("Ahead");
        expect(lookNode.neg).toBe(false);
        expect(lookNode.body).toBeInstanceOf(Alt);
        expect((lookNode.body as Alt).branches).toHaveLength(2);
    });

    test("should parse lookbehind with alternation", () => {
        /**
         * Tests positive lookbehind with alternation: (?<=x|y)
         */
        const [, ast] = parse("(?<=x|y)");
        expect(ast).toBeInstanceOf(Look);
        const lookNode = ast as Look;
        expect(lookNode.dir).toBe("Behind");
        expect(lookNode.neg).toBe(false);
        expect(lookNode.body).toBeInstanceOf(Alt);
        expect((lookNode.body as Alt).branches).toHaveLength(2);
    });

    test("should parse negative lookahead with alternation", () => {
        /**
         * Tests negative lookahead with alternation: (?!a|b|c)
         */
        const [, ast] = parse("(?!a|b|c)");
        expect(ast).toBeInstanceOf(Look);
        const lookNode = ast as Look;
        expect(lookNode.dir).toBe("Ahead");
        expect(lookNode.neg).toBe(true);
        expect(lookNode.body).toBeInstanceOf(Alt);
        expect((lookNode.body as Alt).branches).toHaveLength(3);
    });

    test("should parse nested lookaheads", () => {
        /**
         * Tests nested positive lookaheads: (?=(?=a))
         */
        const [, ast] = parse("(?=(?=a))");
        expect(ast).toBeInstanceOf(Look);
        const outer = ast as Look;
        expect(outer.dir).toBe("Ahead");
        expect(outer.body).toBeInstanceOf(Look);
        const inner = outer.body as Look;
        expect(inner.dir).toBe("Ahead");
        expect(inner.body).toBeInstanceOf(Lit);
    });

    test("should parse nested lookbehinds", () => {
        /**
         * Tests nested lookbehinds: (?<=(?<!a))
         */
        const [, ast] = parse("(?<=(?<!a))");
        expect(ast).toBeInstanceOf(Look);
        const outer = ast as Look;
        expect(outer.dir).toBe("Behind");
        expect(outer.neg).toBe(false);
        expect(outer.body).toBeInstanceOf(Look);
        const inner = outer.body as Look;
        expect(inner.dir).toBe("Behind");
        expect(inner.neg).toBe(true);
        expect(inner.body).toBeInstanceOf(Lit);
    });

    test("should parse mixed nested lookarounds", () => {
        /**
         * Tests lookahead inside lookbehind: (?<=a(?=b))
         */
        const [, ast] = parse("(?<=a(?=b))");
        expect(ast).toBeInstanceOf(Look);
        const lookNode = ast as Look;
        expect(lookNode.dir).toBe("Behind");
        expect(lookNode.body).toBeInstanceOf(Seq);
        const seqBody = lookNode.body as Seq;
        expect(seqBody.parts).toHaveLength(2);
        expect(seqBody.parts[0]).toBeInstanceOf(Lit);
        expect(seqBody.parts[1]).toBeInstanceOf(Look);
        expect((seqBody.parts[1] as Look).dir).toBe("Ahead");
    });
});

describe("Category G: Atomic Group Edge Cases", () => {
    /**
     * Tests for atomic groups with complex content.
     */

    test("should parse atomic group with alternation", () => {
        /**
         * Tests atomic group with alternation: (?>(a|b))
         */
        const [, ast] = parse("(?>(a|b))");
        expect(ast).toBeInstanceOf(Group);
        const atomicGroup = ast as Group;
        expect(atomicGroup.atomic).toBe(true);
        // The atomic group contains a capturing group with alternation
        expect(atomicGroup.body).toBeInstanceOf(Group);
        const innerGroup = atomicGroup.body as Group;
        expect(innerGroup.capturing).toBe(true);
        expect(innerGroup.body).toBeInstanceOf(Alt);
        expect((innerGroup.body as Alt).branches).toHaveLength(2);
    });

    test("should parse atomic group with quantified content", () => {
        /**
         * Tests atomic group with quantified atoms: (?>a+b*)
         */
        const [, ast] = parse("(?>a+b*)");
        expect(ast).toBeInstanceOf(Group);
        const atomicGroup = ast as Group;
        expect(atomicGroup.atomic).toBe(true);
        expect(atomicGroup.body).toBeInstanceOf(Seq);
        const seqBody = atomicGroup.body as Seq;
        expect(seqBody.parts).toHaveLength(2);
        expect(seqBody.parts[0]).toBeInstanceOf(Quant);
        expect(seqBody.parts[1]).toBeInstanceOf(Quant);
    });

    test("should parse empty atomic group", () => {
        /**
         * Tests empty atomic group: (?>)
         * Edge case: should parse correctly.
         */
        const [, ast] = parse("(?>)");
        expect(ast).toBeInstanceOf(Group);
        const atomicGroup = ast as Group;
        expect(atomicGroup.atomic).toBe(true);
        expect(atomicGroup.body).toBeInstanceOf(Seq);
        expect((atomicGroup.body as Seq).parts).toHaveLength(0);
    });
});

describe("Category H: Multiple Backreferences", () => {
    /**
     * Tests for patterns with multiple backreferences and complex
     * backreference interactions.
     */

    test("should parse multiple numeric backrefs sequential", () => {
        /**
         * Tests multiple sequential backreferences: (a)(b)\1\2
         */
        const [, ast] = parse(String.raw`(a)(b)\1\2`);
        expect(ast).toBeInstanceOf(Seq);
        const seqNode = ast as Seq;
        expect(seqNode.parts).toHaveLength(4);
        expect(seqNode.parts[0]).toBeInstanceOf(Group);
        expect(seqNode.parts[1]).toBeInstanceOf(Group);
        expect(seqNode.parts[2]).toBeInstanceOf(Backref);
        expect((seqNode.parts[2] as Backref).byIndex).toBe(1);
        expect(seqNode.parts[3]).toBeInstanceOf(Backref);
        expect((seqNode.parts[3] as Backref).byIndex).toBe(2);
    });

    test("should parse multiple named backrefs", () => {
        /**
         * Tests multiple named backreferences: (?<x>a)(?<y>b)\k<x>\k<y>
         */
        const [, ast] = parse(String.raw`(?<x>a)(?<y>b)\k<x>\k<y>`);
        expect(ast).toBeInstanceOf(Seq);
        const seqNode = ast as Seq;
        expect(seqNode.parts).toHaveLength(4);
        expect(seqNode.parts[0]).toBeInstanceOf(Group);
        expect((seqNode.parts[0] as Group).name).toBe("x");
        expect(seqNode.parts[1]).toBeInstanceOf(Group);
        expect((seqNode.parts[1] as Group).name).toBe("y");
        expect(seqNode.parts[2]).toBeInstanceOf(Backref);
        expect((seqNode.parts[2] as Backref).byName).toBe("x");
        expect(seqNode.parts[3]).toBeInstanceOf(Backref);
        expect((seqNode.parts[3] as Backref).byName).toBe("y");
    });

    test("should parse mixed numeric and named backrefs", () => {
        /**
         * Tests mixed backreference types: (a)(?<x>b)\1\k<x>
         */
        const [, ast] = parse(String.raw`(a)(?<x>b)\1\k<x>`);
        expect(ast).toBeInstanceOf(Seq);
        const seqNode = ast as Seq;
        expect(seqNode.parts).toHaveLength(4);
        expect(seqNode.parts[0]).toBeInstanceOf(Group);
        expect(seqNode.parts[1]).toBeInstanceOf(Group);
        expect((seqNode.parts[1] as Group).name).toBe("x");
        expect(seqNode.parts[2]).toBeInstanceOf(Backref);
        expect((seqNode.parts[2] as Backref).byIndex).toBe(1);
        expect(seqNode.parts[3]).toBeInstanceOf(Backref);
        expect((seqNode.parts[3] as Backref).byName).toBe("x");
    });

    test("should parse backref in alternation", () => {
        /**
         * Tests backreference in alternation: (a)(\1|b)
         */
        const [, ast] = parse(String.raw`(a)(\1|b)`);
        expect(ast).toBeInstanceOf(Seq);
        const seqNode = ast as Seq;
        expect(seqNode.parts).toHaveLength(2);
        expect(seqNode.parts[0]).toBeInstanceOf(Group);
        const group2 = seqNode.parts[1] as Group;
        expect(group2).toBeInstanceOf(Group);
        expect(group2.body).toBeInstanceOf(Alt);
        const altBody = group2.body as Alt;
        expect(altBody.branches).toHaveLength(2);
        expect(altBody.branches[0]).toBeInstanceOf(Backref);
        expect((altBody.branches[0] as Backref).byIndex).toBe(1);
    });

    test("should parse backref to earlier alternation branch", () => {
        /**
         * Tests backreference to group in alternation: (a|b)c\1
         */
        const [, ast] = parse(String.raw`(a|b)c\1`);
        expect(ast).toBeInstanceOf(Seq);
        const seqNode = ast as Seq;
        expect(seqNode.parts).toHaveLength(3);
        expect(seqNode.parts[0]).toBeInstanceOf(Group);
        expect((seqNode.parts[0] as Group).body).toBeInstanceOf(Alt);
        expect(seqNode.parts[1]).toBeInstanceOf(Lit);
        expect(seqNode.parts[2]).toBeInstanceOf(Backref);
        expect((seqNode.parts[2] as Backref).byIndex).toBe(1);
    });

    test("should parse repeated backreference", () => {
        /**
         * Tests same backreference used multiple times: (a)\1\1
         */
        const [, ast] = parse(String.raw`(a)\1\1`);
        expect(ast).toBeInstanceOf(Seq);
        const seqNode = ast as Seq;
        expect(seqNode.parts).toHaveLength(3);
        expect(seqNode.parts[0]).toBeInstanceOf(Group);
        expect(seqNode.parts[1]).toBeInstanceOf(Backref);
        expect((seqNode.parts[1] as Backref).byIndex).toBe(1);
        expect(seqNode.parts[2]).toBeInstanceOf(Backref);
        expect((seqNode.parts[2] as Backref).byIndex).toBe(1);
    });
});

describe("Category I: Groups In Alternation", () => {
    /**
     * Tests for groups and lookarounds inside alternation patterns.
     */

    test("should parse groups in alternation branches", () => {
        /**
         * Tests capturing groups in alternation: (a)|(b)
         */
        const [, ast] = parse("(a)|(b)");
        expect(ast).toBeInstanceOf(Alt);
        const altNode = ast as Alt;
        expect(altNode.branches).toHaveLength(2);
        expect(altNode.branches[0]).toBeInstanceOf(Group);
        expect((altNode.branches[0] as Group).capturing).toBe(true);
        expect(altNode.branches[1]).toBeInstanceOf(Group);
        expect((altNode.branches[1] as Group).capturing).toBe(true);
    });

    test("should parse lookarounds in alternation", () => {
        /**
         * Tests lookarounds in alternation: (?=a)|(?=b)
         */
        const [, ast] = parse("(?=a)|(?=b)");
        expect(ast).toBeInstanceOf(Alt);
        const altNode = ast as Alt;
        expect(altNode.branches).toHaveLength(2);
        expect(altNode.branches[0]).toBeInstanceOf(Look);
        expect((altNode.branches[0] as Look).dir).toBe("Ahead");
        expect(altNode.branches[1]).toBeInstanceOf(Look);
        expect((altNode.branches[1] as Look).dir).toBe("Ahead");
    });

    test("should parse mixed group types in alternation", () => {
        /**
         * Tests mixed group types in alternation: (a)|(?:b)|(?<x>c)
         */
        const [, ast] = parse("(a)|(?:b)|(?<x>c)");
        expect(ast).toBeInstanceOf(Alt);
        const altNode = ast as Alt;
        expect(altNode.branches).toHaveLength(3);

        const branch0 = altNode.branches[0] as Group;
        expect(branch0).toBeInstanceOf(Group);
        expect(branch0.capturing).toBe(true);
        expect(branch0.name).toBeNull();

        const branch1 = altNode.branches[1] as Group;
        expect(branch1).toBeInstanceOf(Group);
        expect(branch1.capturing).toBe(false);

        const branch2 = altNode.branches[2] as Group;
        expect(branch2).toBeInstanceOf(Group);
        expect(branch2.capturing).toBe(true);
        expect(branch2.name).toBe("x");
    });
});
