/**
 * STRling Compiler - AST to IR Transformation
 *
 * This module implements the compiler that transforms Abstract Syntax Tree (AST)
 * nodes from the parser into an optimized Intermediate Representation (IR). The
 * compilation process includes:
 *   - Lowering AST nodes to IR operations
 *   - Flattening nested sequences and alternations
 *   - Coalescing adjacent literal nodes for efficiency
 *   - Ensuring quantifier children are properly grouped
 *   - Analyzing and tracking regex features used
 *
 * The IR is designed to be easily consumed by target emitters (e.g., PCRE2)
 * while maintaining semantic accuracy and enabling optimizations.
 */

import * as N from "./nodes.js";
import * as IR from "./ir.js";

/**
 * Compiler for transforming AST nodes into optimized IR.
 *
 * The Compiler class handles the complete transformation pipeline from parsed
 * AST to normalized IR, including feature detection for metadata generation.
 */
export class Compiler {
    featuresUsed: Set<string>;

    /**
     * Creates a new Compiler instance.
     */
    constructor() {
        this.featuresUsed = new Set();
    }

    /**
     * Compiles an AST node and returns IR with metadata.
     *
     * This is the main entry point for compilation with full metadata tracking.
     * It performs lowering, normalization, and feature analysis.
     *
     * @param rootNode - The root AST node to compile.
     * @returns An object containing the compiled IR and metadata about features used.
     */
    compileWithMetadata(rootNode: N.Node): { ir: IR.IROp; metadata: { features_used: string[] } } {
        let irRoot = this._lower(rootNode);
        irRoot = this._normalize(irRoot);

        // Analyze the final IR tree for special features
        this._analyzeFeatures(irRoot);

        return {
            ir: irRoot, // Return the IR object, not a dict
            metadata: { features_used: Array.from(this.featuresUsed).sort() },
        };
    }

    /**
     * Recursively analyzes the IR tree to detect and log features used.
     *
     * This method walks the entire IR tree and identifies special regex features
     * that are being used (e.g., named groups, lookarounds, atomic groups).
     * The detected features are stored in the featuresUsed set for metadata.
     *
     * @param node - The IR node to analyze.
     */
    _analyzeFeatures(node: IR.IROp): void {
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

    /**
     * Compiles an AST node into optimized IR.
     *
     * This is the standard compilation entry point without metadata tracking.
     * Performs lowering and normalization but doesn't analyze features.
     *
     * @param root - The root AST node to compile.
     * @returns The compiled and normalized IR tree.
     */
    compile(root: N.Node): IR.IROp {
        let ir = this._lower(root);
        ir = this._normalize(ir);
        return ir;
    }

    // ---------- Lowering (AST -> IR) ----------
    /**
     * Lowers an AST node to its IR equivalent.
     *
     * This method recursively transforms AST nodes into their corresponding
     * IR operations. Each AST node type is mapped to an IR operation that
     * represents the same semantic meaning but in a form optimized for
     * emission to target regex engines.
     *
     * @param node - The AST node to lower.
     * @returns The corresponding IR operation.
     * @throws Error if an unknown AST node type is encountered.
     */
    _lower(node: N.Node): IR.IROp {
        const t = node.constructor.name;
        
        if (t === "Seq") {
            return new IR.IRSeq((node as N.Seq).parts.map((p) => this._lower(p)));
        }
        if (t === "Alt") {
            return new IR.IRAlt((node as N.Alt).branches.map((b) => this._lower(b)));
        }
        if (t === "Lit") {
            return new IR.IRLit((node as N.Lit).value);
        }
        if (t === "Dot") {
            return new IR.IRDot();
        }
        if (t === "Anchor") {
            return new IR.IRAnchor((node as N.Anchor).at);
        }
        if (t === "CharClass") {
            const charClass = node as N.CharClass;
            const items: IR.IRClassItem[] = [];
            for (const it of charClass.items) {
                const itT = it.constructor.name;
                if (itT === "ClassRange") {
                    const range = it as N.ClassRange;
                    items.push(new IR.IRClassRange(range.fromCh, range.toCh));
                } else if (itT === "ClassLiteral") {
                    const lit = it as N.ClassLiteral;
                    items.push(new IR.IRClassLiteral(lit.ch));
                } else if (itT === "ClassEscape") {
                    const esc = it as N.ClassEscape;
                    items.push(new IR.IRClassEscape(esc.type, esc.property));
                } else {
                    throw new Error(`Unknown class item ${itT}`);
                }
            }
            return new IR.IRCharClass(charClass.negated, items);
        }
        if (t === "Quant") {
            const quant = node as N.Quant;
            return new IR.IRQuant(
                this._lower(quant.child),
                quant.min,
                quant.max,
                quant.mode
            );
        }
        if (t === "Group") {
            const group = node as N.Group;
            return new IR.IRGroup(
                group.capturing,
                this._lower(group.body),
                group.name,
                group.atomic
            );
        }
        if (t === "Backref") {
            const backref = node as N.Backref;
            return new IR.IRBackref(backref.byIndex, backref.byName);
        }
        if (t === "Look") {
            const look = node as N.Look;
            return new IR.IRLook(look.dir, look.neg, this._lower(look.body));
        }
        throw new Error(`No lowering for AST node ${t}`);
    }

    // ---------- Normalization ----------
    /**
     * Normalizes an IR tree by flattening and coalescing.
     *
     * This method performs several optimization passes on the IR tree:
     *   - Flattens nested sequences (Seq within Seq) and alternations (Alt within Alt)
     *   - Coalesces adjacent literal nodes into single literals for efficiency
     *   - Recursively normalizes all child nodes
     *
     * These optimizations reduce the complexity of the IR tree while maintaining
     * semantic equivalence, making it easier for emitters to generate efficient
     * target regex code.
     *
     * @param node - The IR node to normalize.
     * @returns The normalized IR node.
     */
    _normalize(node: IR.IROp): IR.IROp {
        if (node instanceof IR.IRSeq) {
            const parts: IR.IROp[] = [];
            for (const p of node.parts) {
                const pNorm: IR.IROp = this._normalize(p);
                if (pNorm instanceof IR.IRSeq) {
                    parts.push(...pNorm.parts);
                } else {
                    parts.push(pNorm);
                }
            }
            
            const fused: IR.IROp[] = [];
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
            const branches: IR.IROp[] = [];
            for (const b of node.branches) {
                const bNorm: IR.IROp = this._normalize(b);
                if (bNorm instanceof IR.IRAlt) {
                    branches.push(...bNorm.branches);
                } else {
                    branches.push(bNorm);
                }
            }
            return branches.length === 1 ? branches[0] : new IR.IRAlt(branches);
        }
        
        if (node instanceof IR.IRQuant) {
            const child: IR.IROp = this._normalize(node.child);
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
