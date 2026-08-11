import { createHash } from "node:crypto";

function isPlainObject(value) {
    if (value === null || typeof value !== "object") {
        return false;
    }
    const prototype = Object.getPrototypeOf(value);
    return prototype === Object.prototype || prototype === null;
}

export function canonicalize(value, location = "$") {
    if (
        value === null ||
        typeof value === "string" ||
        typeof value === "boolean"
    ) {
        return value;
    }
    if (typeof value === "number") {
        if (!Number.isFinite(value)) {
            throw new TypeError(`${location} contains a non-finite number`);
        }
        return Object.is(value, -0) ? 0 : value;
    }
    if (Array.isArray(value)) {
        return value.map((item, index) =>
            canonicalize(item, `${location}/${index}`),
        );
    }
    if (!isPlainObject(value)) {
        throw new TypeError(`${location} is not a canonical JSON value`);
    }
    const symbolKeys = Object.getOwnPropertySymbols(value);
    if (symbolKeys.length > 0) {
        throw new TypeError(`${location} contains a symbol key`);
    }

    const result = {};
    for (const key of Object.keys(value).sort()) {
        const child = value[key];
        if (child === undefined) {
            throw new TypeError(`${location}/${key} is undefined`);
        }
        result[key] = canonicalize(child, `${location}/${key}`);
    }
    return result;
}

export function canonicalJson(value) {
    return JSON.stringify(canonicalize(value));
}

export function canonicalLine(value) {
    return canonicalJson(value) + "\n";
}

export function sha256Bytes(value) {
    return createHash("sha256").update(value).digest("hex");
}

export function canonicalFingerprint(value) {
    return `sha256:${sha256Bytes(canonicalJson(value))}`;
}
