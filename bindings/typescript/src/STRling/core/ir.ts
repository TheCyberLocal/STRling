/**
 * STRling Intermediate Representation (IR) Node Definitions
 *
 * This module defines the complete set of IR node classes that represent
 * language-agnostic regex constructs. The IR serves as an intermediate layer
 * between the parsed AST and the target-specific emitters (e.g., PCRE2).
 *
 * IR nodes are designed to be:
 *   - Simple and composable
 *   - Easy to serialize (via toDict methods)
 *   - Independent of any specific regex flavor
 *   - Optimized for transformation and analysis
 *
 * Each IR node corresponds to a fundamental regex operation (alternation,
 * sequencing, character classes, quantification, etc.) and can be serialized
 * to a dictionary representation for further processing or debugging.
 */

/**
 * Base class for all IR operations.
 *
 * All IR nodes extend this base class and must implement the toDict() method
 * for serialization to a dictionary/object representation.
 */
export class IROp {
    /**
     * Serializes the IR node to a dictionary representation.
     *
     * @returns The dictionary representation of this IR node.
     * @throws Error if not implemented by subclass.
     */
    toDict(): any {
        throw new Error("toDict() must be implemented by subclass");
    }
}

/**
 * Represents an alternation (OR) operation in the IR.
 *
 * Matches any one of the provided branches. Equivalent to the | operator
 * in traditional regex syntax.
 */
export class IRAlt extends IROp {
    branches: IROp[];

    /**
     * Creates an alternation IR node.
     *
     * @param branches - Array of IR nodes representing the alternative branches.
     */
    constructor(branches: IROp[]) {
        super();
        this.branches = branches;
    }

    toDict() {
        return {
            ir: "Alt",
            branches: this.branches.map((b) => b.toDict()),
        };
    }
}

/**
 * Represents a sequence (concatenation) operation in the IR.
 *
 * Matches all parts in order. Equivalent to concatenating patterns
 * in traditional regex syntax.
 */
export class IRSeq extends IROp {
    parts: IROp[];

    /**
     * Creates a sequence IR node.
     *
     * @param parts - Array of IR nodes to be matched sequentially.
     */
    constructor(parts: IROp[]) {
        super();
        this.parts = parts;
    }

    toDict() {
        return {
            ir: "Seq",
            parts: this.parts.map((p) => p.toDict()),
        };
    }
}

/**
 * Represents a literal string in the IR.
 *
 * Matches the exact string value with all characters treated as literals
 * (no special regex meaning).
 */
export class IRLit extends IROp {
    value: string;

    /**
     * Creates a literal IR node.
     *
     * @param value - The literal string to match.
     */
    constructor(value: string) {
        super();
        this.value = value;
    }

    toDict() {
        return {
            ir: "Lit",
            value: this.value,
        };
    }
}

/**
 * Represents the "any character" wildcard in the IR.
 *
 * Matches any single character (behavior may depend on flags like dotall).
 * Equivalent to the . metacharacter in traditional regex.
 */
export class IRDot extends IROp {
    toDict() {
        return {
            ir: "Dot",
        };
    }
}

/**
 * Represents an anchor (position assertion) in the IR.
 *
 * Matches a position rather than a character. Common anchors include
 * start of line (^), end of line ($), word boundaries (\b), etc.
 */
export class IRAnchor extends IROp {
    at: string;

    /**
     * Creates an anchor IR node.
     *
     * @param at - The anchor type (e.g., "Start", "End", "WordBoundary").
     */
    constructor(at: string) {
        super();
        this.at = at;
    }

    toDict() {
        return {
            ir: "Anchor",
            at: this.at,
        };
    }
}

/**
 * Base class for character class items.
 *
 * Character class items represent the individual components that can appear
 * inside a character class (ranges, literals, or escape sequences).
 */
export class IRClassItem {
    /**
     * Serializes the character class item to a dictionary representation.
     *
     * @returns The dictionary representation of this item.
     * @throws Error if not implemented by subclass.
     */
    toDict(): any {
        throw new Error("toDict() must be implemented by IRClassItem subclass");
    }
}

/**
 * Represents a character range in a character class.
 *
 * Matches any character between fromCh and toCh inclusive (e.g., a-z, 0-9).
 */
export class IRClassRange extends IRClassItem {
    fromCh: string;
    toCh: string;

    /**
     * Creates a character range item.
     *
     * @param fromCh - The starting character of the range.
     * @param toCh - The ending character of the range.
     */
    constructor(fromCh: string, toCh: string) {
        super();
        this.fromCh = fromCh;
        this.toCh = toCh;
    }

    toDict() {
        return {
            ir: "Range",
            from: this.fromCh,
            to: this.toCh,
        };
    }
}

/**
 * Represents a single literal character in a character class.
 *
 * Matches exactly the specified character.
 */
export class IRClassLiteral extends IRClassItem {
    ch: string;

    /**
     * Creates a literal character item.
     *
     * @param ch - The literal character to match.
     */
    constructor(ch: string) {
        super();
        this.ch = ch;
    }

    toDict() {
        return {
            ir: "Char",
            char: this.ch,
        };
    }
}

/**
 * Represents an escape sequence in a character class.
 *
 * Handles special character class escapes like \d, \w, \s, or Unicode
 * property escapes like \p{Letter}.
 */
export class IRClassEscape extends IRClassItem {
    type: string;
    property: string | null;

    /**
     * Creates an escape sequence item.
     *
     * @param type - The escape type (e.g., "Digit", "Word", "Whitespace", "UnicodeProperty").
     * @param property - The Unicode property name if type is "UnicodeProperty".
     */
    constructor(type: string, property: string | null = null) {
        super();
        this.type = type;
        this.property = property;
    }

    toDict() {
        const d: any = {
            ir: "Esc",
            type: this.type,
        };
        if (this.property) {
            d.property = this.property;
        }
        return d;
    }
}

/**
 * Represents a character class (set of characters) in the IR.
 *
 * Matches any single character from the set defined by its items.
 * Can be negated to match any character NOT in the set.
 */
export class IRCharClass extends IROp {
    negated: boolean;
    items: IRClassItem[];

    /**
     * Creates a character class IR node.
     *
     * @param negated - Whether the character class is negated (matches characters NOT in the set).
     * @param items - Array of character class items (ranges, literals, escapes).
     */
    constructor(negated: boolean, items: IRClassItem[]) {
        super();
        this.negated = negated;
        this.items = items;
    }

    toDict() {
        return {
            ir: "CharClass",
            negated: this.negated,
            items: this.items.map((i) => i.toDict()),
        };
    }
}

/**
 * Represents a quantifier (repetition) in the IR.
 *
 * Specifies how many times the child pattern should be matched.
 * Supports greedy, lazy, and possessive matching modes.
 */
export class IRQuant extends IROp {
    child: IROp;
    min: number;
    max: number | string;
    mode: string;

    /**
     * Creates a quantifier IR node.
     *
     * @param child - The IR node to be quantified.
     * @param min - Minimum number of repetitions.
     * @param max - Maximum number of repetitions (number or "Inf" for unlimited).
     * @param mode - Matching mode: "Greedy", "Lazy", or "Possessive".
     */
    constructor(child: IROp, min: number, max: number | string, mode: string) {
        super();
        this.child = child;
        this.min = min;
        this.max = max;
        this.mode = mode; // Greedy|Lazy|Possessive
    }

    toDict() {
        return {
            ir: "Quant",
            child: this.child.toDict(),
            min: this.min,
            max: this.max,
            mode: this.mode,
        };
    }
}

/**
 * Represents a group (capturing or non-capturing) in the IR.
 *
 * Groups are used for capturing matched text, applying quantifiers to
 * multiple elements, or creating atomic groups for backtracking control.
 */
export class IRGroup extends IROp {
    capturing: boolean;
    body: IROp;
    name: string | null;
    atomic: boolean | null;

    /**
     * Creates a group IR node.
     *
     * @param capturing - Whether this group captures its match.
     * @param body - The IR node contained within the group.
     * @param name - Optional name for named capture groups.
     * @param atomic - Whether this is an atomic group (prevents backtracking).
     */
    constructor(capturing: boolean, body: IROp, name: string | null = null, atomic: boolean | null = null) {
        super();
        this.capturing = capturing;
        this.body = body;
        this.name = name;
        this.atomic = atomic;
    }

    toDict() {
        const d: any = {
            ir: "Group",
            capturing: this.capturing,
            body: this.body.toDict(),
        };
        if (this.name !== null) {
            d.name = this.name;
        }
        if (this.atomic !== null) {
            d.atomic = this.atomic;
        }
        return d;
    }
}

/**
 * Represents a backreference in the IR.
 *
 * References a previously captured group by index or name, matching
 * the exact same text that was captured by that group.
 */
export class IRBackref extends IROp {
    byIndex: number | null;
    byName: string | null;

    /**
     * Creates a backreference IR node.
     *
     * @param byIndexOrObj - Either a numeric group index, an object with byIndex/byName properties,
     *                       or null.
     * @param byName - The name of the group to reference (if using positional arguments).
     */
    constructor(byIndexOrObj: number | { byIndex?: number; byName?: string } | null = null, byName: string | null = null) {
        super();
        // Handle both constructor styles: new IRBackref({byIndex: 1}) or new IRBackref(1, null)
        if (typeof byIndexOrObj === "object" && byIndexOrObj !== null) {
            this.byIndex = byIndexOrObj.byIndex || null;
            this.byName = byIndexOrObj.byName || null;
        } else {
            this.byIndex = byIndexOrObj;
            this.byName = byName;
        }
    }

    toDict() {
        const d: any = { ir: "Backref" };
        if (this.byIndex !== null) {
            d.byIndex = this.byIndex;
        }
        if (this.byName !== null) {
            d.byName = this.byName;
        }
        return d;
    }
}

/**
 * Represents a lookaround assertion in the IR.
 *
 * Lookarounds are zero-width assertions that check for pattern presence
 * or absence without consuming characters. They can look ahead or behind,
 * and can be positive or negative.
 */
export class IRLook extends IROp {
    dir: string;
    neg: boolean;
    body: IROp;

    /**
     * Creates a lookaround IR node.
     *
     * @param dir - Direction: "Ahead" for lookahead or "Behind" for lookbehind.
     * @param neg - Whether this is a negative assertion (pattern must NOT match).
     * @param body - The IR node to look for.
     */
    constructor(dir: string, neg: boolean, body: IROp) {
        super();
        this.dir = dir;
        this.neg = neg;
        this.body = body;
    }

    toDict() {
        return {
            ir: "Look",
            dir: this.dir,
            neg: this.neg,
            body: this.body.toDict(),
        };
    }
}
