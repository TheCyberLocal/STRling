#!/usr/bin/env node
import {
    readdirSync,
    existsSync,
    mkdirSync,
    readFileSync,
    writeFileSync,
} from "fs";
import { join, basename } from "path";

const testsDir = join(__dirname, "../../bindings/javascript/__tests__");
const outDir = join(__dirname, "fixtures");

const files = [];
function walk(dir) {
    const entries = readdirSync(dir, { withFileTypes: true });
    for (const e of entries) {
        const full = join(dir, e.name);
        if (e.isDirectory()) walk(full);
        else if (
            e.isFile() &&
            (e.name.endsWith(".js") || e.name.endsWith(".ts"))
        )
            files.push(full);
    }
}
walk(testsDir);

function unquote(s) {
    if (!s) return s;
    if (
        (s.startsWith('"') && s.endsWith('"')) ||
        (s.startsWith("'") && s.endsWith("'"))
    ) {
        // remove surrounding quotes and unescape
        return s
            .slice(1, -1)
            .replace(/\\n/g, "\n")
            .replace(/\\r/g, "\r")
            .replace(/\\t/g, "\t");
    }
    // Handle String.raw`...` or template literals
    if (s.startsWith("String.raw`") && s.endsWith("`")) {
        return s.slice("String.raw`".length, -1);
    }
    if (s.startsWith("`") && s.endsWith("`")) return s.slice(1, -1);
    return s;
}

if (!existsSync(outDir)) mkdirSync(outDir, { recursive: true });

let count = 0;
for (const f of files) {
    const content = readFileSync(f, "utf8");
    const regex =
        /parse\(\s*(String.raw`[\s\S]*?`|`[\s\S]*?`|"(?:\\.|[^\\"])*"|'(?:\\.|[^\\'])*')\s*\)/g;
    let match;
    while ((match = regex.exec(content)) !== null) {
        const raw = match[1];
        const pattern = unquote(raw);
        if (!pattern) continue;
        // sanitize filename
        const name = `js_test_${basename(f).replace(
            /[^a-zA-Z0-9_\.]/g,
            "_"
        )}_${++count}.pattern`;
        const outPath = join(outDir, name);
        writeFileSync(outPath, pattern + "\n", "utf8");
        console.log("Wrote", outPath);
    }
}
console.log(`Extracted ${count} patterns from JS tests into ${outDir}`);
