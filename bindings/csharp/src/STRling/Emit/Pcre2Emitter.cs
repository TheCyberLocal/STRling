using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using Strling.Core;

namespace Strling.Emit
{
    /// <summary>
    /// Lightweight PCRE2 emitter for the C# binding.
    /// This is a straightforward port of the TypeScript emitter logic used in other bindings.
    /// </summary>
    public static class Pcre2Emitter
    {
        /// <summary>
        /// Default upper bound on AST/IR nesting depth before the emitter
        /// aborts. Mirrors <c>DEFAULT_MAX_DEPTH</c> in the TypeScript SSOT
        /// and the matching constants in every other binding. Tests may
        /// override via <see cref="EmitWithDiagnostics(IROp, Flags, int)"/>.
        /// </summary>
        public const int DEFAULT_MAX_DEPTH = 250;

        private const string REDOS_MESSAGE =
            "The pattern contains overlapping alternations or nested unbounded "
          + "quantifiers (e.g., (a+)+). This can lead to catastrophic backtracking "
          + "and exponential CPU spikes. Consider using possessive quantifiers "
          + "(++ or *+) or atomic groups to guarantee execution safety.";

        /// <summary>
        /// Mutable per-emit context threaded through <see cref="EmitNode"/>
        /// so the depth, lookbehind, and warning-collection guards can fire
        /// without polluting the public API.
        /// </summary>
        private sealed class EmitContext
        {
            public int Depth;
            public int MaxDepth = DEFAULT_MAX_DEPTH;
            public bool InLookbehind;
            public readonly List<STRlingWarning> Warnings = new List<STRlingWarning>();
        }

        private static EmitContext NewContext(int maxDepth)
        {
            return new EmitContext { MaxDepth = maxDepth > 0 ? maxDepth : DEFAULT_MAX_DEPTH };
        }

        /// <summary>True iff a quantifier has an unbounded upper bound.</summary>
        private static bool IsUnboundedQuant(IRQuant q) => q.Max is string s && s == "Inf";

        /// <summary>True iff a quantifier matches a variable number of characters.</summary>
        private static bool IsVariableLengthQuant(IRQuant q)
        {
            // Object.Equals handles the int / "Inf" string sentinel mix.
            return !object.Equals((object)q.Min, q.Max);
        }

        /// <summary>
        /// Mirror of <c>_isFixedLengthBody</c> in the TS SSOT. Returns
        /// <c>true</c> when <paramref name="node"/> consumes a fixed
        /// number of characters and is therefore safe inside a PCRE2
        /// lookbehind.
        /// </summary>
        private static bool IsFixedLengthBody(IROp node)
        {
            switch (node)
            {
                case IRQuant q:
                    return !IsVariableLengthQuant(q) && IsFixedLengthBody(q.Child);
                case IRSeq seq:
                    return seq.Parts.All(IsFixedLengthBody);
                case IRAlt alt:
                    // Conservative parity with TS: every branch must be fixed-length.
                    return alt.Branches.All(IsFixedLengthBody);
                case IRGroup g:
                    return IsFixedLengthBody(g.Body);
                case IRLook _:
                    // Nested lookarounds are zero-width.
                    return true;
                default:
                    return true;
            }
        }

        /// <summary>
        /// Mirror of <c>_hasNestedUnboundedQuant</c> in the TS SSOT.
        /// Detects an unbounded quantifier reachable from <paramref name="child"/>
        /// via single-child wrappers or any branch of an Alt.
        /// </summary>
        private static bool HasNestedUnboundedQuant(IROp child)
        {
            switch (child)
            {
                case IRQuant q:
                    return IsUnboundedQuant(q);
                case IRGroup g:
                    return HasNestedUnboundedQuant(g.Body);
                case IRSeq seq:
                    return seq.Parts.Count == 1 && HasNestedUnboundedQuant(seq.Parts[0]);
                case IRAlt alt:
                    return alt.Branches.Any(HasNestedUnboundedQuant);
                default:
                    return false;
            }
        }

        /// <summary>Append a single REDOS_RISK warning, deduplicated per pass.</summary>
        private static void PushReDoSWarning(EmitContext ctx)
        {
            if (ctx.Warnings.Any(w => w.Code == "REDOS_RISK")) return;
            ctx.Warnings.Add(new STRlingWarning("REDOS_RISK", REDOS_MESSAGE));
        }

        private static string EscapeLiteral(string s)
        {
            var toEscape = new HashSet<char> { ' ', '#', '$', '&', '(', ')', '*', '+', '-', '.', '?', '[', '\\', ']', '^', '{', '|', '}', '~' };
            var sb = new StringBuilder();
            for (int i = 0; i < s.Length; i++)
            {
                var ch = s[i];
                // If this is a backslash and the next char exists, treat it as an escape sequence
                // (e.g. "\d", "\w", "\s") and emit a single backslash plus the next char.
                if (ch == '\\' && i + 1 < s.Length)
                {
                    var next = s[i + 1];
                    sb.Append('\\').Append(next);
                    i++; // skip next
                    continue;
                }

                if (toEscape.Contains(ch))
                {
                    if (ch == '-') sb.Append(ch);
                    else sb.Append('\\').Append(ch);
                }
                else sb.Append(ch);
            }
            return sb.ToString();
        }

        private static string EscapeClassChar(char ch)
        {
            if (ch == '\\' || ch == ']') return "\\" + ch;
            if (ch == '-') return "\\-";
            if (ch == '^') return "\\^";
            if (ch == '\n') return "\\n";
            if (ch == '\r') return "\\r";
            if (ch == '\t') return "\\t";
            if (ch == '\f') return "\\f";
            if (ch == '\v') return "\\v";

            var code = (int)ch;
            if (code < 32 || (code >= 127 && code <= 159))
            {
                return "\\x" + code.ToString("x2");
            }
            return ch.ToString();
        }

        private static string EmitClass(IRCharClass cc)
        {
            var items = cc.Items;

            if (items.Count == 1 && items[0] is IRClassEscape esc)
            {
                var k = esc.Type;
                var prop = esc.Property;
                if (k == "d" || k == "w" || k == "s")
                {
                    if (cc.Negated && k == "d") return "\\D";
                    if (cc.Negated && k == "w") return "\\W";
                    if (cc.Negated && k == "s") return "\\S";
                    return "\\" + k;
                }
                if (k == "D" || k == "W" || k == "S")
                {
                    var basek = k.ToLower();
                    return cc.Negated ? "\\" + basek : "\\" + k;
                }
                if ((k == "p" || k == "P") && prop != null)
                {
                    var use = cc.Negated != (k == "P") ? "P" : "p";
                    return $"\\{use}{{{prop}}}";
                }
            }

            // Smart hyphen handling: collect hyphens separately and emit them first (unescaped)
            var parts = new List<string>();
            var hasHyphen = false;

            foreach (var it in items)
            {
                if (it is IRClassLiteral lit)
                {
                    // Check if this is a hyphen literal
                    if (lit.Ch[0] == '-')
                    {
                        hasHyphen = true;
                        // Don't add to parts yet - we'll add it at the beginning
                    }
                    else
                    {
                        parts.Add(EscapeClassChar(lit.Ch[0]));
                    }
                }
                else if (it is IRClassRange range)
                {
                    parts.Add($"{EscapeClassChar(range.FromCh[0])}-{EscapeClassChar(range.ToCh[0])}");
                }
                else if (it is IRClassEscape e)
                {
                    if (e.Type == "d" || e.Type == "D" || e.Type == "w" || e.Type == "W" || e.Type == "s" || e.Type == "S")
                    {
                        parts.Add("\\" + e.Type);
                    }
                    else if ((e.Type == "p" || e.Type == "P") && e.Property != null)
                    {
                        parts.Add($"\\{e.Type}{{{e.Property}}}");
                    }
                    else
                    {
                        parts.Add("\\" + e.Type);
                    }
                }
                else
                {
                    throw new Exception($"class item {it.GetType().Name}");
                }
            }

            // Build the inner content with hyphen at the start if present
            var inner = hasHyphen ? "-" + string.Join("", parts) : string.Join("", parts);
            return "[" + (cc.Negated ? "^" : "") + inner + "]";
        }

        private static string EmitQuantSuffix(int minv, object maxv, string mode)
        {
            string q;
            if (minv == 0 && maxv is string s && s == "Inf") q = "*";
            else if (minv == 1 && maxv is string ss && ss == "Inf") q = "+";
            else if (minv == 0 && maxv is int i && i == 1) q = "?";
            else if (maxv is int maxi && minv == maxi) q = $"{{{minv}}}";
            else if (maxv is string s2 && s2 == "Inf") q = $"{{{minv},}}";
            else if (maxv is int maxInt) q = $"{{{minv},{maxInt}}}";
            else q = "";

            if (mode == "Lazy") q += "?";
            else if (mode == "Possessive") q += "+";
            return q;
        }

        private static bool NeedsGroupForQuant(IROp child)
        {
            if (child is IRCharClass || child is IRDot || child is IRGroup || child is IRBackref || child is IRAnchor) return false;
            if (child is IRLit lit)
            {
                // Treat single escape sequences like "\\d", "\\w", "\\s" as atomic
                // so quantifiers like {3} won't cause an extra non-capturing group.
                if (lit.Value.Length == 2 && lit.Value[0] == '\\') return false;
                return lit.Value.Length > 1;
            }
            if (child is IRAlt || child is IRLook) return true;
            if (child is IRSeq seq) return seq.Parts.Count > 1;
            return false;
        }

        private static string EmitGroupOpen(IRGroup g)
        {
            if (g.Atomic) return "(?>";
            if (g.Capturing)
            {
                if (g.Name != null) return $"(?<{g.Name}>";
                return "(";
            }
            return "(?:";
        }

        private static string EmitNode(IROp node, string parentKind, EmitContext ctx)
        {
            // Depth tracking surfaces the offending depth as a Signpost-pattern
            // error rather than letting the host stack overflow. Increment on
            // entry; decrement in the finally so every return path stays balanced.
            ctx.Depth += 1;
            try
            {
                if (ctx.Depth > ctx.MaxDepth)
                {
                    throw new STRlingCompilationError(
                        $"Maximum AST depth exceeded (limit: {ctx.MaxDepth}). "
                      + "This pattern is too deeply nested and risks host stack "
                      + "exhaustion during emission. Refactor the pattern to "
                      + "reduce nesting, or flatten capturing groups where possible.",
                        "MAX_DEPTH");
                }

                switch (node)
                {
                    case IRLit lit:
                        return EscapeLiteral(lit.Value);
                    case IRDot:
                        return ".";
                    case IRAnchor anchor:
                        return anchor.At switch
                        {
                            "Start" => "^",
                            "End" => "$",
                            "WordBoundary" => "\\b",
                            "NotWordBoundary" => "\\B",
                            "AbsoluteStart" => "\\A",
                            "EndBeforeFinalNewline" => "\\Z",
                            "AbsoluteEnd" => "\\z",
                            _ => ""
                        };
                    case IRBackref br:
                        if (br.ByName != null) return $"\\k<{br.ByName}>";
                        if (br.ByIndex != null) return "\\" + br.ByIndex;
                        return "";
                    case IRCharClass cls:
                        return EmitClass(cls);
                    case IRSeq seq:
                        var parts = new List<string>();
                        foreach (var p in seq.Parts) parts.Add(EmitNode(p, "Seq", ctx));
                        return string.Join("", parts);
                    case IRAlt alt:
                        var bodyParts = new List<string>();
                        foreach (var b in alt.Branches) bodyParts.Add(EmitNode(b, "Alt", ctx));
                        var body = string.Join("|", bodyParts);
                        return new List<string> { "Seq", "Quant" }.Contains(parentKind) ? $"(?:{body})" : body;
                    case IRQuant q:
                        // ReDoS guard: only flag when the *outer* quantifier is
                        // itself unbounded (e.g. `(a+)+`). A bounded outer like
                        // `(a+){0,3}` cannot produce exponential backtracking on
                        // its own.
                        if (IsUnboundedQuant(q) && HasNestedUnboundedQuant(q.Child))
                        {
                            PushReDoSWarning(ctx);
                        }
                        var childStr = EmitNode(q.Child, "Quant", ctx);
                        if (NeedsGroupForQuant(q.Child) && !(q.Child is IRGroup)) childStr = $"(?:{childStr})";
                        return childStr + EmitQuantSuffix(q.Min, q.Max, q.Mode);
                    case IRGroup g:
                        return EmitGroupOpen(g) + EmitNode(g.Body, "Group", ctx) + ")";
                    case IRLook look:
                        // Variable-length lookbehind guard: PCRE2 mandates a
                        // fixed-width lookbehind body. Detect the violation here
                        // so the user sees a Signpost-pattern error rather than
                        // an opaque PCRE2 compile failure leaking from the runtime.
                        if (look.Dir == "Behind" && !IsFixedLengthBody(look.Body))
                        {
                            throw new STRlingCompilationError(
                                "PCRE2 does not support variable-length lookbehinds. "
                              + "The lookbehind body contains a quantifier that makes "
                              + "its length unpredictable. Rewrite the assertion using "
                              + "a fixed-length range (e.g. `{1,8}` instead of `+`), "
                              + "or restructure the pattern using a Lookahead, or "
                              + "extract the quantified portion outside the assertion.",
                                "VLB_NOT_SUPPORTED");
                        }
                        var wasInLb = ctx.InLookbehind;
                        if (look.Dir == "Behind") ctx.InLookbehind = true;
                        try
                        {
                            string op;
                            if (look.Dir == "Ahead" && !look.Neg) op = "?=";
                            else if (look.Dir == "Ahead" && look.Neg) op = "?!";
                            else if (look.Dir == "Behind" && !look.Neg) op = "?<=";
                            else op = "?<!";
                            return "(" + op + EmitNode(look.Body, "Look", ctx) + ")";
                        }
                        finally
                        {
                            ctx.InLookbehind = wasInLb;
                        }
                    default:
                        throw new Exception($"Emitter missing for {node.GetType().Name}");
                }
            }
            finally
            {
                ctx.Depth -= 1;
            }
        }

        // Back-compat overload used by callers that did not thread a context.
        private static string EmitNode(IROp node, string parentKind = "")
        {
            return EmitNode(node, parentKind, NewContext(0));
        }

        private static string EmitPrefixFromFlags(Flags flags)
        {
            var letters = new StringBuilder();
            if (flags.IgnoreCase) letters.Append('i');
            if (flags.Multiline) letters.Append('m');
            if (flags.DotAll) letters.Append('s');
            if (flags.Unicode) letters.Append('u');
            if (flags.Extended) letters.Append('x');
            return letters.Length > 0 ? $"(?{letters})" : string.Empty;
        }

        public static string Emit(IROp irRoot, Flags? flags = null)
        {
            return EmitWithDiagnostics(irRoot, flags, 0).Pattern;
        }

        /// <summary>
        /// Like <see cref="Emit"/>, but also returns the list of
        /// <see cref="STRlingWarning"/>s collected during emission.
        /// Pass <c>maxDepth &lt;= 0</c> to use <see cref="DEFAULT_MAX_DEPTH"/>.
        /// </summary>
        public static CompileResult EmitWithDiagnostics(IROp irRoot, Flags? flags = null, int maxDepth = 0)
        {
            var prefix = flags != null ? EmitPrefixFromFlags(flags) : string.Empty;
            var ctx = NewContext(maxDepth);
            var body = EmitNode(irRoot, "", ctx);
            return new CompileResult(prefix + body, ctx.Warnings);
        }
    }
}
