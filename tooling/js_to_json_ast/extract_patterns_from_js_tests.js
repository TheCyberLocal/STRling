#!/usr/bin/env node
const fs = require("fs");
const path = require("path");

const testsDir = path.join(__dirname, "../../bindings/javascript/__tests__");
const outDir = path.join(__dirname, "fixtures");

// Statistics tracking
const stats = {
    literalParse: 0,
    inlineArray: 0,
    variableResolved: 0,
    totalFiles: 0,
};

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
        // remove surrounding quotes and unescape
        return s
            .slice(1, -1)
            .replace(/\\n/g, "\n")
            .replace(/\\r/g, "\r")
            .replace(/\\t/g, "\t")
            .replace(/\\\\/g, "\\");
    }
    // Handle String.raw`...` or template literals
    if (s.startsWith("String.raw`") && s.endsWith("`")) {
        return s.slice("String.raw`".length, -1);
    }
    if (s.startsWith("`") && s.endsWith("`")) return s.slice(1, -1);
    return s;
}

// Match brackets/braces/parens with proper nesting
function findMatchingBracket(str, startIdx, openChar, closeChar) {
    let depth = 1;
    let inString = false;
    let stringChar = null;
    let escaped = false;

    for (let i = startIdx + 1; i < str.length; i++) {
        const char = str[i];

        if (escaped) {
            escaped = false;
            continue;
        }

        if (char === "\\") {
            escaped = true;
            continue;
        }

        if (!inString) {
            if (char === '"' || char === "'" || char === "`") {
                inString = true;
                stringChar = char;
            } else if (char === openChar) {
                depth++;
            } else if (char === closeChar) {
                depth--;
                if (depth === 0) {
                    return i;
                }
            }
        } else {
            if (char === stringChar) {
                inString = false;
                stringChar = null;
            }
        }
    }
    return -1;
}

// Extract patterns from array of arrays format: [["pattern", ...], ...]
function extractFromArrayFormat(arrayContent) {
    const patterns = [];
    let i = 0;
    while (i < arrayContent.length) {
        // Skip whitespace and comments
        while (i < arrayContent.length && /\s/.test(arrayContent[i])) i++;
        if (i >= arrayContent.length) break;

        // Skip comments
        if (arrayContent.substring(i, i + 2) === "//") {
            while (i < arrayContent.length && arrayContent[i] !== "\n") i++;
            continue;
        }

        // Look for opening bracket of inner array
        if (arrayContent[i] === "[") {
            const endIdx = findMatchingBracket(arrayContent, i, "[", "]");
            if (endIdx === -1) break;

            const innerArray = arrayContent.substring(i + 1, endIdx);
            // Extract first string literal
            const stringMatch = innerArray.match(
                /^\s*(String\.raw`[^`]*`|`[^`]*`|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')/
            );
            if (stringMatch) {
                const pattern = unquote(stringMatch[1]);
                if (pattern) patterns.push(pattern);
            }
            i = endIdx + 1;
        } else {
            i++;
        }
    }
    return patterns;
}

// Extract patterns from object format: [{ input: "pattern", ... }, ...]
function extractFromObjectFormat(arrayContent) {
    const patterns = [];
    let i = 0;
    while (i < arrayContent.length) {
        // Skip whitespace and comments
        while (i < arrayContent.length && /\s/.test(arrayContent[i])) i++;
        if (i >= arrayContent.length) break;

        // Skip comments
        if (arrayContent.substring(i, i + 2) === "//") {
            while (i < arrayContent.length && arrayContent[i] !== "\n") i++;
            continue;
        }

        // Look for opening brace of object
        if (arrayContent[i] === "{") {
            const endIdx = findMatchingBracket(arrayContent, i, "{", "}");
            if (endIdx === -1) break;

            const objContent = arrayContent.substring(i + 1, endIdx);
            // Look for input: "pattern" or pattern: "pattern"
            const inputMatch = objContent.match(
                /(?:input|pattern)\s*:\s*(String\.raw`[^`]*`|`[^`]*`|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')/
            );
            if (inputMatch) {
                const pattern = unquote(inputMatch[1]);
                if (pattern) patterns.push(pattern);
            }
            i = endIdx + 1;
        } else {
            i++;
        }
    }
    return patterns;
}

// Extract patterns from test.each inline arrays and variable references
function extractPatternsFromTestEach(content, filePath) {
    const patterns = [];
    const regex = /(test|it)\.each\s*(<[^>]+>)?\s*\(/g;
    let match;

    while ((match = regex.exec(content)) !== null) {
        const startIdx = match.index + match[0].length;
        const openParen = startIdx - 1;

        // Find the matching closing paren for .each(...)
        const closeParen = findMatchingBracket(content, openParen, "(", ")");
        if (closeParen === -1) continue;

        const eachArg = content.substring(startIdx, closeParen).trim();

        // Case 1: Inline array literal
        if (eachArg.startsWith("[")) {
            const arrayEnd = findMatchingBracket(eachArg, 0, "[", "]");
            if (arrayEnd !== -1) {
                const arrayContent = eachArg.substring(1, arrayEnd);
                // Try both formats
                const arrayPatterns = extractFromArrayFormat(arrayContent);
                const objPatterns = extractFromObjectFormat(arrayContent);
                patterns.push(...arrayPatterns, ...objPatterns);
                stats.inlineArray += arrayPatterns.length + objPatterns.length;
            }
        }
        // Case 2: Variable reference (e.g., "cases")
        else if (/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(eachArg)) {
            const varName = eachArg;
            // Look for variable declaration: const/let varName = [...]
            const varRegex = new RegExp(
                `(?:const|let)\\s+${varName}\\s*(?::\\s*[^=]+)?\\s*=\\s*\\[`,
                "g"
            );
            let varMatch;
            while ((varMatch = varRegex.exec(content)) !== null) {
                const arrayStart =
                    varMatch.index + varMatch[0].length - 1;
                const arrayEnd = findMatchingBracket(
                    content,
                    arrayStart,
                    "[",
                    "]"
                );
                if (arrayEnd !== -1) {
                    const arrayContent = content.substring(
                        arrayStart + 1,
                        arrayEnd
                    );
                    const arrayPatterns = extractFromArrayFormat(arrayContent);
                    const objPatterns = extractFromObjectFormat(arrayContent);
                    patterns.push(...arrayPatterns, ...objPatterns);
                    stats.variableResolved +=
                        arrayPatterns.length + objPatterns.length;
                }
            }
        }
    }

    return patterns;
}

// Main extraction logic
function extractPatternsFromText(fileContent, filePath) {
    const patterns = [];

    // Extract from literal parse() calls
    const parseRegex =
        /parse\(\s*(String\.raw`[\s\S]*?`|`[\s\S]*?`|"(?:\\.|[^\\"])*"|'(?:\\.|[^\\'])*')\s*\)/g;
    let match;
    while ((match = parseRegex.exec(fileContent)) !== null) {
        const pattern = unquote(match[1]);
        if (pattern) {
            patterns.push(pattern);
            stats.literalParse++;
        }
    }

    // Extract from test.each blocks
    const testEachPatterns = extractPatternsFromTestEach(
        fileContent,
        filePath
    );
    patterns.push(...testEachPatterns);

    return patterns;
}

if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

// Collect all patterns with deduplication
const allPatterns = new Set();
for (const f of files) {
    stats.totalFiles++;
    const content = fs.readFileSync(f, "utf8");
    const patterns = extractPatternsFromText(content, f);
    patterns.forEach((p) => allPatterns.add(p));
}

// Write pattern files
let count = 0;
for (const pattern of allPatterns) {
    const name = "js_test_pattern_" + (++count) + ".pattern";
    const outPath = path.join(outDir, name);
    fs.writeFileSync(outPath, pattern + "\n", "utf8");
}

// Report statistics
console.log("\n=== Pattern Extraction Statistics ===");
console.log("Files processed:", stats.totalFiles);
console.log("Patterns from literal parse() calls:", stats.literalParse);
console.log("Patterns from inline test.each arrays:", stats.inlineArray);
console.log(
    "Patterns from variable-resolved test.each:",
    stats.variableResolved
);
console.log("Total unique patterns extracted:", allPatterns.size);
console.log("Output directory:", outDir);
console.log("=====================================\n");
