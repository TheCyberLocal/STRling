/**
 * STRling VS Code Reference Client
 * --------------------------------
 *
 * Spawns the Python-based STRling language server bundled in this extension
 * (`server/server.py`) over stdio and registers it for both native `.strl`
 * files and a curated set of host languages (TypeScript / Python / Rust /
 * Java). The server is
 * responsible for the Island Grammar bridge — this client only ships the
 * coordinate-faithful diagnostics back to VS Code so the existing host
 * language services (TS Server, Pylance, rust-analyzer, JDT.LS) keep their
 * own syntax highlighting untouched.
 */

import * as path from "path";
import { spawnSync } from "child_process";
import { ExtensionContext, workspace } from "vscode";
import {
    ExecutableOptions,
    LanguageClient,
    LanguageClientOptions,
    ServerOptions,
    TransportKind,
} from "vscode-languageclient/node";

let client: LanguageClient | undefined;

function resolveLanguageServerCommand(configuredCommand?: string): string {
    if (configuredCommand && configuredCommand.trim().length > 0) {
        return configuredCommand;
    }

    const candidates =
        process.platform === "win32" ? ["python", "py"] : ["python3", "python"];

    for (const candidate of candidates) {
        const probe = spawnSync(candidate, ["--version"], {
            encoding: "utf8",
        });
        if (!probe.error && probe.status === 0) {
            return candidate;
        }
    }

    return candidates[0];
}

export function activate(context: ExtensionContext): void {
    const config = workspace.getConfiguration("strling");
    const extensionRoot = context.extensionPath;
    const bundledServerPath = context.asAbsolutePath(
        path.join("server", "server.py"),
    );
    const bundledVendorPath = context.asAbsolutePath(
        path.join("server", "libs"),
    );

    const configuredCommand = config.get<string>("languageServer.command", "");
    const command = resolveLanguageServerCommand(configuredCommand);
    const configuredArgs = config.get<string[]>("languageServer.args", []);
    const args = configuredArgs.length
        ? configuredArgs
        : [
              // Default: launch the bundled server that ships inside the
              // extension package. Advanced users can still override this with
              // `strling.languageServer.args`.
              bundledServerPath,
              "--stdio",
          ];

    const inheritedPythonPath = process.env.PYTHONPATH;
    const pythonPathEntries = inheritedPythonPath
        ? [bundledVendorPath, inheritedPythonPath]
        : [bundledVendorPath];
    const executableOptions: ExecutableOptions = {
        cwd: extensionRoot,
        env: {
            ...process.env,
            PYTHONPATH: pythonPathEntries.join(path.delimiter),
        },
    };

    const serverOptions: ServerOptions = {
        run: {
            command,
            args,
            options: executableOptions,
            transport: TransportKind.stdio,
        },
        debug: {
            command,
            args,
            options: executableOptions,
            transport: TransportKind.stdio,
        },
    };

    // Document selectors: every language we want to receive Island Grammar
    // diagnostics for. Keep this list aligned with `_LANGUAGE_BY_SUFFIX`
    // in `island_extractor.py`.
    const clientOptions: LanguageClientOptions = {
        documentSelector: [
            { scheme: "file", language: "strling" },
            { scheme: "file", language: "typescript" },
            { scheme: "file", language: "typescriptreact" },
            { scheme: "file", language: "javascript" },
            { scheme: "file", language: "javascriptreact" },
            { scheme: "file", language: "python" },
            { scheme: "file", language: "rust" },
            { scheme: "file", language: "java" },
        ],
        synchronize: {
            configurationSection: "strling",
        },
        initializationOptions: {
            features: {
                hover: true,
                semanticTokens: true,
                completion: true,
                codeAction: true,
                documentSymbol: true,
                definition: true,
                formatting: true,
            },
        },
        middleware: {},
    };

    client = new LanguageClient(
        "strling",
        "STRling Language Server",
        serverOptions,
        clientOptions,
    );

    context.subscriptions.push({ dispose: () => client?.stop() });
    client.start();
}

export function deactivate(): Thenable<void> | undefined {
    return client?.stop();
}
