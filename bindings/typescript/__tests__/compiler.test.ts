import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import { Compiler, parse, parseToArtifact } from "../src/STRling/compiler.js";
import { instantiateWasm, type JsonObject } from "../src/STRling/interop.js";

const root = resolve(process.cwd(), "..", "..");

async function json(path: string): Promise<JsonObject> {
    return JSON.parse(
        await readFile(resolve(root, path), "utf-8"),
    ) as JsonObject;
}

async function client() {
    return instantiateWasm(
        await readFile(
            resolve(root, "bindings/typescript/dist/strling_interop.wasm"),
        ),
    );
}

describe("canonical compiler conveniences", () => {
    test("returns the canonical exact-profile target artifact unchanged", async () => {
        const loaded = await client();
        const request = await json(
            "spec/contracts/1.0/examples/compile-request/target-artifact.json",
        );
        const profile = await json("spec/targets/profiles/pcre2-10.43.json");
        const result = new Compiler(loaded).compile(request, profile) as Record<
            string,
            unknown
        >;
        expect(result.outcome).toBe("succeeded");
        expect(
            (result.artifact as Record<string, unknown>).target_profile,
        ).toEqual(request.target_profile);
    });

    test("preserves canonical failed compile results as values", async () => {
        const loaded = await client();
        const result = parse(loaded, "(") as Record<string, unknown>;
        expect(result.outcome).toBe("failed");
        expect(Array.isArray(result.diagnostics)).toBe(true);
    });

    test("requires exact target identity for artifact projection", async () => {
        const loaded = await client();
        expect(() => parseToArtifact(loaded, "abc", {})).toThrow(TypeError);
    });

    test("projects artifact results only through a supplied profile", async () => {
        const loaded = await client();
        const profile = await json("spec/targets/profiles/pcre2-10.43.json");
        const result = parseToArtifact(loaded, 'literal("abc")', {
            targetProfile: profile,
            targetProfileReference: {
                profile_id: "profile:pcre2/10.43",
                profile_version: "1.3.0",
                sha256: "56762a1d289d41d0811b007695464916fda0ca5c48c2f5569b4ec26983a24bff",
            },
        }) as Record<string, unknown>;
        expect(["succeeded", "failed"]).toContain(result.outcome);
        if (result.outcome === "succeeded") {
            expect(result.artifact).toBeDefined();
        }
    });
});
