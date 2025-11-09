/**
 * STRling v3 — AST node definitions (Sprint 3)
 * The AST serializes to the Base TargetArtifact schema's Node defs.
 *
 * Ported from Python reference implementation.
 */

// ---- Flags container ----
export class Flags {
    constructor({
        ignoreCase = false,
        multiline = false,
        dotAll = false,
        unicode = false,
        extended = false,
    } = {}) {
        this.ignoreCase = ignoreCase;
        this.multiline = multiline;
        this.dotAll = dotAll;
        this.unicode = unicode;
        this.extended = extended;
    }

    toDict() {
        return {
            ignoreCase: this.ignoreCase,
            multiline: this.multiline,
            dotAll: this.dotAll,
            unicode: this.unicode,
            extended: this.extended,
        };
    }

    static fromLetters(letters) {
        const f = new Flags();
        for (const ch of letters.replace(/[, ]/g, "")) {
            if (ch === "i") {
                f.ignoreCase = true;
            } else if (ch === "m") {
                f.multiline = true;
            } else if (ch === "s") {
                f.dotAll = true;
            } else if (ch === "u") {
                f.unicode = true;
            } else if (ch === "x") {
                f.extended = true;
            } else if (ch === "") {
                // Empty string, skip
            } else {
                // Unknown flags are ignored at parser stage; may be warned later
            }
        }
        return f;
    }
}

// ---- Base node ----
export class Node {
    toDict() {
        throw new Error("toDict() must be implemented by subclass");
    }
}

// ---- Concrete nodes matching Base Schema ----
export class Alt extends Node {
    constructor(branches) {
        super();
        this.branches = branches;
    }

    toDict() {
        return {
            kind: "Alt",
            branches: this.branches.map((b) => b.toDict()),
        };
    }
}

export class Seq extends Node {
    constructor(parts) {
        super();
        this.parts = parts;
    }

    toDict() {
        return {
            kind: "Seq",
            parts: this.parts.map((p) => p.toDict()),
        };
    }
}

export class Lit extends Node {
    constructor(value) {
        super();
        this.value = value;
    }

    toDict() {
        return {
            kind: "Lit",
            value: this.value,
        };
    }
}

export class Dot extends Node {
    toDict() {
        return {
            kind: "Dot",
        };
    }
}

export class Anchor extends Node {
    constructor(at) {
        super();
        this.at = at; // "Start"|"End"|"WordBoundary"|"NotWordBoundary"|Absolute* variants
    }

    toDict() {
        return {
            kind: "Anchor",
            at: this.at,
        };
    }
}

// --- CharClass --
export class ClassItem {
    toDict() {
        throw new Error(
            "toDict() must be implemented by ClassItem subclass"
        );
    }
}

export class ClassRange extends ClassItem {
    constructor(fromCh, toCh) {
        super();
        this.fromCh = fromCh;
        this.toCh = toCh;
    }

    toDict() {
        return {
            kind: "Range",
            from: this.fromCh,
            to: this.toCh,
        };
    }
}

export class ClassLiteral extends ClassItem {
    constructor(ch) {
        super();
        this.ch = ch;
    }

    toDict() {
        return {
            kind: "Char",
            char: this.ch,
        };
    }
}

export class ClassEscape extends ClassItem {
    constructor(type, property = null) {
        super();
        this.type = type; // d D w W s S p P
        this.property = property;
    }

    toDict() {
        const data = {
            kind: "Esc",
            type: this.type,
        };
        if (["p", "P"].includes(this.type) && this.property) {
            data.property = this.property;
        }
        return data;
    }
}

export class CharClass extends Node {
    constructor(negated, items) {
        super();
        this.negated = negated;
        this.items = items;
    }

    toDict() {
        return {
            kind: "CharClass",
            negated: this.negated,
            items: this.items.map((it) => it.toDict()),
        };
    }
}

export class Quant extends Node {
    constructor(child, min, max, mode) {
        super();
        this.child = child;
        this.min = min;
        this.max = max; // number or "Inf" for unbounded
        this.mode = mode; // "Greedy" | "Lazy" | "Possessive"
    }

    toDict() {
        return {
            kind: "Quant",
            child: this.child.toDict(),
            min: this.min,
            max: this.max,
            mode: this.mode,
        };
    }
}

export class Group extends Node {
    constructor(capturing, body, name = null, atomic = null) {
        super();
        this.capturing = capturing;
        this.body = body;
        this.name = name;
        this.atomic = atomic; // extension
    }

    toDict() {
        const data = {
            kind: "Group",
            capturing: this.capturing,
            body: this.body.toDict(),
        };
        if (this.name !== null) {
            data.name = this.name;
        }
        if (this.atomic !== null) {
            data.atomic = this.atomic;
        }
        return data;
    }
}

export class Backref extends Node {
    constructor(byIndex = null, byName = null) {
        super();
        this.byIndex = byIndex;
        this.byName = byName;
    }

    toDict() {
        const data = { kind: "Backref" };
        if (this.byIndex !== null) {
            data.byIndex = this.byIndex;
        }
        if (this.byName !== null) {
            data.byName = this.byName;
        }
        return data;
    }
}

export class Look extends Node {
    constructor(dir, neg, body) {
        super();
        this.dir = dir; // "Ahead" | "Behind"
        this.neg = neg;
        this.body = body;
    }

    toDict() {
        return {
            kind: "Look",
            dir: this.dir,
            neg: this.neg,
            body: this.body.toDict(),
        };
    }
}
