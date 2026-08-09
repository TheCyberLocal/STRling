package com.strling.emitters;

import com.strling.core.CompileResult;
import com.strling.core.IR.*;
import com.strling.core.Nodes.Flags;
import com.strling.core.STRlingCompilationError;
import com.strling.core.STRlingWarning;

import java.util.ArrayList;
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
     * Default upper bound on AST/IR nesting depth before the emitter aborts.
     * Mirrors {@code DEFAULT_MAX_DEPTH} in the TypeScript reference (and the
     * matching constants in the C/C++/Python bindings). Tests may override
     * this via {@link #emitWithDiagnostics(IROp, Flags, int)}.
     */
    public static final int DEFAULT_MAX_DEPTH = 250;

    /**
     * Mutable context threaded through {@link #emitNode} so the depth,
     * lookbehind, and warning-collection guards can fire without polluting
     * the public API. Kept package-private; the top-level
     * {@link #emit} / {@link #emitWithDiagnostics} entry points remain
     * stateless from the caller's perspective.
     */
    static final class EmitContext {
        int depth = 0;
        int maxDepth = DEFAULT_MAX_DEPTH;
        boolean inLookbehind = false;
        final List<STRlingWarning> warnings = new ArrayList<>();
    }

    private static EmitContext newContext(int maxDepth) {
        EmitContext ctx = new EmitContext();
        ctx.maxDepth = (maxDepth > 0) ? maxDepth : DEFAULT_MAX_DEPTH;
        return ctx;
    }

    /** True iff a quantifier has an unbounded upper bound. */
    private static boolean isUnboundedQuant(IRQuant q) {
        // IRMaxBound sentinel in the wire format is the string "Inf";
        // tolerate negative ints from legacy callers as well.
        if ("Inf".equals(q.max)) return true;
        if (q.max instanceof Integer) return ((Integer) q.max) < 0;
        return false;
    }

    /** True iff a quantifier matches a variable number of characters. */
    private static boolean isVariableLengthQuant(IRQuant q) {
        // Object.equals is null-safe and value-correct for boxed Integers
        // and the "Inf" String sentinel used by the wire format.
        Object minBoxed = Integer.valueOf(q.min);
        return !minBoxed.equals(q.max);
    }

    /**
     * Mirror of {@code _isFixedLengthBody} in the TS SSOT. Returns
     * {@code true} when {@code node} consumes a fixed (statically known)
     * number of characters and is therefore safe inside a PCRE2 lookbehind.
     */
    private static boolean isFixedLengthBody(IROp node) {
        if (node instanceof IRQuant) {
            IRQuant q = (IRQuant) node;
            return !isVariableLengthQuant(q) && isFixedLengthBody(q.child);
        }
        if (node instanceof IRSeq) {
            for (IROp p : ((IRSeq) node).parts) {
                if (!isFixedLengthBody(p)) return false;
            }
            return true;
        }
        if (node instanceof IRAlt) {
            // Conservative parity with TS: every branch must be fixed-length;
            // the per-branch length-equality check is delegated to PCRE2.
            for (IROp b : ((IRAlt) node).branches) {
                if (!isFixedLengthBody(b)) return false;
            }
            return true;
        }
        if (node instanceof IRGroup) {
            return isFixedLengthBody(((IRGroup) node).body);
        }
        if (node instanceof IRLook) {
            // Nested lookarounds are zero-width, hence safe inside a lookbehind.
            return true;
        }
        // Lit, Dot, CharClass, Anchor, Backref are single- or zero-width.
        return true;
    }

    /**
     * Mirror of {@code _hasNestedUnboundedQuant} in the TS SSOT. Detects an
     * unbounded quantifier reachable from {@code child} via single-child
     * wrappers (IRGroup, single-element IRSeq) or any branch of an IRAlt.
     * Used to flag the canonical {@code (a+)+} ReDoS shape ONLY when the
     * outer quantifier is itself unbounded.
     */
    private static boolean hasNestedUnboundedQuant(IROp child) {
        if (child instanceof IRQuant) {
            return isUnboundedQuant((IRQuant) child);
        }
        if (child instanceof IRGroup) {
            return hasNestedUnboundedQuant(((IRGroup) child).body);
        }
        if (child instanceof IRSeq) {
            IRSeq seq = (IRSeq) child;
            if (seq.parts.size() == 1) return hasNestedUnboundedQuant(seq.parts.get(0));
            return false;
        }
        if (child instanceof IRAlt) {
            for (IROp b : ((IRAlt) child).branches) {
                if (hasNestedUnboundedQuant(b)) return true;
            }
        }
        return false;
    }

    private static final String REDOS_MESSAGE =
        "The pattern contains overlapping alternations or nested unbounded "
      + "quantifiers (e.g., (a+)+). This can lead to catastrophic backtracking "
      + "and exponential CPU spikes. Consider using possessive quantifiers "
      + "(++ or *+) or atomic groups to guarantee execution safety.";

    /** Append a single REDOS_RISK warning, deduplicated per emit pass. */
    private static void pushReDoSWarning(EmitContext ctx) {
        for (STRlingWarning w : ctx.warnings) {
            if ("REDOS_RISK".equals(w.getCode())) return;
        }
        ctx.warnings.add(new STRlingWarning("REDOS_RISK", REDOS_MESSAGE));
    }

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
    private static String emitNode(IROp node, String parentKind, EmitContext ctx) {
        // Depth tracking surfaces the offending depth as a Signpost-pattern
        // error rather than letting the host stack overflow. Increment on
        // entry, decrement in the finally block so every return path stays
        // balanced even under exceptions.
        ctx.depth += 1;
        try {
            if (ctx.depth > ctx.maxDepth) {
                throw new STRlingCompilationError(
                    "Maximum AST depth exceeded (limit: " + ctx.maxDepth + "). "
                  + "This pattern is too deeply nested and risks host stack "
                  + "exhaustion during emission. Refactor the pattern to "
                  + "reduce nesting, or flatten capturing groups where possible.",
                    "MAX_DEPTH",
                    "pcre2"
                );
            }

            if (node instanceof IRLit) {
                return escapeLiteral(((IRLit) node).value);
            }

            if (node instanceof IRDot) {
                return ".";
            }

            if (node instanceof IRAnchor) {
                IRAnchor anchor = (IRAnchor) node;
                String at = anchor.at;
                if ("NonWordBoundary".equals(at)) {
                    return "\\B";
                }
                Map<String, String> mapping = Map.of(
                    "Start", "^",
                    "End", "$",
                    "WordBoundary", "\\b",
                    "NotWordBoundary", "\\B",
                    "AbsoluteStart", "\\A",
                    "EndBeforeFinalNewline", "\\Z",
                    "AbsoluteEnd", "\\z"
                );
                return mapping.getOrDefault(at, "");
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
                    sb.append(emitNode(p, "Seq", ctx));
                }
                return sb.toString();
            }

            if (node instanceof IRAlt) {
                IRAlt alt = (IRAlt) node;
                StringBuilder sb = new StringBuilder();
                for (int i = 0; i < alt.branches.size(); i++) {
                    if (i > 0) sb.append("|");
                    sb.append(emitNode(alt.branches.get(i), "Alt", ctx));
                }
                String body = sb.toString();
                if ("Seq".equals(parentKind) || "Quant".equals(parentKind)) {
                    return "(?:" + body + ")";
                }
                return body;
            }

            if (node instanceof IRQuant) {
                IRQuant quant = (IRQuant) node;
                // ReDoS guard: only flag when the *outer* quantifier is itself
                // unbounded (e.g. `(a+)+`). A bounded outer like `(a+){0,3}`
                // cannot produce exponential backtracking on its own.
                if (isUnboundedQuant(quant) && hasNestedUnboundedQuant(quant.child)) {
                    pushReDoSWarning(ctx);
                }

                String childStr = emitNode(quant.child, "Quant", ctx);
                if (needsGroupForQuant(quant.child) && !(quant.child instanceof IRGroup)) {
                    childStr = "(?:" + childStr + ")";
                }
                return childStr + emitQuantSuffix(quant.min, quant.max, quant.mode);
            }

            if (node instanceof IRGroup) {
                IRGroup group = (IRGroup) node;
                return emitGroupOpen(group) + emitNode(group.body, "Group", ctx) + ")";
            }

            if (node instanceof IRLook) {
                IRLook look = (IRLook) node;
                // Variable-length lookbehind guard: PCRE2 mandates a fixed-width
                // lookbehind body. Detect the violation here so the user sees a
                // Signpost-pattern error rather than an opaque PCRE2 compile
                // failure leaking from the runtime.
                if ("Behind".equals(look.dir) && !isFixedLengthBody(look.body)) {
                    throw new STRlingCompilationError(
                        "PCRE2 does not support variable-length lookbehinds. "
                      + "The lookbehind body contains a quantifier that makes "
                      + "its length unpredictable. Rewrite the assertion using "
                      + "a fixed-length range (e.g. `{1,8}` instead of `+`), "
                      + "or restructure the pattern using a Lookahead, or "
                      + "extract the quantified portion outside the assertion.",
                        "VLB_NOT_SUPPORTED",
                        "pcre2"
                    );
                }

                boolean wasInLookbehind = ctx.inLookbehind;
                if ("Behind".equals(look.dir)) ctx.inLookbehind = true;
                try {
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
                    return "(" + op + emitNode(look.body, "Look", ctx) + ")";
                } finally {
                    ctx.inLookbehind = wasInLookbehind;
                }
            }

            throw new UnsupportedOperationException("Emitter missing for " + node.getClass());
        } finally {
            ctx.depth -= 1;
        }
    }

    /**
     * Back-compat overload for callers that already pass without a context.
     * Constructs a fresh context internally — used by the legacy
     * {@link #emit(IROp, Flags)} entry point and by direct unit tests.
     */
    private static String emitNode(IROp node, String parentKind) {
        return emitNode(node, parentKind, newContext(0));
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
     *
     * <p>Throws {@link STRlingCompilationError} when an emitter safety guard
     * rejects the IR (variable-length lookbehind, AST depth exceeded).
     * Diagnostic warnings (e.g. {@code REDOS_RISK}) are silently dropped
     * from this back-compat entry point; callers that need them must use
     * {@link #emitWithDiagnostics(IROp, Flags)} or the depth-aware overload.
     */
    public static String emit(IROp irRoot, Flags flags) {
        return emitWithDiagnostics(irRoot, flags, 0).getPattern();
    }

    /**
     * Emit a PCRE2 pattern string from IR without flags.
     */
    public static String emit(IROp irRoot) {
        return emit(irRoot, null);
    }

    /**
     * Like {@link #emit(IROp, Flags)}, but also returns the list of
     * {@link STRlingWarning}s collected during emission. Used by the
     * conformance test runner and any caller that wants to surface
     * {@code REDOS_RISK} (or future) warnings to the end user.
     */
    public static CompileResult emitWithDiagnostics(IROp irRoot, Flags flags) {
        return emitWithDiagnostics(irRoot, flags, 0);
    }

    /**
     * Diagnostics-bearing entry point with an optional depth-cap override.
     * Pass {@code maxDepth <= 0} to use {@link #DEFAULT_MAX_DEPTH}. The
     * override is primarily used by the conformance fixture
     * {@code tests/conformance/inputs/emitter_edges/} to provoke the depth
     * guard with a small input.
     */
    public static CompileResult emitWithDiagnostics(IROp irRoot, Flags flags, int maxDepth) {
        String prefix = "";
        if (flags != null) {
            Map<String, Boolean> flagDict = flags.toDict();
            prefix = emitPrefixFromFlags(flagDict);
        }
        EmitContext ctx = newContext(maxDepth);
        String body = emitNode(irRoot, "", ctx);
        return new CompileResult(prefix + body, ctx.warnings);
    }
}
