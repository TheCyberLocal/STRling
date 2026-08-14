import fs from "node:fs";
import path from "node:path";

import {
    CliSimplyPreviewTransport,
    SIMPLY_PREVIEW_LEGACY_PROTOCOL_VERSION,
    SIMPLY_PREVIEW_PROTOCOL_VERSION,
    SimplyBuilderRequest,
    SimplyCharacterSetMember,
    SimplyCompileProjection,
    SimplyPreviewBuilder,
    SimplyPreviewError,
    SimplyPreviewTransportError,
    serializeSimplyBuilderRequest,
} from "../../src/STRling/simply/preview.js";
import * as canonicalStdlib from "../../src/STRling/simply/stdlib.generated.js";

const REPOSITORY = path.resolve(__dirname, "../../../..");
const ROOT_CLI = path.join(REPOSITORY, "strling");
const KERNEL_COMMAND =
    process.platform === "win32"
        ? path.join(process.env.USERPROFILE!, ".cargo", "bin", "cargo.exe")
        : ROOT_CLI;
const KERNEL_ARGUMENTS =
    process.platform === "win32"
        ? [
              "run",
              "--quiet",
              "--manifest-path",
              path.join(REPOSITORY, "core", "Cargo.toml"),
              "--bin",
              "strling-kernel",
              "--",
              "--simply",
          ]
        : ["simply"];
const POSITIVE = JSON.parse(
    fs.readFileSync(
        path.join(
            REPOSITORY,
            "spec/frontends/simply/1.0/fixtures/positive.json",
        ),
        "utf8",
    ),
);
const STDLIB_POSITIVE = JSON.parse(
    fs.readFileSync(
        path.join(
            REPOSITORY,
            "spec/frontends/simply/1.1/fixtures/positive.json",
        ),
        "utf8",
    ),
);
const CONVERGENCE = JSON.parse(
    fs.readFileSync(
        path.join(REPOSITORY, "tests/convergence/frontend-convergence.json"),
        "utf8",
    ),
);

const PROJECTION: SimplyCompileProjection = {
    requested_outputs: ["semantic", "analysis"],
    compiler_options: {
        partial_semantics: "forbid",
        diagnostic_policy: { minimum_severity: "warning" },
    },
};

function rebuildFixture(request: SimplyBuilderRequest): SimplyBuilderRequest {
    const builder = new SimplyPreviewBuilder(
        request.identity_namespace,
        request.specification_version,
        request.semantic_options,
        request.protocol_version,
    );
    const values = new Map<string, ReturnType<typeof builder.literal>>();
    for (const step of request.steps) {
        const args = step.arguments as Record<string, any>;
        const value = (() => {
            switch (step.operation) {
                case "empty":
                    return builder.empty(step.step_id);
                case "literal":
                    return builder.literal(step.step_id, args.text);
                case "wildcard":
                    return builder.wildcard(
                        step.step_id,
                        args.line_terminators,
                    );
                case "character_set":
                    return builder.characterSet(
                        step.step_id,
                        args.members as SimplyCharacterSetMember[],
                        args.negated,
                    );
                case "sequence":
                    return builder.sequence(
                        step.step_id,
                        args.values.map((id: string) => values.get(id)!),
                    );
                case "alternation":
                    return builder.alternation(
                        step.step_id,
                        args.values.map((id: string) => values.get(id)!),
                    );
                case "group":
                    return builder.group(step.step_id, values.get(args.value)!);
                case "capture":
                    return builder.capture(
                        step.step_id,
                        args.capture_key,
                        values.get(args.value)!,
                        args.name,
                    );
                case "backreference":
                    return builder.backreference(
                        step.step_id,
                        args.capture_key,
                    );
                case "position":
                    return builder.position(step.step_id, args.position);
                case "lookaround":
                    return builder.lookaround(
                        step.step_id,
                        args.direction,
                        args.polarity,
                        values.get(args.value)!,
                    );
                case "atomic":
                    return builder.atomic(
                        step.step_id,
                        values.get(args.value)!,
                    );
                case "repeat":
                    return builder.repeat(
                        step.step_id,
                        values.get(args.value)!,
                        args.min,
                        args.max,
                        args.mode,
                    );
                case "import_node":
                    return builder.importNode(
                        step.step_id,
                        args.node,
                        args.sources,
                    );
                case "import_program":
                    return builder.importProgram(step.step_id, args.program);
                case "stdlib_helper":
                    return builder.stdlibHelper(
                        step.step_id,
                        args.helper_id,
                        args.parameters,
                    );
                default:
                    throw new Error(
                        `unknown fixture operation ${step.operation}`,
                    );
            }
        })();
        values.set(step.step_id, value);
    }
    return builder.buildRequest(
        values.get(request.root_step_id)!,
        request.compile,
    );
}

function convergenceRequest(
    testCase: Record<string, any>,
): SimplyBuilderRequest {
    return {
        protocol_version: "1.0.0",
        contract_version: "1.0.0",
        specification_version: "1.0-draft.1",
        identity_namespace: testCase.identity_namespace,
        semantic_options: testCase.semantic_options,
        steps: testCase.steps,
        root_step_id: testCase.root_step_id,
        compile: {
            target_profile: CONVERGENCE.target_profiles[0].reference,
            requested_outputs: CONVERGENCE.comparison_outputs,
            compiler_options: CONVERGENCE.compiler_options,
        },
    } as SimplyBuilderRequest;
}

describe("Simply Preview adapter", () => {
    test("serializes the authored basic case exactly and compiles through Rust", () => {
        const builder = new SimplyPreviewBuilder(
            "basic",
            undefined,
            undefined,
            SIMPLY_PREVIEW_LEGACY_PROTOCOL_VERSION,
        );
        const literal = builder.literal("literal", "a.b");
        const emptyText = builder.literal("empty-text", "");
        const empty = builder.empty("empty");
        const grouped = builder.group("grouped", literal);
        const root = builder.sequence("root", [grouped, emptyText, empty]);
        const request = builder.buildRequest(root, PROJECTION);
        const expected = POSITIVE.cases[0];

        expect(request).toEqual(expected.request);
        expect(JSON.parse(serializeSimplyBuilderRequest(request))).toEqual(
            expected.request,
        );

        const response = builder.compile(
            root,
            PROJECTION,
            new CliSimplyPreviewTransport(KERNEL_COMMAND, KERNEL_ARGUMENTS),
        );
        expect(response.compile_request).toEqual(
            expected.expected.compile_request,
        );
        expect(response.compile_result.outcome).toBe("succeeded");
    });

    test("reproduces all nine authored cross-language requests exactly", () => {
        for (const fixture of POSITIVE.cases) {
            expect(
                rebuildFixture(fixture.request as SimplyBuilderRequest),
            ).toEqual(fixture.request);
        }
    });

    test("generated stdlib wrappers record all variants and compile in Rust", () => {
        const transport = new CliSimplyPreviewTransport(
            KERNEL_COMMAND,
            KERNEL_ARGUMENTS,
        );
        for (const fixture of STDLIB_POSITIVE.cases) {
            const request = fixture.request as SimplyBuilderRequest;
            const step = request.steps[0];
            const args = step.arguments as Record<string, any>;
            const builder = new SimplyPreviewBuilder(
                request.identity_namespace,
            );
            const value = (() => {
                switch (args.helper_id) {
                    case "stdlib.date_time":
                        return canonicalStdlib.dateTime(builder, step.step_id);
                    case "stdlib.email":
                        return canonicalStdlib.email(builder, step.step_id);
                    case "stdlib.ip":
                        return canonicalStdlib.ip(
                            builder,
                            step.step_id,
                            args.parameters.version,
                        );
                    case "stdlib.url":
                        return canonicalStdlib.url(builder, step.step_id);
                    case "stdlib.uuid":
                        return canonicalStdlib.uuid(
                            builder,
                            step.step_id,
                            args.parameters.version,
                        );
                    default:
                        throw new Error(`unknown helper ${args.helper_id}`);
                }
            })();
            const actual = builder.buildRequest(value, request.compile);
            expect(actual).toEqual(request);
            const response = transport.execute(actual);
            expect(response.status).toBe("success");
            expect(response.protocol_version).toBe(
                SIMPLY_PREVIEW_PROTOCOL_VERSION,
            );
        }
    });

    test("legacy builders reject the 1.1-only helper operation", () => {
        const builder = new SimplyPreviewBuilder(
            "legacy",
            undefined,
            undefined,
            SIMPLY_PREVIEW_LEGACY_PROTOCOL_VERSION,
        );
        expect(() => builder.stdlibHelper("root", "stdlib.email")).toThrow(
            SimplyPreviewTransportError,
        );
    });

    test("reproduces every convergence request and compiles through Rust", () => {
        const transport = new CliSimplyPreviewTransport(
            KERNEL_COMMAND,
            KERNEL_ARGUMENTS,
            path.join(REPOSITORY, CONVERGENCE.target_profiles[0].path),
        );
        for (const testCase of CONVERGENCE.cases) {
            const request = convergenceRequest(testCase);
            expect(rebuildFixture(request)).toEqual(request);
            const response = transport.execute(request);
            expect(response.status).toBe("success");
            if (response.status === "success") {
                const compileRequest = response.compile_request as Record<
                    string,
                    any
                >;
                const compileResult = response.compile_result as Record<
                    string,
                    any
                >;
                expect(compileRequest.input.kind).toBe("semantic");
                expect(compileResult.semantic_result.status).toBe("complete");
            }
        }
    });

    test("passes exact target-profile evidence through the transport only", () => {
        const fixture = POSITIVE.cases[POSITIVE.cases.length - 1];
        const request = rebuildFixture(fixture.request as SimplyBuilderRequest);
        const response = new CliSimplyPreviewTransport(
            KERNEL_COMMAND,
            KERNEL_ARGUMENTS,
            path.join(REPOSITORY, "spec/targets/profiles/pcre2-10.43.json"),
        ).execute(request);
        expect(response.status).toBe("success");
        if (response.status === "success") {
            expect(response.compile_request).toEqual(
                fixture.expected.compile_request,
            );
            expect(response.compile_result.outcome).toBe("failed");
            expect(response.compile_result.artifact).toBeUndefined();
            expect(response.compile_result.diagnostics).toEqual([
                expect.objectContaining({
                    code: "STRL-PROTOCOL-0005",
                    phase: "target_lowering",
                }),
            ]);
        }
    });

    test("records the complete closed operation inventory without caller aliasing", () => {
        const builder = new SimplyPreviewBuilder("inventory");
        const members = [{ kind: "literal" as const, value: "x" }];
        const empty = builder.empty("empty");
        const literal = builder.literal("literal", "x");
        const wildcard = builder.wildcard("wildcard", "include");
        const characterSet = builder.characterSet("set", members);
        members[0] = { kind: "literal", value: "y" };
        const sequence = builder.sequence("sequence", [empty, literal]);
        const alternation = builder.alternation("alternation", [
            wildcard,
            characterSet,
        ]);
        const grouped = builder.group("group", sequence);
        const capture = builder.capture("capture", "logical", grouped, "name");
        const reference = builder.backreference("reference", "logical");
        const position = builder.position("position", "input_start");
        const lookaround = builder.lookaround(
            "lookaround",
            "ahead",
            "positive",
            alternation,
        );
        const atomic = builder.atomic("atomic", lookaround);
        const repeated = builder.repeat("repeat", atomic, 1, null, "lazy");
        const importedNode = builder.importNode("import-node", {
            node_id: "node:imported",
            kind: "literal",
            text: "n",
        });
        const importedProgram = builder.importProgram("import-program", {
            contract_version: "1.0.0",
            specification_version: "1.0-draft.1",
            normalization: "canonical-v1",
            case_matching: "sensitive",
            root: {
                node_id: "node:program",
                kind: "literal",
                text: "p",
            },
        });
        const root = builder.sequence("root", [
            capture,
            reference,
            position,
            repeated,
            importedNode,
            importedProgram,
        ]);
        const request = builder.buildRequest(root, PROJECTION);

        expect(request.steps.map((step) => step.operation)).toEqual([
            "empty",
            "literal",
            "wildcard",
            "character_set",
            "sequence",
            "alternation",
            "group",
            "capture",
            "backreference",
            "position",
            "lookaround",
            "atomic",
            "repeat",
            "import_node",
            "import_program",
            "sequence",
        ]);
        expect(
            (request.steps[3].arguments.members as Array<{ value: string }>)[0]
                .value,
        ).toBe("x");
    });

    test("translates canonical construction failures without replacing identities", () => {
        const builder = new SimplyPreviewBuilder("duplicate");
        builder.literal("same", "a");
        const root = builder.literal("same", "b");

        try {
            builder.compile(
                root,
                {
                    requested_outputs: ["semantic"],
                    compiler_options: PROJECTION.compiler_options,
                },
                new CliSimplyPreviewTransport(KERNEL_COMMAND, KERNEL_ARGUMENTS),
            );
            throw new Error("expected SimplyPreviewError");
        } catch (error) {
            expect(error).toBeInstanceOf(SimplyPreviewError);
            expect((error as SimplyPreviewError).errors).toEqual([
                {
                    code: "STRL-SIMPLY-0003",
                    path: "$.steps[1].step_id",
                },
            ]);
        }
    });

    test("rejects foreign handles and requires explicit transport commands", () => {
        const first = new SimplyPreviewBuilder("first");
        const second = new SimplyPreviewBuilder("second");
        const foreign = first.literal("foreign", "x");
        expect(() => second.group("bad", foreign)).toThrow(
            SimplyPreviewTransportError,
        );
        expect(() => new CliSimplyPreviewTransport("")).toThrow(
            SimplyPreviewTransportError,
        );
    });
});
