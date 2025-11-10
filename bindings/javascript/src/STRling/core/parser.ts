/**
 * STRling Parser - Recursive Descent Parser for STRling DSL
 *
 * This module implements a hand-rolled recursive-descent parser that transforms
 * STRling pattern syntax into Abstract Syntax Tree (AST) nodes. The parser handles:
 *   - Alternation and sequencing
 *   - Character classes and ranges
 *   - Quantifiers (greedy, lazy, possessive)
 *   - Groups (capturing, non-capturing, named, atomic)
 *   - Lookarounds (lookahead and lookbehind, positive and negative)
 *   - Anchors and special escapes
 *   - Extended/free-spacing mode with comments
 *
 * The parser produces AST nodes (defined in nodes.ts) that can be compiled
 * to IR and ultimately emitted as target-specific regex patterns. It includes
 * comprehensive error handling with position tracking for helpful diagnostics.
 */

import {
    Flags,
    Node,
    Alt,
    Seq,
    Lit,
    Dot,
    Anchor,
    CharClass,
    ClassLiteral,
    ClassRange,
    ClassEscape,
    Quant,
    Group,
    Backref,
    Look,
} from "./nodes.js";

// ---------------- Errors ----------------
export class ParseError extends Error {
    message: string;
    pos: number;

    constructor(message: string, pos: number) {
        super(`${message} at ${pos}`);
        this.message = message;
        this.pos = pos;
    }
}

// ---------------- Lexer helpers ----------------
class Cursor {
    text: string;
    i: number;
    extendedMode: boolean;
    inClass: number;

    constructor(text: string, i: number = 0, extendedMode: boolean = false, inClass: number = 0) {
        this.text = text;
        this.i = i;
        this.extendedMode = extendedMode;
        this.inClass = inClass; // nesting count for char classes
    }

    eof(): boolean {
        return this.i >= this.text.length;
    }

    peek(n: number = 0): string {
        const j = this.i + n;
        return j >= this.text.length ? "" : this.text[j];
    }

    take(): string {
        if (this.eof()) {
            return "";
        }
        const ch = this.text[this.i];
        this.i++;
        return ch;
    }

    match(s: string): boolean {
        if (this.text.startsWith(s, this.i)) {
            this.i += s.length;
            return true;
        }
        return false;
    }

    skipWsAndComments(): void {
        if (!this.extendedMode || this.inClass > 0) {
            return;
        }
        // In free-spacing mode, ignore spaces/tabs/newlines and #-to-EOL comments
        while (!this.eof()) {
            const ch = this.peek();
            if (" \t\r\n".includes(ch)) {
                this.i++;
                continue;
            }
            if (ch === "#") {
                // skip comment to end of line
                while (!this.eof() && !"\r\n".includes(this.peek())) {
                    this.i++;
                }
                continue;
            }
            break;
        }
    }
}

// ---------------- Parser ----------------
class Parser {
    flags: Flags;
    src: string;
    cur: Cursor;
    _capCount: number;
    _capNames: Set<string>;
    CONTROL_ESCAPES: { [key: string]: string };

    constructor(text: string) {
        // Extract directives first
        const [flags, src] = this._parseDirectives(text);
        this.flags = flags;
        this.src = src;
        this.cur = new Cursor(src, 0, flags.extended, 0);
        this._capCount = 0;
        this._capNames = new Set();
        this.CONTROL_ESCAPES = {
            n: "\n",
            r: "\r",
            t: "\t",
            f: "\f",
            v: "\v",
        };
    }

    // -- Directives --
    _parseDirectives(text: string): [Flags, string] {
        let flags = new Flags();
        const lines = text.split(/(\r?\n)/g).reduce((acc: string[], part: string, i: number) => {
            if (i % 2 === 0) acc[acc.length - 1] += part;
            else acc.push("");
            return acc;
        }, [""]);
        
        const patternLines: string[] = [];
        let inPattern = false;

        for (const line of lines) {
            const stripped = line.trim();
            // Skip leading blank lines or comments
            if (!inPattern && (stripped === "" || stripped.startsWith("#"))) {
                continue;
            }
            // Process directives only before pattern content
            if (!inPattern && stripped.startsWith("%flags")) {
                const rest = stripped.slice(6).trim();
                const letters = rest.replace(/[,\[\] ]/g, "");
                flags = Flags.fromLetters(letters);
                continue;
            }
            if (!inPattern && stripped.startsWith("%")) {
                continue;
            }
            // All other lines are pattern content
            inPattern = true;
            patternLines.push(line);
        }
        const pattern = patternLines.join("\n");
        return [flags, pattern];
    }

    parse(): Node {
        const node = this.parseAlt();
        this.cur.skipWsAndComments();
        if (!this.cur.eof()) {
            if (this.cur.peek() === "|") {
                throw new ParseError("Alternation lacks right-hand side", this.cur.i);
            } else {
                throw new ParseError("Unexpected trailing input", this.cur.i);
            }
        }
        return node;
    }

    // alt := seq ('|' seq)+ | seq
    parseAlt(): Node {
        this.cur.skipWsAndComments();
        if (this.cur.peek() === "|") {
            throw new ParseError("Alternation lacks left-hand side", this.cur.i);
        }

        const branches = [this.parseSeq()];
        this.cur.skipWsAndComments();
        
        while (this.cur.peek() === "|") {
            const pipePos = this.cur.i;
            this.cur.take();
            this.cur.skipWsAndComments();
            if (this.cur.peek() === "") {
                throw new ParseError("Alternation lacks right-hand side", pipePos);
            }
            branches.push(this.parseSeq());
            this.cur.skipWsAndComments();
        }
        
        if (branches.length === 1) {
            return branches[0];
        }
        return new Alt(branches);
    }
    // seq := { term }
    parseSeq(): Node {
        const parts: Node[] = [];
        let prevHadFailedQuant = false;

        while (true) {
            this.cur.skipWsAndComments();
            const ch = this.cur.peek();
            
            if (ch === "" || "|)".includes(ch)) {
                break;
            }

            const atom = this.parseAtom();
            const [quantifiedAtom, hadFailedQuantParse] = this.parseQuantIfAny(atom);

            // Coalesce adjacent Lit nodes
            const avoidDigitAfterBackslash = (
                quantifiedAtom instanceof Lit &&
                quantifiedAtom.value.length === 1 &&
                /\d/.test(quantifiedAtom.value) &&
                parts.length > 0 &&
                parts[parts.length - 1] instanceof Lit &&
                (parts[parts.length - 1] as Lit).value.length > 0 &&
                (parts[parts.length - 1] as Lit).value[(parts[parts.length - 1] as Lit).value.length - 1] === "\\"
            );

            const containsNewline = (
                (quantifiedAtom instanceof Lit && quantifiedAtom.value.includes("\n")) ||
                (parts.length > 0 && parts[parts.length - 1] instanceof Lit && (parts[parts.length - 1] as Lit).value.includes("\n"))
            );

            const prevIsBackref = parts.length > 0 && parts[parts.length - 1] instanceof Backref;

            const shouldCoalesce = (
                quantifiedAtom instanceof Lit &&
                parts.length > 0 &&
                parts[parts.length - 1] instanceof Lit &&
                !this.cur.extendedMode &&
                !prevHadFailedQuant &&
                !avoidDigitAfterBackslash &&
                !containsNewline &&
                !prevIsBackref
            );

            if (shouldCoalesce) {
                parts[parts.length - 1] = new Lit((parts[parts.length - 1] as Lit).value + quantifiedAtom.value);
            } else {
                parts.push(quantifiedAtom);
            }

            prevHadFailedQuant = hadFailedQuantParse;
        }

        if (parts.length === 1) {
            return parts[0];
        }
        return new Seq(parts);
    }

    parseQuantIfAny(child: Node): [Node, boolean] {
        const cur = this.cur;
        const ch = cur.peek();

        let minVal: number | null = null;
        let maxVal: number | string | null = null;
        let mode: string = "Greedy";
        let hadFailedQuantParse = false;

        if (ch === "*") {
            minVal = 0;
            maxVal = "Inf";
            cur.take();
        } else if (ch === "+") {
            minVal = 1;
            maxVal = "Inf";
            cur.take();
        } else if (ch === "?") {
            minVal = 0;
            maxVal = 1;
            cur.take();
        } else if (ch === "{") {
            const save = cur.i;
            const [m, n, parsedMode] = this.parseBraceQuant();
            if (m !== null) {
                minVal = m;
                maxVal = n;
                mode = parsedMode;
            } else {
                hadFailedQuantParse = true;
                cur.i = save;
            }
        }

        if (minVal === null) {
            return [child, hadFailedQuantParse];
        }

        if (child instanceof Anchor) {
            throw new ParseError("Cannot quantify anchor", cur.i);
        }

        const nxt = cur.peek();
        if (nxt === "?") {
            mode = "Lazy";
            cur.take();
        } else if (nxt === "+") {
            mode = "Possessive";
            cur.take();
        }

        return [new Quant(child, minVal, maxVal !== null ? maxVal as number | string : "Inf", mode), hadFailedQuantParse];
    }

    parseBraceQuant(): [number | null, number | string | null, string] {
        const cur = this.cur;
        if (!cur.match("{")) {
            return [null, null, "Greedy"];
        }
        
        const m = this._readIntOptional();
        if (m === null) {
            return [null, null, "Greedy"];
        }
        
        if (cur.match(",")) {
            const n = this._readIntOptional();
            if (!cur.match("}")) {
                throw new ParseError("Unterminated {m,n}", cur.i);
            }
            return [m, n !== null ? n : "Inf", "Greedy"];
        } else {
            if (!cur.match("}")) {
                throw new ParseError("Unterminated {n}", cur.i);
            }
            return [m, m, "Greedy"];
        }
    }

    _readIntOptional(): number | null {
        const cur = this.cur;
        let s = "";
        while (/\d/.test(cur.peek())) {
            s += cur.take();
        }
        return s !== "" ? parseInt(s, 10) : null;
    }
    // ---- atom ----
    parseAtom(): Node {
        const cur = this.cur;
        cur.skipWsAndComments();
        const ch = cur.peek();
        
        if (ch === ".") {
            cur.take();
            return new Dot();
        }
        if (ch === "^") {
            cur.take();
            return new Anchor("Start");
        }
        if (ch === "$") {
            cur.take();
            return new Anchor("End");
        }
        if (ch === "(") {
            return this.parseGroupOrLook();
        }
        if (ch === "[") {
            return this.parseCharClass();
        }
        if (ch === "\\") {
            return this.parseEscapeAtom();
        }
        if ("|)".includes(ch)) {
            throw new ParseError("Unexpected token", cur.i);
        }
        return new Lit(this._takeLiteralChar());
    }

    _takeLiteralChar() {
        return this.cur.take();
    }

    // ---- escapes and atoms formed by escapes ----
    parseEscapeAtom() {
        const cur = this.cur;
        const startPos = cur.i;
        if (cur.take() !== "\\") throw new Error("Expected backslash");
        
        const nxt = cur.peek();

        // Backref by index \1.. (but not \0)
        if (/\d/.test(nxt) && nxt !== "0") {
            const savedPos = cur.i;
            let numStr = "";

            while (/\d/.test(cur.peek())) {
                numStr += cur.take();
                const num = parseInt(numStr, 10);

                if (num <= this._capCount) {
                    continue;
                } else {
                    cur.i--;
                    numStr = numStr.slice(0, -1);
                    break;
                }
            }

            if (numStr) {
                const num = parseInt(numStr, 10);
                if (num <= this._capCount) {
                    return new Backref(num, null);
                }
            }

            cur.i = savedPos;
            const num = this._readDecimal();
            throw new ParseError(`Backreference to undefined group \\${num}`, startPos);
        }

        // Anchors \b \B \A \Z \z
        if ("bBAZz".includes(nxt)) {
            const ch = cur.take();
            if (ch === "b") return new Anchor("WordBoundary");
            if (ch === "B") return new Anchor("NotWordBoundary");
            if (ch === "A") return new Anchor("AbsoluteStart");
            if (ch === "Z") return new Anchor("EndBeforeFinalNewline");
            if (ch === "z") return new Anchor("AbsoluteEnd");
        }

        // \k<name> named backref
        if (nxt === "k") {
            cur.take();
            if (!cur.match("<")) {
                throw new ParseError("Expected '<' after \\k", startPos);
            }
            const name = this._readIdentUntil(">");
            if (!cur.match(">")) {
                throw new ParseError("Unterminated named backref", startPos);
            }
            if (!this._capNames.has(name)) {
                throw new ParseError(`Backreference to undefined group <${name}>`, startPos);
            }
            return new Backref(null, name);
        }

        // Shorthand classes \d \D \w \W \s \S
        if ("dDwWsS".includes(nxt)) {
            cur.take();
            return new CharClass(false, [new ClassEscape(nxt)]);
        }

        // Property \p{..} \P{..}
        if ("pP".includes(nxt)) {
            const tp = cur.take();
            if (!cur.match("{")) {
                throw new ParseError("Expected { after \\p/\\P", startPos);
            }
            const prop = this._readUntil("}");
            if (!cur.match("}")) {
                throw new ParseError("Unterminated \\p{...}", startPos);
            }
            return new CharClass(false, [new ClassEscape(tp, prop)]);
        }

        // Core control escapes \n \t \r \f \v
        if (nxt in this.CONTROL_ESCAPES) {
            const ch = cur.take();
            return new Lit(this.CONTROL_ESCAPES[ch]);
        }

        // Hex/Unicode/Null escapes
        if (nxt === "x") {
            return new Lit(this._parseHexEscape(startPos));
        }
        if (nxt === "u" || nxt === "U") {
            return new Lit(this._parseUnicodeEscape(startPos));
        }
        if (nxt === "0") {
            cur.take();
            return new Lit("\x00");
        }

        // Identity escape
        const ch = cur.take();
        return new Lit(ch);
    }

    _readDecimal() {
        const cur = this.cur;
        let s = "";
        while (/\d/.test(cur.peek())) {
            s += cur.take();
        }
        return s ? parseInt(s, 10) : 0;
    }

    _readIdentUntil(end: string): string {
        const cur = this.cur;
        let s = "";
        while (!cur.eof() && cur.peek() !== end) {
            s += cur.take();
        }
        return s;
    }

    _readUntil(end: string): string {
        return this._readIdentUntil(end);
    }

    _parseHexEscape(startPos: number): string {
        const cur = this.cur;
        if (cur.take() !== "x") throw new Error("Expected 'x'");
        
        if (cur.match("{")) {
            let hexs = "";
            while (/[0-9A-Fa-f]/.test(cur.peek() || "")) {
                hexs += cur.take();
            }
            if (!cur.match("}")) {
                throw new ParseError("Unterminated \\x{...}", startPos);
            }
            const cp = parseInt(hexs || "0", 16);
            return String.fromCodePoint(cp);
        }
        
        // \xHH
        const h1 = cur.take();
        const h2 = cur.take();
        if (!/[0-9A-Fa-f]/.test(h1 || "") || !/[0-9A-Fa-f]/.test(h2 || "")) {
            throw new ParseError("Invalid \\xHH escape", startPos);
        }
        return String.fromCharCode(parseInt(h1 + h2, 16));
    }

    _parseUnicodeEscape(startPos: number): string {
        const cur = this.cur;
        const tp = cur.take(); // u or U

        if (tp === "u" && cur.match("{")) {
            let hexs = "";
            while (/[0-9A-Fa-f]/.test(cur.peek() || "")) {
                hexs += cur.take();
            }
            if (!cur.match("}")) {
                throw new ParseError("Unterminated \\u{...}", startPos);
            }
            const cp = parseInt(hexs || "0", 16);
            return String.fromCodePoint(cp);
        }

        if (tp === "u") {
            const hexs = cur.take() + cur.take() + cur.take() + cur.take();
            if (hexs.length !== 4 || !/^[0-9A-Fa-f]{4}$/.test(hexs)) {
                throw new ParseError("Invalid \\uHHHH escape", startPos);
            }
            return String.fromCodePoint(parseInt(hexs, 16));
        }

        if (tp === "U") {
            const hexs = cur.take() + cur.take() + cur.take() + cur.take() + 
                         cur.take() + cur.take() + cur.take() + cur.take();
            if (hexs.length !== 8 || !/^[0-9A-Fa-f]{8}$/.test(hexs)) {
                throw new ParseError("Invalid \\UHHHHHHHH escape", startPos);
            }
            return String.fromCodePoint(parseInt(hexs, 16));
        }

        throw new ParseError("Invalid unicode escape", startPos);
    }
    // ---- Character classes ----
    parseCharClass() {
        const cur = this.cur;
        if (cur.take() !== "[") throw new Error("Expected '['");
        let startPos = cur.i;  // Position after '['
        
        this.cur.inClass++;
        
        let neg = false;
        if (cur.peek() === "^") {
            neg = true;
            cur.take();
            startPos = cur.i;  // Update position after '^'
        }

        const items = [];

        const readItem = () => {
            if (cur.peek() === "\\") {
                return this._parseClassEscape();
            }
            return new ClassLiteral(cur.take());
        };

        while (true) {
            if (cur.eof()) {
                this.cur.inClass--;
                throw new ParseError("Unterminated character class", cur.i);
            }

            if (cur.peek() === "]" && cur.i > startPos) {
                cur.take();
                this.cur.inClass--;
                return new CharClass(neg, items);
            }

            // Range handling
            if (
                cur.peek() === "-" &&
                items.length > 0 &&
                items[items.length - 1] instanceof ClassLiteral &&
                cur.peek(1) !== "]"
            ) {
                cur.take();
                const endItem = readItem();
                if (endItem instanceof ClassLiteral) {
                    const startLit = items.pop() as ClassLiteral;
                    const startCh = startLit.ch;
                    const endCh = endItem.ch;
                    items.push(new ClassRange(startCh, endCh));
                } else {
                    items.push(new ClassLiteral("-"));
                    items.push(endItem);
                }
                continue;
            }

            items.push(readItem());
        }
    }

    _parseClassEscape() {
        const cur = this.cur;
        const startPos = cur.i;
        if (cur.take() !== "\\") throw new Error("Expected backslash");
        
        const nxt = cur.peek();

        // Shorthand classes
        if ("dDwWsS".includes(nxt)) {
            return new ClassEscape(cur.take());
        }

        // Property
        if ("pP".includes(nxt)) {
            const tp = cur.take();
            if (!cur.match("{")) {
                throw new ParseError("Expected { after \\p/\\P", startPos);
            }
            const prop = this._readUntil("}");
            if (!cur.match("}")) {
                throw new ParseError("Unterminated \\p{...}", startPos);
            }
            return new ClassEscape(tp, prop);
        }

        // Control escapes
        if (nxt in this.CONTROL_ESCAPES) {
            const ch = cur.take();
            return new ClassLiteral(this.CONTROL_ESCAPES[ch]);
        }

        // Special case: \b inside class is backspace (0x08)
        if (nxt === "b") {
            cur.take();
            return new ClassLiteral("\x08");
        }

        // Hex escape
        if (nxt === "x") {
            return new ClassLiteral(this._parseHexEscape(startPos));
        }

        // Unicode escape
        if (nxt === "u" || nxt === "U") {
            return new ClassLiteral(this._parseUnicodeEscape(startPos));
        }

        // Null
        if (nxt === "0") {
            cur.take();
            return new ClassLiteral("\x00");
        }

        // Identity escape
        const ch = cur.take();
        return new ClassLiteral(ch);
    }

    // ---- Groups, lookarounds ----
    parseGroupOrLook() {
        const cur = this.cur;
        if (cur.take() !== "(") throw new Error("Expected '('");

        // Reject inline modifiers
        if (cur.peek() === "?" && "imsx".includes(cur.peek(1))) {
            throw new ParseError("Inline modifiers `(?imsx)` are not supported", cur.i);
        }

        // Non-capturing group
        if (cur.match("?:")) {
            const body = this.parseAlt();
            if (!cur.match(")")) {
                throw new ParseError("Unterminated group", cur.i);
            }
            return new Group(false, body);
        }

        // Lookbehind (must be before named group)
        if (cur.match("?<=")) {
            const body = this.parseAlt();
            if (!cur.match(")")) {
                throw new ParseError("Unterminated lookbehind", cur.i);
            }
            return new Look("Behind", false, body);
        }

        if (cur.match("?<!")) {
            const body = this.parseAlt();
            if (!cur.match(")")) {
                throw new ParseError("Unterminated lookbehind", cur.i);
            }
            return new Look("Behind", true, body);
        }

        // Named capturing group
        if (cur.match("?<")) {
            const name = this._readUntil(">");
            if (!cur.match(">")) {
                throw new ParseError("Unterminated group name", cur.i);
            }
            if (this._capNames.has(name)) {
                throw new ParseError(`Duplicate group name <${name}>`, cur.i);
            }
            this._capCount++;
            this._capNames.add(name);
            const body = this.parseAlt();
            if (!cur.match(")")) {
                throw new ParseError("Unterminated group", cur.i);
            }
            return new Group(true, body, name);
        }

        // Atomic group
        if (cur.match("?>")) {
            const body = this.parseAlt();
            if (!cur.match(")")) {
                throw new ParseError("Unterminated atomic group", cur.i);
            }
            return new Group(false, body, null, true);
        }

        // Lookahead
        if (cur.match("?=")) {
            const body = this.parseAlt();
            if (!cur.match(")")) {
                throw new ParseError("Unterminated lookahead", cur.i);
            }
            return new Look("Ahead", false, body);
        }

        if (cur.match("?!")) {
            const body = this.parseAlt();
            if (!cur.match(")")) {
                throw new ParseError("Unterminated lookahead", cur.i);
            }
            return new Look("Ahead", true, body);
        }

        // Capturing group
        this._capCount++;
        const body = this.parseAlt();
        if (!cur.match(")")) {
            throw new ParseError("Unterminated group", cur.i);
        }
        return new Group(true, body);
    }
}

// ---------------- Public API ----------------
export function parse(src: string): [Flags, Node] {
    const p = new Parser(src);
    return [p.flags, p.parse()];
}

export function parseToArtifact(src: string): any {
    const [flags, root] = parse(src);
    const artifact = {
        version: "1.0.0",
        flags: flags.toDict(),
        root: root.toDict(),
        warnings: [],
        errors: [],
    };
    return artifact;
}
