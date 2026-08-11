export const PROTOCOL_VERSION = "1.0.0";
export const OBSERVATION_SCHEMA_VERSION = "1.0.0";
export const REQUEST_KIND = "strling.legacy-reference-request";
export const OBSERVATION_KIND = "strling.legacy-reference-observation";
export const PROTOCOL_FAILURE_KIND =
    "strling.legacy-reference-protocol-failure";

export const OPERATION_SPECS = Object.freeze({
    "parser.parse": Object.freeze({
        surface: "typescript.core.parser.parse",
        input: "source",
        stage: "parser",
        options: Object.freeze([]),
    }),
    "parser.parse_to_artifact": Object.freeze({
        surface: "typescript.core.parser.parseToArtifact",
        input: "source",
        stage: "parser",
        options: Object.freeze([]),
    }),
    "compiler.compile": Object.freeze({
        surface: "typescript.core.Compiler.compile",
        input: "source",
        stage: "compiler",
        options: Object.freeze([]),
    }),
    "compiler.compile_with_metadata": Object.freeze({
        surface: "typescript.core.Compiler.compileWithMetadata",
        input: "source",
        stage: "compiler",
        options: Object.freeze([]),
    }),
    "emitter.pcre2.emit": Object.freeze({
        surface: "typescript.emitters.pcre2.emit",
        input: "source",
        stage: "emitter",
        options: Object.freeze(["max_depth"]),
    }),
    "emitter.pcre2.emit_with_diagnostics": Object.freeze({
        surface: "typescript.emitters.pcre2.emitWithDiagnostics",
        input: "source",
        stage: "emitter",
        options: Object.freeze(["max_depth"]),
    }),
    "api.root.parse": Object.freeze({
        surface: "typescript.package-root.parse",
        input: "source",
        stage: "public_api",
        options: Object.freeze([]),
    }),
    "api.root.parse_to_artifact": Object.freeze({
        surface: "typescript.package-root.parseToArtifact",
        input: "source",
        stage: "public_api",
        options: Object.freeze([]),
    }),
    "api.simply.literal_to_string": Object.freeze({
        surface: "typescript.simply.Pattern.toString",
        input: "literal",
        stage: "public_api",
        options: Object.freeze([]),
    }),
    "api.simply.compile_node": Object.freeze({
        surface: "typescript.simply.compileNode",
        input: "literal",
        stage: "public_api",
        options: Object.freeze(["flags", "target"]),
    }),
    "api.simply.to_regexp": Object.freeze({
        surface: "typescript.simply.toRegExp",
        input: "literal",
        stage: "public_api",
        options: Object.freeze(["flags", "target"]),
    }),
});

export const OPERATION_IDS = Object.freeze(Object.keys(OPERATION_SPECS));
