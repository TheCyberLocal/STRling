package com.strling.core;

import com.strling.core.Nodes.*;
import com.strling.core.IR.*;

import java.util.*;

/**
 * STRling Compiler - AST to IR Transformation
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
     * Compiler for transforming AST nodes into optimized IR.
     *
     * <p>The Compiler class handles the complete transformation pipeline from parsed
     * AST to normalized IR, including feature detection for metadata generation.</p>
     */
    
    /**
     * Creates a new Compiler instance.
     */
    public Compiler() {
        this.featuresUsed = new HashSet<>();
    }
    
    /**
     * Compiles an AST node and returns IR with metadata.
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
     * Compiles an AST node into optimized IR.
     *
     * <p>This is the standard compilation entry point without metadata tracking.
     * Performs lowering and normalization but doesn't analyze features.</p>
     * 
     * @param root The root AST node to compile
     * @return The compiled and normalized IR tree
     */
    public IROp compile(Node root) {
        IROp ir = lower(root);
        ir = normalize(ir);
        return ir;
    }
    
    /**
     * Lowers an AST node to its IR equivalent.
     *
     * <p>This method recursively transforms AST nodes into their corresponding
     * IR operations. Each AST node type is mapped to an IR operation that
     * represents the same semantic meaning but in a form optimized for
     * emission to target regex engines.</p>
     * 
     * <p>Public for testing (TypeScript uses @ts-ignore for private access).</p>
     * 
     * @param node The AST node to lower
     * @return The corresponding IR operation
     * @throws IllegalArgumentException if an unknown AST node type is encountered
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
                        // Unicode property - pass through type (p or P) for emitters
                        irItems.add(new IRClassEscape(e.type, e.property));
                    } else {
                        String t;
                        switch (e.type) {
                            case "Digit": t = "d"; break;
                            case "Word": t = "w"; break;
                            case "Whitespace": t = "s"; break;
                            case "NotDigit": t = "D"; break;
                            case "NotWord": t = "W"; break;
                            case "NotWhitespace": t = "S"; break;
                            default: t = e.type; break;
                        }
                        irItems.add(new IRClassEscape(t));
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
     * Normalizes an IR tree by flattening and coalescing.
     *
     * <p>This method performs several optimization passes on the IR tree:</p>
     * <ul>
     *   <li>Flattens nested sequences (Seq within Seq) and alternations (Alt within Alt)</li>
     *   <li>Coalesces adjacent literal nodes into single literals for efficiency</li>
     *   <li>Recursively normalizes all child nodes</li>
     * </ul>
     *
     * <p>These optimizations reduce the complexity of the IR tree while maintaining
     * semantic equivalence, making it easier for emitters to generate efficient
     * target regex code.</p>
     * 
     * <p>Public for testing (TypeScript uses @ts-ignore for private access).</p>
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
     * Normalizes a sequence: flattens nested sequences and coalesces adjacent literals.
     * 
     * @param seq The sequence to normalize
     * @return The normalized IR node
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
     * Normalizes an alternation: flattens nested alternations.
     * 
     * @param alt The alternation to normalize
     * @return The normalized IR node
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
        
        // Unwrap single-branch alternations
        return flatBranches.size() == 1 ? flatBranches.get(0) : new IRAlt(flatBranches);
    }
    
    /**
     * Recursively analyzes the IR tree to detect and log features used.
     *
     * <p>This method walks the entire IR tree and identifies special regex features
     * that are being used (e.g., named groups, lookarounds, atomic groups).
     * The detected features are stored in the featuresUsed set for metadata.</p>
     * 
     * @param node The IR node to analyze
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
                    // Check for Unicode property escapes (\p{...} or \P{...})
                    if ((esc.type.equals("p") || esc.type.equals("P")) && esc.property != null) {
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
