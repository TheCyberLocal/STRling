import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { canonicalLine } from "../canonical.mjs";
import {
    BATCH_SCHEMA_VERSION,
    CERTIFICATION_SCHEMA_VERSION,
    certifyCorpus,
    CORPUS_VERSION,
    createCorpusContext,
    executeCorpus,
    loadCorpus,
    serializeBatch,
    serializeCertification,
} from "../corpus.mjs";
import {
    OBSERVATION_SCHEMA_VERSION,
    OPERATION_IDS,
    PROTOCOL_VERSION,
    TYPESCRIPT_RUNNER,
} from "../constants.mjs";

const ROOT = fileURLToPath(new URL("../../../", import.meta.url));
const DIST = process.env.STRLING_LEGACY_REFERENCE_DIST;
assert.ok(DIST, "controlled legacy build path is required");

const corpus = await loadCorpus();
const certification = await certifyCorpus({
    distRoot: DIST,
    root: ROOT,
});
const context = await createCorpusContext({
    distRoot: DIST,
    root: ROOT,
});
const requestSnapshot = canonicalLine(corpus);
const firstBatch = await executeCorpus(context);
const secondBatch = await executeCorpus(context);

test("focused corpus has 24 stable cases and covers every operation class", () => {
    assert.equal(corpus.cases.length, 24);
    assert.deepEqual(
        [
            ...new Set(corpus.cases.map((entry) => entry.request.operation)),
        ].sort(),
        [...OPERATION_IDS].sort(),
    );
    const ids = corpus.cases.map((entry) => entry.id);
    assert.equal(new Set(ids).size, ids.length);
});

test("protocol, observations, corpus, batch, and certification version independently", () => {
    assert.equal(PROTOCOL_VERSION, "1.0.0");
    assert.equal(OBSERVATION_SCHEMA_VERSION, "1.1.0");
    assert.equal(CORPUS_VERSION, "1.0.0");
    assert.equal(BATCH_SCHEMA_VERSION, "1.1.0");
    assert.equal(CERTIFICATION_SCHEMA_VERSION, "1.1.0");
    assert.equal(certification.protocol_version, PROTOCOL_VERSION);
    assert.equal(
        certification.observation_schema_version,
        OBSERVATION_SCHEMA_VERSION,
    );
    assert.equal(certification.corpus.version, CORPUS_VERSION);
});

test("three full runs produce equivalent canonical observations", () => {
    assert.equal(certification.status, "passed");
    assert.deepEqual(certification.repeatability, {
        canonical_batches_compared: 3,
        canonical_observations_compared: 72,
        mismatches: 0,
        repeat_runs: 3,
    });
    assert.equal(
        certification.case_summaries.every((entry) => entry.repeat_equivalent),
        true,
    );
});

test("batch execution itself is byte-identical", () => {
    assert.equal(serializeBatch(firstBatch), serializeBatch(secondBatch));
    assert.equal(firstBatch.observations.length, 24);
    assert.deepEqual(firstBatch.runner, TYPESCRIPT_RUNNER);
    assert.deepEqual(certification.runner, TYPESCRIPT_RUNNER);
});

test("each case identity and observation fingerprint is unique", () => {
    const caseIdentities = certification.case_summaries.map(
        (entry) => entry.case_identity,
    );
    const observationFingerprints = certification.case_summaries.map(
        (entry) => entry.observation_fingerprint,
    );
    assert.equal(new Set(caseIdentities).size, 24);
    assert.equal(new Set(observationFingerprints).size, 24);
});

test("reference execution leaves the corpus and governed inputs unchanged", () => {
    assert.equal(canonicalLine(corpus), requestSnapshot);
    assert.deepEqual(certification.fixture_immutability, {
        corpus_unchanged: true,
        governed_implementation_inputs_unchanged: true,
    });
});

test("malformed requests and other legacy failures remain contained observations", () => {
    assert.equal(certification.malformed_cases, 2);
    assert.deepEqual(certification.outcome_counts, {
        legacy_failure: 7,
        success: 17,
    });
    assert.equal(certification.unexplained_failures, 0);
    const malformed = firstBatch.observations.filter(
        (entry) => entry.behavior_family === "malformed-input",
    );
    assert.equal(malformed.length, 2);
    assert.equal(
        malformed.every(
            (entry) => entry.observation.outcome.status === "legacy_failure",
        ),
        true,
    );
});

test("corpus carries no semantic disposition fields or labels", () => {
    const text = JSON.stringify(corpus);
    assert.doesNotMatch(
        text,
        /"classification"|"disposition"|"expected_semantics"/i,
    );
    assert.doesNotMatch(
        text,
        /\b(correct|incorrect|preserved|equivalent)\b|intentional[- ]correction|unsupported by the new compiler/i,
    );
});

test("certification serialization is deterministic canonical JSON", () => {
    assert.equal(
        serializeCertification(certification),
        canonicalLine(certification),
    );
    assert.equal(serializeCertification(certification).endsWith("\n"), true);
});
