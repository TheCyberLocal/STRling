import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { PROTOCOL_VERSION, REQUEST_KIND } from "../constants.mjs";
import { createImplementationIdentity } from "../identity.mjs";
import { createLegacyInvoker, expectedSurface } from "../legacy_runtime.mjs";
import { observeRequest } from "../protocol.mjs";

const ROOT = fileURLToPath(new URL("../../../", import.meta.url));
const DIST = process.env.STRLING_LEGACY_REFERENCE_DIST;
assert.ok(DIST, "controlled legacy build path is required");
const invoke = await createLegacyInvoker(DIST);
const implementation = await createImplementationIdentity(ROOT);

function sourceRequest(operation, source, options = {}) {
    return {
        expected_legacy_surface: expectedSurface(operation),
        input: { source },
        kind: REQUEST_KIND,
        operation,
        options,
        protocol_version: PROTOCOL_VERSION,
    };
}

test("compiler.compile observes the normalized legacy IR and input flags", async () => {
    const observation = await observeRequest(
        sourceRequest("compiler.compile", "%flags i\nabc"),
        implementation,
        invoke,
    );
    assert.equal(observation.outcome.status, "success");
    assert.deepEqual(observation.outcome.evidence.ir, {
        ir: "Lit",
        value: "abc",
    });
    assert.equal(observation.outcome.evidence.input_flags.ignoreCase, true);
    assert.equal(observation.outcome.evidence.return_shape, "IROp");
});

test("compiler metadata retains the legacy sorted feature inventory", async () => {
    const source = "(?<tag>\\p{L}++)(?<=x)\\k<tag>(?>a)";
    const observation = await observeRequest(
        sourceRequest("compiler.compile_with_metadata", source),
        implementation,
        invoke,
    );
    assert.equal(observation.outcome.status, "success");
    assert.deepEqual(observation.outcome.evidence.metadata.features_used, [
        "atomic_group",
        "backreference",
        "lookbehind",
        "named_group",
        "possessive_quantifier",
    ]);
    assert.equal(observation.outcome.evidence.return_shape, "object");
});

test("compiler pipeline contains parser failures at the parser stage", async () => {
    const observation = await observeRequest(
        sourceRequest("compiler.compile", "(abc"),
        implementation,
        invoke,
    );
    assert.equal(observation.outcome.status, "legacy_failure");
    assert.equal(observation.outcome.failure.category, "parse_error");
    assert.equal(observation.outcome.failure.stage, "parser");
});

test("emitter preserves exact legacy pattern text and flag ordering", async () => {
    const observation = await observeRequest(
        sourceRequest("emitter.pcre2.emit", "%flags imsux\na"),
        implementation,
        invoke,
    );
    assert.equal(observation.outcome.status, "success");
    assert.equal(observation.outcome.evidence.emitted_pattern, "(?imsux)a");
    assert.equal(observation.outcome.evidence.return_shape, "string");
    assert.equal(observation.outcome.evidence.target, "pcre2");
});

test("emitter preserves an existing exact-output golden case", async () => {
    const source = "<(?<tag>\\w+)>.*?</\\k<tag>>";
    const observation = await observeRequest(
        sourceRequest("emitter.pcre2.emit", source),
        implementation,
        invoke,
    );
    assert.equal(observation.outcome.status, "success");
    assert.equal(observation.outcome.evidence.emitted_pattern, source);
});

test("diagnostic emitter captures warning evidence with successful output", async () => {
    const observation = await observeRequest(
        sourceRequest("emitter.pcre2.emit_with_diagnostics", "(a+)+"),
        implementation,
        invoke,
    );
    assert.equal(observation.outcome.status, "success");
    assert.equal(observation.outcome.evidence.emitted_pattern, "(a+)+");
    assert.equal(observation.outcome.evidence.warnings.length, 1);
    assert.equal(observation.outcome.evidence.warnings[0].code, "REDOS_RISK");
});

test("variable-length lookbehind is a structured emitter failure", async () => {
    const observation = await observeRequest(
        sourceRequest("emitter.pcre2.emit", "(?<=a+)b"),
        implementation,
        invoke,
    );
    assert.equal(observation.outcome.status, "legacy_failure");
    assert.equal(observation.outcome.failure.category, "compilation_error");
    assert.equal(observation.outcome.failure.code, "VLB_NOT_SUPPORTED");
    assert.equal(observation.outcome.failure.engine, "pcre2");
    assert.equal(observation.outcome.failure.stage, "emitter");
});

test("max_depth is routed unchanged to the legacy emitter", async () => {
    const observation = await observeRequest(
        sourceRequest("emitter.pcre2.emit", "((a))", { max_depth: 2 }),
        implementation,
        invoke,
    );
    assert.equal(observation.outcome.status, "legacy_failure");
    assert.equal(observation.outcome.failure.code, "MAX_DEPTH");
    assert.equal(observation.outcome.failure.stage, "emitter");
});

test("compiler and emitter operations retain distinct surfaces", () => {
    assert.equal(
        expectedSurface("compiler.compile"),
        "typescript.core.Compiler.compile",
    );
    assert.equal(
        expectedSurface("emitter.pcre2.emit"),
        "typescript.emitters.pcre2.emit",
    );
});

test("CLI captures an emitter legacy failure with a zero exit", () => {
    const request = sourceRequest("emitter.pcre2.emit", "(?<=a+)b");
    const completed = spawnSync(
        process.execPath,
        ["tooling/legacy_reference/cli.mjs"],
        {
            cwd: ROOT,
            encoding: "utf8",
            env: process.env,
            input: JSON.stringify(request),
        },
    );
    assert.equal(completed.status, 0, completed.stderr);
    const observation = JSON.parse(completed.stdout);
    assert.equal(observation.outcome.status, "legacy_failure");
    assert.equal(observation.outcome.failure.stage, "emitter");
});
