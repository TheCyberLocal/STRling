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
     * for serialization to a dictionary/object representation.</p>
     */
    public static abstract class IROp {
        /**
         * Serializes the IR node to a dictionary representation.
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
        
        /**
         * Creates an alternation IR node.
         *
         * @param branches Array of IR nodes representing the alternative branches
         */
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
     * Represents a sequence (concatenation) operation in the IR.
     * 
     * <p>Matches all parts in order. Equivalent to concatenating patterns
     * in traditional regex syntax.</p>
     */
    public static class IRSeq extends IROp {
        public List<IROp> parts;
        
        /**
         * Creates a sequence IR node.
         *
         * @param parts Array of IR nodes to be matched sequentially
         */
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
     *
     * <p>Matches the exact string value with all characters treated as literals
     * (no special regex meaning).</p>
     */
    public static class IRLit extends IROp {
        public String value;
        
        /**
         * Creates a literal IR node.
         *
         * @param value The literal string to match
         */
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
     * Represents the "any character" wildcard in the IR.
     *
     * <p>Matches any single character (behavior may depend on flags like dotall).
     * Equivalent to the . metacharacter in traditional regex.</p>
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
     * Represents an anchor (position assertion) in the IR.
     *
     * <p>Matches a position rather than a character. Common anchors include
     * start of line (^), end of line ($), word boundaries (\b), etc.</p>
     */
    public static class IRAnchor extends IROp {
        public String at;
        
        /**
         * Creates an anchor IR node.
         *
         * @param at The anchor type (e.g., "Start", "End", "WordBoundary")
         */
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
     * Base class for character class items.
     *
     * <p>Character class items represent the individual components that can appear
     * inside a character class (ranges, literals, or escape sequences).</p>
     */
    public static abstract class IRClassItem {
        /**
         * Serializes the character class item to a dictionary representation.
         * 
         * @return Map containing the item's serialized representation
         */
        public abstract Map<String, Object> toDict();
    }
    
    /**
     * Represents a character range in a character class.
     *
     * <p>Matches any character between fromCh and toCh inclusive (e.g., a-z, 0-9).</p>
     */
    public static class IRClassRange extends IRClassItem {
        public String fromCh;
        public String toCh;
        
        /**
         * Creates a character range item.
         *
         * @param fromCh The starting character of the range
         * @param toCh The ending character of the range
         */
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
     * Represents a single literal character in a character class.
     *
     * <p>Matches exactly the specified character.</p>
     */
    public static class IRClassLiteral extends IRClassItem {
        public String ch;
        
        /**
         * Creates a literal character item.
         *
         * @param ch The literal character to match
         */
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
     * Represents an escape sequence in a character class.
     *
     * <p>Handles special character class escapes like \d, \w, \s, or Unicode
     * property escapes like \p{Letter}.</p>
     */
    public static class IRClassEscape extends IRClassItem {
        public String type;
        public String property;
        
        /**
         * Creates an escape sequence item.
         *
         * @param type The escape type (e.g., "Digit", "Word", "Whitespace", "UnicodeProperty")
         */
        public IRClassEscape(String type) {
            this(type, null);
        }
        
        /**
         * Creates an escape sequence item.
         *
         * @param type The escape type (e.g., "Digit", "Word", "Whitespace", "UnicodeProperty")
         * @param property The Unicode property name if type is "UnicodeProperty"
         */
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
     * Represents a character class in the IR.
     *
     * <p>Matches any single character from the set of allowed characters or ranges.
     * Can be negated to match any character NOT in the set.</p>
     */
    public static class IRCharClass extends IROp {
        public boolean negated;
        public List<IRClassItem> items;
        
        /**
         * Creates a character class IR node.
         *
         * @param negated Whether the character class is negated (e.g., [^...])
         * @param items List of character class items (ranges, literals, escapes)
         */
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
     * Represents a quantifier (repetition) in the IR.
     *
     * <p>Specifies how many times the child pattern should be matched.
     * Supports greedy, lazy, and possessive matching modes.</p>
     */
    public static class IRQuant extends IROp {
        public IROp child;
        public int min;
        /**
         * Maximum repetitions (number), or 0 for unbounded (infinity).
         */
        public Object max; // int or 0 for "Inf"
        /**
         * Quantifier mode: "Greedy", "Lazy", or "Possessive".
         */
        public String mode;
        
        /**
         * Creates a quantifier IR node.
         *
         * @param child The IR node to be quantified
         * @param min Minimum number of repetitions
         * @param max Maximum number of repetitions (number or 0 for unlimited)
         * @param mode Matching mode: "Greedy", "Lazy", or "Possessive"
         */
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
     * Represents a group (capturing or non-capturing) in the IR.
     *
     * <p>Groups are used for capturing matched text, applying quantifiers to
     * multiple elements, or creating atomic groups for backtracking control.</p>
     */
    public static class IRGroup extends IROp {
        public boolean capturing;
        public IROp body;
        public String name;
        public Boolean atomic;
        
        /**
         * Creates a group IR node.
         *
         * @param capturing Whether this group captures its match
         * @param body The IR node contained within the group
         */
        public IRGroup(boolean capturing, IROp body) {
            this(capturing, body, null, null);
        }
        
        /**
         * Creates a group IR node.
         *
         * @param capturing Whether this group captures its match
         * @param body The IR node contained within the group
         * @param name Optional name for named capture groups
         */
        public IRGroup(boolean capturing, IROp body, String name) {
            this(capturing, body, name, null);
        }
        
        /**
         * Creates a group IR node.
         *
         * @param capturing Whether this group captures its match
         * @param body The IR node contained within the group
         * @param name Optional name for named capture groups
         * @param atomic Whether this is an atomic group (prevents backtracking)
         */
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
            if (atomic != null && atomic) {
                map.put("atomic", atomic);
            }
            return map;
        }
    }
    
    /**
     * Represents a backreference in the IR.
     *
     * <p>References a previously captured group by index or name, matching
     * the exact same text that was captured by that group.</p>
     */
    public static class IRBackref extends IROp {
        public Integer byIndex;
        public String byName;
        
        /**
         * Creates a backreference IR node.
         */
        public IRBackref() {
            this(null, null);
        }
        
        /**
         * Creates a backreference IR node.
         *
         * @param byIndex The numeric group index to reference
         * @param byName The name of the group to reference
         */
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
     * Represents a lookaround assertion in the IR.
     *
     * <p>Lookarounds are zero-width assertions that check for pattern presence
     * or absence without consuming characters. They can look ahead or behind,
     * and can be positive or negative.</p>
     */
    public static class IRLook extends IROp {
        public String dir;
        public boolean neg;
        public IROp body;
        
        /**
         * Creates a lookaround IR node.
         *
         * @param dir Direction: "Ahead" for lookahead or "Behind" for lookbehind
         * @param neg Whether this is a negative assertion (pattern must NOT match)
         * @param body The IR node to look for
         */
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
