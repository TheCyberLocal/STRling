/** Explicit Node-only loader for the packaged WebAssembly artifact. */

import { readFile } from "node:fs/promises";

import {
    instantiateWasm,
    wasmArtifactUrl,
    type WasmClient,
} from "./STRling/interop.js";

export async function loadBundledWasm(): Promise<WasmClient> {
    return instantiateWasm(await readFile(wasmArtifactUrl()));
}

export async function loadWasmFile(path: string | URL): Promise<WasmClient> {
    return instantiateWasm(await readFile(path));
}
