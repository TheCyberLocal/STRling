import fs from "fs";
import path from "path";
import { parse, ParseError } from "../../src/STRling/core/parser";
import { Compiler } from "../../src/STRling/core/compiler";
import { emit } from "../../src/STRling/emitters/pcre2";

const FIXTURES_DIR = path.resolve(__dirname, "../../../../tests/spec");

function getFixtures() {
    if (!fs.existsSync(FIXTURES_DIR)) return [];
    return fs
        .readdirSync(FIXTURES_DIR)
        .filter((f) => f.endsWith(".json"))
        .map((f) => path.join(FIXTURES_DIR, f));
}

// Helper to convert JS AST Nodes to JSON-compatible object matching the schema
// Copied from tooling/js_to_json_ast/generate_json_ast.js
function mapAnchor(a: string): string {
    if (!a) return a;
    switch (a) {
        case "NotWordBoundary":
            return "NonWordBoundary";
        default:
            return a;
    }
}

function convertNode(node: any): any {
    if (!node) return null;
    if (typeof node.toDict === "function") {
        node = node.toDict();
    }
    const k = node.kind || node.type || null;
    if (!k) return null;
    switch (k) {
        case "Lit":
        case "Literal":
            return { type: "Literal", value: node.value };
        case "Seq":
        case "Sequence":
            return {
                type: "Sequence",
                parts: (node.parts || node.children || []).map(convertNode),
            };
        case "Dot":
            return { type: "Dot" };
        case "Alt":
        case "Alternation":
            return {
                type: "Alternation",
                alternatives: (node.branches || node.alternatives || []).map(
                    convertNode
                ),
            };
        case "Anchor":
            return { type: "Anchor", at: mapAnchor(node.at) };
        case "CharClass":
        case "Class":
            return {
                type: "CharacterClass",
                negated: !!node.negated,
                members: (node.items || node.members || []).map(convertNode),
            };
        case "ClassLiteral":
        case "Char":
            return { type: "Literal", value: node.char || node.ch };
        case "ClassRange":
        case "Range":
            return {
                type: "Range",
                from: node.from || node.fromCh,
                to: node.to || node.toCh,
            };
        case "ClassEscape":
        case "Esc":
            const escKind =
                node.type ||
                node.kind ||
                node.escape ||
                node.kindName ||
                node.name;
            if (!escKind) return { type: "Escape", kind: null };
            if (
                escKind === "p" ||
                escKind === "P" ||
                escKind === "UnicodeProperty"
            ) {
                return {
                    type: "UnicodeProperty",
                    name: node.name || null,
                    value: node.property || node.value || null,
                    negated: escKind === "P" || !!node.negated,
                };
            }
            const shorthandMap: Record<string, string> = {
                d: "digit",
                D: "not-digit",
                w: "word",
                W: "not-word",
                s: "space",
                S: "not-space",
                b: "wordBoundary",
                B: "wordBoundary",
            };
            const mappedKind = shorthandMap[escKind] || escKind;
            return { type: "Escape", kind: mappedKind };
        case "Quant":
        case "Quantifier":
            const greedy = node.mode !== "Lazy" && node.lazy !== true;
            return {
                type: "Quantifier",
                target: convertNode(node.child || node.target),
                min: node.min,
                max: node.max === "Inf" ? null : node.max,
                greedy: !!greedy,
                lazy: !greedy,
                possessive: node.mode === "Possessive" || !!node.possessive,
            };
        case "Group":
            const bodyNode = convertNode(
                node.body || (node.parts && { kind: "Seq", parts: node.parts })
            );
            return {
                type: "Group",
                capturing: !!node.capturing,
                body: bodyNode,
                expression: bodyNode,
                name: node.name || null,
                atomic: !!node.atomic,
            };
        case "Backref":
            return {
                type: "Backreference",
                index: node.byIndex || node.by_index || node.index || null,
                name: node.byName || node.by_name || node.name || null,
            };
        case "Look":
            const dir = node.dir || node.direction || null;
            const isNeg = !!node.neg;
            if (dir === "Ahead") {
                return {
                    type: isNeg ? "NegativeLookahead" : "Lookahead",
                    body: convertNode(node.body),
                };
            } else if (dir === "Behind") {
                return {
                    type: isNeg ? "NegativeLookbehind" : "Lookbehind",
                    body: convertNode(node.body),
                };
            }
            return { type: "Lookahead", body: convertNode(node.body) };
        default:
            return node;
    }
}

describe("Shared JSON Conformance Suite", () => {
    const fixtures = getFixtures();

    fixtures.forEach((fixturePath) => {
        const fileName = path.basename(fixturePath);
        let testName = `should pass conformance test ${fileName}`;

        if (fileName === "semantic_duplicates.json") {
            testName = "test_semantic_duplicate_capture_group";
        } else if (fileName === "semantic_ranges.json") {
            testName = "test_semantic_ranges";
        }

        test(testName, () => {
            const content = fs.readFileSync(fixturePath, "utf8");
            const data = JSON.parse(content);
            const dsl = data.input_dsl;

            if (data.expected_error) {
                if (!dsl) {
                    throw new Error("Error test case missing 'input_dsl'");
                }
                expect(() => parse(dsl)).toThrow(ParseError);
                try {
                    parse(dsl);
                } catch (e: any) {
                    expect(e.message).toContain(data.expected_error);
                }
                return;
            }

            if (!dsl) {
                // Skip if no DSL (should not happen with updated generator)
                return;
            }

            // 1. Verify Parser
            const [flags, ast] = parse(dsl);
            const jsonAst = convertNode(ast);
            expect(jsonAst).toEqual(data.input_ast);

            // 2. Verify Compiler & Emitter (if expected_codegen present)
            if (data.expected_codegen && data.expected_codegen.pcre) {
                const compiler = new Compiler();
                const ir = compiler.compile(ast);
                const pcre = emit(ir, flags);
                expect(pcre).toEqual(data.expected_codegen.pcre);
            }
        });
    });
});
