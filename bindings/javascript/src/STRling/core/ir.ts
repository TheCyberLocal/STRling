/**
 * STRling v3 — IR node definitions
 * Intermediate representation (language-agnostic regex constructs).
 * 
 * Ported from Python reference implementation.
 */

// Base class for IR nodes
export class IROp {
    toDict() {
        throw new Error("toDict() must be implemented by subclass");
    }
}

export class IRAlt extends IROp {
    constructor(branches) {
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

export class IRSeq extends IROp {
    constructor(parts) {
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

export class IRLit extends IROp {
    constructor(value) {
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

export class IRDot extends IROp {
    toDict() {
        return {
            ir: "Dot",
        };
    }
}

export class IRAnchor extends IROp {
    constructor(at) {
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

export class IRClassItem {
    toDict() {
        throw new Error("toDict() must be implemented by IRClassItem subclass");
    }
}

export class IRClassRange extends IRClassItem {
    constructor(fromCh, toCh) {
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

export class IRClassLiteral extends IRClassItem {
    constructor(ch) {
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

export class IRClassEscape extends IRClassItem {
    constructor(type, property = null) {
        super();
        this.type = type;
        this.property = property;
    }

    toDict() {
        const d = {
            ir: "Esc",
            type: this.type,
        };
        if (this.property) {
            d.property = this.property;
        }
        return d;
    }
}

export class IRCharClass extends IROp {
    constructor(negated, items) {
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

export class IRQuant extends IROp {
    constructor(child, min, max, mode) {
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

export class IRGroup extends IROp {
    constructor(capturing, body, name = null, atomic = null) {
        super();
        this.capturing = capturing;
        this.body = body;
        this.name = name;
        this.atomic = atomic;
    }

    toDict() {
        const d = {
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

export class IRBackref extends IROp {
    constructor(byIndexOrObj = null, byName = null) {
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
        const d = { ir: "Backref" };
        if (this.byIndex !== null) {
            d.byIndex = this.byIndex;
        }
        if (this.byName !== null) {
            d.byName = this.byName;
        }
        return d;
    }
}

export class IRLook extends IROp {
    constructor(dir, neg, body) {
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
