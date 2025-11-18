package com.strling.core;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * STRling AST Node Definitions.
 * 
 * <p>This module defines the complete set of Abstract Syntax Tree (AST) node classes
 * that represent the parsed structure of STRling patterns. The AST is the direct
 * output of the parser and represents the syntactic structure of the pattern before
 * optimization and lowering to IR.</p>
 * 
 * <p>AST nodes are designed to:</p>
 * <ul>
 *   <li>Closely mirror the source pattern syntax</li>
 *   <li>Be easily serializable to the Base TargetArtifact schema</li>
 *   <li>Provide a clean separation between parsing and compilation</li>
 *   <li>Support multiple target regex flavors through the compilation pipeline</li>
 * </ul>
 * 
 * <p>Each AST node type corresponds to a syntactic construct in the STRling DSL
 * (alternation, sequencing, character classes, anchors, etc.) and can be
 * serialized to a dictionary representation for debugging or storage.</p>
 */
public class Nodes {
    
    // ---- Flags container ----
    
    /**
     * Container for regex flags/modifiers.
     * 
     * <p>Flags control the behavior of pattern matching (case sensitivity, multiline
     * mode, etc.). This class encapsulates all standard regex flags and provides
     * utilities for creating flags from string representations.</p>
     */
    public static class Flags {
        public boolean ignoreCase = false;
        public boolean multiline = false;
        public boolean dotAll = false;
        public boolean unicode = false;
        public boolean extended = false;
        
        /**
         * Serializes the flags to a dictionary representation.
         * 
         * @return Object containing all flag values
         */
        public Map<String, Boolean> toDict() {
            Map<String, Boolean> map = new HashMap<>();
            map.put("ignoreCase", ignoreCase);
            map.put("multiline", multiline);
            map.put("dotAll", dotAll);
            map.put("unicode", unicode);
            map.put("extended", extended);
            return map;
        }
        
        /**
         * Creates Flags from a string of flag letters.
         * 
         * @param letters String containing flag letters (i, m, s, u, x)
         * @return A new Flags instance with the specified flags enabled
         */
        public static Flags fromLetters(String letters) {
            Flags f = new Flags();
            String cleaned = letters.replace(",", "").replace(" ", "");
            for (char ch : cleaned.toCharArray()) {
                switch (ch) {
                    case 'i':
                        f.ignoreCase = true;
                        break;
                    case 'm':
                        f.multiline = true;
                        break;
                    case 's':
                        f.dotAll = true;
                        break;
                    case 'u':
                        f.unicode = true;
                        break;
                    case 'x':
                        f.extended = true;
                        break;
                    default:
                        // Unknown flags are ignored at parser stage; may be warned later
                        break;
                }
            }
            return f;
        }
    }
    
    // ---- Base node ----
    
    /**
     * Base class for all AST nodes.
     */
    public static abstract class Node {
        /**
         * Serialize node to a dictionary representation.
         * 
         * @return Map containing the node's serialized representation
         */
        public abstract Map<String, Object> toDict();
    }
    
    // ---- Concrete nodes matching Base Schema ----
    
    /**
     * Alternation node - represents a choice between multiple branches.
     * Corresponds to the | operator in traditional regex.
     */
    public static class Alt extends Node {
        public List<Node> branches;
        
        public Alt(List<Node> branches) {
            this.branches = branches;
        }
        
        @Override
        public Map<String, Object> toDict() {
            Map<String, Object> map = new HashMap<>();
            map.put("kind", "Alt");
            List<Map<String, Object>> branchDicts = new ArrayList<>();
            for (Node branch : branches) {
                branchDicts.add(branch.toDict());
            }
            map.put("branches", branchDicts);
            return map;
        }
    }
    
    /**
     * Sequence node - represents a sequence of patterns that must match in order.
     */
    public static class Seq extends Node {
        public List<Node> parts;
        
        public Seq(List<Node> parts) {
            this.parts = parts;
        }
        
        @Override
        public Map<String, Object> toDict() {
            Map<String, Object> map = new HashMap<>();
            map.put("kind", "Seq");
            List<Map<String, Object>> partDicts = new ArrayList<>();
            for (Node part : parts) {
                partDicts.add(part.toDict());
            }
            map.put("parts", partDicts);
            return map;
        }
    }
    
    /**
     * Literal node - represents a literal string to match.
     */
    public static class Lit extends Node {
        public String value;
        
        public Lit(String value) {
            this.value = value;
        }
        
        @Override
        public Map<String, Object> toDict() {
            Map<String, Object> map = new HashMap<>();
            map.put("kind", "Lit");
            map.put("value", value);
            return map;
        }
    }
    
    /**
     * Dot node - represents the wildcard (.) that matches any character.
     */
    public static class Dot extends Node {
        @Override
        public Map<String, Object> toDict() {
            Map<String, Object> map = new HashMap<>();
            map.put("kind", "Dot");
            return map;
        }
    }
    
    /**
     * Anchor node - represents position anchors (start, end, word boundary, etc.).
     */
    public static class Anchor extends Node {
        /**
         * The anchor type: "Start"|"End"|"WordBoundary"|"NotWordBoundary"|Absolute* variants.
         */
        public String at;
        
        public Anchor(String at) {
            this.at = at;
        }
        
        @Override
        public Map<String, Object> toDict() {
            Map<String, Object> map = new HashMap<>();
            map.put("kind", "Anchor");
            map.put("at", at);
            return map;
        }
    }
    
    // --- CharClass ---
    
    /**
     * Base class for character class items.
     */
    public static abstract class ClassItem {
        /**
         * Serialize class item to a dictionary representation.
         * 
         * @return Map containing the item's serialized representation
         */
        public abstract Map<String, Object> toDict();
    }
    
    /**
     * Character range within a character class (e.g., a-z).
     */
    public static class ClassRange extends ClassItem {
        public String fromCh;
        public String toCh;
        
        public ClassRange(String fromCh, String toCh) {
            this.fromCh = fromCh;
            this.toCh = toCh;
        }
        
        @Override
        public Map<String, Object> toDict() {
            Map<String, Object> map = new HashMap<>();
            map.put("kind", "Range");
            map.put("from", fromCh);
            map.put("to", toCh);
            return map;
        }
    }
    
    /**
     * Literal character within a character class.
     */
    public static class ClassLiteral extends ClassItem {
        public String ch;
        
        public ClassLiteral(String ch) {
            this.ch = ch;
        }
        
        @Override
        public Map<String, Object> toDict() {
            Map<String, Object> map = new HashMap<>();
            map.put("kind", "Char");
            map.put("char", ch);
            return map;
        }
    }
    
    /**
     * Character class escape sequence (e.g., \d, \w, \s, \p{...}).
     */
    public static class ClassEscape extends ClassItem {
        /**
         * The escape type: d, D, w, W, s, S, p, P.
         */
        public String type;
        
        /**
         * For Unicode property escapes (\p, \P), the property name.
         */
        public String property;
        
        public ClassEscape(String type) {
            this(type, null);
        }
        
        public ClassEscape(String type, String property) {
            this.type = type;
            this.property = property;
        }
        
        @Override
        public Map<String, Object> toDict() {
            Map<String, Object> map = new HashMap<>();
            map.put("kind", "Esc");
            map.put("type", type);
            if ((type.equals("p") || type.equals("P")) && property != null) {
                map.put("property", property);
            }
            return map;
        }
    }
    
    /**
     * Character class node - represents a character class [...] or negated class [^...].
     */
    public static class CharClass extends Node {
        public boolean negated;
        public List<ClassItem> items;
        
        public CharClass(boolean negated, List<ClassItem> items) {
            this.negated = negated;
            this.items = items;
        }
        
        @Override
        public Map<String, Object> toDict() {
            Map<String, Object> map = new HashMap<>();
            map.put("kind", "CharClass");
            map.put("negated", negated);
            List<Map<String, Object>> itemDicts = new ArrayList<>();
            for (ClassItem item : items) {
                itemDicts.add(item.toDict());
            }
            map.put("items", itemDicts);
            return map;
        }
    }
    
    /**
     * Quantifier node - represents repetition (*, +, ?, {m,n}).
     */
    public static class Quant extends Node {
        public Node child;
        public int min;
        /**
         * Maximum repetitions, or "Inf" for unbounded.
         */
        public Object max; // int or String "Inf"
        /**
         * Quantifier mode: "Greedy" | "Lazy" | "Possessive".
         */
        public String mode;
        
        public Quant(Node child, int min, Object max, String mode) {
            this.child = child;
            this.min = min;
            this.max = max;
            this.mode = mode;
        }
        
        @Override
        public Map<String, Object> toDict() {
            Map<String, Object> map = new HashMap<>();
            map.put("kind", "Quant");
            map.put("child", child.toDict());
            map.put("min", min);
            map.put("max", max);
            map.put("mode", mode);
            return map;
        }
    }
    
    /**
     * Group node - represents a capturing or non-capturing group.
     */
    public static class Group extends Node {
        public boolean capturing;
        public Node body;
        public String name;
        /**
         * Extension: whether the group is atomic (possessive).
         */
        public Boolean atomic;
        
        public Group(boolean capturing, Node body) {
            this(capturing, body, null, null);
        }
        
        public Group(boolean capturing, Node body, String name) {
            this(capturing, body, name, null);
        }
        
        public Group(boolean capturing, Node body, String name, Boolean atomic) {
            this.capturing = capturing;
            this.body = body;
            this.name = name;
            this.atomic = atomic;
        }
        
        @Override
        public Map<String, Object> toDict() {
            Map<String, Object> map = new HashMap<>();
            map.put("kind", "Group");
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
     * Backreference node - references a previously captured group by index or name.
     */
    public static class Backref extends Node {
        public Integer byIndex;
        public String byName;
        
        public Backref() {
            this(null, null);
        }
        
        public Backref(Integer byIndex, String byName) {
            this.byIndex = byIndex;
            this.byName = byName;
        }
        
        @Override
        public Map<String, Object> toDict() {
            Map<String, Object> map = new HashMap<>();
            map.put("kind", "Backref");
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
     * Lookaround node - represents lookahead or lookbehind assertions.
     */
    public static class Look extends Node {
        /**
         * Direction: "Ahead" | "Behind".
         */
        public String dir;
        /**
         * Whether the lookaround is negative.
         */
        public boolean neg;
        public Node body;
        
        public Look(String dir, boolean neg, Node body) {
            this.dir = dir;
            this.neg = neg;
            this.body = body;
        }
        
        @Override
        public Map<String, Object> toDict() {
            Map<String, Object> map = new HashMap<>();
            map.put("kind", "Look");
            map.put("dir", dir);
            map.put("neg", neg);
            map.put("body", body.toDict());
            return map;
        }
    }
}
