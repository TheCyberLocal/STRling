#!/usr/bin/env node

import { readFileSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

import { createImplementationIdentity } from "./identity.mjs";
import {
    createLegacyInvoker,
    SUPPORTED_OPERATION_IDS,
} from "./legacy_runtime.mjs";
import {
    observeRequest,
    ProtocolError,
    serializeObservation,
    serializeProtocolFailure,
    validateRequest,
} from "./protocol.mjs";

const ROOT = fileURLToPath(new URL("../../", import.meta.url));

async function readRequest(arguments_) {
    if (arguments_.length === 0) {
        return readFileSync(0, "utf8");
    }
    if (arguments_.length === 2 && arguments_[0] === "--request") {
        return readFile(arguments_[1], "utf8");
    }
    throw new ProtocolError(
        "INVALID_INVOCATION",
        "usage: cli.mjs [--request <request.json>]",
    );
}

async function main() {
    const text = await readRequest(process.argv.slice(2));
    let rawRequest;
    try {
        rawRequest = JSON.parse(text);
    } catch {
        throw new ProtocolError("MALFORMED_JSON", "request is not valid JSON");
    }

    const request = validateRequest(rawRequest);
    if (!SUPPORTED_OPERATION_IDS.includes(request.operation)) {
        throw new ProtocolError(
            "OPERATION_NOT_AVAILABLE",
            `operation '${request.operation}' is not yet available`,
        );
    }

    const distRoot = process.env.STRLING_LEGACY_REFERENCE_DIST;
    if (!distRoot) {
        throw new ProtocolError(
            "MISSING_LEGACY_BUILD",
            "the controlled legacy build location was not provided",
        );
    }

    const [implementation, invoke] = await Promise.all([
        createImplementationIdentity(ROOT),
        createLegacyInvoker(distRoot),
    ]);
    const observation = await observeRequest(request, implementation, invoke);
    process.stdout.write(serializeObservation(observation));
}

main().catch((error) => {
    const failure =
        error instanceof ProtocolError
            ? error
            : new ProtocolError(
                  "RUNNER_FAILURE",
                  "the legacy reference runner could not complete the request",
              );
    process.stderr.write(serializeProtocolFailure(failure));
    process.exitCode = 2;
});
