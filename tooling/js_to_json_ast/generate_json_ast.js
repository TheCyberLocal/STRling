#!/usr/bin/env node
const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "../..");
const distParser = path.join(
    repoRoot,
    "bindings/javascript/dist/STRling/core/parser.js"
);
const srcParser = path.join(
    repoRoot,
    "bindings/javascript/src/STRling/core/parser.ts"
);

function findParser() {
    if (fs.existsSync(distParser)) return distParser;
    // We cannot require TS source directly. Ask user to build if dist missing.
    if (fs.existsSync(srcParser)) {
        console.error(
            "Compiled JS not found. Please build the JavaScript binding first:"
        );
        console.error(
            "  cd bindings/javascript && npm install && npm run build"
        );
    } else {
        console.error("Parser source not found. Expected at:", distParser);
    }
    process.exit(2);
}

const parserPath = findParser();
const parser = require(parserPath);
// Try to load compiler & emitter to annotate expected results (pcre or error)
let Compiler = null;
let emitter = null;
try {
    Compiler = require(path.join(
        repoRoot,
        "bindings/javascript/dist/STRling/core/compiler.js"
    )).Compiler;
    emitter = require(path.join(
        repoRoot,
        "bindings/javascript/dist/STRling/emitters/pcre2.js"
    ));
} catch (e) {
    // It's ok if emitter/compilation isn't available; we'll just skip expected annotation
    Compiler = null;
    emitter = null;
}

if (typeof parser.parseToArtifact !== "function") {
    console.error(
        "parseToArtifact() not found on parser module at",
        parserPath
    );
    process.exit(3);
}

const fixturesDir = path.join(__dirname, "fixtures");
const outDir = path.join(__dirname, "out");
if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

const files = fs.readdirSync(fixturesDir).filter((f) => f.endsWith(".pattern"));
if (files.length === 0) {
    console.error("No fixture files found in", fixturesDir);
    process.exit(1);
}

for (const f of files) {
    const fp = path.join(fixturesDir, f);
    const src = fs.readFileSync(fp, "utf8");
    try {
        const artifact = parser.parseToArtifact(src);
        // Parse the original DSL into Node instances (not the dict artifact)
        // so we can compile with the Compiler which expects Node objects.
        let rootNode = null;
        let nodeFlags = null;
        try {
            if (typeof parser.parse === "function") {
                const parsed = parser.parse(src);
                // parsed is [flags, rootNode]
                nodeFlags = parsed[0];
                rootNode = parsed[1];
            }
        } catch (e) {
            rootNode = null; // continue gracefully; expected computation will be skipped
        }

        function mapAnchor(a) {
            // Map JS anchor names to C binding expected names
            if (!a) return a;
            switch (a) {
                case "NotWordBoundary":
                    return "NonWordBoundary";
                // In PCRE2: \Z = end before final newline, \z = absolute end
                // JS uses "EndBeforeFinalNewline" for \Z behavior
                // Keep it as-is, don't change to AbsoluteEnd
                default:
                    return a;
            }
        }

        function convertNode(node) {
            if (!node) return null;
            const k = node.kind || node.type || null;
            if (!k) return null;
            switch (k) {
                case "Lit":
                case "Literal":
                    return { type: "Literal", value: node.value };
                case "Seq":
                case "Sequence":
                    return {
                        type: "Sequence",
                        parts: (node.parts || node.children || []).map(
                            convertNode
                        ),
                    };
                case "Dot":
                    return { type: "Dot" };
                case "Alt":
                case "Alternation":
                    return {
                        type: "Alternation",
                        alternatives: (
                            node.branches ||
                            node.alternatives ||
                            []
                        ).map(convertNode),
                    };
                case "Anchor":
                    return { type: "Anchor", at: mapAnchor(node.at) };
                case "CharClass":
                case "Class":
                    return {
                        type: "CharacterClass",
                        negated: !!node.negated,
                        members: (node.items || node.members || []).map(
                            convertNode
                        ),
                    };
                case "ClassLiteral":
                case "Char":
                    // Class literal used inside CharacterClass should be treated as a Literal with value
                    return { type: "Literal", value: node.char || node.ch };
                case "ClassRange":
                case "Range":
                    // The C binding and existing tests expect `type: "Range"` for class ranges
                    return {
                        type: "Range",
                        from: node.from || node.fromCh,
                        to: node.to || node.toCh,
                    };
                case "ClassEscape":
                case "Esc":
                    // Map escapes inside character classes into the `Escape` node used by C binding
                    // JS `Esc` has fields like `type` or `escape` to indicate \d, \w, \p{...}
                    const escKind =
                        node.type ||
                        node.kind ||
                        node.escape ||
                        node.kindName ||
                        node.name;
                    if (!escKind) {
                        // fallback: unknown escape
                        return { type: "Escape", kind: null };
                    }
                    if (
                        escKind === "p" ||
                        escKind === "P" ||
                        escKind === "UnicodeProperty"
                    ) {
                        // The C binding expects `type: "UnicodeProperty"` instead of `Escape` for \p{...}
                        return {
                            type: "UnicodeProperty",
                            name: node.name || null,
                            value: node.property || node.value || null,
                            negated: escKind === "P" || !!node.negated,
                        };
                    }
                    // Map standard shorthands to more descriptive kinds the C emitter expects
                    const shorthandMap = {
                        d: "digit",
                        D: "not-digit",
                        w: "word",
                        W: "not-word",
                        s: "space",
                        S: "not-space",
                        b: "wordBoundary",
                        B: "wordBoundary",
                    };
                    const mappedKind = shorthandMap[escKind] || escKind;
                    return { type: "Escape", kind: mappedKind };
                case "Quant":
                case "Quantifier":
                    // The C emitter expects a `greedy` boolean instead of separate lazy/possessive flags.
                    const greedy = node.mode !== "Lazy" && node.lazy !== true;
                    return {
                        type: "Quantifier",
                        target: convertNode(node.child || node.target),
                        min: node.min,
                        max: node.max === "Inf" ? null : node.max,
                        greedy: !!greedy,
                        lazy: !greedy,
                        possessive:
                            node.mode === "Possessive" || !!node.possessive,
                    };
                case "Group":
                    // The C binding tests expect `expression` as the group payload key in some places,
                    // but other parts use `body`. Emit both for compatibility.
                    const bodyNode = convertNode(
                        node.body ||
                            (node.parts && { kind: "Seq", parts: node.parts })
                    );
                    return {
                        type: "Group",
                        capturing: !!node.capturing,
                        body: bodyNode,
                        expression: bodyNode,
                        name: node.name || null,
                        atomic: !!node.atomic,
                    };
                case "Backref":
                    // The C binding expects keys 'index' and 'name' on a Backreference node
                    return {
                        type: "Backreference",
                        index:
                            node.byIndex || node.by_index || node.index || null,
                        name: node.byName || node.by_name || node.name || null,
                    };
                case "Look":
                    // Normalize Look to the C emitter's specific node kinds
                    // node.dir expected to be 'Ahead' or 'Behind'; node.neg is boolean
                    const dir = node.dir || node.direction || null;
                    const isNeg = !!node.neg;
                    if (dir === "Ahead") {
                        return {
                            type: isNeg ? "NegativeLookahead" : "Lookahead",
                            body: convertNode(node.body),
                        };
                    } else if (dir === "Behind") {
                        return {
                            type: isNeg ? "NegativeLookbehind" : "Lookbehind",
                            body: convertNode(node.body),
                        };
                    }
                    // Fallback to a generic look node
                    return {
                        type: "Lookahead",
                        body: convertNode(node.body),
                    };
                default:
                    // Unknown node kind; attempt to pass-through
                    return node;
            }
        }

        // Attempt to compute expected output (PCRE) by compiling via JS compiler
        let expected = { success: true, pcre: null };
        if (Compiler && emitter && rootNode) {
            try {
                const Comp = new Compiler();
                const ir = Comp.compile(rootNode);
                const pcre = emitter.emit(
                    ir,
                    nodeFlags && nodeFlags.toDict
                        ? nodeFlags.toDict()
                        : artifact.flags || {}
                );
                expected = { success: true, pcre };
            } catch (e) {
                expected = {
                    success: false,
                    error: e && e.message ? e.message : String(e),
                };
            }
        }

        const cArtifact = {
            pattern: convertNode(artifact.root),
            flags: artifact.flags || {},
            // Annotate expected result for tests: success + pcre, or error
            expected,
        };

        const outPath = path.join(outDir, f.replace(/\.pattern$/, ".json"));
        fs.writeFileSync(outPath, JSON.stringify(cArtifact, null, 2), "utf8");
        console.log("Wrote", outPath);
    } catch (err) {
        console.error(
            "Failed to parse",
            f,
            ":",
            err && err.message ? err.message : err
        );
    }
}
