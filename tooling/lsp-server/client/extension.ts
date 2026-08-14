/**
 * STRling VS Code reference client.
 *
 * The client launches the bundled Python LSP transport over stdio and binds it
 * to the two packaged canonical Rust processes. Host language services retain
 * ownership of their own syntax highlighting and language semantics.
 */

import { spawnSync } from "child_process";
import { ExtensionContext, window, workspace } from "vscode";
import {
    ExecutableOptions,
    LanguageClient,
    LanguageClientOptions,
    ServerOptions,
    TransportKind,
} from "vscode-languageclient/node";
import {
    bundledRuntime,
    documentSelectors,
    missingPythonError,
    resolveLanguageServerCommand,
} from "./runtime";

let client: LanguageClient | undefined;

function pythonProbe(command: string, prefixArgs: string[]): boolean {
    const probe = spawnSync(
        command,
        [
            ...prefixArgs,
            "-c",
            "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)",
        ],
        { encoding: "utf8" },
    );
    return !probe.error && probe.status === 0;
}

export function activate(context: ExtensionContext): void {
    const config = workspace.getConfiguration("strling");
    const extensionRoot = context.extensionPath;
    const runtime = bundledRuntime(
        extensionRoot,
        process.platform,
        process.env.PYTHONPATH,
    );

    const configuredCommand = config.get<string>("languageServer.command", "");
    const resolvedCommand = resolveLanguageServerCommand(
        configuredCommand,
        process.platform,
        pythonProbe,
    );
    if (!resolvedCommand) {
        void window.showErrorMessage(missingPythonError);
        return;
    }
    const configuredArgs = config.get<string[]>("languageServer.args", []);
    const args = [
        ...resolvedCommand.prefixArgs,
        ...(configuredArgs.length
            ? configuredArgs
            : [runtime.serverPath, "--stdio"]),
    ];

    const executableOptions: ExecutableOptions = {
        cwd: extensionRoot,
        env: {
            ...process.env,
            ...runtime.environment,
        },
    };

    const serverOptions: ServerOptions = {
        run: {
            command: resolvedCommand.command,
            args,
            options: executableOptions,
            transport: TransportKind.stdio,
        },
        debug: {
            command: resolvedCommand.command,
            args,
            options: executableOptions,
            transport: TransportKind.stdio,
        },
    };

    const clientOptions: LanguageClientOptions = {
        documentSelector: documentSelectors.map((language) => ({
            scheme: "file",
            language,
        })),
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
                references: true,
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
