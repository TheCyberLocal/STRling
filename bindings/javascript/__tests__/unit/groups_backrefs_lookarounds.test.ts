/**
 * @file Test Design — groups_backrefs_lookarounds.test.ts
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
 * -   Validation of backreferences (e.g., ensuring no forward references).
 * -   Parsing of all four lookaround types: positive/negative lookahead and
 * positive/negative lookbehind.
 * -   Error handling for unterminated constructs and invalid backreferences.
 * -   The structure of the resulting `nodes.Group`, `nodes.Backref`, and
 * `nodes.Look` AST nodes.
 * -   **Out of scope:**
 * -   Quantification of these constructs (covered in `quantifiers.test.ts`).
 * -   Semantic validation of lookbehind contents (e.g., the fixed-length
 * requirement).
 * -   Emitter-specific syntax transformations (e.g., Python's `(?P<name>...)`).
 */

import { parse, ParseError } from "../../src/STRling/core/parser";
import {
    Group,
    Backref,
    Look,
    Seq,
    Lit,
    Quant,
} from "../../src/STRling/core/nodes";

// --- Test Suite -----------------------------------------------------------------

describe("Category A: Positive Cases", () => {
    /**
     * Covers all positive cases for valid group, backreference, and lookaround syntax.
     *
     */

    test.each<[string, boolean, string | null, boolean | null, string]>([
        ["(a)", true, null, null, "capturing"],
        ["(?:a)", false, null, null, "non_capturing"],
        ["(?<name>a)", true, "name", null, "named_capturing"],
        ["(?>a)", false, null, true, "atomic_ext"],
    ])(
        'should parse group type for "%s" (ID: %s)',
        (inputDsl, expectedCapturing, expectedName, expectedAtomic) => {
            /** Tests that various group types are parsed with the correct attributes. */
            const [, ast] = parse(inputDsl);
            expect(ast).toBeInstanceOf(Group);
            const groupNode = ast as Group;
            expect(groupNode.capturing).toBe(expectedCapturing);
            expect(groupNode.name).toBe(expectedName);
            expect(groupNode.atomic).toBe(expectedAtomic ?? null); // Handle undefined vs null
            expect(groupNode.body).toBeInstanceOf(Lit);
        }
    );

    test.each<[string, Backref, string]>([
        ["(a)\\1", new Backref({ byIndex: 1 }), "numeric_backref"],
        ["(?<A>a)\\k<A>", new Backref({ byName: "A" }), "named_backref"],
    ])(
        'should parse backreference for "%s" (ID: %s)',
        (inputDsl, expectedBackref) => {
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
        (inputDsl, expectedDir, expectedNeg) => {
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
     *
     */
    test.each<[string, string, number, string]>([
        // B.1: Unterminated constructs
        ["(a", "Unterminated group", 2, "unterminated_group"],
        ["(?<name", "Unterminated group name", 7, "unterminated_named_group"],
        ["(?=a", "Unterminated lookahead", 4, "unterminated_lookahead"],
        [
            "\\k<A",
            "Unterminated named backref",
            0,
            "unterminated_named_backref",
        ],
        // B.2: Invalid backreferences
        [
            "\\k<A>(?<A>a)",
            "Backreference to undefined group <A>",
            0,
            "forward_ref_by_name",
        ],
        [
            "\\2(a)(b)",
            "Backreference to undefined group \\2",
            0,
            "forward_ref_by_index",
        ],
        [
            "(a)\\2",
            "Backreference to undefined group \\2",
            3,
            "nonexistent_ref_by_index",
        ],
        // B.3: Invalid syntax
        ["(?i)a", "Inline modifiers", 1, "disallowed_inline_modifier"],
    ])('should fail for "%s" (ID: %s)', (invalidDsl, errorPrefix, errorPos) => {
        /** Tests that invalid syntax for groups and backrefs raises a ParseError. */
        expect(() => parse(invalidDsl)).toThrow(ParseError);
        try {
            parse(invalidDsl);
        } catch (e) {
            const err = e as ParseError;
            expect(err.message).toContain(errorPrefix);
            expect(err.pos).toBe(errorPos);
        }
    });

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

describe("Category C: Edge Cases", () => {
    /**
     * Covers edge cases for groups and backreferences.
     *
     */
    test.each<[string, boolean, string | null, string]>([
        ["()", true, null, "empty_capturing"],
        ["(?:)", false, null, "empty_noncapturing"],
        ["(?<A>)", true, "A", "empty_named"],
    ])(
        'should parse empty group for "%s" (ID: %s)',
        (inputDsl, expectedCapturing, expectedName) => {
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
         *
         */
        const [, ast] = parse("(a)?\\1");
        expect(ast).toBeInstanceOf(Seq);
        const seqNode = ast as Seq;
        expect(seqNode.parts[0]).toBeInstanceOf(Quant);
        expect((seqNode.parts[0] as Quant).child).toBeInstanceOf(Group);
        expect(seqNode.parts[1]).toEqual(new Backref({ byIndex: 1 }));
    });

    test("should parse \\0 as a null byte, not a backreference", () => {
        /**
         * Tests that \0 is parsed as a literal null byte, not backreference 0.
         *
         */
        const [, ast] = parse("\\0");
        expect(ast).toEqual(new Lit("\x00"));
    });
});

describe("Category D: Interaction Cases", () => {
    /**
     * Covers interactions between groups, lookarounds, and other DSL features.
     *
     */

    test("should handle a backreference inside a lookaround", () => {
        /**
         * Tests that a backreference can refer to a group defined before a lookaround.
         *
         */
        const [, ast] = parse("(?<A>a)(?=\\k<A>)");
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
         *
         */
        const [, ast] = parse(`%flags x
(?<name> a #comment
 b)`);
        expect(ast).toBeInstanceOf(Group);
        const groupNode = ast as Group;
        expect(groupNode.name).toBe("name");
        expect(groupNode.body).toEqual(new Seq([new Lit("a"), new Lit("b")]));
    });
});
