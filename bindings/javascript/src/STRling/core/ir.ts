/**
 * STRling v3 — IR node definitions
 * Intermediate representation (language-agnostic regex constructs).
 * 
 * Ported from Python reference implementation.
 */

// Base class for IR nodes
export class IROp {
    toDict(): any {
        throw new Error("toDict() must be implemented by subclass");
    }
}

export class IRAlt extends IROp {
    branches: IROp[];

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

export class IRSeq extends IROp {
    parts: IROp[];

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

export class IRLit extends IROp {
    value: string;

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

export class IRDot extends IROp {
    toDict() {
        return {
            ir: "Dot",
        };
    }
}

export class IRAnchor extends IROp {
    at: string;

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

export class IRClassItem {
    toDict(): any {
        throw new Error("toDict() must be implemented by IRClassItem subclass");
    }
}

export class IRClassRange extends IRClassItem {
    fromCh: string;
    toCh: string;

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

export class IRClassLiteral extends IRClassItem {
    ch: string;

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

export class IRClassEscape extends IRClassItem {
    type: string;
    property: string | null;

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

export class IRCharClass extends IROp {
    negated: boolean;
    items: IRClassItem[];

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

export class IRQuant extends IROp {
    child: IROp;
    min: number;
    max: number | string;
    mode: string;

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

export class IRGroup extends IROp {
    capturing: boolean;
    body: IROp;
    name: string | null;
    atomic: boolean | null;

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

export class IRBackref extends IROp {
    byIndex: number | null;
    byName: string | null;

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

export class IRLook extends IROp {
    dir: string;
    neg: boolean;
    body: IROp;

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
