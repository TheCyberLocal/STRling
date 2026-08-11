import path from "node:path";
import { pathToFileURL } from "node:url";

import { OPERATION_SPECS } from "./constants.mjs";
import { legacySurfaceFailure, ProtocolError } from "./protocol.mjs";

export const PARSER_API_OPERATION_IDS = Object.freeze([
    "parser.parse",
    "parser.parse_to_artifact",
    "api.root.parse",
    "api.root.parse_to_artifact",
    "api.simply.literal_to_string",
    "api.simply.compile_node",
    "api.simply.to_regexp",
]);

async function loadModule(distRoot, relative) {
    const absolute = path.join(distRoot, ...relative.split("/"));
    return import(pathToFileURL(absolute).href);
}

function parseProjection(parse, source) {
    const [flags, root] = parse(source);
    return {
        flags: flags.toDict(),
        return_shape: "tuple",
        root: root.toDict(),
    };
}

function simplyPattern(rootModule, literal) {
    return rootModule.simply.lit(literal);
}

function simplyOptions(options) {
    const result = {};
    if (Object.hasOwn(options, "flags")) result.flags = options.flags;
    return result;
}

export async function createLegacyInvoker(distRoot) {
    let parserModule;
    let rootModule;
    try {
        [parserModule, rootModule] = await Promise.all([
            loadModule(distRoot, "STRling/core/parser.js"),
            loadModule(distRoot, "index.js"),
        ]);
    } catch {
        throw new ProtocolError(
            "LEGACY_LOAD_FAILURE",
            "could not load governed legacy TypeScript modules",
        );
    }

    return async function invokeLegacy(request) {
        const { input, operation, options } = request;
        if (!PARSER_API_OPERATION_IDS.includes(operation)) {
            throw new ProtocolError(
                "OPERATION_NOT_AVAILABLE",
                `operation '${operation}' is not available in this runner checkpoint`,
            );
        }

        if (operation === "parser.parse") {
            return parseProjection(parserModule.parse, input.source);
        }
        if (operation === "parser.parse_to_artifact") {
            return {
                artifact: parserModule.parseToArtifact(input.source),
                return_shape: "object",
            };
        }
        if (operation === "api.root.parse") {
            return parseProjection(rootModule.parse, input.source);
        }
        if (operation === "api.root.parse_to_artifact") {
            return {
                artifact: rootModule.parseToArtifact(input.source),
                return_shape: "object",
            };
        }

        const pattern = simplyPattern(rootModule, input.literal);
        if (operation === "api.simply.literal_to_string") {
            return {
                emitted_pattern: pattern.toString(),
                named_groups: [...pattern.namedGroups],
                node: pattern.node.toDict(),
                return_shape: "string",
            };
        }
        if (operation === "api.simply.compile_node") {
            const target = options.target ?? "pcre2";
            try {
                return {
                    emitted_pattern: rootModule.simply.compileNode(
                        pattern,
                        target,
                        simplyOptions(options),
                    ),
                    return_shape: "string",
                    target,
                };
            } catch (error) {
                throw legacySurfaceFailure("public_api", error);
            }
        }
        if (operation === "api.simply.to_regexp") {
            const flags =
                typeof options.flags === "string" ? options.flags : "";
            const regexpOptions = {};
            if (Object.hasOwn(options, "target")) {
                regexpOptions.target = options.target;
            }
            try {
                const regexp = rootModule.simply.toRegExp(
                    pattern,
                    flags,
                    regexpOptions,
                );
                return {
                    flags: regexp.flags,
                    return_shape: "RegExp",
                    source: regexp.source,
                    string: regexp.toString(),
                };
            } catch (error) {
                throw legacySurfaceFailure("public_api", error);
            }
        }

        throw new ProtocolError(
            "OPERATION_NOT_AVAILABLE",
            `operation '${operation}' has no legacy invocation`,
        );
    };
}

export function expectedSurface(operation) {
    return OPERATION_SPECS[operation]?.surface;
}
