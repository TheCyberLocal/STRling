/** Black-box smoke tests for the canonical Rust CLI transport. */

import { spawnSync, SpawnSyncOptions } from "child_process";
import fs from "fs";
import os from "os";
import path from "path";

const TEST_DIR = __dirname;
const PROJECT_ROOT = path.resolve(TEST_DIR, "..", "..", "..", "..");
const KERNEL_MANIFEST = path.join(PROJECT_ROOT, "core", "Cargo.toml");
const PCRE2_PROFILE = "pcre2-10.43";
const VALID_REGEX = "a(?<b>c)";
const CONVENTIONAL_CARGO = path.join(
    os.homedir(),
    ".cargo",
    "bin",
    process.platform === "win32" ? "cargo.exe" : "cargo",
);
const CARGO =
    process.env.CARGO ||
    (fs.existsSync(CONVENTIONAL_CARGO) ? CONVENTIONAL_CARGO : "cargo");
const TEMP_ROOT = path.join(PROJECT_ROOT, "core", "target");

interface CliResult {
    code: number | null;
    stdout: string;
    stderr: string;
}

function runCli(arguments_: string[], stdin?: string): CliResult {
    const options: SpawnSyncOptions = {
        cwd: PROJECT_ROOT,
        encoding: "utf-8",
        input: stdin,
        stdio: ["pipe", "pipe", "pipe"],
    };
    const result = spawnSync(
        CARGO,
        [
            "run",
            "--quiet",
            "--manifest-path",
            KERNEL_MANIFEST,
            "--bin",
            "strling-kernel",
            "--",
            ...arguments_,
        ],
        options,
    );
    if (result.error) {
        throw result.error;
    }
    return {
        code: result.status,
        stdout: (result.stdout as string) ?? "",
        stderr: (result.stderr as string) ?? "",
    };
}

let cliDirectory: string;

beforeAll(() => {
    fs.mkdirSync(TEMP_ROOT, { recursive: true });
    cliDirectory = fs.mkdtempSync(
        path.join(TEMP_ROOT, "typescript-cli-smoke-"),
    );
});

afterAll(() => {
    fs.rmSync(cliDirectory, { recursive: true, force: true });
});

test("file import emits a canonical target artifact", () => {
    const source = path.join(cliDirectory, "valid-file.regex");
    fs.writeFileSync(source, VALID_REGEX, "utf-8");

    const result = runCli([
        "import",
        "--input",
        source,
        "--target",
        PCRE2_PROFILE,
        "--output",
        "target_artifact",
        "--format",
        "json",
    ]);

    expect(result.code).toBe(0);
    expect(result.stderr).toBe("");
    const response = JSON.parse(result.stdout);
    expect(response.contract_version).toBe("1.0.0");
    expect(response.outcome).toBe("succeeded");
    expect(response.artifact.pattern.text).toBe(VALID_REGEX);
    expect(response.semantic_result.program.sources[0].provenance).toEqual({
        kind: "imported",
    });
});

test("stdin import emits the same target artifact", () => {
    const result = runCli(
        [
            "import",
            "--input",
            "-",
            "--target",
            PCRE2_PROFILE,
            "--output",
            "target_artifact",
            "--format",
            "json",
        ],
        VALID_REGEX,
    );

    expect(result.code).toBe(0);
    expect(result.stderr).toBe("");
    expect(JSON.parse(result.stdout).artifact.pattern.text).toBe(VALID_REGEX);
});

test("check returns a canonical CompileResult", () => {
    const source = path.join(cliDirectory, "valid-check.regex");
    fs.writeFileSync(source, VALID_REGEX, "utf-8");

    const result = runCli([
        "check",
        "--input",
        source,
        "--frontend",
        "regex",
        "--format",
        "json",
    ]);

    expect(result.code).toBe(0);
    expect(result.stderr).toBe("");
    const response = JSON.parse(result.stdout);
    expect(response.outcome).toBe("succeeded");
    expect(response.diagnostics).toEqual([]);
});

test("parse failure is structured and exits two", () => {
    const source = path.join(cliDirectory, "invalid.regex");
    fs.writeFileSync(source, "a(b", "utf-8");

    const result = runCli(["import", "--input", source, "--format", "json"]);

    expect(result.code).toBe(2);
    expect(result.stderr).toBe("");
    const response = JSON.parse(result.stdout);
    expect(response.outcome).toBe("failed");
    expect(response.diagnostics[0].code).toBe("STRL-FRONTEND-2012");
});

test("retired schema flag is rejected explicitly", () => {
    const source = path.join(cliDirectory, "retired-schema.regex");
    fs.writeFileSync(source, VALID_REGEX, "utf-8");

    const result = runCli([
        "import",
        "--input",
        source,
        "--schema",
        "legacy.schema.json",
    ]);

    expect(result.code).toBe(64);
    expect(result.stdout).toBe("");
    expect(result.stderr).toContain("--schema is retired");
});

test("missing file uses the stable I/O exit", () => {
    const missing = path.join(cliDirectory, "does-not-exist.regex");

    const result = runCli(["import", "--input", missing]);

    expect(result.code).toBe(74);
    expect(result.stdout).toBe("");
    expect(result.stderr).toContain("cannot open source input");
});
