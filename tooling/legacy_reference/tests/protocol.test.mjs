import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { canonicalJson } from "../canonical.mjs";
import {
    OPERATION_SPECS,
    PROTOCOL_VERSION,
    REQUEST_KIND,
    TYPESCRIPT_RUNNER,
} from "../constants.mjs";
import {
    createImplementationIdentity,
    fingerprintImplementationManifest,
} from "../identity.mjs";
import {
    observeRequest,
    ProtocolError,
    serializeObservation,
    unsupportedOperation,
    validateRunnerIdentity,
    validateRequest,
} from "../protocol.mjs";

const REPOSITORY_ROOT = fileURLToPath(new URL("../../../", import.meta.url));
const SOURCE_ROOT =
    process.env.STRLING_LEGACY_REFERENCE_SOURCE_ROOT ?? REPOSITORY_ROOT;

const PYTHON_RUNNER = Object.freeze({
    id: "python",
    kind: TYPESCRIPT_RUNNER.kind,
    language: "python",
    version: "1.0.0",
});
const PYTHON_OPERATION_SPECS = Object.freeze({
    "parser.parse": Object.freeze({
        input: "source",
        options: Object.freeze([]),
        stage: "parser",
        surface: "python.core.parser.parse",
    }),
});
function request(overrides = {}) {
    return {
        expected_legacy_surface: OPERATION_SPECS["parser.parse"].surface,
        input: { source: "a" },
        kind: REQUEST_KIND,
        operation: "parser.parse",
        options: {},
        protocol_version: PROTOCOL_VERSION,
        ...overrides,
    };
}

test("valid request is copied into the stable contract", () => {
    const raw = request();
    const validated = validateRequest(raw);
    assert.deepEqual(validated, raw);
    assert.notEqual(validated, raw);
});

test("malformed request rejects missing and additional fields", () => {
    const missing = request();
    delete missing.options;
    assert.throws(
        () => validateRequest(missing),
        (error) =>
            error instanceof ProtocolError && error.code === "INVALID_SHAPE",
    );

    assert.throws(
        () => validateRequest({ ...request(), timestamp: "never" }),
        (error) =>
            error instanceof ProtocolError && error.code === "INVALID_SHAPE",
    );
});

test("unknown operation is a protocol failure", () => {
    assert.throws(
        () =>
            validateRequest(
                request({
                    expected_legacy_surface: "typescript.unknown",
                    operation: "unknown.operation",
                }),
            ),
        (error) =>
            error instanceof ProtocolError &&
            error.code === "UNKNOWN_OPERATION",
    );
});

test("expected legacy surface cannot silently drift", () => {
    assert.throws(
        () =>
            validateRequest(
                request({ expected_legacy_surface: "typescript.other.parse" }),
            ),
        (error) =>
            error instanceof ProtocolError && error.code === "SURFACE_MISMATCH",
    );
});

test("canonical JSON recursively sorts keys and preserves arrays", () => {
    assert.equal(
        canonicalJson({ z: 1, a: { y: 2, x: [3, { b: 4, a: 5 }] } }),
        '{"a":{"x":[3,{"a":5,"b":4}],"y":2},"z":1}',
    );
});

test("implementation identity is stable for the governed inputs", async () => {
    const first = await createImplementationIdentity(SOURCE_ROOT, "22.0.0");
    const second = await createImplementationIdentity(SOURCE_ROOT, "22.0.0");
    assert.deepEqual(second, first);
    assert.match(first.fingerprint, /^sha256:[0-9a-f]{64}$/);
    assert.ok(
        first.inputs.some(
            (entry) =>
                entry.path === "bindings/typescript/src/STRling/core/parser.ts",
        ),
    );
    assert.ok(
        first.inputs.some(
            (entry) => entry.path === "bindings/typescript/package-lock.json",
        ),
    );
    assert.equal(
        first.inputs.some((entry) => entry.path.startsWith("/")),
        false,
    );
});

test("governed implementation mutation changes the fingerprint", () => {
    const original = [
        { bytes: 1, path: "bindings/typescript/src/index.ts", sha256: "a" },
    ];
    const changed = [
        { bytes: 1, path: "bindings/typescript/src/index.ts", sha256: "b" },
    ];
    assert.notEqual(
        fingerprintImplementationManifest(original, "22.0.0"),
        fingerprintImplementationManifest(changed, "22.0.0"),
    );
});

test("repeat observation invocation is byte-identical", async () => {
    const implementation = {
        algorithm: "sha256",
        fingerprint: "sha256:" + "0".repeat(64),
        inputs: [],
        kind: "strling.legacy-typescript-implementation",
        manifest_encoding: "canonical-json-v1",
        runtime: { name: "node", version: "22.0.0" },
    };
    const invoke = () => ({
        ast: { kind: "Lit", value: "a" },
        flags: { extended: false },
    });
    const first = await observeRequest(request(), implementation, invoke);
    const second = await observeRequest(request(), implementation, invoke);
    assert.equal(serializeObservation(first), serializeObservation(second));
});

test("legacy failure is structured and stack-free", async () => {
    class STRlingParseError extends Error {
        constructor() {
            super("Unterminated group");
            this.name = "STRlingParseError";
            this.pos = 3;
            this.text = "(ab";
            this.hint = "Add a matching ')'.";
        }

        toFormattedString() {
            return "STRling Parse Error: Unterminated group";
        }
    }

    const observation = await observeRequest(
        request({ input: { source: "(ab" } }),
        { fingerprint: "sha256:" + "1".repeat(64) },
        () => {
            throw new STRlingParseError();
        },
    );
    assert.equal(observation.outcome.status, "legacy_failure");
    assert.deepEqual(observation.outcome.failure, {
        category: "parse_error",
        class: "STRlingParseError",
        formatted: "STRling Parse Error: Unterminated group",
        hint: "Add a matching ')'.",
        message: "Unterminated group",
        name: "STRlingParseError",
        position: 3,
        source_text: "(ab",
        stage: "parser",
    });
    assert.equal(Object.hasOwn(observation.outcome.failure, "stack"), false);
});

test("runner identity and operation maps are independently validated", async () => {
    const pythonRequest = request({
        expected_legacy_surface: PYTHON_OPERATION_SPECS["parser.parse"].surface,
    });
    assert.deepEqual(
        validateRequest(pythonRequest, PYTHON_OPERATION_SPECS),
        pythonRequest,
    );
    assert.throws(
        () => validateRequest(pythonRequest),
        (error) =>
            error instanceof ProtocolError && error.code === "SURFACE_MISMATCH",
    );
    assert.deepEqual(validateRunnerIdentity(PYTHON_RUNNER), PYTHON_RUNNER);
    assert.throws(
        () => validateRunnerIdentity({ ...PYTHON_RUNNER, authority: true }),
        (error) =>
            error instanceof ProtocolError && error.code === "INVALID_SHAPE",
    );

    const implementation = { fingerprint: "sha256:" + "2".repeat(64) };
    const typescriptObservation = await observeRequest(
        request(),
        implementation,
        () => ({ runtime: "typescript" }),
    );
    const pythonObservation = await observeRequest(
        pythonRequest,
        implementation,
        () => ({ runtime: "python" }),
        {
            operationSpecs: PYTHON_OPERATION_SPECS,
            runner: PYTHON_RUNNER,
        },
    );
    assert.deepEqual(
        Object.keys(pythonObservation).sort(),
        Object.keys(typescriptObservation).sort(),
    );
    assert.deepEqual(typescriptObservation.runner, TYPESCRIPT_RUNNER);
    assert.deepEqual(pythonObservation.runner, PYTHON_RUNNER);
});

test("not-exposed operations are observations rather than fabricated calls", async () => {
    const observation = await observeRequest(
        request({
            expected_legacy_surface:
                PYTHON_OPERATION_SPECS["parser.parse"].surface,
        }),
        { fingerprint: "sha256:" + "3".repeat(64) },
        () => {
            throw unsupportedOperation(
                "the historical Python package root does not expose parse",
            );
        },
        {
            operationSpecs: PYTHON_OPERATION_SPECS,
            runner: PYTHON_RUNNER,
        },
    );
    assert.deepEqual(observation.outcome, {
        reason: "the historical Python package root does not expose parse",
        status: "unsupported",
    });
});
