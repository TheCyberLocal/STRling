/**
 * @file Test Design — unit/ir_compiler.test.ts
 *
 * ## Purpose
 * This test suite validates the compiler's two primary responsibilities: the
 * **lowering** of the AST into an Intermediate Representation (IR), and the
 * subsequent **normalization** of that IR. It ensures that every AST construct is
 * correctly translated and that the IR is optimized according to a set of defined
 * rules.
 *
 * ## Description
 * The compiler (`core/compiler.ts`) acts as the "middle-end" of the STRling
 * pipeline. It receives a structured Abstract Syntax Tree (AST) from the parser
 * and transforms it into a simpler, canonical Intermediate Representation (IR)
 * that is ideal for the final emitters. This process involves a direct
 * translation from AST nodes to IR nodes, followed by a normalization pass that
 * flattens nested structures and fuses adjacent literals for efficiency. This test
 * suite verifies the correctness of these tree-to-tree transformations in isolation.
 *
 * ## Scope
 * -   **In scope:**
 * -   The one-to-one mapping (lowering) of every AST node from `nodes.ts` to
 * its corresponding IR node in `ir.ts`.
 * -   The specific transformation rules of the IR normalization pass:
 * flattening nested `IRSeq` and `IRAlt` nodes, and coalescing adjacent
 * `IRLit` nodes.
 * -   The structural integrity of the final IR tree after both lowering and
 * normalization.
 * -   The correct generation of the `metadata.features_used` list for
 * patterns containing special features (e.g., atomic groups).
 *
 * -   **Out of scope:**
 * -   The correctness of the input AST (this is the parser's responsibility).
 * Tests will construct AST nodes manually.
 * -   The final emitted regex string (this is the emitter's responsibility).
 *
 * -   The parsing of the source DSL (covered in other unit tests).
 *
 */

import { Compiler } from "../../src/STRling/core/compiler";
import * as N from "../../src/STRling/core/nodes";
import * as IR from "../../src/STRling/core/ir";

// --- Test Suite -----------------------------------------------------------------

describe("Category A: AST to IR Lowering", () => {
    /**
     * Verifies the direct, pre-normalization translation from AST to IR.
     * These tests use bracket notation to access the private `_lower` method
     * to test this stage in isolation.
     */

    test.each<[string, N.Node, IR.IROp]>([
        ["Lit", new N.Lit("a"), new IR.IRLit("a")],
        ["Dot", new N.Dot(), new IR.IRDot()],
        ["Anchor", new N.Anchor("Start"), new IR.IRAnchor("Start")],
        [
            "CharClass",
            new N.CharClass(false, [new N.ClassRange("a", "z")]),
            new IR.IRCharClass(false, [new IR.IRClassRange("a", "z")]),
        ],
        [
            "Seq",
            new N.Seq([new N.Lit("a"), new N.Dot()]),
            new IR.IRSeq([new IR.IRLit("a"), new IR.IRDot()]),
        ],
        [
            "Alt",
            new N.Alt([new N.Lit("a"), new N.Lit("b")]),
            new IR.IRAlt([new IR.IRLit("a"), new IR.IRLit("b")]),
        ],
        [
            "Quant",
            new N.Quant(new N.Lit("a"), 1, "Inf", "Greedy"),
            new IR.IRQuant(new N.Lit("a"), 1, "Inf", "Greedy"),
        ],
        [
            "Group",
            new N.Group(true, new N.Dot(), "x"),
            new IR.IRGroup(true, new IR.IRDot(), "x"),
        ],
        [
            "Backref",
            new N.Backref({ byIndex: 1 }),
            new IR.IRBackref({ byIndex: 1 }),
        ],
        [
            "Look",
            new N.Look("Ahead", false, new N.Lit("a")),
            new IR.IRLook("Ahead", false, new IR.IRLit("a")),
        ],
    ])(
        "should lower AST node for %s correctly",
        (id, astNode, expectedIrNode) => {
            /**
             * Tests that each AST node type is correctly lowered to its corresponding IR node type.
             */
            const compiler = new Compiler();
            // Accessing private method for isolated unit testing
            // @ts-ignore - Accessing private method for testing
            expect(compiler._lower(astNode)).toEqual(expectedIrNode);
        }
    );
});

describe("Category B: IR Normalization", () => {
    /**
     * Verifies the specific transformation rules of the IR normalization pass.
     * These tests use bracket notation to access the private `_normalize` method.
     */
    const compiler = new Compiler();

    test("should fuse adjacent literals", () => {
        /**
         * An IRSeq with adjacent IRLit nodes must be fused into a single IRLit.
         */
        const unNormalized = new IR.IRSeq([
            new IR.IRLit("a"),
            new IR.IRLit("b"),
            new IR.IRDot(),
            new IR.IRLit("c"),
        ]);
        // @ts-ignore - Accessing private method for testing
        const normalized = compiler._normalize(unNormalized);
        expect(normalized).toEqual(
            new IR.IRSeq([
                new IR.IRLit("ab"),
                new IR.IRDot(),
                new IR.IRLit("c"),
            ])
        );
    });

    test("should flatten nested sequences", () => {
        /** A nested IRSeq must be flattened into a single IRSeq. */
        const unNormalized = new IR.IRSeq([
            new IR.IRLit("a"),
            new IR.IRSeq([new IR.IRLit("b"), new IR.IRLit("c")]),
        ]);
        // Note: Flattening and fusion happen in the same pass
        // @ts-ignore - Accessing private method for testing
        const normalized = compiler._normalize(unNormalized);
        expect(normalized).toEqual(new IR.IRLit("abc"));
    });

    test("should flatten nested alternations", () => {
        /** A nested IRAlt must be flattened into a single IRAlt. */
        const unNormalized = new IR.IRAlt([
            new IR.IRLit("a"),
            new IR.IRAlt([new IR.IRLit("b"), new IR.IRLit("c")]),
        ]);
        // @ts-ignore - Accessing private method for testing
        const normalized = compiler._normalize(unNormalized);
        expect(normalized).toEqual(
            new IR.IRAlt([
                new IR.IRLit("a"),
                new IR.IRLit("b"),
                new IR.IRLit("c"),
            ])
        );
    });

    test("should be idempotent", () => {
        /** Running normalize on an already-normalized IR should produce no changes. */
        const normalizedIr = new IR.IRSeq([new IR.IRLit("ab"), new IR.IRDot()]);
        // @ts-ignore - Accessing private method for testing
        const result = compiler._normalize(normalizedIr);
        expect(result).toEqual(normalizedIr);
    });
});

describe("Category C: Full Compilation (Lower + Normalize)", () => {
    /**
     * Verifies the public `compile()` method to ensure both lowering and
     * normalization work together correctly.
     */
    const compiler = new Compiler();

    test("should compile an AST with adjacent literals to a single fused IRLit", () => {
        /**
         * An AST with adjacent Lit nodes should compile to a single fused IRLit.
         */
        const ast = new N.Seq([
            new N.Lit("hello"),
            new N.Lit(" "),
            new N.Lit("world"),
        ]);
        const ir = compiler.compile(ast);
        expect(ir).toEqual(new IR.IRLit("hello world"));
    });

    test("should compile a nested AST sequence to a flat, fused IR node", () => {
        /**
         * A deeply nested AST Seq should compile to a single, flat, fused IR node.
         */
        const ast = new N.Seq([
            new N.Lit("a"),
            new N.Seq([new N.Lit("b"), new N.Seq([new N.Dot()])]),
        ]);
        const ir = compiler.compile(ast);
        expect(ir).toEqual(new IR.IRSeq([new IR.IRLit("ab"), new IR.IRDot()]));
    });
});

describe("Category D: Metadata Generation", () => {
    /**
     * Verifies the `compileWithMetadata` method and its feature analysis.
     */

    test.each<[string, N.Node, string]>([
        [
            "atomic_group",
            new N.Group(false, new N.Lit("a"), undefined, true),
            "atomic_group",
        ],
        [
            "possessive_quantifier",
            new N.Quant(new N.Lit("a"), 1, "Inf", "Possessive"),
            "possessive_quantifier",
        ],
        [
            "lookbehind",
            new N.Look("Behind", false, new N.Lit("a")),
            "lookbehind",
        ],
    ])(
        "should detect feature for %s (ID: %s)",
        (id, astNode, expectedFeature) => {
            /**
             * Tests that ASTs with special features produce an artifact with the
             * correct metadata.
             */
            const compiler = new Compiler();
            const artifact = compiler.compileWithMetadata(astNode);

            // This matches the Python implementation which checks the dict directly
            expect(artifact.metadata).toBeDefined();
            expect(artifact.metadata.features_used).toContain(expectedFeature);
        }
    );

    test("should produce empty metadata for a pattern with no special features", () => {
        /**
         * Tests that a simple AST with no special features produces an empty
         * features_used list.
         */
        const compiler = new Compiler();
        const ast = new N.Seq([new N.Lit("a"), new N.Dot()]);
        const artifact = compiler.compileWithMetadata(ast);

        expect(artifact.metadata).toBeDefined();
        expect(artifact.metadata.features_used).toEqual([]);
    });
});

// --- New Test Stubs for 3-Test Standard Compliance -----------------------------

describe("Category E: Deeply Nested Alternations", () => {
    /**
     * Tests for deeply nested alternation structures and their normalization.
     */

    test("should flatten three-level nested alternation", () => {
        /**
         * Tests deeply nested alternation: (a|(b|(c|d)))
         * Should be flattened to IRAlt([a, b, c, d]).
         */
        const compiler = new Compiler();
        // Build: Alt([Lit("a"), Alt([Lit("b"), Alt([Lit("c"), Lit("d")])])])
        const ast = new N.Alt([
            new N.Lit("a"),
            new N.Alt([
                new N.Lit("b"),
                new N.Alt([new N.Lit("c"), new N.Lit("d")]),
            ]),
        ]);
        const ir = compiler.compile(ast);
        expect(ir).toEqual(
            new IR.IRAlt([
                new IR.IRLit("a"),
                new IR.IRLit("b"),
                new IR.IRLit("c"),
                new IR.IRLit("d"),
            ])
        );
    });

    test("should fuse sequences within an alternation", () => {
        /**
         * Tests alternation containing sequences: (ab|cd|ef)
         */
        const compiler = new Compiler();
        const ast = new N.Alt([
            new N.Seq([new N.Lit("a"), new N.Lit("b")]),
            new N.Seq([new N.Lit("c"), new N.Lit("d")]),
            new N.Seq([new N.Lit("e"), new N.Lit("f")]),
        ]);
        const ir = compiler.compile(ast);
        // Each sequence should be fused into a single literal
        expect(ir).toEqual(
            new IR.IRAlt([
                new IR.IRLit("ab"),
                new IR.IRLit("cd"),
                new IR.IRLit("ef"),
            ])
        );
    });

    test("should handle mixed alternation and sequence nesting", () => {
        /**
         * Tests mixed nesting: ((a|b)(c|d))
         * Two alternations in a sequence inside a group.
         */
        const compiler = new Compiler();
        const ast = new N.Group(
            false, // non-capturing
            new N.Seq([
                new N.Alt([new N.Lit("a"), new N.Lit("b")]),
                new N.Alt([new N.Lit("c"), new N.Lit("d")]),
            ])
        );
        const ir = compiler.compile(ast);
        // Should preserve structure: Group with Seq containing two Alts
        expect(ir).toEqual(
            new IR.IRGroup(
                false,
                new IR.IRSeq([
                    new IR.IRAlt([new IR.IRLit("a"), new IR.IRLit("b")]),
                    new IR.IRAlt([new IR.IRLit("c"), new IR.IRLit("d")]),
                ]),
                null,
                null
            )
        );
    });
});

describe("Category F: Complex Sequence Normalization", () => {
    /**
     * Tests for complex sequence normalization scenarios.
     */

    test("should flatten deeply nested sequences", () => {
        /**
         * Tests deeply nested sequences: Seq([Lit("a"), Seq([Lit("b"), Seq([Lit("c")])])])
         * Should normalize to IRLit("abc").
         */
        const compiler = new Compiler();
        const ast = new N.Seq([
            new N.Lit("a"),
            new N.Seq([new N.Lit("b"), new N.Seq([new N.Lit("c")])]),
        ]);
        const ir = compiler.compile(ast);
        // All literals should be fused into one
        expect(ir).toEqual(new IR.IRLit("abc"));
    });

    test("should handle sequence with non-literal in middle", () => {
        /**
         * Tests sequence with non-literal: Seq([Lit("a"), Dot(), Lit("b")])
         * Should normalize to IRSeq([IRLit("a"), IRDot(), IRLit("b")]).
         */
        const compiler = new Compiler();
        const ast = new N.Seq([new N.Lit("a"), new N.Dot(), new N.Lit("b")]);
        const ir = compiler.compile(ast);
        // Should preserve structure with no fusion across Dot
        expect(ir).toEqual(
            new IR.IRSeq([new IR.IRLit("a"), new IR.IRDot(), new IR.IRLit("b")])
        );
    });

    test("should normalize an empty sequence", () => {
        /**
         * Tests normalization of empty sequence: Seq([])
         * Should produce IRSeq([]) or equivalent.
         */
        const compiler = new Compiler();
        const ast = new N.Seq([]);
        const ir = compiler.compile(ast);
        // Empty sequence should remain empty sequence
        expect(ir).toEqual(new IR.IRSeq([]));
    });
});

describe("Category G: Literal Fusion Edge Cases", () => {
    /**
     * Tests for edge cases in literal fusion during normalization.
     */

    test("should fuse literals with escaped chars", () => {
        /**
         * Tests fusion of literals with escape sequences: Lit("a") + Lit("\n") + Lit("b")
         * Should fuse to single IRLit("a\nb").
         */
        const compiler = new Compiler();
        const ast = new N.Seq([
            new N.Lit("a"),
            new N.Lit("\n"),
            new N.Lit("b"),
        ]);
        const ir = compiler.compile(ast);
        // Literals with escape sequences should fuse normally
        expect(ir).toEqual(new IR.IRLit("a\nb"));
    });

    test("should fuse unicode literals", () => {
        /**
         * Tests fusion of Unicode literals: Lit("😀") + Lit("a")
         */
        const compiler = new Compiler();
        const ast = new N.Seq([new N.Lit("😀"), new N.Lit("a")]);
        const ir = compiler.compile(ast);
        // Unicode literals should fuse normally
        expect(ir).toEqual(new IR.IRLit("😀a"));
    });

    test("should not fuse across non-literals", () => {
        /**
         * Tests that literals don't fuse across non-literal nodes:
         * Seq([Lit("a"), Dot(), Lit("b")]) should keep three separate nodes.
         */
        const compiler = new Compiler();
        const ast = new N.Seq([new N.Lit("a"), new N.Dot(), new N.Lit("b")]);
        const ir = compiler.compile(ast);
        // Should NOT fuse across the Dot
        expect(ir).toEqual(
            new IR.IRSeq([new IR.IRLit("a"), new IR.IRDot(), new IR.IRLit("b")])
        );
    });
});

describe("Category H: Quantifier Normalization", () => {
    /**
     * Tests for quantifier normalization scenarios.
     */

    test("should unwrap quantifier of single-item sequence", () => {
        /**
         * Tests quantifier wrapping sequence with single item:
         * Quant(Seq([Lit("a")]), ...)
         * Should potentially unwrap to Quant(Lit("a"), ...).
         */
        const compiler = new Compiler();
        const ast = new N.Quant(
            new N.Seq([new N.Lit("a")]),
            1,
            "Inf",
            "Greedy"
        );
        const ir = compiler.compile(ast);
        // Single-item sequence should be unwrapped
        expect(ir).toEqual(
            new IR.IRQuant(new IR.IRLit("a"), 1, "Inf", "Greedy")
        );
    });

    test("should preserve quantifier of empty sequence", () => {
        /**
         * Tests quantifier of empty sequence: Quant(Seq([]), ...)
         * Edge case behavior.
         */
        const compiler = new Compiler();
        const ast = new N.Quant(new N.Seq([]), 0, "Inf", "Greedy");
        const ir = compiler.compile(ast);
        // Quantifier of empty sequence should preserve structure
        expect(ir).toEqual(
            new IR.IRQuant(new IR.IRSeq([]), 0, "Inf", "Greedy")
        );
    });

    test("should preserve nested quantifiers", () => {
        /**
         * Tests normalization of nested quantifiers: Quant(Quant(Lit("a"), ...), ...)
         */
        const compiler = new Compiler();
        // This is an unusual case - quantifier of a quantifier
        // We'll just test that it doesn't crash and preserves structure
        const ast = new N.Quant(
            new N.Quant(new N.Lit("a"), 1, 3, "Greedy"),
            0,
            1,
            "Greedy"
        );
        const ir = compiler.compile(ast);
        // Should preserve the nested structure (no special normalization for this case)
        expect(ir).toEqual(
            new IR.IRQuant(
                new IR.IRQuant(new IR.IRLit("a"), 1, 3, "Greedy"),
                0,
                1,
                "Greedy"
            )
        );
    });
});

describe("Category I: Feature Detection Comprehensive", () => {
    /**
     * Comprehensive tests for feature detection in metadata.
     */

    test("should detect named groups", () => {
        /**
         * Tests feature detection for named groups.
         */
        const compiler = new Compiler();
        const ast = new N.Group(true, new N.Lit("a"), "mygroup");
        const artifact = compiler.compileWithMetadata(ast);

        expect(artifact.metadata).toBeDefined();
        expect(artifact.metadata.features_used).toContain("named_group");
    });

    test("should detect backreferences", () => {
        /**
         * Tests feature detection for backreferences (if tracked).
         */
        const compiler = new Compiler();
        // Create an AST with a backreference
        const ast = new N.Seq([
            new N.Group(true, new N.Lit("a")),
            new N.Backref({ byIndex: 1 }),
        ]);
        const artifact = compiler.compileWithMetadata(ast);

        expect(artifact.metadata).toBeDefined();
        expect(artifact.metadata.features_used).toContain("backreference");
    });

    test("should detect lookahead", () => {
        /**
         * Tests feature detection for lookahead assertions.
         */
        const compiler = new Compiler();
        const ast = new N.Look("Ahead", false, new N.Lit("a"));
        const artifact = compiler.compileWithMetadata(ast);

        expect(artifact.metadata).toBeDefined();
        expect(artifact.metadata.features_used).toContain("lookahead");
    });

    test("should detect unicode properties", () => {
        /**
         * Tests feature detection for Unicode properties (if tracked).
         */
        const compiler = new Compiler();
        // Create a character class with Unicode property escape
        const ast = new N.CharClass(false, [
            new N.ClassEscape("UnicodeProperty", "Letter"),
        ]);
        const artifact = compiler.compileWithMetadata(ast);

        expect(artifact.metadata).toBeDefined();
        expect(artifact.metadata.features_used).toContain("unicode_property");
    });

    test("should detect multiple features in one pattern", () => {
        /**
         * Tests pattern with multiple special features:
         * atomic group + possessive quantifier + lookbehind.
         */
        const compiler = new Compiler();
        const ast = new N.Seq([
            new N.Group(false, new N.Lit("a"), undefined, true), // atomic
            new N.Quant(new N.Lit("b"), 1, "Inf", "Possessive"),
            new N.Look("Behind", false, new N.Lit("c")),
        ]);
        const artifact = compiler.compileWithMetadata(ast);

        const features = artifact.metadata.features_used;
        expect(features).toContain("atomic_group");
        expect(features).toContain("possessive_quantifier");
        expect(features).toContain("lookbehind");
    });
});

describe("Category J: Alternation Normalization Edge Cases", () => {
    /**
     * Edge cases for alternation normalization.
     */

    test("should unwrap alternation with a single branch", () => {
        /**
         * Tests alternation with only one branch: Alt([Lit("a")])
         * Should potentially unwrap to just Lit("a").
         */
        const compiler = new Compiler();
        const ast = new N.Alt([new N.Lit("a")]);
        const ir = compiler.compile(ast);
        // Single-branch alternation should be unwrapped
        expect(ir).toEqual(new IR.IRLit("a"));
    });

    test("should preserve alternation with empty branches", () => {
        /**
         * Tests alternation with empty alternatives: Alt([Lit("a"), Seq([])])
         */
        const compiler = new Compiler();
        const ast = new N.Alt([new N.Lit("a"), new N.Seq([])]);
        const ir = compiler.compile(ast);
        // Should preserve both branches, with empty sequence normalized
        expect(ir).toEqual(new IR.IRAlt([new IR.IRLit("a"), new IR.IRSeq([])]));
    });

    test("should flatten alternations nested at different depths", () => {
        /**
         * Tests alternations nested at different depths in different branches.
         */
        const compiler = new Compiler();
        // Alt([Lit("a"), Alt([Lit("b"), Lit("c")]), Lit("d")])
        const ast = new N.Alt([
            new N.Lit("a"),
            new N.Alt([new N.Lit("b"), new N.Lit("c")]),
            new N.Lit("d"),
        ]);
        const ir = compiler.compile(ast);
        // Nested alternation should be flattened
        expect(ir).toEqual(
            new IR.IRAlt([
                new IR.IRLit("a"),
                new IR.IRLit("b"),
                new IR.IRLit("c"),
                new IR.IRLit("d"),
            ])
        );
    });
});
