package com.strling.core;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * STRling Intermediate Representation (IR) Node Definitions.
 * 
 * <p>This module defines the complete set of IR node classes that represent
 * language-agnostic regex constructs. The IR serves as an intermediate layer
 * between the parsed AST and the target-specific emitters (e.g., PCRE2).</p>
 * 
 * <p>IR nodes are designed to be:</p>
 * <ul>
 *   <li>Simple and composable</li>
 *   <li>Easy to serialize (via toDict methods)</li>
 *   <li>Independent of any specific regex flavor</li>
 *   <li>Optimized for transformation and analysis</li>
 * </ul>
 * 
 * <p>Each IR node corresponds to a fundamental regex operation (alternation,
 * sequencing, character classes, quantification, etc.) and can be serialized
 * to a dictionary representation for further processing or debugging.</p>
 */
public class IR {
    
    /**
     * Base class for all IR operations.
     * 
     * <p>All IR nodes extend this base class and must implement the toDict() method
     * for serialization to a dictionary representation.</p>
     */
    public static abstract class IROp {
        /**
         * Serialize the IR node to a dictionary representation.
         * 
         * @return The dictionary representation of this IR node
         */
        public abstract Map<String, Object> toDict();
    }
    
    /**
     * Represents an alternation (OR) operation in the IR.
     * 
     * <p>Matches any one of the provided branches. Equivalent to the | operator
     * in traditional regex syntax.</p>
     */
    public static class IRAlt extends IROp {
        public List<IROp> branches;
        
        public IRAlt(List<IROp> branches) {
            this.branches = branches;
        }
        
        @Override
        public Map<String, Object> toDict() {
            Map<String, Object> map = new HashMap<>();
            map.put("ir", "Alt");
            List<Map<String, Object>> branchDicts = new ArrayList<>();
            for (IROp branch : branches) {
                branchDicts.add(branch.toDict());
            }
            map.put("branches", branchDicts);
            return map;
        }
    }
    
    /**
     * Represents a sequence operation in the IR.
     * 
     * <p>Matches all parts in order.</p>
     */
    public static class IRSeq extends IROp {
        public List<IROp> parts;
        
        public IRSeq(List<IROp> parts) {
            this.parts = parts;
        }
        
        @Override
        public Map<String, Object> toDict() {
            Map<String, Object> map = new HashMap<>();
            map.put("ir", "Seq");
            List<Map<String, Object>> partDicts = new ArrayList<>();
            for (IROp part : parts) {
                partDicts.add(part.toDict());
            }
            map.put("parts", partDicts);
            return map;
        }
    }
    
    /**
     * Represents a literal string in the IR.
     */
    public static class IRLit extends IROp {
        public String value;
        
        public IRLit(String value) {
            this.value = value;
        }
        
        @Override
        public Map<String, Object> toDict() {
            Map<String, Object> map = new HashMap<>();
            map.put("ir", "Lit");
            map.put("value", value);
            return map;
        }
    }
    
    /**
     * Represents the wildcard (.) in the IR.
     */
    public static class IRDot extends IROp {
        @Override
        public Map<String, Object> toDict() {
            Map<String, Object> map = new HashMap<>();
            map.put("ir", "Dot");
            return map;
        }
    }
    
    /**
     * Represents an anchor in the IR.
     */
    public static class IRAnchor extends IROp {
        public String at;
        
        public IRAnchor(String at) {
            this.at = at;
        }
        
        @Override
        public Map<String, Object> toDict() {
            Map<String, Object> map = new HashMap<>();
            map.put("ir", "Anchor");
            map.put("at", at);
            return map;
        }
    }
    
    /**
     * Base class for character class items in the IR.
     */
    public static abstract class IRClassItem {
        /**
         * Serialize class item to a dictionary representation.
         * 
         * @return Map containing the item's serialized representation
         */
        public abstract Map<String, Object> toDict();
    }
    
    /**
     * Character range within a character class in the IR.
     */
    public static class IRClassRange extends IRClassItem {
        public String fromCh;
        public String toCh;
        
        public IRClassRange(String fromCh, String toCh) {
            this.fromCh = fromCh;
            this.toCh = toCh;
        }
        
        @Override
        public Map<String, Object> toDict() {
            Map<String, Object> map = new HashMap<>();
            map.put("ir", "Range");
            map.put("from", fromCh);
            map.put("to", toCh);
            return map;
        }
    }
    
    /**
     * Literal character within a character class in the IR.
     */
    public static class IRClassLiteral extends IRClassItem {
        public String ch;
        
        public IRClassLiteral(String ch) {
            this.ch = ch;
        }
        
        @Override
        public Map<String, Object> toDict() {
            Map<String, Object> map = new HashMap<>();
            map.put("ir", "Char");
            map.put("char", ch);
            return map;
        }
    }
    
    /**
     * Character class escape sequence in the IR.
     */
    public static class IRClassEscape extends IRClassItem {
        public String type;
        public String property;
        
        public IRClassEscape(String type) {
            this(type, null);
        }
        
        public IRClassEscape(String type, String property) {
            this.type = type;
            this.property = property;
        }
        
        @Override
        public Map<String, Object> toDict() {
            Map<String, Object> map = new HashMap<>();
            map.put("ir", "Esc");
            map.put("type", type);
            if (property != null) {
                map.put("property", property);
            }
            return map;
        }
    }
    
    /**
     * Character class in the IR.
     */
    public static class IRCharClass extends IROp {
        public boolean negated;
        public List<IRClassItem> items;
        
        public IRCharClass(boolean negated, List<IRClassItem> items) {
            this.negated = negated;
            this.items = items;
        }
        
        @Override
        public Map<String, Object> toDict() {
            Map<String, Object> map = new HashMap<>();
            map.put("ir", "CharClass");
            map.put("negated", negated);
            List<Map<String, Object>> itemDicts = new ArrayList<>();
            for (IRClassItem item : items) {
                itemDicts.add(item.toDict());
            }
            map.put("items", itemDicts);
            return map;
        }
    }
    
    /**
     * Quantifier in the IR.
     */
    public static class IRQuant extends IROp {
        public IROp child;
        public int min;
        /**
         * Maximum repetitions, or "Inf" for unbounded.
         */
        public Object max; // int or String "Inf"
        /**
         * Quantifier mode: Greedy|Lazy|Possessive.
         */
        public String mode;
        
        public IRQuant(IROp child, int min, Object max, String mode) {
            this.child = child;
            this.min = min;
            this.max = max;
            this.mode = mode;
        }
        
        @Override
        public Map<String, Object> toDict() {
            Map<String, Object> map = new HashMap<>();
            map.put("ir", "Quant");
            map.put("child", child.toDict());
            map.put("min", min);
            map.put("max", max);
            map.put("mode", mode);
            return map;
        }
    }
    
    /**
     * Group in the IR.
     */
    public static class IRGroup extends IROp {
        public boolean capturing;
        public IROp body;
        public String name;
        public Boolean atomic;
        
        public IRGroup(boolean capturing, IROp body) {
            this(capturing, body, null, null);
        }
        
        public IRGroup(boolean capturing, IROp body, String name) {
            this(capturing, body, name, null);
        }
        
        public IRGroup(boolean capturing, IROp body, String name, Boolean atomic) {
            this.capturing = capturing;
            this.body = body;
            this.name = name;
            this.atomic = atomic;
        }
        
        @Override
        public Map<String, Object> toDict() {
            Map<String, Object> map = new HashMap<>();
            map.put("ir", "Group");
            map.put("capturing", capturing);
            map.put("body", body.toDict());
            if (name != null) {
                map.put("name", name);
            }
            if (atomic != null) {
                map.put("atomic", atomic);
            }
            return map;
        }
    }
    
    /**
     * Backreference in the IR.
     */
    public static class IRBackref extends IROp {
        public Integer byIndex;
        public String byName;
        
        public IRBackref() {
            this(null, null);
        }
        
        public IRBackref(Integer byIndex, String byName) {
            this.byIndex = byIndex;
            this.byName = byName;
        }
        
        @Override
        public Map<String, Object> toDict() {
            Map<String, Object> map = new HashMap<>();
            map.put("ir", "Backref");
            if (byIndex != null) {
                map.put("byIndex", byIndex);
            }
            if (byName != null) {
                map.put("byName", byName);
            }
            return map;
        }
    }
    
    /**
     * Lookaround in the IR.
     */
    public static class IRLook extends IROp {
        public String dir;
        public boolean neg;
        public IROp body;
        
        public IRLook(String dir, boolean neg, IROp body) {
            this.dir = dir;
            this.neg = neg;
            this.body = body;
        }
        
        @Override
        public Map<String, Object> toDict() {
            Map<String, Object> map = new HashMap<>();
            map.put("ir", "Look");
            map.put("dir", dir);
            map.put("neg", neg);
            map.put("body", body.toDict());
            return map;
        }
    }
}
