const fs = require('fs');
const path = require('path');

const testsDir = path.join(__dirname, "../../bindings/javascript/__tests__");
const outDir = path.join(__dirname, "fixtures");

const files = [];
function walk(dir) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const e of entries) {
        const full = path.join(dir, e.name);
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
        return s
            .slice(1, -1)
            .replace(/\\n/g, "\n")
            .replace(/\\r/g, "\r")
            .replace(/\\t/g, "\t");
    }
    if (s.startsWith("String.raw`") && s.endsWith("`")) {
        return s.slice("String.raw`".length, -1);
    }
    if (s.startsWith("`") && s.endsWith("`")) return s.slice(1, -1);
    return s;
}

if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

let count = 0;
for (const f of files) {
    const content = fs.readFileSync(f, "utf8");
    const regex =
        /parse\(\s*(String.raw`[\s\S]*?`|`[\s\S]*?`|"(?:\\.|[^\\"])*"|'(?:\\.|[^\\'])*')\s*\)/g;
    let match;
    while ((match = regex.exec(content)) !== null) {
        const raw = match[1];
        const pattern = unquote(raw);
        if (!pattern) continue;
        const name = "js_test_" + path.basename(f).replace(
            /[^a-zA-Z0-9_\.]/g,
            "_"
        ) + "_" + (++count) + ".pattern";
        const outPath = path.join(outDir, name);
        fs.writeFileSync(outPath, pattern + "\n", "utf8");
    }
}
console.log("Extracted " + count + " patterns from JS tests into " + outDir);
