import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import {
    INTEROP_PROTOCOL_VERSION,
    InteropProtocolError,
    MAX_INTEROP_REQUEST_BYTES,
    WasmAdapterError,
    WasmClient,
    instantiateWasm,
} from "../src/STRling/interop.js";
import { loadWasmFile } from "../src/node.js";

const artifact = resolve(process.cwd(), "dist", "strling_interop.wasm");

async function client(): Promise<WasmClient> {
    return instantiateWasm(await readFile(artifact));
}

describe("raw strling.wasm-abi adapter", () => {
    test("loads the assembled artifact through the explicit Node entrypoint", async () => {
        const loaded = await loadWasmFile(artifact);
        const description = loaded.describe() as Record<string, unknown>;
        expect(description.protocol_version).toBe(INTEROP_PROTOCOL_VERSION);
        expect((description.wasm_abi as Record<string, unknown>).id).toBe(
            "strling.wasm-abi",
        );
    });

    test("accepts raw bytes without a filesystem or network dependency", async () => {
        const loaded = await client();
        expect(
            (loaded.describe() as Record<string, unknown>).operations,
        ).toEqual([
            "describe",
            "compile",
            "target_profile.inspect",
            "simply.compile",
        ]);
    });

    test("preserves stable protocol codes and paths", async () => {
        const loaded = await client();
        expect(() =>
            loaded.execute({
                interop_protocol_version: INTEROP_PROTOCOL_VERSION,
                operation: "not-supported",
                payload: {},
            }),
        ).not.toThrow();
        const response = loaded.execute({
            interop_protocol_version: INTEROP_PROTOCOL_VERSION,
            operation: "not-supported",
            payload: {},
        });
        expect(response).toMatchObject({
            status: "error",
            error: { code: "STRL-INTEROP-0005", path: "$.operation" },
        });
    });

    test("distinguishes malformed transport bytes from host failures", async () => {
        const loaded = await client();
        const response = loaded.executeBytes(new Uint8Array([0xff]));
        expect(response).toMatchObject({
            status: "error",
            error: { code: "STRL-INTEROP-0001", path: "$" },
        });
        expect(() =>
            loaded.executeBytes(new Uint8Array(MAX_INTEROP_REQUEST_BYTES + 1)),
        ).toThrow(WasmAdapterError);
    });

    test("rejects an unsupported operation through a typed canonical exception", async () => {
        const loaded = await client();
        expect(() =>
            loaded.inspectTargetProfile({ contract_version: "invalid" }),
        ).toThrow(InteropProtocolError);
    });

    test("releases request and response allocations across repeated cycles", async () => {
        const loaded = await client();
        for (let index = 0; index < 128; index += 1) {
            expect(
                (loaded.describe() as Record<string, unknown>).protocol_version,
            ).toBe(INTEROP_PROTOCOL_VERSION);
        }
    });

    test("isolates independent module instances", async () => {
        const bytes = await readFile(artifact);
        const [left, right] = await Promise.all([
            instantiateWasm(bytes),
            instantiateWasm(bytes),
        ]);
        expect(left.describe()).toEqual(right.describe());
    });
});
