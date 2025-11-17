package com.strling.emitters;

import com.strling.core.IR.*;
import com.strling.core.Nodes.Flags;

import java.util.List;
import java.util.Map;

/**
 * STRling PCRE2 Emitter - IR to PCRE2 Pattern String
 *
 * This class implements the emitter that transforms STRling's Intermediate
 * Representation (IR) into PCRE2-compatible regex pattern strings. The emitter:
 *   - Converts IR operations to PCRE2 syntax
 *   - Handles proper escaping of metacharacters
 *   - Manages character classes and ranges
 *   - Emits quantifiers, groups, and lookarounds
 *   - Applies regex flags as needed
 *
 * The emitter is the final stage of the compilation pipeline, producing actual
 * regex patterns that can be used with PCRE2-compatible regex engines (which
 * includes most modern regex implementations).
 */
public class Pcre2Emitter {
    
    /**
     * Escapes PCRE2 metacharacters in literal strings.
     *
     * <p>Escapes characters that have special meaning in PCRE2 regex syntax when
     * used outside character classes. This ensures literal strings are matched
     * exactly as written.</p>
     * 
     * @param s The literal string to escape
     * @return The escaped string safe for use in PCRE2 patterns
     */
    public static String escapeLiteral(String s) {
        // Escape PCRE2 metacharacters: . ^ $ | ( ) ? * + { } [ ] \
        StringBuilder result = new StringBuilder();
        for (char ch : s.toCharArray()) {
            switch (ch) {
                case '.':
                case '^':
                case '$':
                case '|':
                case '(':
                case ')':
                case '?':
                case '*':
                case '+':
                case '{':
                case '}':
                case '[':
                case ']':
                case '\\':
                    result.append('\\').append(ch);
                    break;
                default:
                    result.append(ch);
            }
        }
        return result.toString();
    }
    
    /**
     * Escapes a character for use inside [...] per PCRE2 rules.
     * 
     * @param ch The character to escape
     * @return The escaped character safe for use inside character classes
     */
    public static String escapeClassChar(String ch) {
        if (ch.length() != 1) {
            throw new IllegalArgumentException("escapeClassChar expects single character");
        }
        char c = ch.charAt(0);
        
        // Inside [], ], \, -, ^ and [ are special and need escaping for safety.
        // ] and \ ALWAYS need escaping.
        // -, ^ and [ should be escaped to avoid ambiguity (Java's regex engine requires [ to be escaped).
        if (c == '\\' || c == ']') {
            return "\\" + c;
        }
        if (c == '[') {
            return "\\[";
        }
        if (c == '-') {
            return "\\-";
        }
        if (c == '^') {
            return "\\^";
        }
        
        // Handle non-printable chars / whitespace for clarity
        switch (c) {
            case '\n':
                return "\\n";
            case '\r':
                return "\\r";
            case '\t':
                return "\\t";
            case '\f':
                return "\\f";
            case '\u000B': // \v
                return "\\v";
        }
        
        // Handle other non-printable characters
        if (!isPrintable(c) || c < 32) {
            return String.format("\\x%02x", (int) c);
        }
        
        // All other characters are literal within [] including ., *, ?, [, etc.
        return String.valueOf(c);
    }
    
    private static boolean isPrintable(char c) {
        Character.UnicodeBlock block = Character.UnicodeBlock.of(c);
        return (!Character.isISOControl(c)) &&
                c != Character.LINE_SEPARATOR &&
                c != Character.PARAGRAPH_SEPARATOR &&
                block != null &&
                block != Character.UnicodeBlock.SPECIALS;
    }
    
    /**
     * Emit a PCRE2 character class. If the class is exactly one shorthand escape
     * (like \d or \p{Lu}), prefer the shorthand (with negation flipping) instead
     * of a bracketed class.
     */
    private static String emitClass(IRCharClass cc) {
        List<IRClassItem> items = cc.items;
        
        // --- Single-item shorthand optimization ---------------------------------
        if (items.size() == 1 && items.get(0) instanceof IRClassEscape) {
            IRClassEscape esc = (IRClassEscape) items.get(0);
            String k = esc.type;
            String prop = esc.property;
            
            if (k.equals("d") || k.equals("w") || k.equals("s")) {
                // Flip to uppercase negated forms when the entire class is negated.
                if (cc.negated && k.equals("d")) return "\\D";
                if (cc.negated && k.equals("w")) return "\\W";
                if (cc.negated && k.equals("s")) return "\\S";
                return "\\" + k;
            }
            
            if (k.equals("D") || k.equals("W") || k.equals("S")) {
                // Already-negated shorthands; flip back if the class itself is negated.
                String base = k.toLowerCase();
                return cc.negated ? ("\\" + base) : ("\\" + k);
            }
            
            if ((k.equals("p") || k.equals("P")) && prop != null) {
                // For \p{..}/\P{..}, flip p<->P iff exactly-negated class.
                boolean isKUpperP = k.equals("P");
                boolean useUpperP = cc.negated ^ isKUpperP;
                String use = useUpperP ? "P" : "p";
                return "\\" + use + "{" + prop + "}";
            }
        }
        
        // --- General case: build a bracket class --------------------------------
        StringBuilder parts = new StringBuilder();
        for (IRClassItem it : items) {
            if (it instanceof IRClassLiteral) {
                parts.append(escapeClassChar(((IRClassLiteral) it).ch));
            } else if (it instanceof IRClassRange) {
                IRClassRange range = (IRClassRange) it;
                // Escape ends of range appropriately, use unescaped - for the range operator
                parts.append(escapeClassChar(range.fromCh))
                     .append('-')
                     .append(escapeClassChar(range.toCh));
            } else if (it instanceof IRClassEscape) {
                IRClassEscape esc = (IRClassEscape) it;
                // Shorthands like \d, \p{L} are used directly
                if (esc.type.matches("[dDwWsS]")) {
                    parts.append('\\').append(esc.type);
                } else if ((esc.type.equals("p") || esc.type.equals("P")) && esc.property != null) {
                    parts.append('\\').append(esc.type).append('{').append(esc.property).append('}');
                } else {
                    // Fallback for potentially unknown escapes (shouldn't happen with valid IR)
                    parts.append('\\').append(esc.type);
                }
            } else {
                throw new UnsupportedOperationException("Unknown class item type: " + it.getClass());
            }
        }
        
        // Assemble the inner part
        String inner = parts.toString();
        return "[" + (cc.negated ? "^" : "") + inner + "]";
    }
    
    /**
     * Emit *, +, ?, {m}, {m,}, {m,n} plus optional lazy/possessive suffix.
     */
    private static String emitQuantSuffix(Object minv, Object maxv, String mode) {
        String q;
        
        int min = (minv instanceof Integer) ? (Integer) minv : 0;
        
        if (min == 0 && "Inf".equals(maxv)) {
            q = "*";
        } else if (min == 1 && "Inf".equals(maxv)) {
            q = "+";
        } else if (min == 0 && maxv.equals(1)) {
            q = "?";
        } else if (minv.equals(maxv)) {
            q = "{" + min + "}";
        } else if ("Inf".equals(maxv)) {
            q = "{" + min + ",}";
        } else {
            q = "{" + min + "," + maxv + "}";
        }
        
        if ("Lazy".equals(mode)) {
            q += "?";
        } else if ("Possessive".equals(mode)) {
            q += "+";
        }
        
        return q;
    }
    
    /**
     * Return true if 'child' needs a non-capturing group when quantifying.
     * Literals of length > 1, Seq, Alt, and Look typically require grouping.
     */
    private static boolean needsGroupForQuant(IROp child) {
        if (child instanceof IRCharClass || child instanceof IRDot ||
            child instanceof IRGroup || child instanceof IRBackref ||
            child instanceof IRAnchor) {
            return false;
        }
        if (child instanceof IRLit) {
            return ((IRLit) child).value.length() > 1;
        }
        // Group Alt/Look, but only group Seq if it's > 1 part
        if (child instanceof IRAlt || child instanceof IRLook) {
            return true;
        }
        if (child instanceof IRSeq) {
            return ((IRSeq) child).parts.size() > 1;
        }
        return false;
    }
    
    /**
     * Generate opening for group based on type.
     */
    private static String emitGroupOpen(IRGroup g) {
        if (Boolean.TRUE.equals(g.atomic)) {
            return "(?>";
        }
        if (g.capturing) {
            if (g.name != null) {
                return "(?<" + g.name + ">";
            }
            return "(";
        }
        return "(?:";
    }
    
    /**
     * Emit a single IR node to PCRE2 syntax.
     */
    private static String emitNode(IROp node, String parentKind) {
        if (node instanceof IRLit) {
            return escapeLiteral(((IRLit) node).value);
        }
        
        if (node instanceof IRDot) {
            return ".";
        }
        
        if (node instanceof IRAnchor) {
            IRAnchor anchor = (IRAnchor) node;
            Map<String, String> mapping = Map.of(
                "Start", "^",
                "End", "$",
                "WordBoundary", "\\b",
                "NotWordBoundary", "\\B",
                "AbsoluteStart", "\\A",
                "EndBeforeFinalNewline", "\\Z",
                "AbsoluteEnd", "\\z"
            );
            return mapping.getOrDefault(anchor.at, "");
        }
        
        if (node instanceof IRBackref) {
            IRBackref backref = (IRBackref) node;
            if (backref.byName != null) {
                return "\\k<" + backref.byName + ">";
            }
            if (backref.byIndex != null) {
                return "\\" + backref.byIndex;
            }
            return "";
        }
        
        if (node instanceof IRCharClass) {
            return emitClass((IRCharClass) node);
        }
        
        if (node instanceof IRSeq) {
            IRSeq seq = (IRSeq) node;
            StringBuilder sb = new StringBuilder();
            for (IROp p : seq.parts) {
                sb.append(emitNode(p, "Seq"));
            }
            return sb.toString();
        }
        
        if (node instanceof IRAlt) {
            IRAlt alt = (IRAlt) node;
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < alt.branches.size(); i++) {
                if (i > 0) sb.append("|");
                sb.append(emitNode(alt.branches.get(i), "Alt"));
            }
            String body = sb.toString();
            // Alt inside sequence/quant should be grouped
            if ("Seq".equals(parentKind) || "Quant".equals(parentKind)) {
                return "(?:" + body + ")";
            }
            return body;
        }
        
        if (node instanceof IRQuant) {
            IRQuant quant = (IRQuant) node;
            String childStr = emitNode(quant.child, "Quant");
            if (needsGroupForQuant(quant.child) && !(quant.child instanceof IRGroup)) {
                childStr = "(?:" + childStr + ")";
            }
            return childStr + emitQuantSuffix(quant.min, quant.max, quant.mode);
        }
        
        if (node instanceof IRGroup) {
            IRGroup group = (IRGroup) node;
            return emitGroupOpen(group) + emitNode(group.body, "Group") + ")";
        }
        
        if (node instanceof IRLook) {
            IRLook look = (IRLook) node;
            String op;
            if ("Ahead".equals(look.dir) && !look.neg) {
                op = "?=";
            } else if ("Ahead".equals(look.dir) && look.neg) {
                op = "?!";
            } else if ("Behind".equals(look.dir) && !look.neg) {
                op = "?<=";
            } else {
                op = "?<!";
            }
            return "(" + op + emitNode(look.body, "Look") + ")";
        }
        
        throw new UnsupportedOperationException("Emitter missing for " + node.getClass());
    }
    
    /**
     * Build the inline prefix form expected by tests, e.g. "(?imx)"
     */
    private static String emitPrefixFromFlags(Map<String, Boolean> flags) {
        StringBuilder letters = new StringBuilder();
        if (Boolean.TRUE.equals(flags.get("ignoreCase"))) {
            letters.append('i');
        }
        if (Boolean.TRUE.equals(flags.get("multiline"))) {
            letters.append('m');
        }
        if (Boolean.TRUE.equals(flags.get("dotAll"))) {
            letters.append('s');
        }
        if (Boolean.TRUE.equals(flags.get("unicode"))) {
            letters.append('u');
        }
        if (Boolean.TRUE.equals(flags.get("extended"))) {
            letters.append('x');
        }
        return letters.length() > 0 ? "(?" + letters + ")" : "";
    }
    
    /**
     * Emit a PCRE2 pattern string from IR.
     *
     * If 'flags' is provided, it can be a Flags object with toDict() method.
     */
    public static String emit(IROp irRoot, Flags flags) {
        String prefix = "";
        if (flags != null) {
            Map<String, Boolean> flagDict = flags.toDict();
            prefix = emitPrefixFromFlags(flagDict);
        }
        String body = emitNode(irRoot, "");
        // IMPORTANT: Always return prefix + body (no localized "(?imx:...)" groups)
        return prefix + body;
    }
    
    /**
     * Emit a PCRE2 pattern string from IR without flags.
     */
    public static String emit(IROp irRoot) {
        return emit(irRoot, null);
    }
}
