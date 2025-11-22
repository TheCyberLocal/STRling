import fs from "fs";
import path from "path";
import { Compiler } from "../../src/STRling/core/compiler";
import { Node } from "../../src/STRling/core/nodes";

const fixturesDir = path.resolve(
    __dirname,
    "../../../../tooling/js_to_json_ast/out"
);

// Filter for .json files
const fixtures = fs
    .readdirSync(fixturesDir)
    .filter((f) => f.endsWith(".json"))
    .map((f) => {
        const content = fs.readFileSync(path.join(fixturesDir, f), "utf-8");
        return JSON.parse(content);
    })
    // Filter out fixtures that failed to compile (no expected_ir)
    .filter((f) => f.expected_ir);

describe("Shared JSON AST Conformance", () => {
    test.each(fixtures)("$id: $description", (fixture) => {
        const ast = Node.fromJSON(fixture.input_ast);
        const compiler = new Compiler();
        const result = compiler.compile(ast);
        expect(result.toDict()).toEqual(fixture.expected_ir);
    });
});
