/**
 * STRling v3 — PCRE2 Emitter
 * Emit PCRE2 pattern string from IR.
 * 
 * Ported from Python reference implementation.
 */

import * as IR from "../core/ir.js";

// ---- helpers ----------------------------------------------------------------

function _escapeLiteral(s: string): string {
    /**
     * Escape PCRE2 metacharacters outside character classes, but do NOT escape dashes (-).
     */
    // JavaScript's simple escape for regex metachars
    const metachars = /[\\^$.*+?()[\]{}|]/g;
    return s.replace(metachars, "\\$&");
}

function _escapeClassChar(ch: string): string {
    /**
     * Escape a char for use inside [...] per PCRE2 rules.
     */
    // Inside [], ], \, -, and ^ are special and need escaping for safety
    if (ch === "\\" || ch === "]") {
        return "\\" + ch;
    }
    if (ch === "-") {
        return "\\-";
    }
    if (ch === "^") {
        return "\\^";
    }

    // Handle non-printable chars / whitespace for clarity
    if (ch === "\n") return "\\n";
    if (ch === "\r") return "\\r";
    if (ch === "\t") return "\\t";
    if (ch === "\f") return "\\f";
    if (ch === "\v") return "\\v";
    
    const code = ch.charCodeAt(0);
    if (code < 32 || (code >= 127 && code <= 159)) {
        return `\\x${code.toString(16).padStart(2, "0")}`;
    }

    // All other characters are literal within []
    return ch;
}

function _emitClass(cc: IR.IRCharClass): string {
    /**
     * Emit a PCRE2 character class. If the class is exactly one shorthand escape
     * (like \d or \p{Lu}), prefer the shorthand (with negation flipping) instead
     * of a bracketed class.
     */
    const items = cc.items;

    // --- Single-item shorthand optimization ---------------------------------
    if (items.length === 1 && items[0] instanceof IR.IRClassEscape) {
        const k = items[0].type; // 'd','D','w','W','s','S','p','P'
        const prop = items[0].property;

        if (["d", "w", "s"].includes(k)) {
            // Flip to uppercase negated forms when the entire class is negated
            if (cc.negated && k === "d") return "\\D";
            if (cc.negated && k === "w") return "\\W";
            if (cc.negated && k === "s") return "\\S";
            return "\\" + k;
        }

        if (["D", "W", "S"].includes(k)) {
            // Already-negated shorthands; flip back if the class itself is negated
            const base = k.toLowerCase();
            return cc.negated ? "\\" + base : "\\" + k;
        }

        if (["p", "P"].includes(k) && prop) {
            // For \p{..}/\P{..}, flip p<->P iff exactly-negated class
            const use = (cc.negated !== (k === "P")) ? "P" : "p";
            return `\\${use}{${prop}}`;
        }
    }

    // --- General case: build a bracket class --------------------------------
    const parts: string[] = [];
    for (const it of items) {
        if (it instanceof IR.IRClassLiteral) {
            parts.push(_escapeClassChar(it.ch));
        } else if (it instanceof IR.IRClassRange) {
            parts.push(`${_escapeClassChar(it.fromCh)}-${_escapeClassChar(it.toCh)}`);
        } else if (it instanceof IR.IRClassEscape) {
            if (["d", "D", "w", "W", "s", "S"].includes(it.type)) {
                parts.push("\\" + it.type);
            } else if (["p", "P"].includes(it.type) && it.property) {
                parts.push(`\\${it.type}{${it.property}}`);
            } else {
                parts.push("\\" + it.type);
            }
        } else {
            throw new Error(`class item ${it.constructor.name}`);
        }
    }

    const inner = parts.join("");
    return `[${cc.negated ? "^" : ""}${inner}]`;
}

function _emitQuantSuffix(minv: number, maxv: number | string, mode: string): string {
    /**
     * Emit *, +, ?, {m}, {m,}, {m,n} plus optional lazy/possessive suffix.
     */
    let q: string;
    if (minv === 0 && maxv === "Inf") {
        q = "*";
    } else if (minv === 1 && maxv === "Inf") {
        q = "+";
    } else if (minv === 0 && maxv === 1) {
        q = "?";
    } else if (minv === maxv) {
        q = `{${minv}}`;
    } else if (maxv === "Inf") {
        q = `{${minv},}`;
    } else {
        q = `{${minv},${maxv}}`;
    }

    if (mode === "Lazy") {
        q += "?";
    } else if (mode === "Possessive") {
        q += "+";
    }
    return q;
}

function _needsGroupForQuant(child: IR.IROp): boolean {
    /**
     * Return true if 'child' needs a non-capturing group when quantifying.
     */
    if (
        child instanceof IR.IRCharClass ||
        child instanceof IR.IRDot ||
        child instanceof IR.IRGroup ||
        child instanceof IR.IRBackref ||
        child instanceof IR.IRAnchor
    ) {
        return false;
    }
    if (child instanceof IR.IRLit) {
        return child.value.length > 1;
    }
    if (child instanceof IR.IRAlt || child instanceof IR.IRLook) {
        return true;
    }
    if (child instanceof IR.IRSeq) {
        return child.parts.length > 1;
    }
    return false;
}

function _emitGroupOpen(g: IR.IRGroup): string {
    if (g.atomic) {
        return "(?>";
    }
    if (g.capturing) {
        if (g.name !== null) {
            return `(?<${g.name}>`;
        }
        return "(";
    }
    return "(?:";
}

function _emitNode(node: IR.IROp, parentKind: string = ""): string {
    if (node instanceof IR.IRLit) {
        return _escapeLiteral(node.value);
    }

    if (node instanceof IR.IRDot) {
        return ".";
    }

    if (node instanceof IR.IRAnchor) {
        const mapping: { [key: string]: string } = {
            Start: "^",
            End: "$",
            WordBoundary: "\\b",
            NotWordBoundary: "\\B",
            AbsoluteStart: "\\A",
            EndBeforeFinalNewline: "\\Z",
            AbsoluteEnd: "\\z",
        };
        return mapping[node.at] || "";
    }

    if (node instanceof IR.IRBackref) {
        if (node.byName !== null) {
            return `\\k<${node.byName}>`;
        }
        if (node.byIndex !== null) {
            return "\\" + node.byIndex;
        }
        return "";
    }

    if (node instanceof IR.IRCharClass) {
        return _emitClass(node);
    }

    if (node instanceof IR.IRSeq) {
        return node.parts.map((p: IR.IROp): string => _emitNode(p, "Seq")).join("");
    }

    if (node instanceof IR.IRAlt) {
        const body: string = node.branches.map((b: IR.IROp): string => _emitNode(b, "Alt")).join("|");
        // Alt inside sequence/quant should be grouped
        return ["Seq", "Quant"].includes(parentKind) ? `(?:${body})` : body;
    }

    if (node instanceof IR.IRQuant) {
        let childStr: string = _emitNode(node.child, "Quant");
        if (_needsGroupForQuant(node.child) && !(node.child instanceof IR.IRGroup)) {
            childStr = `(?:${childStr})`;
        }
        return childStr + _emitQuantSuffix(node.min, node.max, node.mode);
    }

    if (node instanceof IR.IRGroup) {
        return _emitGroupOpen(node) + _emitNode(node.body, "Group") + ")";
    }

    if (node instanceof IR.IRLook) {
        let op: string;
        if (node.dir === "Ahead" && !node.neg) {
            op = "?=";
        } else if (node.dir === "Ahead" && node.neg) {
            op = "?!";
        } else if (node.dir === "Behind" && !node.neg) {
            op = "?<=";
        } else {
            op = "?<!";
        }
        return "(" + op + _emitNode(node.body, "Look") + ")";
    }

    throw new Error(`Emitter missing for ${node.constructor.name}`);
}

function _emitPrefixFromFlags(flags: any): string {
    /**
     * Build the inline prefix form expected by tests, e.g. "(?imx)"
     */
    let letters = "";
    if (flags.ignoreCase) letters += "i";
    if (flags.multiline) letters += "m";
    if (flags.dotAll) letters += "s";
    if (flags.unicode) letters += "u";
    if (flags.extended) letters += "x";
    return letters ? `(?${letters})` : "";
}

export function emit(irRoot: IR.IROp, flags: any = null): string {
    /**
     * Emit a PCRE2 pattern string from IR.
     * 
     * If 'flags' is provided, it can be a plain object or a Flags object with .toDict().
     */
    let flagDict: any = null;
    if (flags !== null) {
        if (typeof flags === "object" && !flags.toDict) {
            flagDict = flags;
        } else if (flags.toDict) {
            flagDict = flags.toDict();
        }
    }

    const prefix = flagDict ? _emitPrefixFromFlags(flagDict) : "";
    const body = _emitNode(irRoot, "");
    return prefix + body;
}
