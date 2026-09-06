import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import { instantiateWasm, type JsonObject } from "../src/STRling/interop.js";
import {
    canonicalStdlib,
    digit,
    email,
    lit,
    merge,
    type SimplyCompileProjection,
} from "../src/STRling/simply/index.js";

const root = resolve(process.cwd(), "..", "..");

async function fixture(path: string): Promise<JsonObject> {
    return JSON.parse(
        await readFile(resolve(root, path), "utf-8"),
    ) as JsonObject;
}

const compile: SimplyCompileProjection = {
    target_profile: {
        profile_id: "profile:pcre2/10.43",
        profile_version: "1.2.0",
        sha256: "56762a1d289d41d0811b007695464916fda0ca5c48c2f5569b4ec26983a24bff",
    },
    requested_outputs: ["semantic", "portability", "target_artifact"],
    compiler_options: {
        partial_semantics: "forbid",
        diagnostic_policy: { minimum_severity: "hint" },
    },
};

async function client() {
    return instantiateWasm(
        await readFile(
            resolve(root, "bindings/typescript/dist/strling_interop.wasm"),
        ),
    );
}

describe("canonical Simply facade", () => {
    test("records ergonomic sequence and repetition through Simply 1.1", async () => {
        const loaded = await client();
        const profile = await fixture("spec/targets/profiles/pcre2-10.43.json");
        const result = merge(lit("A"), digit(1, 3)).compile(
            loaded,
            compile,
            profile,
        );
        expect(result.status).toBe("success");
        expect(result.protocol_version).toBe("1.1.0");
        expect(result.compile_result.outcome).toBe("succeeded");
    });

    test("delegates every generated helper identity to the canonical registry", async () => {
        const loaded = await client();
        const profile = await fixture("spec/targets/profiles/pcre2-10.43.json");
        expect(canonicalStdlib.STDLIB_HELPER_IDS).toHaveLength(5);
        const pattern = email();
        const request = pattern.buildRequest(compile) as {
            steps: {
                operation: string;
                arguments: { helper_id: string };
            }[];
        };
        expect(request.steps[0]).toMatchObject({
            operation: "stdlib_helper",
            arguments: { helper_id: "stdlib.email" },
        });
        expect(pattern.compile(loaded, compile, profile).status).toBe(
            "success",
        );
    });

    test("does not simulate runtime regex execution or implicit rendering", () => {
        const pattern = lit("abc");
        expect(() => pattern.exec("abc")).toThrow(/retired/);
        expect(() => pattern.toRegExp()).toThrow(/retired/);
        expect(() => pattern.toString()).toThrow(/retired/);
    });

    test("keeps lexical helpers as canonical lexical-shape helpers", () => {
        const request = email().buildRequest(compile);
        expect(JSON.stringify(request)).toContain('"helper_id":"stdlib.email"');
        expect(JSON.stringify(request)).not.toContain("semantic_validator");
    });
});
