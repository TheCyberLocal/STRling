import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const packagePath = resolve(process.cwd(), "package.json");

describe("package boundary", () => {
    test("publishes only supported browser, Node, Simply, and WASM entrypoints", async () => {
        const manifest = JSON.parse(await readFile(packagePath, "utf-8")) as {
            exports: Record<string, unknown>;
        };
        expect(Object.keys(manifest.exports).sort()).toEqual([
            ".",
            "./node",
            "./simply",
            "./strling_interop.wasm",
        ]);
        expect(manifest.exports).not.toHaveProperty("./core");
        expect(manifest.exports).not.toHaveProperty("./emitters/pcre2");
    });

    test("keeps the browser-safe root free of Node built-ins and implicit fetch", async () => {
        const rootSource = await readFile(
            resolve(process.cwd(), "src", "index.ts"),
            "utf-8",
        );
        const interopSource = await readFile(
            resolve(process.cwd(), "src", "STRling", "interop.ts"),
            "utf-8",
        );
        expect(rootSource).not.toMatch(/node:/);
        expect(interopSource).not.toMatch(/\bfetch\s*\(/);
    });
});
