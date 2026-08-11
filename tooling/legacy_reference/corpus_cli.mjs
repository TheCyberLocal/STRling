#!/usr/bin/env node

import { fileURLToPath } from "node:url";

import {
    certifyCorpus,
    createCorpusContext,
    executeCorpus,
    serializeBatch,
    serializeCertification,
} from "./corpus.mjs";
import { ProtocolError, serializeProtocolFailure } from "./protocol.mjs";

const ROOT = fileURLToPath(new URL("../../", import.meta.url));

async function main() {
    const arguments_ = process.argv.slice(2);
    if (
        arguments_.length !== 1 ||
        !["--certify", "--observations"].includes(arguments_[0])
    ) {
        throw new ProtocolError(
            "INVALID_INVOCATION",
            "usage: corpus_cli.mjs (--certify|--observations)",
        );
    }
    const distRoot = process.env.STRLING_LEGACY_REFERENCE_DIST;
    if (!distRoot) {
        throw new ProtocolError(
            "MISSING_LEGACY_BUILD",
            "the controlled legacy build location was not provided",
        );
    }

    if (arguments_[0] === "--certify") {
        const certification = await certifyCorpus({
            distRoot,
            root: ROOT,
        });
        process.stdout.write(serializeCertification(certification));
        return;
    }

    const context = await createCorpusContext({
        distRoot,
        root: ROOT,
    });
    process.stdout.write(serializeBatch(await executeCorpus(context)));
}

main().catch((error) => {
    const failure =
        error instanceof ProtocolError
            ? error
            : new ProtocolError(
                  "RUNNER_FAILURE",
                  "the legacy reference corpus runner could not complete",
              );
    process.stderr.write(serializeProtocolFailure(failure));
    process.exitCode = 2;
});
