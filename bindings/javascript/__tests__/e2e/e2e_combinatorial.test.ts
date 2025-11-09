/**
 * @file Test Design — e2e/test_e2e_combinatorial.ts
 *
 * ## Purpose
 * This test suite provides systematic combinatorial E2E validation to ensure that
 * different STRling features work correctly when combined. It follows a risk-based,
 * tiered approach to manage test complexity while achieving comprehensive coverage.
 *
 * ## Description
 * Unlike unit tests that test individual features in isolation, this suite tests
 * feature interactions using two strategies:
 *
 * 1. **Tier 1 (Pairwise)**: Tests all N=2 combinations of core features
 * 2. **Tier 2 (Strategic Triplets)**: Tests N=3 combinations of high-risk features
 *
 * The tests verify that the full compile pipeline (parse -> compile -> emit)
 * correctly handles feature interactions.
 *
 * ## Scope
 * -   **In scope:**
 * -   Pairwise (N=2) combinations of all core features
 * -   Strategic triplet (N=3) combinations of high-risk features
 * -   End-to-end validation from DSL to PCRE2 output
 * -   Detection of interaction bugs between features
 *
 * -   **Out of scope:**
 * -   Exhaustive N³ or higher combinations
 * -   Runtime behavior validation (covered by conformance tests)
 * -   Individual feature testing (covered by unit tests)
 */

// These imports assume a project structure.
// The paths may need adjustment based on your 'tsconfig.json' or test setup.
import { parse } from "../../src/STRling/core/parser";
import { Compiler } from "../../src/STRling/core/compiler";
import { emit as emitPcre2 } from "../../src/STRling/emitters/pcre2";

// --- Helper Function ------------------------------------------------------------

function compileToPcre(src: string): string {
    // A helper to run the full DSL -> PCRE2 string pipeline.
    const [flags, ast] = parse(src);
    const irRoot = new Compiler().compile(ast);
    return emitPcre2(irRoot, flags);
}

// Type alias for test cases
type TestCase = {
    id: string;
    input: string;
    expected: string;
};

// --- Tier 1: Pairwise Combinatorial Tests (N=2) --------------------------------

describe("Tier 1: Pairwise Combinatorial Tests (N=2)", () => {
    /**
     * Tests all pairwise (N=2) combinations of core STRling features.
     */

    // Flags + Other Features
    describe("Flags + other features", () => {
        const cases: TestCase[] = [
            // Flags + Literals
            {
                id: "flags_literals_case_insensitive",
                input: "%flags i\nhello",
                expected: String.raw`(?i)hello`,
            },
            {
                id: "flags_literals_free_spacing",
                input: "%flags x\na b c",
                expected: String.raw`(?x)abc`,
            },
            // Flags + Character Classes
            {
                id: "flags_charclass_case_insensitive",
                input: "%flags i\n[a-z]+",
                expected: String.raw`(?i)[a-z]+`,
            },
            {
                id: "flags_charclass_unicode",
                input: "%flags u\n\\p{L}+",
                expected: String.raw`(?u)\p{L}+`,
            },
            // Flags + Anchors
            {
                id: "flags_anchor_multiline_start",
                input: "%flags m\n^start",
                expected: String.raw`(?m)^start`,
            },
            {
                id: "flags_anchor_multiline_end",
                input: "%flags m\nend$",
                expected: String.raw`(?m)end$`,
            },
            // Flags + Quantifiers
            {
                id: "flags_quantifier_dotall",
                input: "%flags s\na*",
                expected: String.raw`(?s)a*`,
            },
            {
                id: "flags_quantifier_free_spacing",
                input: "%flags x\na{2,5}",
                expected: String.raw`(?x)a{2,5}`,
            },
            // Flags + Groups
            {
                id: "flags_group_case_insensitive",
                input: "%flags i\n(hello)",
                expected: String.raw`(?i)(hello)`,
            },
            {
                id: "flags_group_named_free_spacing",
                input: "%flags x\n(?<name>\\d+)",
                expected: String.raw`(?x)(?<name>\d+)`,
            },
            // Flags + Lookarounds
            {
                id: "flags_lookahead_case_insensitive",
                input: "%flags i\n(?=test)",
                expected: String.raw`(?i)(?=test)`,
            },
            {
                id: "flags_lookbehind_multiline",
                input: "%flags m\n(?<=^foo)",
                expected: String.raw`(?m)(?<=^foo)`,
            },
            // Flags + Alternation
            {
                id: "flags_alternation_case_insensitive",
                input: "%flags i\na|b|c",
                expected: String.raw`(?i)a|b|c`,
            },
            {
                id: "flags_alternation_free_spacing",
                input: "%flags x\nfoo | bar",
                expected: String.raw`(?x)foo|bar`,
            },
            // Flags + Backreferences
            {
                id: "flags_backref_case_insensitive",
                input: "%flags i\n(\\w+)\\s+\\1",
                expected: String.raw`(?i)(\w+)\s+\1`,
            },
        ];

        test.each(cases)("$id", ({ input, expected }) => {
            /** Tests flags combined with each other core feature. */
            expect(compileToPcre(input)).toBe(expected);
        });
    });

    // Literals + Other Features
    describe("Literals + other features", () => {
        const cases: TestCase[] = [
            // Literals + Character Classes
            {
                id: "literals_charclass",
                input: "abc[xyz]",
                expected: String.raw`abc[xyz]`,
            },
            {
                id: "literals_charclass_mixed",
                input: "\\d\\d\\d-[0-9]",
                expected: String.raw`\d\d\d-[0-9]`,
            },
            // Literals + Anchors
            {
                id: "literals_anchor_start",
                input: "^hello",
                expected: String.raw`^hello`,
            },
            {
                id: "literals_anchor_end",
                input: "world$",
                expected: String.raw`world$`,
            },
            {
                id: "literals_anchor_word_boundary",
                input: "\\bhello\\b",
                expected: String.raw`\bhello\b`,
            },
            // Literals + Quantifiers
            {
                id: "literals_quantifier_plus",
                input: "a+bc",
                expected: String.raw`a+bc`,
            },
            {
                id: "literals_quantifier_brace",
                input: "test\\d{3}",
                expected: String.raw`test\d{3}`,
            },
            // Literals + Groups
            {
                id: "literals_group_capturing",
                input: "hello(world)",
                expected: String.raw`hello(world)`,
            },
            {
                id: "literals_group_noncapturing",
                input: "test(?:group)",
                expected: String.raw`test(?:group)`,
            },
            // Literals + Lookarounds
            {
                id: "literals_lookahead",
                input: "hello(?=world)",
                expected: String.raw`hello(?=world)`,
            },
            {
                id: "literals_lookbehind",
                input: "(?<=test)result",
                expected: String.raw`(?<=test)result`,
            },
            // Literals + Alternation
            {
                id: "literals_alternation_words",
                input: "hello|world",
                expected: String.raw`hello|world`,
            },
            {
                id: "literals_alternation_chars",
                input: "a|b|c",
                expected: String.raw`a|b|c`,
            },
            // Literals + Backreferences
            {
                id: "literals_backref",
                input: "(\\w+)=\\1",
                expected: String.raw`(\w+)=\1`,
            },
        ];

        test.each(cases)("$id", ({ input, expected }) => {
            /** Tests literals combined with each other core feature. */
            expect(compileToPcre(input)).toBe(expected);
        });
    });

    // Character Classes + Other Features
    describe("Character classes + other features", () => {
        const cases: TestCase[] = [
            // Character Classes + Anchors
            {
                id: "charclass_anchor_start",
                input: "^[a-z]+",
                expected: String.raw`^[a-z]+`,
            },
            {
                id: "charclass_anchor_end",
                input: "[0-9]+$",
                expected: String.raw`[0-9]+$`,
            },
            // Character Classes + Quantifiers
            {
                id: "charclass_quantifier_star",
                input: "[a-z]*",
                expected: String.raw`[a-z]*`,
            },
            {
                id: "charclass_quantifier_brace",
                input: "[0-9]{2,4}",
                expected: String.raw`[0-9]{2,4}`,
            },
            {
                id: "charclass_quantifier_lazy",
                input: "\\w+?",
                expected: String.raw`\w+?`,
            },
            // Character Classes + Groups
            {
                id: "charclass_group_capturing",
                input: "([a-z]+)",
                expected: String.raw`([a-z]+)`,
            },
            {
                id: "charclass_group_noncapturing",
                input: "(?:[0-9]+)",
                expected: String.raw`(?:[0-9]+)`,
            },
            // Character Classes + Lookarounds
            {
                id: "charclass_lookahead",
                input: "(?=[a-z])",
                expected: String.raw`(?=[a-z])`,
            },
            {
                id: "charclass_lookbehind",
                input: "(?<=\\d)",
                expected: String.raw`(?<=\d)`,
            },
            // Character Classes + Alternation
            {
                id: "charclass_alternation_classes",
                input: "[a-z]|[0-9]",
                expected: String.raw`[a-z]|[0-9]`,
            },
            {
                id: "charclass_alternation_shorthands",
                input: "\\w|\\s",
                expected: String.raw`\w|\s`,
            },
            // Character Classes + Backreferences
            {
                id: "charclass_backref",
                input: "([a-z])\\1",
                expected: String.raw`([a-z])\1`,
            },
        ];

        test.each(cases)("$id", ({ input, expected }) => {
            /** Tests character classes combined with each other core feature. */
            expect(compileToPcre(input)).toBe(expected);
        });
    });

    // Anchors + Other Features
    describe("Anchors + other features", () => {
        const cases: TestCase[] = [
            // Anchors + Quantifiers
            {
                id: "anchor_quantifier_start",
                input: "^a+",
                expected: String.raw`^a+`,
            },
            {
                id: "anchor_quantifier_boundary",
                input: "\\b\\w+",
                expected: String.raw`\b\w+`,
            },
            // Anchors + Groups
            {
                id: "anchor_group_start",
                input: "^(test)",
                expected: String.raw`^(test)`,
            },
            {
                id: "anchor_group_end",
                input: "(start)$",
                expected: String.raw`(start)$`,
            },
            // Anchors + Lookarounds
            {
                id: "anchor_lookahead",
                input: "^(?=test)",
                expected: String.raw`^(?=test)`,
            },
            {
                id: "anchor_lookbehind",
                input: "(?<=^foo)",
                expected: String.raw`(?<=^foo)`,
            },
            // Anchors + Alternation
            {
                id: "anchor_alternation",
                input: "^a|b$",
                expected: String.raw`^a|b$`,
            },
            // Anchors + Backreferences
            {
                id: "anchor_backref",
                input: "^(\\w+)\\s+\\1$",
                expected: String.raw`^(\w+)\s+\1$`,
            },
        ];

        test.each(cases)("$id", ({ input, expected }) => {
            /** Tests anchors combined with each other core feature. */
            expect(compileToPcre(input)).toBe(expected);
        });
    });

    // Quantifiers + Other Features
    describe("Quantifiers + other features", () => {
        const cases: TestCase[] = [
            // Quantifiers + Groups
            {
                id: "quantifier_group_capturing",
                input: "(abc)+",
                expected: String.raw`(abc)+`,
            },
            {
                id: "quantifier_group_noncapturing",
                input: "(?:test)*",
                expected: String.raw`(?:test)*`,
            },
            {
                id: "quantifier_group_named",
                input: "(?<name>\\d)+",
                expected: String.raw`(?<name>\d)+`,
            },
            // Quantifiers + Lookarounds
            {
                id: "quantifier_lookahead",
                input: "(?=a)+",
                expected: String.raw`(?:(?=a))+`,
            },
            {
                id: "quantifier_lookbehind",
                input: "test(?<=\\d)*",
                expected: String.raw`test(?:(?<=\d))*`,
            },
            // Quantifiers + Alternation
            {
                id: "quantifier_alternation_group",
                input: "(a|b)+",
                expected: String.raw`(a|b)+`,
            },
            {
                id: "quantifier_alternation_noncapturing",
                input: "(?:foo|bar)*",
                expected: String.raw`(?:foo|bar)*`,
            },
            // Quantifiers + Backreferences
            {
                id: "quantifier_backref_repeated",
                input: "(\\w)\\1+",
                expected: String.raw`(\w)\1+`,
            },
            {
                id: "quantifier_backref_specific",
                input: "(\\d+)-\\1{2}",
                expected: String.raw`(\d+)-\1{2}`,
            },
        ];

        test.each(cases)("$id", ({ input, expected }) => {
            /** Tests quantifiers combined with each other core feature. */
            expect(compileToPcre(input)).toBe(expected);
        });
    });

    // Groups + Other Features
    describe("Groups + other features", () => {
        const cases: TestCase[] = [
            // Groups + Lookarounds
            {
                id: "group_lookahead_inside",
                input: "((?=test)abc)",
                expected: String.raw`((?=test)abc)`,
            },
            {
                id: "group_lookbehind_inside",
                input: "(?:(?<=\\d)result)",
                expected: String.raw`(?:(?<=\d)result)`,
            },
            // Groups + Alternation
            {
                id: "group_alternation_capturing",
                input: "(a|b|c)",
                expected: String.raw`(a|b|c)`,
            },
            {
                id: "group_alternation_noncapturing",
                input: "(?:foo|bar)",
                expected: String.raw`(?:foo|bar)`,
            },
            // Groups + Backreferences
            {
                id: "group_backref_numbered",
                input: "(\\w+)\\s+\\1",
                expected: String.raw`(\w+)\s+\1`,
            },
            {
                id: "group_backref_named",
                input: "(?<tag>\\w+)\\k<tag>",
                expected: String.raw`(?<tag>\w+)\k<tag>`,
            },
        ];

        test.each(cases)("$id", ({ input, expected }) => {
            /** Tests groups combined with each other core feature. */
            expect(compileToPcre(input)).toBe(expected);
        });
    });

    // Lookarounds + Other Features
    describe("Lookarounds + other features", () => {
        const cases: TestCase[] = [
            // Lookarounds + Alternation
            {
                id: "lookahead_alternation",
                input: "(?=a|b)",
                expected: String.raw`(?=a|b)`,
            },
            {
                id: "lookbehind_alternation",
                input: "(?<=foo|bar)",
                expected: String.raw`(?<=foo|bar)`,
            },
            // Lookarounds + Backreferences
            {
                id: "lookahead_backref",
                input: "(\\w+)(?=\\1)",
                expected: String.raw`(\w+)(?=\1)`,
            },
        ];

        test.each(cases)("$id", ({ input, expected }) => {
            /** Tests lookarounds combined with each other core feature. */
            expect(compileToPcre(input)).toBe(expected);
        });
    });

    // Alternation + Backreferences
    describe("Alternation + backreferences", () => {
        const cases: TestCase[] = [
            {
                id: "alternation_backref",
                input: "(a)\\1|(b)\\2",
                expected: String.raw`(a)\1|(b)\2`,
            },
        ];

        test.each(cases)("$id", ({ input, expected }) => {
            /** Tests alternation combined with backreferences. */
            expect(compileToPcre(input)).toBe(expected);
        });
    });
});

// --- Tier 2: Strategic Triplet Tests (N=3) -------------------------------------

describe("Tier 2: Strategic Triplet Tests (N=3)", () => {
    /**
     * Tests strategic triplet (N=3) combinations of high-risk features where
     * bugs are most likely to hide: Flags, Groups, Quantifiers, Lookarounds,
     * and Alternation.
     */
    const cases: TestCase[] = [
        // Flags + Groups + Quantifiers
        {
            id: "flags_groups_quantifiers_case",
            input: "%flags i\n(hello)+",
            expected: String.raw`(?i)(hello)+`,
        },
        {
            id: "flags_groups_quantifiers_spacing",
            input: "%flags x\n(?:a b)+",
            expected: String.raw`(?x)(?:ab)+`,
        },
        {
            id: "flags_groups_quantifiers_named",
            input: "%flags i\n(?<name>\\w)+",
            expected: String.raw`(?i)(?<name>\w)+`,
        },
        // Flags + Groups + Lookarounds
        {
            id: "flags_groups_lookahead",
            input: "%flags i\n((?=test)result)",
            expected: String.raw`(?i)((?=test)result)`,
        },
        {
            id: "flags_groups_lookbehind",
            input: "%flags m\n(?:(?<=^)start)",
            expected: String.raw`(?m)(?:(?<=^)start)`,
        },
        // Flags + Quantifiers + Lookarounds
        {
            id: "flags_quantifiers_lookahead",
            input: "%flags i\n(?=test)+",
            expected: String.raw`(?i)(?:(?=test))+`,
        },
        {
            id: "flags_quantifiers_lookbehind",
            input: "%flags s\n.*(?<=end)",
            expected: String.raw`(?s).*(?<=end)`,
        },
        // Flags + Alternation + Groups
        {
            id: "flags_alternation_groups_case",
            input: "%flags i\n(a|b|c)",
            expected: String.raw`(?i)(a|b|c)`,
        },
        {
            id: "flags_alternation_groups_spacing",
            input: "%flags x\n(?:foo | bar | baz)",
            expected: String.raw`(?x)(?:foo|bar|baz)`,
        },
        // Groups + Quantifiers + Lookarounds
        {
            id: "groups_quantifiers_lookahead",
            input: "((?=\\d)\\w)+",
            expected: String.raw`((?=\d)\w)+`,
        },
        {
            id: "groups_quantifiers_lookbehind",
            input: "(?:(?<=test)\\w+)*",
            expected: String.raw`(?:(?<=test)\w+)*`,
        },
        // Groups + Quantifiers + Alternation
        {
            id: "groups_quantifiers_alternation",
            input: "(a|b)+",
            expected: String.raw`(a|b)+`,
        },
        {
            id: "groups_quantifiers_alternation_brace",
            input: "(?:foo|bar){2,5}",
            expected: String.raw`(?:foo|bar){2,5}`,
        },
        // Quantifiers + Lookarounds + Alternation
        {
            id: "quantifiers_lookahead_alternation",
            input: "(?=a|b)+",
            expected: String.raw`(?:(?=a|b))+`,
        },
        {
            id: "quantifiers_lookbehind_alternation",
            input: "(foo|bar)(?<=test)*",
            expected: String.raw`(foo|bar)(?:(?<=test))*`,
        },
    ];

    test.each(cases)("$id", ({ input, expected }) => {
        /** Tests strategic triplets of high-risk feature interactions. */
        expect(compileToPcre(input)).toBe(expected);
    });
});

// --- Complex Nested Feature Tests -----------------------------------------------

describe("Complex Nested Feature Tests", () => {
    /**
     * Tests complex nested combinations that are especially prone to bugs.
     */
    const cases: TestCase[] = [
        // Deeply nested groups with quantifiers
        {
            id: "deeply_nested_quantifiers",
            input: "((a+)+)+",
            expected: String.raw`((a+)+)+`,
        },
        // Multiple lookarounds in sequence
        {
            id: "multiple_lookarounds",
            input: "(?=test)(?!fail)result",
            expected: String.raw`(?=test)(?!fail)result`,
        },
        // Nested alternation with groups
        {
            id: "nested_alternation",
            input: "(a|(b|c))",
            expected: String.raw`(a|(b|c))`,
        },
        // Quantified lookaround with backreference
        {
            id: "quantified_lookaround_backref",
            input: "(\\w)(?=\\1)+",
            expected: String.raw`(\w)(?:(?=\1))+`,
        },
        // Complex free spacing with all features
        {
            id: "complex_free_spacing",
            input: "%flags x\n(?<tag> \\w+ ) \\s* = \\s* (?<value> [^>]+ ) \\k<tag>",
            expected: String.raw`(?x)(?<tag>\w+)\s*=\s*(?<value>[^>]+)\k<tag>`,
        },
        // Atomic group with quantifiers
        {
            id: "atomic_group_quantifier",
            input: "(?>a+)b",
            expected: String.raw`(?>a+)b`,
        },
        // Possessive quantifiers in groups
        {
            id: "possessive_in_group",
            input: "(a*+)b",
            expected: String.raw`(a*+)b`,
        },
    ];

    test.each(cases)("$id", ({ input, expected }) => {
        /** Tests complex nested feature combinations. */
        expect(compileToPcre(input)).toBe(expected);
    });
});
