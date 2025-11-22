package com.strling.core;

import com.strling.core.nodes.*;
import com.strling.core.IR.*;

import java.util.List;
import java.util.ArrayList;
import java.util.stream.Collectors;

/**
 * JSON AST to IR Compiler
 *
 * This class converts JSON AST nodes (deserialized from fixture files) directly
 * to IR operations, bypassing the traditional Parser AST layer. This is used
 * for conformance testing to ensure the Java binding can work with the universal
 * JSON AST schema.
 */
public class JsonAstCompiler {
    
    /**
     * Compile a JSON AST node to IR
     */
    public IROp compile(IRNode node) {
        if (node instanceof LiteralNode) {
            return new IRLit(((LiteralNode) node).getValue());
        }
        
        if (node instanceof SequenceNode) {
            List<IROp> parts = new ArrayList<>();
            List<IRNode> nodeParts = ((SequenceNode) node).getParts();
            
            StringBuilder pendingLiteral = null;
            
            for (IRNode part : nodeParts) {
                IROp compiledPart = compile(part);
                
                if (compiledPart instanceof IRLit) {
                    if (pendingLiteral == null) {
                        pendingLiteral = new StringBuilder();
                    }
                    pendingLiteral.append(((IRLit) compiledPart).value);
                } else {
                    if (pendingLiteral != null) {
                        parts.add(new IRLit(pendingLiteral.toString()));
                        pendingLiteral = null;
                    }
                    parts.add(compiledPart);
                }
            }
            
            if (pendingLiteral != null) {
                parts.add(new IRLit(pendingLiteral.toString()));
            }
            
            if (parts.size() == 1) {
                return parts.get(0);
            }
            
            return new IRSeq(parts);
        }
        
        if (node instanceof AlternationNode) {
            List<IROp> branches = ((AlternationNode) node).getAlternatives().stream()
                .map(this::compile)
                .collect(Collectors.toList());
            return new IRAlt(branches);
        }
        
        if (node instanceof QuantifierNode) {
            QuantifierNode q = (QuantifierNode) node;
            IROp target = compile(q.getTarget());
            
            int min = q.getMin();
            Object max = q.getMax() != null ? q.getMax() : "Inf";
            
            String mode = "Greedy";
            if (q.isLazy()) {
                mode = "Lazy";
            } else if (q.isPossessive()) {
                mode = "Possessive";
            }
            
            return new IRQuant(target, min, max, mode);
        }
        
        if (node instanceof GroupNode) {
            GroupNode g = (GroupNode) node;
            IROp body = compile(g.getBody());
            return new IRGroup(g.isCapturing(), body, g.getName(), g.isAtomic());
        }
        
        if (node instanceof CharacterClassNode) {
            CharacterClassNode cc = (CharacterClassNode) node;
            List<IRClassItem> items = new ArrayList<>();
            
            for (CharacterClassNode.ClassMember member : cc.getMembers()) {
                if (member instanceof CharacterClassNode.ClassLiteralMember) {
                    String value = ((CharacterClassNode.ClassLiteralMember) member).getValue();
                    items.add(new IRClassLiteral(value));
                } else if (member instanceof CharacterClassNode.ClassRangeMember) {
                    CharacterClassNode.ClassRangeMember range = 
                        (CharacterClassNode.ClassRangeMember) member;
                    items.add(new IRClassRange(range.getFrom(), range.getTo()));
                } else if (member instanceof CharacterClassNode.ClassEscapeMember) {
                    String kind = ((CharacterClassNode.ClassEscapeMember) member).getKind();
                    String irType = mapEscapeKind(kind);
                    items.add(new IRClassEscape(irType, null));
                } else if (member instanceof CharacterClassNode.ClassUnicodePropertyMember) {
                    CharacterClassNode.ClassUnicodePropertyMember prop = 
                        (CharacterClassNode.ClassUnicodePropertyMember) member;
                    String type = prop.isNegated() ? "P" : "p";
                    items.add(new IRClassEscape(type, prop.getValue()));
                }
            }
            
            return new IRCharClass(cc.isNegated(), items);
        }
        
        if (node instanceof AnchorNode) {
            String at = ((AnchorNode) node).getAt();
            if ("NonWordBoundary".equals(at)) {
                at = "NotWordBoundary";
            }
            return new IRAnchor(at);
        }
        
        if (node instanceof BackReferenceNode) {
            BackReferenceNode br = (BackReferenceNode) node;
            return new IRBackref(br.getIndex(), br.getName());
        }
        
        if (node instanceof LookaheadNode) {
            LookaheadNode la = (LookaheadNode) node;
            IROp body = compile(la.getBody());
            return new IRLook("Ahead", false, body);
        }
        
        if (node instanceof NegativeLookaheadNode) {
            NegativeLookaheadNode la = (NegativeLookaheadNode) node;
            IROp body = compile(la.getBody());
            return new IRLook("Ahead", true, body);
        }
        
        if (node instanceof LookbehindNode) {
            LookbehindNode la = (LookbehindNode) node;
            IROp body = compile(la.getBody());
            return new IRLook("Behind", false, body);
        }
        
        if (node instanceof NegativeLookbehindNode) {
            NegativeLookbehindNode la = (NegativeLookbehindNode) node;
            IROp body = compile(la.getBody());
            return new IRLook("Behind", true, body);
        }
        
        if (node instanceof LookaroundNode) {
            // This is a generic fallback - we need to handle the specific types
            // For now, just compile the body
            LookaroundNode la = (LookaroundNode) node;
            IROp body = compile(la.getBody());
            
            // Default to lookahead positive
            return new IRLook("Ahead", false, body);
        }
        
        if (node instanceof DotNode) {
            return new IRDot();
        }
        
        throw new IllegalArgumentException("Unknown JSON AST node type: " + node.getClass().getName());
    }
    
    /**
     * Map JSON escape kind to IR escape type
     */
    private String mapEscapeKind(String kind) {
        switch (kind) {
            case "digit": return "d";
            case "not-digit": return "D";
            case "space": return "s";
            case "not-space": return "S";
            case "word": return "w";
            case "not-word": return "W";
            default: 
                throw new IllegalArgumentException("Unknown escape kind: " + kind);
        }
    }
}
