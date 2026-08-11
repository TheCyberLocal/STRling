import {
    OBSERVATION_KIND,
    OBSERVATION_SCHEMA_VERSION,
    OPERATION_SPECS,
    PROTOCOL_FAILURE_KIND,
    PROTOCOL_VERSION,
    REQUEST_KIND,
} from "./constants.mjs";
import { canonicalFingerprint, canonicalLine } from "./canonical.mjs";

const TOP_LEVEL_KEYS = Object.freeze([
    "expected_legacy_surface",
    "input",
    "kind",
    "operation",
    "options",
    "protocol_version",
]);

export class ProtocolError extends Error {
    constructor(code, message) {
        super(message);
        this.name = "LegacyReferenceProtocolError";
        this.code = code;
        Object.setPrototypeOf(this, ProtocolError.prototype);
    }
}

export class LegacySurfaceFailure {
    constructor(stage, error) {
        this.stage = stage;
        this.error = error;
    }
}

export function legacySurfaceFailure(stage, error) {
    return new LegacySurfaceFailure(stage, error);
}

function isObject(value) {
    return (
        value !== null &&
        typeof value === "object" &&
        !Array.isArray(value) &&
        (Object.getPrototypeOf(value) === Object.prototype ||
            Object.getPrototypeOf(value) === null)
    );
}

function exactKeys(value, expected, location) {
    const actual = Object.keys(value).sort();
    const wanted = [...expected].sort();
    if (
        actual.length !== wanted.length ||
        actual.some((key, index) => key !== wanted[index])
    ) {
        throw new ProtocolError(
            "INVALID_SHAPE",
            `${location} keys must be exactly: ${wanted.join(", ")}`,
        );
    }
}

function copyJsonValue(value) {
    if (Array.isArray(value)) {
        return value.map(copyJsonValue);
    }
    if (isObject(value)) {
        const result = {};
        for (const key of Object.keys(value)) {
            result[key] = copyJsonValue(value[key]);
        }
        return result;
    }
    return value;
}

function validateFlags(value) {
    if (typeof value === "string") {
        return value;
    }
    if (!isObject(value)) {
        throw new ProtocolError(
            "INVALID_OPTIONS",
            "options.flags must be a string or legacy flag object",
        );
    }
    const allowed = new Set([
        "dotAll",
        "extended",
        "ignoreCase",
        "multiline",
        "unicode",
    ]);
    for (const [key, enabled] of Object.entries(value)) {
        if (!allowed.has(key) || typeof enabled !== "boolean") {
            throw new ProtocolError(
                "INVALID_OPTIONS",
                "options.flags contains an unknown key or non-boolean value",
            );
        }
    }
    return copyJsonValue(value);
}

function validateOptions(options, spec) {
    if (!isObject(options)) {
        throw new ProtocolError("INVALID_OPTIONS", "options must be an object");
    }
    const allowed = new Set(spec.options);
    for (const key of Object.keys(options)) {
        if (!allowed.has(key)) {
            throw new ProtocolError(
                "INVALID_OPTIONS",
                `option '${key}' is not supported by this operation`,
            );
        }
    }

    const normalized = {};
    if (Object.hasOwn(options, "max_depth")) {
        if (!Number.isSafeInteger(options.max_depth) || options.max_depth < 1) {
            throw new ProtocolError(
                "INVALID_OPTIONS",
                "options.max_depth must be a positive safe integer",
            );
        }
        normalized.max_depth = options.max_depth;
    }
    if (Object.hasOwn(options, "target")) {
        if (typeof options.target !== "string") {
            throw new ProtocolError(
                "INVALID_OPTIONS",
                "options.target must be a string",
            );
        }
        normalized.target = options.target;
    }
    if (Object.hasOwn(options, "flags")) {
        normalized.flags = validateFlags(options.flags);
    }
    return normalized;
}

export function validateRequest(value) {
    if (!isObject(value)) {
        throw new ProtocolError("INVALID_REQUEST", "request must be an object");
    }
    exactKeys(value, TOP_LEVEL_KEYS, "request");

    if (value.kind !== REQUEST_KIND) {
        throw new ProtocolError(
            "UNSUPPORTED_KIND",
            `kind must be '${REQUEST_KIND}'`,
        );
    }
    if (value.protocol_version !== PROTOCOL_VERSION) {
        throw new ProtocolError(
            "UNSUPPORTED_PROTOCOL_VERSION",
            `protocol_version must be '${PROTOCOL_VERSION}'`,
        );
    }
    if (typeof value.operation !== "string") {
        throw new ProtocolError(
            "INVALID_OPERATION",
            "operation must be a string",
        );
    }
    const spec = OPERATION_SPECS[value.operation];
    if (spec === undefined) {
        throw new ProtocolError(
            "UNKNOWN_OPERATION",
            `unknown operation '${value.operation}'`,
        );
    }
    if (value.expected_legacy_surface !== spec.surface) {
        throw new ProtocolError(
            "SURFACE_MISMATCH",
            `operation '${value.operation}' requires expected legacy surface '${spec.surface}'`,
        );
    }
    if (!isObject(value.input)) {
        throw new ProtocolError("INVALID_INPUT", "input must be an object");
    }
    exactKeys(value.input, [spec.input], "input");
    if (typeof value.input[spec.input] !== "string") {
        throw new ProtocolError(
            "INVALID_INPUT",
            `input.${spec.input} must be a string`,
        );
    }

    return {
        expected_legacy_surface: value.expected_legacy_surface,
        input: { [spec.input]: value.input[spec.input] },
        kind: REQUEST_KIND,
        operation: value.operation,
        options: validateOptions(value.options, spec),
        protocol_version: PROTOCOL_VERSION,
    };
}

function errorCategory(name) {
    if (name === "STRlingParseError") return "parse_error";
    if (name === "STRlingCompilationError") return "compilation_error";
    if (name === "SyntaxError") return "syntax_error";
    if (name === "TypeError") return "type_error";
    if (name === "RangeError") return "range_error";
    return name === "NonErrorThrow" ? "legacy_throw" : "legacy_exception";
}

export function projectLegacyFailure(error, stage) {
    const objectLike =
        error !== null &&
        (typeof error === "object" || typeof error === "function");
    const name =
        objectLike && typeof error.name === "string"
            ? error.name
            : objectLike && error.constructor?.name
              ? error.constructor.name
              : "NonErrorThrow";
    const failure = {
        category: errorCategory(name),
        class:
            objectLike && error.constructor?.name
                ? error.constructor.name
                : "NonErrorThrow",
        message:
            objectLike && typeof error.message === "string"
                ? error.message
                : String(error),
        name,
        stage,
    };

    for (const [sourceKey, targetKey] of [
        ["code", "code"],
        ["engine", "engine"],
        ["pos", "position"],
        ["text", "source_text"],
        ["hint", "hint"],
    ]) {
        if (
            objectLike &&
            Object.hasOwn(error, sourceKey) &&
            error[sourceKey] !== undefined
        ) {
            failure[targetKey] = copyJsonValue(error[sourceKey]);
        }
    }
    if (objectLike && typeof error.toFormattedString === "function") {
        failure.formatted = error.toFormattedString();
    }
    return failure;
}

export async function observeRequest(rawRequest, implementation, invoke) {
    const request = validateRequest(rawRequest);
    const spec = OPERATION_SPECS[request.operation];
    const requestFingerprint = canonicalFingerprint(request);
    let outcome;
    try {
        const evidence = await invoke(request);
        outcome = { evidence: copyJsonValue(evidence), status: "success" };
    } catch (caught) {
        const wrapped =
            caught instanceof LegacySurfaceFailure
                ? caught
                : new LegacySurfaceFailure(spec.stage, caught);
        outcome = {
            failure: projectLegacyFailure(wrapped.error, wrapped.stage),
            status: "legacy_failure",
        };
    }
    return {
        implementation,
        kind: OBSERVATION_KIND,
        observation_schema_version: OBSERVATION_SCHEMA_VERSION,
        operation: request.operation,
        outcome,
        protocol_version: PROTOCOL_VERSION,
        request: {
            algorithm: "sha256",
            fingerprint: requestFingerprint,
            value: request,
        },
        surface: request.expected_legacy_surface,
    };
}

export function serializeObservation(observation) {
    return canonicalLine(observation);
}

export function protocolFailure(error) {
    const normalized =
        error instanceof ProtocolError
            ? error
            : new ProtocolError("PROTOCOL_FAILURE", String(error));
    return {
        error: {
            category: "protocol",
            class: normalized.name,
            code: normalized.code,
            message: normalized.message,
        },
        kind: PROTOCOL_FAILURE_KIND,
        protocol_version: PROTOCOL_VERSION,
    };
}

export function serializeProtocolFailure(error) {
    return canonicalLine(protocolFailure(error));
}
