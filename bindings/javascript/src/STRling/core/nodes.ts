/**
 * STRling AST Node Definitions
 *
 * This module defines the complete set of Abstract Syntax Tree (AST) node classes
 * that represent the parsed structure of STRling patterns. The AST is the direct
 * output of the parser and represents the syntactic structure of the pattern before
 * optimization and lowering to IR.
 *
 * AST nodes are designed to:
 *   - Closely mirror the source pattern syntax
 *   - Be easily serializable to the Base TargetArtifact schema
 *   - Provide a clean separation between parsing and compilation
 *   - Support multiple target regex flavors through the compilation pipeline
 *
 * Each AST node type corresponds to a syntactic construct in the STRling DSL
 * (alternation, sequencing, character classes, anchors, etc.) and can be
 * serialized to a dictionary representation for debugging or storage.
 */

/**
 * Container for regex flags/modifiers.
 *
 * Flags control the behavior of pattern matching (case sensitivity, multiline
 * mode, etc.). This class encapsulates all standard regex flags and provides
 * utilities for creating flags from string representations.
 */
export class Flags {
    ignoreCase: boolean;
    multiline: boolean;
    dotAll: boolean;
    unicode: boolean;
    extended: boolean;

    /**
     * Creates a new Flags instance.
     *
     * @param options - Object containing flag values (all default to false).
     */
    constructor({
        ignoreCase = false,
        multiline = false,
        dotAll = false,
        unicode = false,
        extended = false,
    }: {
        ignoreCase?: boolean;
        multiline?: boolean;
        dotAll?: boolean;
        unicode?: boolean;
        extended?: boolean;
    } = {}) {
        this.ignoreCase = ignoreCase;
        this.multiline = multiline;
        this.dotAll = dotAll;
        this.unicode = unicode;
        this.extended = extended;
    }

    /**
     * Serializes the flags to a dictionary representation.
     *
     * @returns Object containing all flag values.
     */
    toDict() {
        return {
            ignoreCase: this.ignoreCase,
            multiline: this.multiline,
            dotAll: this.dotAll,
            unicode: this.unicode,
            extended: this.extended,
        };
    }

    /**
     * Creates Flags from a string of flag letters.
     *
     * @param letters - String containing flag letters (i, m, s, u, x).
     * @returns A new Flags instance with the specified flags enabled.
     */
    static fromLetters(letters: string): Flags {
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

/**
 * Base class for all AST nodes.
 *
 * All AST nodes extend this base class and must implement the toDict() method
 * for serialization to a dictionary/object representation.
 */
export class Node {
    /**
     * Serializes the AST node to a dictionary representation.
     *
     * @returns The dictionary representation of this AST node.
     * @throws Error if not implemented by subclass.
     */
    toDict(): any {
        throw new Error("toDict() must be implemented by subclass");
    }
}

/**
 * Represents an alternation (OR) in the AST.
 *
 * Matches any one of the provided branches. Corresponds to the | operator
 * in traditional regex syntax.
 */
export class Alt extends Node {
    branches: Node[];

    /**
     * Creates an alternation AST node.
     *
     * @param branches - Array of AST nodes representing the alternative branches.
     */
    constructor(branches: Node[]) {
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
    parts: Node[];

    constructor(parts: Node[]) {
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
    value: string;

    constructor(value: string) {
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
    at: string; // "Start"|"End"|"WordBoundary"|"NotWordBoundary"|Absolute* variants

    constructor(at: string) {
        super();
        this.at = at;
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
    toDict(): any {
        throw new Error(
            "toDict() must be implemented by ClassItem subclass"
        );
    }
}

export class ClassRange extends ClassItem {
    fromCh: string;
    toCh: string;

    constructor(fromCh: string, toCh: string) {
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
    ch: string;

    constructor(ch: string) {
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
    type: string; // d D w W s S p P
    property: string | null;

    constructor(type: string, property: string | null = null) {
        super();
        this.type = type;
        this.property = property;
    }

    toDict() {
        const data: any = {
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
    negated: boolean;
    items: ClassItem[];

    constructor(negated: boolean, items: ClassItem[]) {
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
    child: Node;
    min: number;
    max: number | string; // number or "Inf" for unbounded
    mode: string; // "Greedy" | "Lazy" | "Possessive"

    constructor(child: Node, min: number, max: number | string, mode: string) {
        super();
        this.child = child;
        this.min = min;
        this.max = max;
        this.mode = mode;
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
    capturing: boolean;
    body: Node;
    name: string | null;
    atomic: boolean | null; // extension

    constructor(capturing: boolean, body: Node, name: string | null = null, atomic: boolean | null = null) {
        super();
        this.capturing = capturing;
        this.body = body;
        this.name = name;
        this.atomic = atomic;
    }

    toDict() {
        const data: any = {
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
    byIndex: number | null;
    byName: string | null;

    constructor(byIndexOrObj: number | { byIndex?: number; byName?: string } | null = null, byName: string | null = null) {
        super();
        // Handle both constructor styles: new Backref({byIndex: 1}) or new Backref(1, null)
        if (typeof byIndexOrObj === "object" && byIndexOrObj !== null) {
            this.byIndex = byIndexOrObj.byIndex || null;
            this.byName = byIndexOrObj.byName || null;
        } else {
            this.byIndex = byIndexOrObj;
            this.byName = byName;
        }
    }

    toDict() {
        const data: any = { kind: "Backref" };
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
    dir: string; // "Ahead" | "Behind"
    neg: boolean;
    body: Node;

    constructor(dir: string, neg: boolean, body: Node) {
        super();
        this.dir = dir;
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
