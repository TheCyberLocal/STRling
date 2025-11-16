package com.strling.core;

import com.strling.core.Nodes.*;
import com.strling.core.IR.*;

import java.util.*;

/**
 * STRling Compiler - AST to IR Transformation.
 * 
 * <p>This module implements the compiler that transforms Abstract Syntax Tree (AST)
 * nodes from the parser into an optimized Intermediate Representation (IR). The
 * compilation process includes:</p>
 * <ul>
 *   <li>Lowering AST nodes to IR operations</li>
 *   <li>Flattening nested sequences and alternations</li>
 *   <li>Coalescing adjacent literal nodes for efficiency</li>
 *   <li>Ensuring quantifier children are properly grouped</li>
 *   <li>Analyzing and tracking regex features used</li>
 * </ul>
 * 
 * <p>The IR is designed to be easily consumed by target emitters (e.g., PCRE2)
 * while maintaining semantic accuracy and enabling optimizations.</p>
 */
public class Compiler {
    
    private Set<String> featuresUsed;
    
    /**
     * Create a new Compiler instance.
     */
    public Compiler() {
        this.featuresUsed = new HashSet<>();
    }
    
    /**
     * Compile an AST node and return IR with metadata.
     * 
     * <p>This is the main entry point for compilation with full metadata tracking.
     * It performs lowering, normalization, and feature analysis.</p>
     * 
     * @param rootNode The root AST node to compile
     * @return Map containing the compiled IR and metadata about features used
     */
    public Map<String, Object> compileWithMetadata(Node rootNode) {
        IROp irRoot = lower(rootNode);
        irRoot = normalize(irRoot);
        
        // Analyze the final IR tree for special features
        analyzeFeatures(irRoot);
        
        Map<String, Object> result = new HashMap<>();
        result.put("ir", irRoot);
        
        Map<String, Object> metadata = new HashMap<>();
        List<String> featuresList = new ArrayList<>(featuresUsed);
        Collections.sort(featuresList);
        metadata.put("features_used", featuresList);
        result.put("metadata", metadata);
        
        return result;
    }
    
    /**
     * Compile an AST node to IR without metadata.
     * 
     * @param root The root AST node to compile
     * @return The compiled IR node
     */
    public IROp compile(Node root) {
        IROp ir = lower(root);
        ir = normalize(ir);
        return ir;
    }
    
    /**
     * Lower an AST node to IR (direct translation).
     * Public for testing (TypeScript uses @ts-ignore for private access).
     * 
     * @param node The AST node to lower
     * @return The corresponding IR node
     */
    public IROp lower(Node node) {
        if (node instanceof Lit) {
            return new IRLit(((Lit) node).value);
        }
        if (node instanceof Dot) {
            return new IRDot();
        }
        if (node instanceof Anchor) {
            return new IRAnchor(((Anchor) node).at);
        }
        if (node instanceof CharClass) {
            CharClass cc = (CharClass) node;
            List<IRClassItem> irItems = new ArrayList<>();
            for (ClassItem item : cc.items) {
                if (item instanceof ClassRange) {
                    ClassRange r = (ClassRange) item;
                    irItems.add(new IRClassRange(r.fromCh, r.toCh));
                } else if (item instanceof ClassLiteral) {
                    ClassLiteral l = (ClassLiteral) item;
                    irItems.add(new IRClassLiteral(l.ch));
                } else if (item instanceof ClassEscape) {
                    ClassEscape e = (ClassEscape) item;
                    if (e.property != null) {
                        // Unicode property - mark type as "UnicodeProperty" for feature detection
                        irItems.add(new IRClassEscape("UnicodeProperty", e.property));
                    } else {
                        irItems.add(new IRClassEscape(e.type));
                    }
                }
            }
            return new IRCharClass(cc.negated, irItems);
        }
        if (node instanceof Seq) {
            Seq seq = (Seq) node;
            List<IROp> irParts = new ArrayList<>();
            for (Node part : seq.parts) {
                irParts.add(lower(part));
            }
            return new IRSeq(irParts);
        }
        if (node instanceof Alt) {
            Alt alt = (Alt) node;
            List<IROp> irBranches = new ArrayList<>();
            for (Node branch : alt.branches) {
                irBranches.add(lower(branch));
            }
            return new IRAlt(irBranches);
        }
        if (node instanceof Quant) {
            Quant q = (Quant) node;
            return new IRQuant(lower(q.child), q.min, q.max, q.mode);
        }
        if (node instanceof Group) {
            Group g = (Group) node;
            return new IRGroup(g.capturing, lower(g.body), g.name, g.atomic);
        }
        if (node instanceof Backref) {
            Backref b = (Backref) node;
            return new IRBackref(b.byIndex, b.byName);
        }
        if (node instanceof Look) {
            Look l = (Look) node;
            return new IRLook(l.dir, l.neg, lower(l.body));
        }
        
        throw new IllegalArgumentException("Unknown AST node type: " + node.getClass().getName());
    }
    
    /**
     * Normalize IR (flatten sequences/alternations, coalesce literals).
     * Public for testing (TypeScript uses @ts-ignore for private access).
     * 
     * @param node The IR node to normalize
     * @return The normalized IR node
     */
    public IROp normalize(IROp node) {
        if (node instanceof IRSeq) {
            return normalizeSeq((IRSeq) node);
        }
        if (node instanceof IRAlt) {
            return normalizeAlt((IRAlt) node);
        }
        if (node instanceof IRQuant) {
            IRQuant q = (IRQuant) node;
            return new IRQuant(normalize(q.child), q.min, q.max, q.mode);
        }
        if (node instanceof IRGroup) {
            IRGroup g = (IRGroup) node;
            return new IRGroup(g.capturing, normalize(g.body), g.name, g.atomic);
        }
        if (node instanceof IRLook) {
            IRLook l = (IRLook) node;
            return new IRLook(l.dir, l.neg, normalize(l.body));
        }
        if (node instanceof IRCharClass) {
            // Character classes don't need normalization
            return node;
        }
        
        // Atomic nodes: IRLit, IRDot, IRAnchor, IRBackref
        return node;
    }
    
    /**
     * Normalize a sequence: flatten nested sequences and coalesce adjacent literals.
     */
    private IROp normalizeSeq(IRSeq seq) {
        List<IROp> flatParts = new ArrayList<>();
        
        // Flatten and normalize children
        for (IROp part : seq.parts) {
            IROp normalized = normalize(part);
            if (normalized instanceof IRSeq) {
                // Flatten nested sequences
                flatParts.addAll(((IRSeq) normalized).parts);
            } else {
                flatParts.add(normalized);
            }
        }
        
        // Coalesce adjacent literals
        List<IROp> coalescedParts = new ArrayList<>();
        StringBuilder litBuffer = new StringBuilder();
        
        for (IROp part : flatParts) {
            if (part instanceof IRLit) {
                litBuffer.append(((IRLit) part).value);
            } else {
                if (litBuffer.length() > 0) {
                    coalescedParts.add(new IRLit(litBuffer.toString()));
                    litBuffer.setLength(0);
                }
                coalescedParts.add(part);
            }
        }
        
        if (litBuffer.length() > 0) {
            coalescedParts.add(new IRLit(litBuffer.toString()));
        }
        
        // If only one part remains, return it directly
        if (coalescedParts.size() == 1) {
            return coalescedParts.get(0);
        }
        
        return new IRSeq(coalescedParts);
    }
    
    /**
     * Normalize an alternation: flatten nested alternations.
     */
    private IROp normalizeAlt(IRAlt alt) {
        List<IROp> flatBranches = new ArrayList<>();
        
        // Flatten and normalize children
        for (IROp branch : alt.branches) {
            IROp normalized = normalize(branch);
            if (normalized instanceof IRAlt) {
                // Flatten nested alternations
                flatBranches.addAll(((IRAlt) normalized).branches);
            } else {
                flatBranches.add(normalized);
            }
        }
        
        return new IRAlt(flatBranches);
    }
    
    /**
     * Recursively analyze IR tree and track features used.
     */
    private void analyzeFeatures(IROp node) {
        if (node instanceof IRGroup) {
            IRGroup g = (IRGroup) node;
            if (g.atomic != null && g.atomic) {
                featuresUsed.add("atomic_group");
            }
            if (g.name != null) {
                featuresUsed.add("named_group");
            }
            analyzeFeatures(g.body);
        } else if (node instanceof IRQuant) {
            IRQuant q = (IRQuant) node;
            if ("Possessive".equals(q.mode)) {
                featuresUsed.add("possessive_quantifier");
            }
            analyzeFeatures(q.child);
        } else if (node instanceof IRLook) {
            IRLook l = (IRLook) node;
            if ("Behind".equals(l.dir)) {
                featuresUsed.add("lookbehind");
            } else if ("Ahead".equals(l.dir)) {
                featuresUsed.add("lookahead");
            }
            analyzeFeatures(l.body);
        } else if (node instanceof IRBackref) {
            featuresUsed.add("backreference");
        } else if (node instanceof IRCharClass) {
            IRCharClass cc = (IRCharClass) node;
            for (IRClassItem item : cc.items) {
                if (item instanceof IRClassEscape) {
                    IRClassEscape esc = (IRClassEscape) item;
                    if ("UnicodeProperty".equals(esc.type)) {
                        featuresUsed.add("unicode_property");
                    }
                }
            }
        } else if (node instanceof IRSeq) {
            for (IROp part : ((IRSeq) node).parts) {
                analyzeFeatures(part);
            }
        } else if (node instanceof IRAlt) {
            for (IROp branch : ((IRAlt) node).branches) {
                analyzeFeatures(branch);
            }
        }
    }
}
