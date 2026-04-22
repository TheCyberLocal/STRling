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
import { ExtensionContext, workspace } from "vscode";
import {
    LanguageClient,
    LanguageClientOptions,
    ServerOptions,
    TransportKind,
} from "vscode-languageclient/node";

let client: LanguageClient | undefined;

export function activate(context: ExtensionContext): void {
    const config = workspace.getConfiguration("strling");

    const command = config.get<string>("languageServer.command", "python");
    const configuredArgs = config.get<string[]>("languageServer.args", []);
    const args = configuredArgs.length
        ? configuredArgs
        : [
              // Default: launch the bundled server that ships inside the
              // extension package. Advanced users can still override this with
              // `strling.languageServer.args`.
              context.asAbsolutePath(path.join("server", "server.py")),
              "--stdio",
          ];

    const serverOptions: ServerOptions = {
        run: { command, args, transport: TransportKind.stdio },
        debug: { command, args, transport: TransportKind.stdio },
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
        // Phase 1.1 handshake: explicitly opt-in to ambient-intelligence
        // features so the language server knows the client supports them.
        // `vscode-languageclient` auto-registers the matching providers
        // (hover, semanticTokens/full) once the server advertises the
        // capabilities in its initialize response — these flags are what
        // we surface to the server via `initializationOptions` so it can
        // choose whether to pay the compile/tokenise cost.
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
        // Important: do NOT contribute syntax highlighting for host languages —
        // the host LSPs remain authoritative. The client registers the
        // Semantic Token Provider returned by the server and overlays its
        // tokens on top of the host's existing colouring.
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
