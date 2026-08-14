import assert from "node:assert/strict";
import { createRequire } from "node:module";
import path from "node:path";
import { pathToFileURL } from "node:url";

const compiledPath = path.resolve(process.argv[2]);
const require = createRequire(import.meta.url);
const runtime = require(compiledPath);

assert.deepEqual(runtime.documentSelectors, [
    "strling",
    "c",
    "cpp",
    "csharp",
    "dart",
    "fsharp",
    "go",
    "java",
    "javascript",
    "javascriptreact",
    "kotlin",
    "lua",
    "perl",
    "php",
    "python",
    "r",
    "ruby",
    "rust",
    "swift",
    "typescript",
    "typescriptreact",
]);

assert.deepEqual(
    runtime.resolveLanguageServerCommand(
        "C:/custom/python.exe",
        "win32",
        () => {
            throw new Error("configured commands must not be probed");
        },
    ),
    { command: "C:/custom/python.exe", prefixArgs: [] },
);

const probes = [];
assert.deepEqual(
    runtime.resolveLanguageServerCommand("", "win32", (command, args) => {
        probes.push([command, args]);
        return command === "py";
    }),
    { command: "py", prefixArgs: ["-3"] },
);
assert.deepEqual(probes, [
    ["python", []],
    ["py", ["-3"]],
]);
assert.equal(
    runtime.resolveLanguageServerCommand("", "linux", () => false),
    undefined,
);
assert.match(runtime.missingPythonError, /Python 3\.11 or newer/);

const win = runtime.bundledRuntime("C:/extension", "win32", "C:/inherited");
assert.equal(win.serverPath, path.join("C:/extension", "server", "server.py"));
assert.equal(
    win.environment.STRLING_KERNEL,
    path.join("C:/extension", "server", "bin", "strling-kernel.exe"),
);
assert.equal(
    win.environment.STRLING_EDITOR_CORE,
    path.join("C:/extension", "server", "bin", "strling-editor-core.exe"),
);
assert.equal(
    win.environment.PYTHONPATH,
    [path.join("C:/extension", "server", "libs"), "C:/inherited"].join(
        path.delimiter,
    ),
);
assert.deepEqual(Object.keys(win.environment).sort(), [
    "PYTHONPATH",
    "STRLING_EDITOR_CORE",
    "STRLING_ISLAND_BOUNDARIES_PATH",
    "STRLING_KERNEL",
    "STRLING_SIMPLY_PROTOCOL_PATH",
    "STRLING_STDLIB_REGISTRY_PATH",
]);

const linux = runtime.bundledRuntime("/extension", "linux");
assert.equal(
    linux.environment.STRLING_KERNEL,
    path.join("/extension", "server", "bin", "strling-kernel"),
);
assert.equal(
    linux.environment.STRLING_EDITOR_CORE,
    path.join("/extension", "server", "bin", "strling-editor-core"),
);
assert.equal(
    linux.environment.PYTHONPATH,
    path.join("/extension", "server", "libs"),
);

process.stdout.write(
    JSON.stringify({
        module: pathToFileURL(compiledPath).href,
        selectors: runtime.documentSelectors.length,
        environment: Object.keys(win.environment).length,
    }),
);
