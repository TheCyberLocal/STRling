#!/usr/bin/env node
/*
 * Convert JS generated JSON ASTs into a single C test file skeleton that uses
 * `test_helpers.h` helper functions.
 *
 * This is a starter implementation: it generates simple cmocka tests that
 * assert compilation success for each fixture in `tooling/js_to_json_ast/out`.
 */
const fs = require("fs");
const path = require("path");

const fixturesOut = path.join(__dirname, "out");
const destPath = path.join(
    __dirname,
    "../../bindings/c/tests/unit/converted_from_js_test.c"
);
const fixturesRel = "../../tooling/js_to_json_ast/out/";

if (!fs.existsSync(fixturesOut)) {
    console.error(
        "Fixtures out directory does not exist. Run generate_json_ast.js first."
    );
    process.exit(1);
}

const fixtures = fs.readdirSync(fixturesOut).filter((f) => f.endsWith(".json"));
const lines = [];
lines.push(
    "/* Auto-generated C test file from JS fixtures — simple compile assertions */"
);
lines.push("#include <stdarg.h>");
lines.push("#include <cmocka.h>");
lines.push('#include "../test_helpers.h"');
lines.push("");

fixtures.forEach((f, idx) => {
    const fn = `test_js_fixture_${idx + 1}`;
    const fixturePath = path.join(fixturesRel, f);
    lines.push(`static void ${fn}(void **state) {`);
    lines.push("    (void)state;");
    // Read fixture and decide expected assertion
    const content = JSON.parse(
        fs.readFileSync(path.join(fixturesOut, f), "utf8")
    );
    // Delegate to helper that inspects the fixture's `expected` field
    lines.push(`    assert_compile_matches_expected("${fixturePath}");`);
    lines.push("}");
    lines.push("");
});

lines.push("int main(void) {");
lines.push("    const struct CMUnitTest tests[] = {");
fixtures.forEach((f, idx) => {
    const fn = `test_js_fixture_${idx + 1}`;
    lines.push(`        cmocka_unit_test(${fn}),`);
});
lines.push("    };");
lines.push("    return cmocka_run_group_tests(tests, NULL, NULL);");
lines.push("}");

fs.writeFileSync(destPath, lines.join("\n") + "\n", "utf8");
console.log(`Wrote ${destPath} with ${fixtures.length} tests`);
