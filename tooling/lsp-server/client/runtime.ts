import * as path from "path";

export interface ResolvedCommand {
    command: string;
    prefixArgs: string[];
}

export interface BundledRuntime {
    serverPath: string;
    vendorPath: string;
    environment: Record<string, string>;
}

export type PythonProbe = (command: string, args: string[]) => boolean;

export const missingPythonError =
    "STRling requires Python 3.11 or newer to start its bundled language server. " +
    "Configure strling.languageServer.command or install Python.";

export const documentSelectors = [
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
] as const;

export function pythonCandidates(platform: NodeJS.Platform): ResolvedCommand[] {
    return platform === "win32"
        ? [
              { command: "python", prefixArgs: [] },
              { command: "py", prefixArgs: ["-3"] },
          ]
        : [
              { command: "python3", prefixArgs: [] },
              { command: "python", prefixArgs: [] },
          ];
}

export function resolveLanguageServerCommand(
    configuredCommand: string,
    platform: NodeJS.Platform,
    probe: PythonProbe,
): ResolvedCommand | undefined {
    if (configuredCommand.trim().length > 0) {
        return { command: configuredCommand, prefixArgs: [] };
    }
    return pythonCandidates(platform).find((candidate) =>
        probe(candidate.command, candidate.prefixArgs),
    );
}

export function bundledRuntime(
    extensionRoot: string,
    platform: NodeJS.Platform,
    inheritedPythonPath?: string,
): BundledRuntime {
    const executableSuffix = platform === "win32" ? ".exe" : "";
    const serverPath = path.join(extensionRoot, "server", "server.py");
    const vendorPath = path.join(extensionRoot, "server", "libs");
    return {
        serverPath,
        vendorPath,
        environment: {
            PYTHONPATH: inheritedPythonPath
                ? [vendorPath, inheritedPythonPath].join(path.delimiter)
                : vendorPath,
            STRLING_KERNEL: path.join(
                extensionRoot,
                "server",
                "bin",
                `strling-kernel${executableSuffix}`,
            ),
            STRLING_EDITOR_CORE: path.join(
                extensionRoot,
                "server",
                "bin",
                `strling-editor-core${executableSuffix}`,
            ),
            STRLING_SIMPLY_PROTOCOL_PATH: path.join(
                extensionRoot,
                "server",
                "resources",
                "simply-protocol.json",
            ),
            STRLING_STDLIB_REGISTRY_PATH: path.join(
                extensionRoot,
                "server",
                "resources",
                "stdlib-registry.json",
            ),
            STRLING_ISLAND_BOUNDARIES_PATH: path.join(
                extensionRoot,
                "server",
                "resources",
                "island-boundaries.json",
            ),
        },
    };
}
