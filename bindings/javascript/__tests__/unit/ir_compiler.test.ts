/**
 * @file Test Design — ir_compiler.test.ts
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

    test.each<[N.Node, IR.IROp, string]>([
        [new N.Lit("a"), new IR.IRLit("a"), "Lit"],
        [new N.Dot(), new IR.IRDot(), "Dot"],
        [new N.Anchor("Start"), new IR.IRAnchor("Start"), "Anchor"],
        [
            new N.CharClass(false, [new N.ClassRange("a", "z")]),
            new IR.IRCharClass(false, [new IR.IRClassRange("a", "z")]),
            "CharClass",
        ],
        [
            new N.Seq([new N.Lit("a"), new N.Dot()]),
            new IR.IRSeq([new IR.IRLit("a"), new IR.IRDot()]),
            "Seq",
        ],
        [
            new N.Alt([new N.Lit("a"), new N.Lit("b")]),
            new IR.IRAlt([new IR.IRLit("a"), new IR.IRLit("b")]),
            "Alt",
        ],
        [
            new N.Quant(new N.Lit("a"), 1, "Inf", "Greedy"),
            new IR.IRQuant(new IR.IRLit("a"), 1, "Inf", "Greedy"),
            "Quant",
        ],
        [
            new N.Group(true, new N.Dot(), "x"),
            new IR.IRGroup(true, new IR.IRDot(), "x"),
            "Group",
        ],
        [
            new N.Backref({ byIndex: 1 }),
            new IR.IRBackref({ byIndex: 1 }),
            "Backref",
        ],
        [
            new N.Look("Ahead", false, new N.Lit("a")),
            new IR.IRLook("Ahead", false, new IR.IRLit("a")),
            "Look",
        ],
    ])("should lower AST node for %s correctly", (astNode, expectedIrNode) => {
        /**
         * Tests that each AST node type is correctly lowered to its corresponding IR node type.
         *
         */
        const compiler = new Compiler();
        // Accessing private method for isolated unit testing
        expect(compiler["_lower"](astNode)).toEqual(expectedIrNode);
    });
});

describe("Category B: IR Normalization", () => {
    /**
     * Verifies the specific transformation rules of the IR normalization pass.
     * These tests use bracket notation to access the private `_normalize` method.
     *
     */
    const compiler = new Compiler();

    test("should fuse adjacent literals", () => {
        /**
         * An IRSeq with adjacent IRLit nodes must be fused into a single IRLit.
         *
         */
        const unNormalized = new IR.IRSeq([
            new IR.IRLit("a"),
            new IR.IRLit("b"),
            new IR.IRDot(),
            new IR.IRLit("c"),
        ]);
        const normalized = compiler["_normalize"](unNormalized);
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
        const normalized = compiler["_normalize"](unNormalized);
        expect(normalized).toEqual(new IR.IRLit("abc"));
    });

    test("should flatten nested alternations", () => {
        /** A nested IRAlt must be flattened into a single IRAlt. */
        const unNormalized = new IR.IRAlt([
            new IR.IRLit("a"),
            new IR.IRAlt([new IR.IRLit("b"), new IR.IRLit("c")]),
        ]);
        const normalized = compiler["_normalize"](unNormalized);
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
        const result = compiler["_normalize"](normalizedIr);
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
         *
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
         *
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
     *
     */

    test.each<[N.Node, string, string]>([
        [
            new N.Group(false, new N.Lit("a"), undefined, true),
            "atomic_group",
            "atomic_group",
        ],
        [
            new N.Quant(new N.Lit("a"), 1, "Inf", "Possessive"),
            "possessive_quantifier",
            "possessive_quantifier",
        ],
        [
            new N.Look("Behind", false, new N.Lit("a")),
            "lookbehind",
            "lookbehind",
        ],
    ])("should detect feature for %s (ID: %s)", (astNode, expectedFeature) => {
        /**
         * Tests that ASTs with special features produce an artifact with the
         * correct metadata.
         */
        const compiler = new Compiler();
        const artifact = compiler.compileWithMetadata(astNode);
        expect(artifact.metadata.features_used).toContain(expectedFeature);
    });

    test("should produce empty metadata for a pattern with no special features", () => {
        /**
         * Tests that a simple AST with no special features produces an empty
         * features_used list.
         */
        const compiler = new Compiler();
        const ast = new N.Seq([new N.Lit("a"), new N.Dot()]);
        const artifact = compiler.compileWithMetadata(ast);
        expect(artifact.metadata.features_used).toEqual([]);
    });
});
