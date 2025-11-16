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
import { STRlingParseError } from "./errors.js";
import { getHint } from "./hint_engine.js";

// ---------------- Errors ----------------
// Keep ParseError as an alias for backward compatibility (both value and type)
export const ParseError = STRlingParseError;
export type ParseError = STRlingParseError;

// ---------------- Lexer helpers ----------------
class Cursor {
    text: string;
    i: number;
    extendedMode: boolean;
    inClass: number;

    constructor(
        text: string,
        i: number = 0,
        extendedMode: boolean = false,
        inClass: number = 0
    ) {
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
    private _originalText: string;

    constructor(text: string) {
        // Store original text for error reporting
        this._originalText = text;
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

    /**
     * Raise a STRlingParseError with an instructional hint.
     *
     * @param message - The error message
     * @param pos - The position where the error occurred
     * @throws {STRlingParseError} Always throws with context and hint
     */
    private _raiseError(message: string, pos: number): never {
        const hint = getHint(message, this.src, pos);
        throw new STRlingParseError(message, pos, this.src, hint);
    }

    // -- Directives --
    _parseDirectives(text: string): [Flags, string] {
        let flags = new Flags();
        const lines = text.split(/(\r?\n)/g).reduce(
            (acc: string[], part: string, i: number) => {
                if (i % 2 === 0) acc[acc.length - 1] += part;
                else acc.push("");
                return acc;
            },
            [""]
        );

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
                // Work from the original `line` so we can detect inline pattern
                const idx = line.indexOf("%flags");
                const after = line.slice(idx + "%flags".length);
                // scan allowed chars for the flags token (spaces, tabs, commas,
                // brackets and known flag letters). Stop at first char that is
                // not allowed — that's the start of inline pattern content.
                const allowed = new Set(Array.from(" \t,[]imsuxIMSUX"));
                let j = 0;
                while (j < after.length && allowed.has(after[j])) j++;
                const flagsToken = after.slice(0, j);
                const remainder = after.slice(j);
                const letters = flagsToken
                    .replace(/[,\[\]\s]+/g, " ")
                    .trim()
                    .toLowerCase();
                if (letters.replace(/ /g, "") === "") {
                    // No valid letters parsed; if remainder contains non-space
                    // characters this is an invalid-flag error.
                    if (remainder.trim() !== "") {
                        const leadingWS =
                            remainder.length - remainder.trimStart().length;
                        const ch = remainder.trimStart()[0];
                        const pos =
                            lines.slice(0, lines.indexOf(line)).join("")
                                .length +
                            idx +
                            j +
                            leadingWS;
                        const hint = getHint(
                            `Invalid flag '${ch}'`,
                            this._originalText,
                            pos
                        );
                        throw new STRlingParseError(
                            `Invalid flag '${ch}'`,
                            pos,
                            this._originalText,
                            hint
                        );
                    }
                } else {
                    // Validate parsed flags
                    for (const ch of letters.replace(/ /g, "")) {
                        if (!"imsux".includes(ch)) {
                            const pos =
                                lines.slice(0, lines.indexOf(line)).join("")
                                    .length + idx;
                            const hint = getHint(
                                `Invalid flag '${ch}'`,
                                this._originalText,
                                pos
                            );
                            throw new STRlingParseError(
                                `Invalid flag '${ch}'`,
                                pos,
                                this._originalText,
                                hint
                            );
                        }
                    }
                    flags = Flags.fromLetters(letters.replace(/ /g, ""));
                    // If remainder exists on same line treat it as start of pattern
                    if (remainder.trim() !== "") {
                        inPattern = true;
                        patternLines.push(remainder);
                    }
                }
                continue;
            }
            if (!inPattern && stripped.startsWith("%")) {
                // Any other percent-directive (e.g. malformed ones) are
                // considered invalid. IEH requires malformed directives to
                // raise a parse error rather than being silently ignored.
                const idx = line.indexOf("%");
                const pos =
                    lines.slice(0, lines.indexOf(line)).join("").length + idx;
                const hint = getHint(
                    "Malformed directive",
                    this._originalText,
                    pos
                );
                throw new STRlingParseError(
                    "Malformed directive",
                    pos,
                    this._originalText,
                    hint
                );
            }
            // All other lines are pattern content. If a `%flags` directive
            // appears after pattern content has started, treat it as an
            // explicit error rather than silently allowing it inside the
            // pattern body.
            if (line.indexOf("%flags") !== -1) {
                const idx = line.indexOf("%flags");
                const pos =
                    lines.slice(0, lines.indexOf(line)).join("").length + idx;
                const hint = getHint(
                    "Directive after pattern",
                    this._originalText,
                    pos
                );
                throw new STRlingParseError(
                    "Directive after pattern",
                    pos,
                    this._originalText,
                    hint
                );
            }
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
            // If there's an unmatched closing parenthesis at top-level, throw
            // an explicit STRlingParseError with the instructional hint.
            if (this.cur.peek() === ")") {
                throw new STRlingParseError(
                    "Unmatched ')'",
                    this.cur.i,
                    this.src,
                    "This ')' character does not have a matching opening '('. Did you mean to escape it with '\\)'?"
                );
            }
            if (this.cur.peek() === "|") {
                this._raiseError(
                    "Alternation lacks right-hand side",
                    this.cur.i
                );
            } else {
                this._raiseError("Unexpected trailing input", this.cur.i);
            }
        }
        return node;
    }

    // alt := seq ('|' seq)+ | seq
    parseAlt(): Node {
        this.cur.skipWsAndComments();
        if (this.cur.peek() === "|") {
            this._raiseError("Alternation lacks left-hand side", this.cur.i);
        }

        const branches = [this.parseSeq()];
        this.cur.skipWsAndComments();

        while (this.cur.peek() === "|") {
            const pipePos = this.cur.i;
            this.cur.take();
            this.cur.skipWsAndComments();
            if (this.cur.peek() === "") {
                this._raiseError("Alternation lacks right-hand side", pipePos);
            }
            if (this.cur.peek() === "|") {
                this._raiseError("Empty alternation", pipePos);
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
            // Invalid quantifier at start of sequence/group (no previous atom)
            if (ch !== "" && "*+?{".includes(ch) && parts.length === 0) {
                // Delegate to hint engine for a context-aware hint
                this._raiseError(`Invalid quantifier '${ch}'`, this.cur.i);
            }

            if (ch === "" || "|)".includes(ch)) {
                break;
            }

            const atom = this.parseAtom();
            const [quantifiedAtom, hadFailedQuantParse] =
                this.parseQuantIfAny(atom);

            // Coalesce adjacent Lit nodes
            const avoidDigitAfterBackslash =
                quantifiedAtom instanceof Lit &&
                quantifiedAtom.value.length === 1 &&
                /\d/.test(quantifiedAtom.value) &&
                parts.length > 0 &&
                parts[parts.length - 1] instanceof Lit &&
                (parts[parts.length - 1] as Lit).value.length > 0 &&
                (parts[parts.length - 1] as Lit).value[
                    (parts[parts.length - 1] as Lit).value.length - 1
                ] === "\\";

            const containsNewline =
                (quantifiedAtom instanceof Lit &&
                    quantifiedAtom.value.includes("\n")) ||
                (parts.length > 0 &&
                    parts[parts.length - 1] instanceof Lit &&
                    (parts[parts.length - 1] as Lit).value.includes("\n"));

            const prevIsBackref =
                parts.length > 0 && parts[parts.length - 1] instanceof Backref;

            const shouldCoalesce =
                quantifiedAtom instanceof Lit &&
                parts.length > 0 &&
                parts[parts.length - 1] instanceof Lit &&
                !this.cur.extendedMode &&
                !prevHadFailedQuant &&
                !avoidDigitAfterBackslash &&
                !containsNewline &&
                !prevIsBackref;

            if (shouldCoalesce) {
                parts[parts.length - 1] = new Lit(
                    (parts[parts.length - 1] as Lit).value +
                        quantifiedAtom.value
                );
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

        // Validate quantifier numeric range (m <= n)
        if (typeof minVal === "number" && typeof maxVal === "number") {
            if (minVal > (maxVal as number)) {
                this._raiseError("Invalid quantifier range", cur.i);
            }
        }

        if (child instanceof Anchor) {
            this._raiseError("Cannot quantify anchor", cur.i);
        }

        const nxt = cur.peek();
        if (nxt === "?") {
            mode = "Lazy";
            cur.take();
        } else if (nxt === "+") {
            mode = "Possessive";
            cur.take();
        }

        return [
            new Quant(
                child,
                minVal,
                maxVal !== null ? (maxVal as number | string) : "Inf",
                mode
            ),
            hadFailedQuantParse,
        ];
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
                // Unterminated brace quantifier -> throw specific corpus hint
                // For the form 'a{1,' we signal a concise, instructional name
                throw new STRlingParseError(
                    "Incomplete quantifier",
                    cur.i,
                    this.src,
                    "Unterminated brace quantifier. Expected a closing '}'."
                );
            }
            return [m, n !== null ? n : "Inf", "Greedy"];
        } else {
            if (!cur.match("}")) {
                // Unterminated brace quantifier -> throw specific corpus hint
                // For the form 'a{1' we signal a concise, instructional name
                throw new STRlingParseError(
                    "Incomplete quantifier",
                    cur.i,
                    this.src,
                    "Unterminated brace quantifier. Expected a closing '}'."
                );
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
        // If we encounter a closing paren here it means there was no matching
        // opening paren at a higher level => unmatched parenthesis.
        if (ch === ")") {
            throw new STRlingParseError(
                "Unmatched ')'",
                cur.i,
                this.src,
                "This ')' character does not have a matching opening '('. Did you mean to escape it with '\\\\)'?"
            );
        }
        if ("|".includes(ch)) {
            this._raiseError("Unexpected token", cur.i);
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
            this._raiseError(
                `Backreference to undefined group \\${num}`,
                startPos
            );
        }

        // Anchors \b \B \A \Z
        // NOTE: lowercase '\z' is intentionally NOT treated as an anchor; it's
        // handled below as a potential unknown escape sequence per the corpus.
        if ("bBAZ".includes(nxt)) {
            const ch = cur.take();
            if (ch === "b") return new Anchor("WordBoundary");
            if (ch === "B") return new Anchor("NotWordBoundary");
            if (ch === "A") return new Anchor("AbsoluteStart");
            if (ch === "Z") return new Anchor("EndBeforeFinalNewline");
        }

        // \k<name> named backref
        if (nxt === "k") {
            cur.take();
            if (!cur.match("<")) {
                this._raiseError("Expected '<' after \\k", startPos);
            }
            const name = this._readIdentUntil(">");
            if (!cur.match(">")) {
                this._raiseError("Unterminated named backref", startPos);
            }
            if (!this._capNames.has(name)) {
                this._raiseError(
                    `Backreference to undefined group <${name}>`,
                    startPos
                );
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
                this._raiseError("Expected { after \\p/\\P", startPos);
            }
            const prop = this._readUntil("}");
            if (!cur.match("}")) {
                this._raiseError("Unterminated \\p{...}", startPos);
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

        // In extended (free-spacing) mode, an escaped space ("\\ ") should
        // be treated as a literal space character rather than an unknown
        // escape sequence. Handle that before the identity-escape check.
        if (nxt === " " && this.cur.extendedMode) {
            cur.take();
            return new Lit(" ");
        }

        // Identity escape: validate allowed identity escapes and treat next
        // char literally. If the escape is not recognized (e.g. \z), throw
        // an instructional STRlingParseError using the corpus hint.
        const allowedIdentity = new Set([
            ".",
            "\\",
            "^",
            "$",
            "*",
            "+",
            "?",
            "(",
            ")",
            "[",
            "]",
            "{",
            "}",
            "|",
            "/",
            "-",
            ":",
            ",",
        ]);
        const peekCh = cur.peek();
        if (peekCh === "") {
            this._raiseError("Unexpected end of escape", startPos);
        }
        if (!allowedIdentity.has(peekCh)) {
            // Use hint engine to provide a context-aware hint for unknown escapes
            this._raiseError(`Unknown escape sequence \\${peekCh}`, startPos);
        }
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
                this._raiseError("Unterminated \\x{...}", startPos);
            }
            const cp = parseInt(hexs || "0", 16);
            return String.fromCodePoint(cp);
        }

        // \xHH
        const h1 = cur.take();
        const h2 = cur.take();
        if (!/[0-9A-Fa-f]/.test(h1 || "") || !/[0-9A-Fa-f]/.test(h2 || "")) {
            this._raiseError("Invalid \\xHH escape", startPos);
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
                this._raiseError("Unterminated \\u{...}", startPos);
            }
            const cp = parseInt(hexs || "0", 16);
            return String.fromCodePoint(cp);
        }

        if (tp === "u") {
            const hexs = cur.take() + cur.take() + cur.take() + cur.take();
            if (hexs.length !== 4 || !/^[0-9A-Fa-f]{4}$/.test(hexs)) {
                this._raiseError("Invalid \\uHHHH escape", startPos);
            }
            return String.fromCodePoint(parseInt(hexs, 16));
        }

        if (tp === "U") {
            const hexs =
                cur.take() +
                cur.take() +
                cur.take() +
                cur.take() +
                cur.take() +
                cur.take() +
                cur.take() +
                cur.take();
            if (hexs.length !== 8 || !/^[0-9A-Fa-f]{8}$/.test(hexs)) {
                this._raiseError("Invalid \\UHHHHHHHH escape", startPos);
            }
            return String.fromCodePoint(parseInt(hexs, 16));
        }

        this._raiseError("Invalid unicode escape", startPos);
    }
    // ---- Character classes ----
    parseCharClass() {
        const cur = this.cur;
        if (cur.take() !== "[") throw new Error("Expected '['");
        let startPos = cur.i; // Position after '['

        this.cur.inClass++;

        let neg = false;
        if (cur.peek() === "^") {
            neg = true;
            cur.take();
            startPos = cur.i; // Update position after '^'
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
                this._raiseError("Unterminated character class", cur.i);
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
                    // Validate ascending order for ranges when both endpoints
                    // are letters or digits. Reject reversed ranges like [z-a]
                    // or [9-0].
                    const sc = startCh.charCodeAt(0);
                    const ec = endCh.charCodeAt(0);
                    const bothDigits =
                        /[0-9]/.test(startCh) && /[0-9]/.test(endCh);
                    const bothLetters =
                        /[A-Za-z]/.test(startCh) && /[A-Za-z]/.test(endCh);
                    if ((bothDigits || bothLetters) && sc > ec) {
                        this._raiseError("Invalid character range", cur.i);
                    }
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
                this._raiseError("Expected { after \\p/\\P", startPos);
            }
            const prop = this._readUntil("}");
            if (!cur.match("}")) {
                this._raiseError("Unterminated \\p{...}", startPos);
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
            this._raiseError(
                "Inline modifiers `(?imsx)` are not supported",
                cur.i
            );
        }

        // Non-capturing group
        if (cur.match("?:")) {
            const body = this.parseAlt();
            if (!cur.match(")")) {
                this._raiseError("Unterminated group", cur.i);
            }
            return new Group(false, body);
        }

        // Lookbehind (must be before named group)
        if (cur.match("?<=")) {
            const body = this.parseAlt();
            if (!cur.match(")")) {
                this._raiseError("Unterminated lookbehind", cur.i);
            }
            return new Look("Behind", false, body);
        }

        if (cur.match("?<!")) {
            const body = this.parseAlt();
            if (!cur.match(")")) {
                this._raiseError("Unterminated lookbehind", cur.i);
            }
            return new Look("Behind", true, body);
        }

        // Named capturing group
        if (cur.match("?<")) {
            const nameStartPos = cur.i;
            const name = this._readUntil(">");
            if (!cur.match(">")) {
                this._raiseError("Unterminated group name", cur.i);
            }
            // Validate identifier per EBNF: IDENT_START = LETTER | "_";
            // IDENT_CONT = IDENT_START | DIGIT
            if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(name)) {
                this._raiseError(`Invalid group name <${name}>`, nameStartPos);
            }
            if (this._capNames.has(name)) {
                this._raiseError(`Duplicate group name <${name}>`, cur.i);
            }
            this._capCount++;
            this._capNames.add(name);
            const body = this.parseAlt();
            if (!cur.match(")")) {
                // Unclosed named capture group -> throw a specific instructional hint
                throw new STRlingParseError(
                    "Incomplete named capture group",
                    cur.i,
                    this.src,
                    "Incomplete named capture group. Expected ')' to close the group."
                );
            }
            return new Group(true, body, name);
        }

        // Atomic group
        if (cur.match("?>")) {
            const body = this.parseAlt();
            if (!cur.match(")")) {
                this._raiseError("Unterminated atomic group", cur.i);
            }
            return new Group(false, body, null, true);
        }

        // Lookahead
        if (cur.match("?=")) {
            const body = this.parseAlt();
            if (!cur.match(")")) {
                this._raiseError("Unterminated lookahead", cur.i);
            }
            return new Look("Ahead", false, body);
        }

        if (cur.match("?!")) {
            const body = this.parseAlt();
            if (!cur.match(")")) {
                this._raiseError("Unterminated lookahead", cur.i);
            }
            return new Look("Ahead", true, body);
        }

        // Capturing group
        this._capCount++;
        const body = this.parseAlt();
        if (!cur.match(")")) {
            this._raiseError("Unterminated group", cur.i);
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
