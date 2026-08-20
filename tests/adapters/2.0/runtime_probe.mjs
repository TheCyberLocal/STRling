import { readFileSync } from "node:fs";

import { MAX_INTEROP_REQUEST_BYTES } from "../../../bindings/typescript/dist/index.js";
import { loadBundledWasm } from "../../../bindings/typescript/dist/node.js";

const actions = JSON.parse(readFileSync(0, "utf8"));
const client = await loadBundledWasm();
const results = [];

for (const action of actions) {
    try {
        let value;
        switch (action.kind) {
            case "describe":
                value = client.describe();
                break;
            case "compile":
                value = client.compile(action.request, action.target_profile);
                break;
            case "target_profile.inspect":
                value = client.inspectTargetProfile(action.target_profile);
                break;
            case "simply.compile":
                value = client.simplyCompile(
                    action.request,
                    action.target_profile,
                );
                break;
            case "raw":
                value = client.execute(action.request);
                break;
            case "invalid_utf8":
                value = client.executeBytes(Uint8Array.of(0xff));
                break;
            case "oversize":
                value = client.executeBytes(
                    new Uint8Array(MAX_INTEROP_REQUEST_BYTES + 1),
                );
                break;
            default:
                throw new Error(`unknown Node action kind: ${action.kind}`);
        }
        results.push({ id: action.id, state: "value", value });
    } catch (error) {
        results.push({
            id: action.id,
            state: "host_error",
            message: error instanceof Error ? error.message : String(error),
        });
    }
}

process.stdout.write(
    JSON.stringify({ node_version: process.version, results }),
);
