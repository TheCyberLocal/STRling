#!/usr/bin/env node
const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const repoRoot = path.resolve(__dirname, "../..");
const outDir = path.join(__dirname, "out");
const inspectCompilePath = path.join(__dirname, "inspect_compile");

function buildHelper() {
    // Build the inspect helper binary in this folder
    const gccArgs = [
        "-I",
        path.join(repoRoot, "bindings/c/include"),
        "-I",
        path.join(repoRoot, "bindings/c/src"),
        path.join(__dirname, "inspect_compile.c"),
        path.join(repoRoot, "bindings/c/libstrling.a"),
        "-o",
        inspectCompilePath,
        "-ljansson",
    ];
    const r = spawnSync("gcc", gccArgs, { stdio: "inherit" });
    if (r.status !== 0)
        throw new Error("Failed to build inspect_compile helper");
}

function runCCompile(jsonPath) {
    const r = spawnSync(inspectCompilePath, [jsonPath]);
    return {
        status: r.status,
        stdout: r.stdout ? r.stdout.toString() : "",
        stderr: r.stderr ? r.stderr.toString() : "",
    };
}

function runVerification() {
    if (!fs.existsSync(outDir)) {
        console.error("No out dir:", outDir);
        process.exit(1);
    }
    const files = fs.readdirSync(outDir).filter((f) => f.endsWith(".json"));
    if (files.length === 0) {
        console.error("No JSON artifacts found in", outDir);
        process.exit(1);
    }
    try {
        buildHelper();
    } catch (e) {
        console.error(e.message);
        process.exit(2);
    }

    const mismatches = [];
    for (const f of files) {
        const jsonPath = path.join(outDir, f);
        const content = JSON.parse(fs.readFileSync(jsonPath, "utf8"));
        let jsPcre = null;
        if (
            content.expected &&
            content.expected.success &&
            content.expected.pcre
        ) {
            jsPcre = content.expected.pcre;
        }
        const cres = runCCompile(jsonPath);
        let cPcre = null;
        let cError = null;
        if (cres.stdout) {
            const out = cres.stdout.toString().trim();
            if (out.startsWith("SUCCESS:"))
                cPcre = out.slice("SUCCESS:".length).trim();
            else if (out.startsWith("ERROR:"))
                cError = out.slice("ERROR:".length).trim();
        }
        // Normalize patterns for fair comparison (JS expected often includes actual newlines, C returns escaped `\\n`) -> stringify newline as `\\n`
        function stripSurroundingParens(s) {
            if (!s) return s;
            s = s.trim();
            while (s.length > 1 && s[0] === "(" && s[s.length - 1] === ")") {
                // Verify parentheses match at top level
                let depth = 0;
                let matched = true;
                for (let i = 0; i < s.length; i++) {
                    if (s[i] === "(") depth++;
                    else if (s[i] === ")") depth--;
                    if (depth === 0 && i < s.length - 1) {
                        matched = false;
                        break;
                    }
                }
                if (matched) s = s.slice(1, -1).trim();
                else break;
            }
            return s;
        }

        function normalizePattern(s) {
            if (!s) return s;
            // Replace actual newline chars with escaped \n for canonical representation
            s = s.replace(/\r/g, "").replace(/\n/g, "\\n");
            s = stripSurroundingParens(s);

            // Reduce escaped hyphen inside char classes (\- -> -) for equivalence
            s = s.replace(/\\\-/g, "-");

            // Remove redundant parentheses wrapping alternations inside lookarounds: (?=(a|b)) -> (?=a|b)
            s = s.replace(/\(\?=\(([^()]+)\)\)/g, "(?=$1)");
            s = s.replace(/\(\?<=\(([^()]+)\)\)/g, "(?<=$1)");
            s = s.replace(/\(\?\!\(([^()]+)\)\)/g, "(?!$1)");
            s = s.replace(/\(\?<\!\(([^()]+)\)\)/g, "(?<!$1)");

            // Convert common single-element character classes like [\d] -> \d
            s = s.replace(/\[\\([dws])\]/g, "\\$1");

            // Convert single-element character classes that wrap Unicode property escapes: [\P{L}] -> \P{L}
            s = s.replace(/\[\\P\{([^}]+)\}\]/g, "\\P{$1}");
            s = s.replace(/\[\\p\{([^}]+)\}\]/g, "\\p{$1}");
            // Convert negated forms [^\p{L}] -> \P{L}, [^\P{L}] -> \p{L}
            s = s.replace(/\[\^\\p\{([^}]+)\}\]/g, "\\P{$1}");
            s = s.replace(/\[\^\\P\{([^}]+)\}\]/g, "\\p{$1}");

            // Normalize NUL and zero hex escapes to PCRE2 canonical \x{0}
            s = s.replace(/\\x00/g, "\\x{0}");
            s = s.replace(/\\x\{0+\}/g, "\\x{0}");

            // Replace {1} quantifier with empty (equivalent) to match JS simplification
            s = s.replace(/\{1\}/g, "");

            // Collapse double parentheses ((X)) -> (X), repeated until stable
            while (/\(\(.*?\)\)/.test(s)) {
                s = s.replace(/\(\((.*?)\)\)/g, "($1)");
            }

            // Convert explicit non-ascii characters in JS patterns into \x{hex} form
            // We'll translate any non-ASCII printable characters to hex so they match C emitter's \x{...}
            s = s.replace(/[\u0080-\uFFFF]/g, (ch) => {
                const code = ch.codePointAt(0).toString(16);
                return `\\x{${code}}`;
            });

            return s;
        }

        // Compare
        const record = {
            file: f,
            js: jsPcre,
            c: { pattern: cPcre, error: cError },
        };
        if (jsPcre && cPcre) {
            if (normalizePattern(jsPcre) !== normalizePattern(cPcre)) {
                record.reason = "pattern_mismatch";
                mismatches.push(record);
            }
        } else if (jsPcre && !cPcre) {
            record.reason = "js_success_c_failure";
            mismatches.push(record);
        } else if (!jsPcre && cPcre) {
            record.reason = "c_success_js_failure";
            mismatches.push(record);
        } else if (!jsPcre && !cPcre) {
            // Both failed or no expected: compare error messages as available
            if (content.expected && content.expected.error && cError) {
                // Normalize error strings as well to ignore trailing whitespace
                const expectedErr = (content.expected.error || "").trim();
                if (!cError.includes(expectedErr)) {
                    record.reason = "error_message_mismatch";
                    mismatches.push(record);
                }
            }
        }
    }
    // Write a mismatch report
    const outReport = path.join(outDir, "parity_mismatch_report.json");
    fs.writeFileSync(
        outReport,
        JSON.stringify(
            { mismatches, total: files.length, failed: mismatches.length },
            null,
            2
        )
    );
    console.log(
        `Done. Total artifacts: ${files.length}. Mismatches: ${mismatches.length}. Report: ${outReport}`
    );
}

if (require.main === module) {
    runVerification();
}
