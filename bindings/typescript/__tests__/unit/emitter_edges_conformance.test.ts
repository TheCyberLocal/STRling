/**
 * Emitter Edges Conformance Bridge
 *
 * Drives the global pathological-AST fixture
 * (`tests/conformance/inputs/emitter_edges/pathological.json`) through the
 * TypeScript reference Pcre2Emitter and asserts each safety guard fires.
 *
 * This bridges the orphaned fixture into a runnable conformance check so the
 * "Red Matrix" produces actionable signal for the TS reference. The
 * 16 sister bindings have no equivalent runner; replicating this file
 * (adapter + driver) is the per-binding work tracked in the binding rollout.
 *
 * Schema of each test entry (per the user's pathological.json):
 *   {
 *     "name": "...",
 *     "ast": <PathologicalAst>,
 *     "depth_override_for_test": <int>?,    // optional; routed to maxDepth
 *     "expected_error":    "STRlingCompilationError: <substring>"  |
 *     "expected_warning":  "STRlingWarning [REDOS_RISK]: <substring>"
 *   }
 *
 * The fixture's `ast` shape is the user-facing AST sketch (e.g.
 * `{type: "Lookbehind", content: ...}`), NOT the post-lowering IR. The
 * adapter `astToIR` below builds the equivalent IR directly so the test
 * targets the emitter without coupling to the parser/compiler stages.
 */

import fs from "fs";
import path from "path";
import * as IR from "../../src/STRling/core/ir";
import { emit, emitWithDiagnostics } from "../../src/STRling/emitters/pcre2";
import { STRlingCompilationError } from "../../src/STRling/core/errors";

const FIXTURE_PATH = path.resolve(
    __dirname,
    "../../../../tests/conformance/inputs/emitter_edges/pathological.json",
);

interface PathologicalAst {
    type: string;
    content?: PathologicalAst;
    value?: string;
    min?: number;
    max?: number | null | string;
    mode?: string;
}

interface PathologicalCase {
    name: string;
    ast: PathologicalAst;
    depth_override_for_test?: number;
    expected_error?: string;
    expected_warning?: string;
}

interface PathologicalFixture {
    description: string;
    tests: PathologicalCase[];
}

/**
 * Convert the user-facing AST sketch into IR. Only the node types appearing
 * in pathological.json are supported — this is intentionally minimal so the
 * adapter cannot mask emitter bugs by silently dropping nodes.
 */
function astToIR(node: PathologicalAst): IR.IROp {
    switch (node.type) {
        case "Literal":
            return new IR.IRLit(node.value ?? "");

        case "Group":
            // Pathological fixtures use non-capturing groups for nesting.
            if (!node.content) {
                throw new Error("Group node missing content");
            }
            return new IR.IRGroup(false, astToIR(node.content));

        case "Quantifier": {
            if (!node.content) {
                throw new Error("Quantifier node missing content");
            }
            const child = astToIR(node.content);
            const min = node.min ?? 0;
            // null in the user-facing AST means "unbounded" → IR sentinel "Inf".
            const max =
                node.max === null || node.max === undefined ? "Inf" : node.max;
            const mode = node.mode ?? "Greedy";
            return new IR.IRQuant(child, min, max, mode);
        }

        case "Lookbehind":
            if (!node.content) {
                throw new Error("Lookbehind node missing content");
            }
            return new IR.IRLook("Behind", false, astToIR(node.content));

        case "NegativeLookbehind":
            if (!node.content) {
                throw new Error("NegativeLookbehind node missing content");
            }
            return new IR.IRLook("Behind", true, astToIR(node.content));

        case "Lookahead":
            if (!node.content) {
                throw new Error("Lookahead node missing content");
            }
            return new IR.IRLook("Ahead", false, astToIR(node.content));

        case "NegativeLookahead":
            if (!node.content) {
                throw new Error("NegativeLookahead node missing content");
            }
            return new IR.IRLook("Ahead", true, astToIR(node.content));

        default:
            throw new Error(
                `astToIR: unsupported pathological AST node type "${node.type}". ` +
                    "Extend the adapter when new pathological vectors are added.",
            );
    }
}

/**
 * Strip the "STRlingCompilationError: " or "STRlingWarning [CODE]: " prefix
 * from the fixture's expected string so we can substring-match against the
 * actual error message / warning message.
 */
function expectedSubstring(prefix: string): string {
    // Match "STRlingCompilationError: " or "STRlingWarning [REDOS_RISK]: "
    const errMatch = prefix.match(/^STRlingCompilationError:\s*(.*)$/);
    if (errMatch) return errMatch[1];
    const warnMatch = prefix.match(/^STRlingWarning\s*\[[^\]]+\]:\s*(.*)$/);
    if (warnMatch) return warnMatch[1];
    return prefix;
}

describe("Emitter Edges Conformance — pathological.json", () => {
    const fixture: PathologicalFixture = JSON.parse(
        fs.readFileSync(FIXTURE_PATH, "utf-8"),
    );

    it("fixture file is present and well-formed", () => {
        expect(fixture.tests).toBeInstanceOf(Array);
        expect(fixture.tests.length).toBeGreaterThan(0);
    });

    fixture.tests.forEach((tc) => {
        it(tc.name, () => {
            const ir = astToIR(tc.ast);
            const options = tc.depth_override_for_test
                ? { maxDepth: tc.depth_override_for_test }
                : undefined;

            if (tc.expected_error) {
                const needle = expectedSubstring(tc.expected_error);
                expect(() => emit(ir, null, options)).toThrow(
                    STRlingCompilationError,
                );
                try {
                    emit(ir, null, options);
                } catch (e) {
                    expect((e as Error).message).toContain(needle);
                }
            } else if (tc.expected_warning) {
                const needle = expectedSubstring(tc.expected_warning);
                const result = emitWithDiagnostics(ir, null, options);
                expect(result.warnings.length).toBeGreaterThan(0);
                expect(
                    result.warnings.some((w) => w.message.includes(needle)),
                ).toBe(true);
                // Pattern must still be produced — warnings do not abort.
                expect(typeof result.pattern).toBe("string");
                expect(result.pattern.length).toBeGreaterThan(0);
            } else {
                throw new Error(
                    `Test case "${tc.name}" declares neither expected_error nor expected_warning.`,
                );
            }
        });
    });
});
