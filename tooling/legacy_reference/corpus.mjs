import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
    OBSERVATION_SCHEMA_VERSION,
    OPERATION_IDS,
    PROTOCOL_VERSION,
} from "./constants.mjs";
import {
    canonicalFingerprint,
    canonicalLine,
    sha256Bytes,
} from "./canonical.mjs";
import { createImplementationIdentity } from "./identity.mjs";
import { createLegacyInvoker } from "./legacy_runtime.mjs";
import { observeRequest, ProtocolError, validateRequest } from "./protocol.mjs";

export const CORPUS_KIND = "strling.legacy-reference-corpus";
export const CORPUS_VERSION = "1.0.0";
export const BATCH_KIND = "strling.legacy-reference-batch";
export const BATCH_SCHEMA_VERSION = "1.1.0";
export const CERTIFICATION_KIND = "strling.legacy-reference-certification";
export const CERTIFICATION_SCHEMA_VERSION = "1.1.0";
export const DEFAULT_CORPUS_PATH = fileURLToPath(
    new URL("./corpus.json", import.meta.url),
);

const TOP_LEVEL_KEYS = Object.freeze([
    "cases",
    "corpus_kind",
    "corpus_version",
    "description",
]);
const CASE_KEYS = Object.freeze([
    "behavior_family",
    "id",
    "provenance",
    "request",
]);
const DISPOSITION_PATTERN =
    /\b(correct|incorrect|preserved|equivalent)\b|intentional[- ]correction|unsupported by the new compiler/i;

function isObject(value) {
    return (
        value !== null &&
        typeof value === "object" &&
        !Array.isArray(value) &&
        (Object.getPrototypeOf(value) === Object.prototype ||
            Object.getPrototypeOf(value) === null)
    );
}

function assertExactKeys(value, expected, location) {
    const actual = Object.keys(value).sort();
    const wanted = [...expected].sort();
    if (
        actual.length !== wanted.length ||
        actual.some((key, index) => key !== wanted[index])
    ) {
        throw new ProtocolError(
            "INVALID_CORPUS",
            location + " keys must be exactly: " + wanted.join(", "),
        );
    }
}

function assertNonDisposition(value, location) {
    if (typeof value === "string" && DISPOSITION_PATTERN.test(value)) {
        throw new ProtocolError(
            "CORPUS_DISPOSITION",
            location + " contains a comparison disposition",
        );
    }
    if (Array.isArray(value)) {
        value.forEach((item, index) =>
            assertNonDisposition(item, location + "/" + index),
        );
    } else if (isObject(value)) {
        for (const [key, child] of Object.entries(value)) {
            if (
                [
                    "classification",
                    "disposition",
                    "expected_semantics",
                ].includes(key)
            ) {
                throw new ProtocolError(
                    "CORPUS_DISPOSITION",
                    location + " contains forbidden field '" + key + "'",
                );
            }
            assertNonDisposition(child, location + "/" + key);
        }
    }
}

function validateCorpus(value) {
    if (!isObject(value)) {
        throw new ProtocolError(
            "INVALID_CORPUS",
            "reference corpus must be an object",
        );
    }
    assertExactKeys(value, TOP_LEVEL_KEYS, "corpus");
    if (value.corpus_kind !== CORPUS_KIND) {
        throw new ProtocolError(
            "INVALID_CORPUS",
            "corpus_kind must be '" + CORPUS_KIND + "'",
        );
    }
    if (value.corpus_version !== CORPUS_VERSION) {
        throw new ProtocolError(
            "UNSUPPORTED_CORPUS_VERSION",
            "corpus_version must be '" + CORPUS_VERSION + "'",
        );
    }
    if (
        typeof value.description !== "string" ||
        value.description.length === 0
    ) {
        throw new ProtocolError(
            "INVALID_CORPUS",
            "description must be a non-empty string",
        );
    }
    if (!Array.isArray(value.cases) || value.cases.length === 0) {
        throw new ProtocolError(
            "INVALID_CORPUS",
            "cases must be a non-empty array",
        );
    }

    const ids = new Set();
    const operations = new Set();
    const cases = value.cases.map((entry, index) => {
        const location = "cases/" + index;
        if (!isObject(entry)) {
            throw new ProtocolError(
                "INVALID_CORPUS",
                location + " must be an object",
            );
        }
        assertExactKeys(entry, CASE_KEYS, location);
        if (
            typeof entry.id !== "string" ||
            !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(entry.id)
        ) {
            throw new ProtocolError(
                "INVALID_CORPUS",
                location + ".id is not a stable kebab-case identifier",
            );
        }
        if (ids.has(entry.id)) {
            throw new ProtocolError(
                "INVALID_CORPUS",
                "duplicate case id '" + entry.id + "'",
            );
        }
        ids.add(entry.id);
        for (const key of ["behavior_family", "provenance"]) {
            if (typeof entry[key] !== "string" || entry[key].length === 0) {
                throw new ProtocolError(
                    "INVALID_CORPUS",
                    location + "." + key + " must be a non-empty string",
                );
            }
        }
        const request = validateRequest(entry.request);
        operations.add(request.operation);
        return {
            behavior_family: entry.behavior_family,
            id: entry.id,
            provenance: entry.provenance,
            request,
        };
    });

    const missing = OPERATION_IDS.filter(
        (operation) => !operations.has(operation),
    );
    if (missing.length > 0) {
        throw new ProtocolError(
            "INCOMPLETE_CORPUS",
            "corpus does not cover operations: " + missing.join(", "),
        );
    }
    const corpus = {
        cases,
        corpus_kind: CORPUS_KIND,
        corpus_version: CORPUS_VERSION,
        description: value.description,
    };
    assertNonDisposition(corpus, "corpus");
    return corpus;
}

export async function loadCorpus(corpusPath = DEFAULT_CORPUS_PATH) {
    let parsed;
    try {
        parsed = JSON.parse(await readFile(corpusPath, "utf8"));
    } catch (error) {
        if (error instanceof SyntaxError) {
            throw new ProtocolError(
                "MALFORMED_CORPUS",
                "reference corpus is not valid JSON",
            );
        }
        throw error;
    }
    return validateCorpus(parsed);
}

export function caseIdentity(entry, corpusVersion = CORPUS_VERSION) {
    return canonicalFingerprint({
        case_id: entry.id,
        corpus_version: corpusVersion,
        request: entry.request,
    });
}

export async function executeCorpus({ corpus, implementation, invoke }) {
    const observations = [];
    for (const entry of corpus.cases) {
        observations.push({
            behavior_family: entry.behavior_family,
            case_id: entry.id,
            case_identity: caseIdentity(entry, corpus.corpus_version),
            observation: await observeRequest(
                entry.request,
                implementation,
                invoke,
            ),
            provenance: entry.provenance,
        });
    }
    return {
        batch_kind: BATCH_KIND,
        batch_schema_version: BATCH_SCHEMA_VERSION,
        corpus: {
            algorithm: "sha256",
            fingerprint: canonicalFingerprint(corpus),
            version: corpus.corpus_version,
        },
        implementation,
        observation_schema_version: OBSERVATION_SCHEMA_VERSION,
        observations,
        protocol_version: PROTOCOL_VERSION,
        runner: observations[0].observation.runner,
    };
}

export async function createCorpusContext({
    root,
    distRoot,
    corpusPath = DEFAULT_CORPUS_PATH,
}) {
    const [corpus, implementation, invoke] = await Promise.all([
        loadCorpus(corpusPath),
        createImplementationIdentity(root),
        createLegacyInvoker(distRoot),
    ]);
    return { corpus, implementation, invoke };
}

export async function certifyCorpus({
    root,
    distRoot,
    corpusPath = DEFAULT_CORPUS_PATH,
    repeatRuns = 3,
}) {
    if (!Number.isSafeInteger(repeatRuns) || repeatRuns < 2) {
        throw new ProtocolError(
            "INVALID_CERTIFICATION",
            "repeatRuns must be an integer of at least 2",
        );
    }

    const corpusBytesBefore = await readFile(corpusPath);
    const context = await createCorpusContext({ root, distRoot, corpusPath });
    const batches = [];
    const batchLines = [];
    for (let index = 0; index < repeatRuns; index += 1) {
        const batch = await executeCorpus(context);
        batches.push(batch);
        batchLines.push(canonicalLine(batch));
    }

    const firstLine = batchLines[0];
    const mismatches = batchLines.filter((line) => line !== firstLine).length;
    const [corpusBytesAfter, implementationAfter] = await Promise.all([
        readFile(corpusPath),
        createImplementationIdentity(root),
    ]);
    const corpusUnchanged =
        sha256Bytes(corpusBytesBefore) === sha256Bytes(corpusBytesAfter);
    const implementationUnchanged =
        canonicalLine(context.implementation) ===
        canonicalLine(implementationAfter);
    if (!corpusUnchanged || !implementationUnchanged) {
        throw new ProtocolError(
            "REFERENCE_INPUT_MUTATION",
            "reference execution modified the corpus or governed implementation inputs",
        );
    }
    if (mismatches !== 0) {
        throw new ProtocolError(
            "NONDETERMINISTIC_OBSERVATION",
            "repeat corpus executions produced different canonical observations",
        );
    }

    const first = batches[0];
    const outcomeCounts = {};
    const operationCounts = {};
    for (const entry of first.observations) {
        const status = entry.observation.outcome.status;
        outcomeCounts[status] = (outcomeCounts[status] ?? 0) + 1;
        const operation = entry.observation.operation;
        operationCounts[operation] = (operationCounts[operation] ?? 0) + 1;
    }
    const malformedCases = context.corpus.cases.filter(
        (entry) => entry.behavior_family === "malformed-input",
    ).length;

    return {
        case_summaries: first.observations.map((entry) => ({
            case_id: entry.case_id,
            case_identity: entry.case_identity,
            observation_fingerprint: canonicalFingerprint(entry.observation),
            operation: entry.observation.operation,
            outcome_status: entry.observation.outcome.status,
            repeat_equivalent: true,
        })),
        certification_kind: CERTIFICATION_KIND,
        certification_schema_version: CERTIFICATION_SCHEMA_VERSION,
        corpus: first.corpus,
        fixture_immutability: {
            corpus_unchanged: corpusUnchanged,
            governed_implementation_inputs_unchanged: implementationUnchanged,
        },
        implementation: context.implementation,
        malformed_cases: malformedCases,
        observation_schema_version: OBSERVATION_SCHEMA_VERSION,
        operation_counts: operationCounts,
        outcome_counts: outcomeCounts,
        protocol_version: PROTOCOL_VERSION,
        runner: first.runner,
        repeatability: {
            canonical_batches_compared: repeatRuns,
            canonical_observations_compared:
                context.corpus.cases.length * repeatRuns,
            mismatches,
            repeat_runs: repeatRuns,
        },
        status: "passed",
        unexplained_failures: 0,
    };
}

export function serializeBatch(batch) {
    return canonicalLine(batch);
}

export function serializeCertification(certification) {
    return canonicalLine(certification);
}
