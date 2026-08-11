import { readdir, readFile } from "node:fs/promises";
import path from "node:path";

import {
    canonicalFingerprint,
    canonicalJson,
    sha256Bytes,
} from "./canonical.mjs";

const FIXED_INPUTS = Object.freeze([
    "bindings/typescript/package-lock.json",
    "bindings/typescript/package.json",
    "bindings/typescript/tsconfig.json",
]);

async function collectTypescriptSources(directory, root) {
    const entries = await readdir(directory, { withFileTypes: true });
    const paths = [];
    for (const entry of entries.sort((left, right) =>
        left.name.localeCompare(right.name),
    )) {
        const absolute = path.join(directory, entry.name);
        if (entry.isDirectory()) {
            paths.push(...(await collectTypescriptSources(absolute, root)));
        } else if (entry.isFile() && entry.name.endsWith(".ts")) {
            paths.push(path.relative(root, absolute).split(path.sep).join("/"));
        }
    }
    return paths;
}

export async function governedImplementationPaths(root) {
    const sources = await collectTypescriptSources(
        path.join(root, "bindings/typescript/src"),
        root,
    );
    return [...FIXED_INPUTS, ...sources].sort();
}

export async function readImplementationManifest(root) {
    const manifest = [];
    for (const relative of await governedImplementationPaths(root)) {
        const bytes = await readFile(path.join(root, relative));
        manifest.push({
            bytes: bytes.length,
            path: relative,
            sha256: sha256Bytes(bytes),
        });
    }
    return manifest;
}

export function fingerprintImplementationManifest(manifest, nodeVersion) {
    return canonicalFingerprint({
        inputs: manifest,
        runtime: { name: "node", version: nodeVersion },
    });
}

export async function createImplementationIdentity(
    root,
    nodeVersion = process.versions.node,
) {
    const inputs = await readImplementationManifest(root);
    const runtime = { name: "node", version: nodeVersion };
    return {
        algorithm: "sha256",
        fingerprint: fingerprintImplementationManifest(inputs, nodeVersion),
        inputs,
        kind: "strling.legacy-typescript-implementation",
        manifest_encoding: "canonical-json-v1",
        runtime,
    };
}

export function implementationManifestBytes(manifest) {
    return canonicalJson(manifest);
}
