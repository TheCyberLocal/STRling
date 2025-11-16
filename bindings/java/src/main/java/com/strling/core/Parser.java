package com.strling.core;

import com.strling.core.Nodes.*;

import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * STRling Parser - Recursive Descent Parser for STRling DSL
 *
 * <p>This module implements a hand-rolled recursive-descent parser that transforms
 * STRling pattern syntax into Abstract Syntax Tree (AST) nodes. The parser handles:</p>
 * <ul>
 *   <li>Alternation and sequencing</li>
 *   <li>Character classes and ranges</li>
 *   <li>Quantifiers (greedy, lazy, possessive)</li>
 *   <li>Groups (capturing, non-capturing, named, atomic)</li>
 *   <li>Lookarounds (lookahead and lookbehind, positive and negative)</li>
 *   <li>Anchors and special escapes</li>
 *   <li>Extended/free-spacing mode with comments</li>
 * </ul>
 *
 * <p>The parser produces AST nodes (defined in Nodes.java) that can be compiled
 * to IR and ultimately emitted as target-specific regex patterns. It includes
 * comprehensive error handling with position tracking for helpful diagnostics.</p>
 */
public class Parser {
    
    /**
     * Result of a parse operation containing flags and the parsed AST.
     */
    public static class ParseResult {
        public final Flags flags;
        public final Node ast;
        
        public ParseResult(Flags flags, Node ast) {
            this.flags = flags;
            this.ast = ast;
        }
    }
    
    /**
     * Lexer cursor for tracking position within the input text.
     */
    static class Cursor {
        final String text;
        int i = 0;
        boolean extendedMode = false;
        int inClass = 0; // nesting count for char classes
        
        Cursor(String text, int i, boolean extendedMode, int inClass) {
            this.text = text;
            this.i = i;
            this.extendedMode = extendedMode;
            this.inClass = inClass;
        }
        
        boolean eof() {
            return i >= text.length();
        }
        
        String peek() {
            return peek(0);
        }
        
        String peek(int n) {
            int j = i + n;
            return (j >= text.length()) ? "" : String.valueOf(text.charAt(j));
        }
        
        String take() {
            if (eof()) return "";
            char ch = text.charAt(i);
            i++;
            return String.valueOf(ch);
        }
        
        boolean match(String s) {
            if (text.startsWith(s, i)) {
                i += s.length();
                return true;
            }
            return false;
        }
        
        /**
         * Skip whitespace and comments in extended/free-spacing mode.
         * 
         * <p>In free-spacing mode, ignore spaces/tabs/newlines and #-to-EOL comments.</p>
         */
        void skipWsAndComments() {
            if (!extendedMode || inClass > 0) {
                return;
            }
            // In free-spacing mode, ignore spaces/tabs/newlines and #-to-EOL comments
            while (!eof()) {
                String ch = peek();
                if (ch.equals(" ") || ch.equals("\t") || ch.equals("\r") || ch.equals("\n")) {
                    i++;
                    continue;
                }
                if (ch.equals("#")) {
                    // skip comment to end of line
                    while (!eof() && !peek().equals("\r") && !peek().equals("\n")) {
                        i++;
                    }
                    continue;
                }
                break;
            }
        }
    }
    
    private final String originalText;
    private final Flags flags;
    private final String src;
    private final Cursor cur;
    private int capCount = 0;
    private final Set<String> capNames = new HashSet<>();
    private final Map<String, String> CONTROL_ESCAPES = new HashMap<>();
    
    private Parser(String text) {
        this.originalText = text;
        // Extract directives first
        DirectiveResult dirResult = parseDirectives(text);
        this.flags = dirResult.flags;
        this.src = dirResult.pattern;
        this.cur = new Cursor(this.src, 0, this.flags.extended, 0);
        
        CONTROL_ESCAPES.put("n", "\n");
        CONTROL_ESCAPES.put("r", "\r");
        CONTROL_ESCAPES.put("t", "\t");
        CONTROL_ESCAPES.put("f", "\f");
        CONTROL_ESCAPES.put("v", "\u000B");
    }
    
    /**
     * Raise a STRlingParseError with an instructional hint.
     *
     * @param message The error message
     * @param pos The position where the error occurred
     * @throws STRlingParseError Always throws with context and hint
     */
    private void raiseError(String message, int pos) {
        String hint = getHint(message, src, pos);
        throw new STRlingParseError(message, pos, src, hint);
    }
    
    /**
     * Simple hint generation for common error cases.
     * 
     * @param message The error message
     * @param source The source text
     * @param pos The error position
     * @return A helpful hint message
     */
    private static String getHint(String message, String source, int pos) {
        // Simple hint generation - can be enhanced later
        if (message.contains("Cannot quantify anchor")) {
            return "Anchors like ^, $, \\b, and \\B match positions, not characters, so they cannot be quantified.";
        }
        if (message.contains("Unknown escape sequence")) {
            return "This escape sequence is not recognized. Check the documentation for valid escape sequences.";
        }
        if (message.contains("Invalid quantifier")) {
            return "Quantifiers (*, +, ?, {n,m}) must follow an atom (literal, group, character class, etc.).";
        }
        return "Please check your pattern syntax.";
    }
    
    /**
     * Directive parsing result.
     */
    static class DirectiveResult {
        final Flags flags;
        final String pattern;
        
        DirectiveResult(Flags flags, String pattern) {
            this.flags = flags;
            this.pattern = pattern;
        }
    }
    
    /**
     * Parse directives (like %flags) from the pattern.
     *
     * @param text The full input text
     * @return DirectiveResult containing flags and the pattern portion
     */
    private static DirectiveResult parseDirectives(String text) {
        Flags flags = new Flags();
        String[] lines = text.split("\\r?\\n", -1);
        List<String> patternLines = new ArrayList<>();
        boolean inPattern = false;
        
        for (String line : lines) {
            String stripped = line.trim();
            // Skip leading blank lines or comments
            if (!inPattern && (stripped.isEmpty() || stripped.startsWith("#"))) {
                continue;
            }
            // Process directives only before pattern content
            if (!inPattern && stripped.startsWith("%flags")) {
                int idx = line.indexOf("%flags");
                String after = line.substring(idx + "%flags".length());
                
                // Extract flags - simple version
                String flagsStr = after.replaceAll("[\\s,\\[\\]]+", " ").trim().toLowerCase();
                for (char ch : flagsStr.toCharArray()) {
                    if (ch == ' ') continue;
                    switch (ch) {
                        case 'i': flags.ignoreCase = true; break;
                        case 'm': flags.multiline = true; break;
                        case 's': flags.dotAll = true; break;
                        case 'u': flags.unicode = true; break;
                        case 'x': flags.extended = true; break;
                    }
                }
                inPattern = true;
                continue;
            }
            // Once we see non-directive content, we're in the pattern
            inPattern = true;
            patternLines.add(line);
        }
        
        String pattern = String.join("\n", patternLines);
        return new DirectiveResult(flags, pattern);
    }
    
    /**
     * Parse the entire STRling pattern into an AST.
     *
     * <p>Entry point for parsing. Parses the pattern (after directives have been
     * extracted) and validates that the entire input has been consumed.</p>
     *
     * @return The root AST node representing the entire pattern
     * @throws STRlingParseError If there is unexpected trailing input or if the pattern ends with
     *                           an incomplete alternation
     */
    private Node parseInternal() {
        Node node = parseAlt();
        cur.skipWsAndComments();
        if (!cur.eof()) {
            // If there's an unmatched closing parenthesis at top-level, raise an explicit error
            if (cur.peek().equals(")")) {
                throw new STRlingParseError(
                    "Unmatched ')'",
                    cur.i,
                    src,
                    "This ')' character does not have a matching opening '('. Did you mean to escape it with '\\)'?"
                );
            }
            if (cur.peek().equals("|")) {
                // Alternation must have a right-hand side
                raiseError("Alternation lacks right-hand side", cur.i);
            } else {
                raiseError("Unexpected trailing input", cur.i);
            }
        }
        return node;
    }
    
    /**
     * Parse an alternation expression: seq ('|' seq)+ | seq
     *
     * @return Node representing the alternation or single sequence
     */
    private Node parseAlt() {
        // Check if the pattern starts with a pipe (no left-hand side)
        cur.skipWsAndComments();
        if (cur.peek().equals("|")) {
            raiseError("Alternation lacks left-hand side", cur.i);
        }
        
        List<Node> branches = new ArrayList<>();
        branches.add(parseSeq());
        cur.skipWsAndComments();
        
        while (cur.peek().equals("|")) {
            int pipePos = cur.i;
            cur.take();
            cur.skipWsAndComments();
            // Check if the pipe is followed by end-of-input (no right-hand side)
            if (cur.peek().isEmpty()) {
                raiseError("Alternation lacks right-hand side", pipePos);
            }
            // Check if the pipe is followed by another pipe (empty branch)
            if (cur.peek().equals("|")) {
                raiseError("Empty alternation branch", pipePos);
            }
            branches.add(parseSeq());
            cur.skipWsAndComments();
        }
        
        if (branches.size() == 1) {
            return branches.get(0);
        }
        return new Alt(branches);
    }
    
    /**
     * Parse a sequence of terms.
     *
     * @return Node representing the sequence
     */
    private Node parseSeq() {
        List<Node> parts = new ArrayList<>();
        boolean prevHadFailedQuant = false;
        
        while (true) {
            cur.skipWsAndComments();
            String ch = cur.peek();
            
            // Invalid quantifier at start of sequence/group (no previous atom)
            if (!ch.isEmpty() && ("*+?{".indexOf(ch) >= 0) && parts.isEmpty()) {
                raiseError(String.format("Invalid quantifier '%s'", ch), cur.i);
            }
            
            // Stop parsing sequence if we hit end, closing paren, or alternation pipe
            if (ch.isEmpty() || ch.equals(")") || ch.equals("|")) {
                break;
            }
            
            // Parse the fundamental unit (literal, class, group, escape, etc.)
            Node atom = parseAtom();
            
            // Parse any quantifier (*, +, ?, {m,n}) that might follow the atom
            QuantResult quantResult = parseQuantIfAny(atom);
            Node quantifiedAtom = quantResult.node;
            boolean hadFailedQuantParse = quantResult.hadFailedParse;
            
            // Coalesce adjacent Lit nodes if appropriate
            boolean shouldCoalesce = quantifiedAtom instanceof Lit
                && !parts.isEmpty()
                && parts.get(parts.size() - 1) instanceof Lit
                && !cur.extendedMode
                && !prevHadFailedQuant;
            
            if (shouldCoalesce) {
                Lit prevLit = (Lit) parts.get(parts.size() - 1);
                Lit currLit = (Lit) quantifiedAtom;
                parts.set(parts.size() - 1, new Lit(prevLit.value + currLit.value));
            } else {
                parts.add(quantifiedAtom);
            }
            
            prevHadFailedQuant = hadFailedQuantParse;
        }
        
        // If the sequence ended up being just one atom, return it directly
        if (parts.size() == 1) {
            return parts.get(0);
        }
        // Otherwise, return a Sequence node containing all parts
        return new Seq(parts);
    }
    
    /**
     * Result of quantifier parsing.
     */
    static class QuantResult {
        final Node node;
        final boolean hadFailedParse;
        
        QuantResult(Node node, boolean hadFailedParse) {
            this.node = node;
            this.hadFailedParse = hadFailedParse;
        }
    }
    
    /**
     * Parse an optional quantifier following an atom and apply it if present.
     *
     * @param child The atom to potentially quantify
     * @return QuantResult containing the (possibly quantified) node and whether quantifier parsing failed
     */
    private QuantResult parseQuantIfAny(Node child) {
        cur.skipWsAndComments();
        String ch = cur.peek();
        
        // Check if child is an anchor - anchors cannot be quantified
        if (child instanceof Anchor) {
            if (!ch.isEmpty() && "*+?{".indexOf(ch) >= 0) {
                raiseError("Cannot quantify anchor", cur.i);
            }
            return new QuantResult(child, false);
        }
        
        int min = 0;
        Object max = 0;
        
        if (ch.equals("*")) {
            cur.take();
            min = 0;
            max = "Inf";
        } else if (ch.equals("+")) {
            cur.take();
            min = 1;
            max = "Inf";
        } else if (ch.equals("?")) {
            cur.take();
            min = 0;
            max = 1;
        } else if (ch.equals("{")) {
            BraceQuantResult bq = parseBraceQuant();
            if (bq == null) {
                return new QuantResult(child, true);
            }
            min = bq.min != null ? bq.min : 0;
            max = bq.max != null ? bq.max : "Inf";
        } else {
            // No quantifier
            return new QuantResult(child, false);
        }
        
        // Check for mode suffix (?, +)
        cur.skipWsAndComments();
        String mode = "Greedy";
        String suffix = cur.peek();
        if (suffix.equals("?")) {
            cur.take();
            mode = "Lazy";
        } else if (suffix.equals("+")) {
            cur.take();
            mode = "Possessive";
        }
        
        return new QuantResult(new Quant(child, min, max, mode), false);
    }
    
    /**
     * Result of brace quantifier parsing.
     */
    static class BraceQuantResult {
        final Integer min;
        final Object max; // Integer or String "Inf"
        
        BraceQuantResult(Integer min, Object max) {
            this.min = min;
            this.max = max;
        }
    }
    
    /**
     * Parse a brace quantifier {m,n}.
     *
     * @return BraceQuantResult or null if parsing failed
     */
    private BraceQuantResult parseBraceQuant() {
        if (!cur.match("{")) return null;
        
        int start = cur.i;
        StringBuilder digits = new StringBuilder();
        
        // Read first number
        while (!cur.eof() && Character.isDigit(cur.peek().charAt(0))) {
            digits.append(cur.take());
        }
        
        Integer min = digits.length() > 0 ? Integer.parseInt(digits.toString()) : null;
        
        cur.skipWsAndComments();
        if (cur.peek().equals(",")) {
            cur.take();
            cur.skipWsAndComments();
            
            digits = new StringBuilder();
            while (!cur.eof() && Character.isDigit(cur.peek().charAt(0))) {
                digits.append(cur.take());
            }
            
            Object max = digits.length() > 0 ? (Object) Integer.parseInt(digits.toString()) : "Inf";
            
            cur.skipWsAndComments();
            if (!cur.match("}")) {
                raiseError("Incomplete quantifier", cur.i);
            }
            
            return new BraceQuantResult(min, max);
        } else if (cur.peek().equals("}")) {
            cur.take();
            return new BraceQuantResult(min, min);
        }
        
        raiseError("Invalid brace quantifier", start);
        return null;
    }
    
    /**
     * Parse an atomic pattern element (the most basic building blocks).
     *
     * <p>Atoms are the fundamental units of a pattern:</p>
     * <ul>
     *   <li>Dot (.) for any character</li>
     *   <li>Anchors (^ for start, $ for end)</li>
     *   <li>Groups and lookarounds (parentheses)</li>
     *   <li>Character classes (square brackets)</li>
     *   <li>Escapes (backslash sequences)</li>
     *   <li>Literal characters</li>
     * </ul>
     *
     * @return An AST node representing the parsed atom
     * @throws STRlingParseError If an unexpected token is encountered
     */
    private Node parseAtom() {
        cur.skipWsAndComments();
        String ch = cur.peek();
        
        if (ch.equals(".")) {
            cur.take();
            return new Dot();
        }
        if (ch.equals("^")) {
            cur.take();
            return new Anchor("Start");
        }
        if (ch.equals("$")) {
            cur.take();
            return new Anchor("End");
        }
        if (ch.equals("(")) {
            return parseGroupOrLook();
        }
        if (ch.equals("[")) {
            return parseCharClass();
        }
        if (ch.equals("\\")) {
            return parseEscapeAtom();
        }
        // literal
        // If we encounter a closing paren here it means there was no matching opening parenthesis
        if (ch.equals(")")) {
            throw new STRlingParseError(
                "Unmatched ')'",
                cur.i,
                src,
                "This ')' character does not have a matching opening '('. Did you mean to escape it with '\\)'?"
            );
        }
        if (ch.equals("|")) {
            raiseError("Unexpected token", cur.i);
        }
        return new Lit(takeLiteralChar());
    }
    
    /**
     * Take a single literal character from the input.
     *
     * @return The literal character as a string
     */
    private String takeLiteralChar() {
        return cur.take();
    }
    
    /**
     * Parse an escape sequence atom.
     *
     * @return Node representing the escape sequence
     */
    private Node parseEscapeAtom() {
        int startPos = cur.i; // Save position at start of escape
        assert cur.take().equals("\\");
        String nxt = cur.peek();
        
        // Backref by index \1.. (but not \0)
        if (!nxt.isEmpty() && Character.isDigit(nxt.charAt(0)) && !nxt.equals("0")) {
            int savedPos = cur.i;
            StringBuilder numStr = new StringBuilder();
            
            // Read digits one at a time
            while (!cur.peek().isEmpty() && Character.isDigit(cur.peek().charAt(0))) {
                numStr.append(cur.take());
                int num = Integer.parseInt(numStr.toString());
                
                if (num <= capCount) {
                    continue;
                } else {
                    // Too large, backtrack
                    cur.i--;
                    numStr.setLength(numStr.length() - 1);
                    break;
                }
            }
            
            if (numStr.length() > 0) {
                int num = Integer.parseInt(numStr.toString());
                if (num <= capCount) {
                    return new Backref(num, null);
                }
            }
            
            // No valid backref found
            cur.i = savedPos;
            int num = readDecimal();
            raiseError(String.format("Backreference to undefined group \\%d", num), startPos);
        }
        
        // Anchors \b \B \A \Z
        if (nxt.equals("b") || nxt.equals("B") || nxt.equals("A") || nxt.equals("Z")) {
            String ch = cur.take();
            switch (ch) {
                case "b": return new Anchor("WordBoundary");
                case "B": return new Anchor("NotWordBoundary");
                case "A": return new Anchor("AbsoluteStart");
                case "Z": return new Anchor("EndBeforeFinalNewline");
            }
        }
        
        // \k<name> named backref
        if (nxt.equals("k")) {
            cur.take();
            if (!cur.match("<")) {
                raiseError("Expected '<' after \\k", startPos);
            }
            String name = readIdentUntil(">");
            if (!cur.match(">")) {
                raiseError("Unterminated named backref", startPos);
            }
            if (!capNames.contains(name)) {
                raiseError(String.format("Backreference to undefined group <%s>", name), startPos);
            }
            return new Backref(null, name);
        }
        
        // Shorthand classes \d \D \w \W \s \S
        if ("dDwWsS".indexOf(nxt) >= 0) {
            String type = cur.take();
            return new CharClass(false, Collections.singletonList(new ClassEscape(type)));
        }
        
        // Property escapes \p{...} \P{...}
        if (nxt.equals("p") || nxt.equals("P")) {
            String tp = cur.take();
            if (!cur.match("{")) {
                raiseError("Expected { after \\p/\\P", cur.i);
            }
            String prop = readUntil("}");
            if (!cur.match("}")) {
                raiseError("Unterminated \\p{...}", cur.i);
            }
            return new CharClass(false, Collections.singletonList(new ClassEscape(tp, prop)));
        }
        
        // Core control escapes \n \t \r \f \v
        if (CONTROL_ESCAPES.containsKey(nxt)) {
            String ch = cur.take();
            return new Lit(CONTROL_ESCAPES.get(ch));
        }
        
        // Escaped literal
        if (!nxt.isEmpty()) {
            String escapedChar = cur.take();
            // Check for unknown escapes
            if ("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ".indexOf(escapedChar) >= 0) {
                raiseError(String.format("Unknown escape sequence \\%s", escapedChar), startPos);
            }
            return new Lit(escapedChar);
        }
        
        raiseError("Incomplete escape at end of pattern", startPos);
        return null;
    }
    
    /**
     * Read a decimal number from the current position.
     *
     * @return The decimal number
     */
    private int readDecimal() {
        StringBuilder digits = new StringBuilder();
        while (!cur.eof() && Character.isDigit(cur.peek().charAt(0))) {
            digits.append(cur.take());
        }
        return Integer.parseInt(digits.toString());
    }
    
    /**
     * Read an identifier until the specified terminator.
     *
     * @param terminator The terminating string
     * @return The identifier
     */
    private String readIdentUntil(String terminator) {
        StringBuilder result = new StringBuilder();
        while (!cur.eof() && !cur.peek().equals(terminator)) {
            result.append(cur.take());
        }
        return result.toString();
    }
    
    /**
     * Read until the specified terminator.
     *
     * @param terminator The terminating string
     * @return The read string
     */
    private String readUntil(String terminator) {
        StringBuilder result = new StringBuilder();
        while (!cur.eof() && !cur.peek().equals(terminator)) {
            result.append(cur.take());
        }
        return result.toString();
    }
    
    /**
     * Parse a character class [...] or negated class [^...].
     *
     * @return CharClass node
     */
    private Node parseCharClass() {
        int startPos = cur.i;
        cur.take(); // consume [
        cur.inClass++;
        
        boolean negated = false;
        if (cur.peek().equals("^")) {
            negated = true;
            cur.take();
        }
        
        List<ClassItem> items = new ArrayList<>();
        
        while (!cur.eof() && !cur.peek().equals("]")) {
            String ch = cur.take();
            
            // Check for range
            if (cur.peek().equals("-") && !cur.peek(1).equals("]")) {
                cur.take(); // consume -
                String toCh = cur.take();
                items.add(new ClassRange(ch, toCh));
            } else {
                items.add(new ClassLiteral(ch));
            }
        }
        
        if (!cur.match("]")) {
            raiseError("Unterminated character class", cur.i);
        }
        
        cur.inClass--;
        return new CharClass(negated, items);
    }
    
    /**
     * Parse a group or lookaround construct.
     *
     * @return Node representing the group or lookaround
     */
    private Node parseGroupOrLook() {
        int startPos = cur.i;
        cur.take(); // consume (
        
        // Check for special group types
        if (cur.match("?:")) {
            // Non-capturing group
            Node body = parseAlt();
            if (!cur.match(")")) {
                raiseError("Unterminated group", cur.i);
            }
            return new Group(false, body);
        }
        
        if (cur.match("?>")) {
            // Atomic group
            Node body = parseAlt();
            if (!cur.match(")")) {
                raiseError("Unterminated group", cur.i);
            }
            return new Group(false, body, null, true);
        }
        
        if (cur.match("?=")) {
            // Positive lookahead
            Node body = parseAlt();
            if (!cur.match(")")) {
                raiseError("Unterminated lookahead", cur.i);
            }
            return new Look("Ahead", false, body);
        }
        
        if (cur.match("?!")) {
            // Negative lookahead
            Node body = parseAlt();
            if (!cur.match(")")) {
                raiseError("Unterminated lookahead", cur.i);
            }
            return new Look("Ahead", true, body);
        }
        
        if (cur.match("?<=")) {
            // Positive lookbehind
            Node body = parseAlt();
            if (!cur.match(")")) {
                raiseError("Unterminated lookbehind", cur.i);
            }
            return new Look("Behind", false, body);
        }
        
        if (cur.match("?<!")) {
            // Negative lookbehind
            Node body = parseAlt();
            if (!cur.match(")")) {
                raiseError("Unterminated lookbehind", cur.i);
            }
            return new Look("Behind", true, body);
        }
        
        if (cur.match("?<")) {
            // Named capturing group
            String name = readIdentUntil(">");
            if (!cur.match(">")) {
                raiseError("Unterminated group name", cur.i);
            }
            // Check for duplicate group name
            if (capNames.contains(name)) {
                raiseError("Duplicate group name <" + name + ">", startPos);
            }
            capNames.add(name);
            capCount++;
            Node body = parseAlt();
            if (!cur.match(")")) {
                raiseError("Unterminated group", cur.i);
            }
            return new Group(true, body, name);
        }
        
        // Check for inline modifiers (not supported)
        if (cur.peek().equals("?")) {
            raiseError("Inline modifiers are not supported", startPos + 1);
        }
        
        // Default: capturing group
        capCount++;
        Node body = parseAlt();
        if (!cur.match(")")) {
            raiseError("Unterminated group", cur.i);
        }
        return new Group(true, body);
    }
    
    /**
     * Public API: Parse a STRling pattern string into an AST.
     *
     * @param src The STRling pattern string
     * @return ParseResult containing the flags and parsed AST
     * @throws STRlingParseError If the pattern is invalid
     */
    public static ParseResult parse(String src) {
        Parser p = new Parser(src);
        Node ast = p.parseInternal();
        return new ParseResult(p.flags, ast);
    }
}
