/**
 * STRling v3 — Compiler
 * AST -> IR lowering with normalization:
 *  - Flatten nested Seq/Alt
 *  - Coalesce adjacent Lit nodes
 *  - Ensure quantifier children are grouped appropriately
 * 
 * Ported from Python reference implementation.
 */

import * as N from "./nodes.js";
import * as IR from "./ir.js";

export class Compiler {
    constructor() {
        this.featuresUsed = new Set();
    }

    compileWithMetadata(rootNode) {
        /**
         * Compiles the AST and returns a full artifact with metadata.
         */
        let irRoot = this._lower(rootNode);
        irRoot = this._normalize(irRoot);

        // Analyze the final IR tree for special features
        this._analyzeFeatures(irRoot);

        return {
            ir: irRoot, // Return the IR object, not a dict
            metadata: { features_used: Array.from(this.featuresUsed).sort() },
        };
    }

    _analyzeFeatures(node) {
        /**
         * Recursively walk the IR tree and log features used.
         */
        if (node instanceof IR.IRGroup) {
            if (node.atomic) {
                this.featuresUsed.add("atomic_group");
            }
            if (node.name !== null) {
                this.featuresUsed.add("named_group");
            }
        }
        if (node instanceof IR.IRQuant && node.mode === "Possessive") {
            this.featuresUsed.add("possessive_quantifier");
        }
        if (node instanceof IR.IRLook) {
            if (node.dir === "Behind") {
                this.featuresUsed.add("lookbehind");
            } else if (node.dir === "Ahead") {
                this.featuresUsed.add("lookahead");
            }
        }
        if (node instanceof IR.IRBackref) {
            this.featuresUsed.add("backreference");
        }
        if (node instanceof IR.IRCharClass) {
            // Check for Unicode property escapes in character class items
            for (const item of node.items) {
                if (item instanceof IR.IRClassEscape && item.type === "UnicodeProperty") {
                    this.featuresUsed.add("unicode_property");
                }
            }
        }

        // Recurse into children
        if (node instanceof IR.IRSeq) {
            for (const child of node.parts) {
                this._analyzeFeatures(child);
            }
        } else if (node instanceof IR.IRAlt) {
            for (const child of node.branches) {
                this._analyzeFeatures(child);
            }
        } else if (node instanceof IR.IRQuant) {
            this._analyzeFeatures(node.child);
        } else if (node instanceof IR.IRGroup || node instanceof IR.IRLook) {
            this._analyzeFeatures(node.body);
        }
    }

    compile(root) {
        let ir = this._lower(root);
        ir = this._normalize(ir);
        return ir;
    }

    // ---------- Lowering (AST -> IR) ----------
    _lower(node) {
        const t = node.constructor.name;
        
        if (t === "Seq") {
            return new IR.IRSeq(node.parts.map((p) => this._lower(p)));
        }
        if (t === "Alt") {
            return new IR.IRAlt(node.branches.map((b) => this._lower(b)));
        }
        if (t === "Lit") {
            return new IR.IRLit(node.value);
        }
        if (t === "Dot") {
            return new IR.IRDot();
        }
        if (t === "Anchor") {
            return new IR.IRAnchor(node.at);
        }
        if (t === "CharClass") {
            const items = [];
            for (const it of node.items) {
                const itT = it.constructor.name;
                if (itT === "ClassRange") {
                    items.push(new IR.IRClassRange(it.fromCh, it.toCh));
                } else if (itT === "ClassLiteral") {
                    items.push(new IR.IRClassLiteral(it.ch));
                } else if (itT === "ClassEscape") {
                    items.push(new IR.IRClassEscape(it.type, it.property));
                } else {
                    throw new Error(`Unknown class item ${itT}`);
                }
            }
            return new IR.IRCharClass(node.negated, items);
        }
        if (t === "Quant") {
            return new IR.IRQuant(
                this._lower(node.child),
                node.min,
                node.max,
                node.mode
            );
        }
        if (t === "Group") {
            return new IR.IRGroup(
                node.capturing,
                this._lower(node.body),
                node.name,
                node.atomic
            );
        }
        if (t === "Backref") {
            return new IR.IRBackref(node.byIndex, node.byName);
        }
        if (t === "Look") {
            return new IR.IRLook(node.dir, node.neg, this._lower(node.body));
        }
        throw new Error(`No lowering for AST node ${t}`);
    }

    // ---------- Normalization ----------
    _normalize(node) {
        /**
         * Flatten alt/seq and fuse adjacent literals.
         */
        if (node instanceof IR.IRSeq) {
            const parts = [];
            for (const p of node.parts) {
                const pNorm = this._normalize(p);
                if (pNorm instanceof IR.IRSeq) {
                    parts.push(...pNorm.parts);
                } else {
                    parts.push(pNorm);
                }
            }
            
            const fused = [];
            let buf = "";
            for (const p of parts) {
                if (p instanceof IR.IRLit) {
                    buf += p.value;
                } else {
                    if (buf) {
                        fused.push(new IR.IRLit(buf));
                        buf = "";
                    }
                    fused.push(p);
                }
            }
            if (buf) {
                fused.push(new IR.IRLit(buf));
            }
            return fused.length === 1 ? fused[0] : new IR.IRSeq(fused);
        }
        
        if (node instanceof IR.IRAlt) {
            const branches = [];
            for (const b of node.branches) {
                const bNorm = this._normalize(b);
                if (bNorm instanceof IR.IRAlt) {
                    branches.push(...bNorm.branches);
                } else {
                    branches.push(bNorm);
                }
            }
            return branches.length === 1 ? branches[0] : new IR.IRAlt(branches);
        }
        
        if (node instanceof IR.IRQuant) {
            const child = this._normalize(node.child);
            return new IR.IRQuant(child, node.min, node.max, node.mode);
        }
        
        if (node instanceof IR.IRGroup) {
            return new IR.IRGroup(
                node.capturing,
                this._normalize(node.body),
                node.name,
                node.atomic
            );
        }
        
        if (node instanceof IR.IRLook) {
            return new IR.IRLook(node.dir, node.neg, this._normalize(node.body));
        }
        
        return node;
    }
}
