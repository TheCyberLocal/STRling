const assert = require("node:assert/strict");
const Module = require("node:module");
const path = require("node:path");

const bundlePath = path.resolve(process.argv[2]);
let configuredCommand = "C:/tools/python.exe";
const errors = [];
const clients = [];
let startCount = 0;
let stopCount = 0;

const vscode = {
    window: {
        showErrorMessage(message) {
            errors.push(message);
            return Promise.resolve(message);
        },
    },
    workspace: {
        getConfiguration() {
            return {
                get(name, fallback) {
                    if (name === "languageServer.command") {
                        return configuredCommand;
                    }
                    return fallback;
                },
            };
        },
    },
};

class LanguageClient {
    constructor(id, name, serverOptions, clientOptions) {
        clients.push({ id, name, serverOptions, clientOptions });
    }

    start() {
        startCount += 1;
    }

    stop() {
        stopCount += 1;
        return Promise.resolve();
    }
}

const languageClient = {
    LanguageClient,
    TransportKind: { stdio: "stdio" },
};

const originalLoad = Module._load;
Module._load = function (request, parent, isMain) {
    if (request === "vscode") return vscode;
    if (request === "vscode-languageclient/node") return languageClient;
    if (request === "child_process") {
        return {
            spawnSync() {
                return { error: new Error("python unavailable"), status: null };
            },
        };
    }
    return originalLoad.call(this, request, parent, isMain);
};

const extension = require(bundlePath);
const extensionRoot = path.resolve("C:/isolated/extensions/strling");
const executableSuffix = process.platform === "win32" ? ".exe" : "";
const subscriptions = [];
const context = {
    extensionPath: extensionRoot,
    asAbsolutePath(relative) {
        return path.join(extensionRoot, relative);
    },
    subscriptions,
};

extension.activate(context);
assert.equal(clients.length, 1);
assert.equal(startCount, 1);
assert.equal(subscriptions.length, 1);
const created = clients[0];
assert.equal(created.id, "strling");
assert.equal(created.serverOptions.run.command, configuredCommand);
assert.deepEqual(created.serverOptions.run.args, [
    path.join(extensionRoot, "server", "server.py"),
    "--stdio",
]);
assert.equal(created.serverOptions.run.options.cwd, extensionRoot);
assert.equal(created.serverOptions.run.transport, "stdio");
assert.equal(
    created.serverOptions.run.options.env.STRLING_KERNEL,
    path.join(
        extensionRoot,
        "server",
        "bin",
        `strling-kernel${executableSuffix}`,
    ),
);
assert.equal(
    created.serverOptions.run.options.env.STRLING_EDITOR_CORE,
    path.join(
        extensionRoot,
        "server",
        "bin",
        `strling-editor-core${executableSuffix}`,
    ),
);
assert.equal(created.clientOptions.documentSelector.length, 21);
assert.deepEqual(
    created.clientOptions.documentSelector.map((selector) => selector.language),
    [
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
    ],
);
assert.equal(
    created.clientOptions.initializationOptions.features.references,
    true,
);

configuredCommand = "";
extension.activate(context);
assert.equal(clients.length, 1);
assert.equal(errors.length, 1);
assert.match(errors[0], /Python 3\.11 or newer/);

Promise.resolve(extension.deactivate()).then(() => {
    assert.equal(stopCount, 1);
    process.stdout.write(
        JSON.stringify({
            clients: clients.length,
            errors: errors.length,
            selectors: 21,
        }),
    );
});
