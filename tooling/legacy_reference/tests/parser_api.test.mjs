import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { createImplementationIdentity } from "../identity.mjs";
import { createLegacyInvoker, expectedSurface } from "../legacy_runtime.mjs";
import { observeRequest, serializeObservation } from "../protocol.mjs";
import { PROTOCOL_VERSION, REQUEST_KIND } from "../constants.mjs";

const REPOSITORY_ROOT = fileURLToPath(new URL("../../../", import.meta.url));
const SOURCE_ROOT =
    process.env.STRLING_LEGACY_REFERENCE_SOURCE_ROOT ?? REPOSITORY_ROOT;
const DIST = process.env.STRLING_LEGACY_REFERENCE_DIST;
assert.ok(DIST, "controlled legacy build path is required");
const invoke = await createLegacyInvoker(DIST);
const implementation = await createImplementationIdentity(SOURCE_ROOT);

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

function literalRequest(operation, literal, options = {}) {
    return {
        expected_legacy_surface: expectedSurface(operation),
        input: { literal },
        kind: REQUEST_KIND,
        operation,
        options,
        protocol_version: PROTOCOL_VERSION,
    };
}

test("legacy parser returns its existing tuple projection", async () => {
    const observation = await observeRequest(
        sourceRequest("parser.parse", "a"),
        implementation,
        invoke,
    );
    assert.equal(observation.outcome.status, "success");
    assert.deepEqual(observation.outcome.evidence, {
        flags: {
            dotAll: false,
            extended: false,
            ignoreCase: false,
            multiline: false,
            unicode: false,
        },
        return_shape: "tuple",
        root: { kind: "Lit", value: "a" },
    });
});

test("parser projection retains flags, captures, classes, repetition, alternation, and lookaround", async () => {
    const source = String.raw`%flags im
(?<word>[a-z]+)(?=\\d)|x{2,3}`;
    const observation = await observeRequest(
        sourceRequest("parser.parse_to_artifact", source),
        implementation,
        invoke,
    );
    assert.equal(observation.outcome.status, "success");
    assert.equal(observation.outcome.evidence.artifact.flags.ignoreCase, true);
    assert.equal(observation.outcome.evidence.artifact.flags.multiline, true);
    assert.equal(observation.outcome.evidence.artifact.root.kind, "Alt");
});

test("escapes and extended-mode preprocessing remain visible", async () => {
    const source = String.raw`%flags x
a \\n # ignored
[\\d_]`;
    const observation = await observeRequest(
        sourceRequest("parser.parse", source),
        implementation,
        invoke,
    );
    assert.equal(observation.outcome.status, "success");
    assert.equal(observation.outcome.evidence.flags.extended, true);
    assert.equal(observation.outcome.evidence.root.kind, "Seq");
});

test("parser failure is contained with legacy diagnostic evidence", async () => {
    const observation = await observeRequest(
        sourceRequest("parser.parse", "(abc"),
        implementation,
        invoke,
    );
    assert.equal(observation.outcome.status, "legacy_failure");
    assert.equal(observation.outcome.failure.category, "parse_error");
    assert.equal(observation.outcome.failure.message, "Unterminated group");
    assert.equal(observation.outcome.failure.position, 4);
    assert.equal(observation.outcome.failure.source_text, "(abc");
    assert.equal(Object.hasOwn(observation.outcome.failure, "stack"), false);
});

test("package-root parser is invoked independently", async () => {
    const observation = await observeRequest(
        sourceRequest("api.root.parse", String.raw`(?<n>\\d+)`),
        implementation,
        invoke,
    );
    assert.equal(observation.surface, "typescript.package-root.parse");
    assert.equal(observation.outcome.status, "success");
    assert.equal(observation.outcome.evidence.root.kind, "Group");
});

test("package-root parseToArtifact preserves its legacy return shape", async () => {
    const observation = await observeRequest(
        sourceRequest("api.root.parse_to_artifact", "a|b"),
        implementation,
        invoke,
    );
    assert.equal(observation.outcome.status, "success");
    assert.equal(observation.outcome.evidence.return_shape, "object");
    assert.deepEqual(observation.outcome.evidence.artifact.warnings, []);
    assert.deepEqual(observation.outcome.evidence.artifact.errors, []);
});

test("Simply literal Pattern.toString observes exact legacy escaping", async () => {
    const observation = await observeRequest(
        literalRequest("api.simply.literal_to_string", "a.b"),
        implementation,
        invoke,
    );
    assert.equal(observation.outcome.status, "success");
    assert.equal(observation.outcome.evidence.emitted_pattern, "a\\.b");
    assert.deepEqual(observation.outcome.evidence.node, {
        kind: "Lit",
        value: "a.b",
    });
});

test("Simply compileNode preserves target failure as API evidence", async () => {
    const observation = await observeRequest(
        literalRequest("api.simply.compile_node", "a", {
            target: "javascript",
        }),
        implementation,
        invoke,
    );
    assert.equal(observation.outcome.status, "legacy_failure");
    assert.equal(observation.outcome.failure.stage, "public_api");
    assert.equal(
        observation.outcome.failure.message,
        "Target 'javascript' not supported in TypeScript binding.",
    );
});

test("Simply toRegExp success exposes RegExp source and flags", async () => {
    const observation = await observeRequest(
        literalRequest("api.simply.to_regexp", "a.b"),
        implementation,
        invoke,
    );
    assert.equal(observation.outcome.status, "success");
    assert.deepEqual(observation.outcome.evidence, {
        flags: "",
        return_shape: "RegExp",
        source: "a\\.b",
        string: "/a\\.b/",
    });
});

test("source request and source string remain unchanged", async () => {
    const request = sourceRequest("parser.parse", "[a-z]+");
    const before = JSON.stringify(request);
    await observeRequest(request, implementation, invoke);
    assert.equal(JSON.stringify(request), before);
});

test("repeat parser observation is byte-identical", async () => {
    const request = sourceRequest("parser.parse", String.raw`(?:a|b)+`);
    const first = await observeRequest(request, implementation, invoke);
    const second = await observeRequest(request, implementation, invoke);
    assert.equal(serializeObservation(first), serializeObservation(second));
});

test("CLI returns zero for a captured legacy failure", () => {
    const request = sourceRequest("parser.parse", "(");
    const completed = spawnSync(
        process.execPath,
        ["tooling/legacy_reference/cli.mjs"],
        {
            cwd: REPOSITORY_ROOT,
            encoding: "utf8",
            env: process.env,
            input: JSON.stringify(request),
        },
    );
    assert.equal(completed.status, 0, completed.stderr);
    assert.equal(JSON.parse(completed.stdout).outcome.status, "legacy_failure");
});

test("CLI returns nonzero structured evidence for malformed JSON", () => {
    const completed = spawnSync(
        process.execPath,
        ["tooling/legacy_reference/cli.mjs"],
        {
            cwd: REPOSITORY_ROOT,
            encoding: "utf8",
            env: process.env,
            input: "{",
        },
    );
    assert.equal(completed.status, 2);
    assert.equal(completed.stdout, "");
    const failure = JSON.parse(completed.stderr);
    assert.equal(failure.error.code, "MALFORMED_JSON");
    assert.equal(failure.error.category, "protocol");
});
