using System;
using System.Collections.Generic;
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

            var parts = new List<string>();
            foreach (var it in items)
            {
                if (it is IRClassLiteral lit)
                {
                    parts.Add(EscapeClassChar(lit.Ch[0]));
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
            var inner = string.Join("", parts);
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

        private static string EmitNode(IROp node, string parentKind = "")
        {
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
                    foreach (var p in seq.Parts) parts.Add(EmitNode(p, "Seq"));
                    return string.Join("", parts);
                case IRAlt alt:
                    var bodyParts = new List<string>();
                    foreach (var b in alt.Branches) bodyParts.Add(EmitNode(b, "Alt"));
                    var body = string.Join("|", bodyParts);
                    return new List<string> { "Seq", "Quant" }.Contains(parentKind) ? $"(?:{body})" : body;
                case IRQuant q:
                    var childStr = EmitNode(q.Child, "Quant");
                    if (NeedsGroupForQuant(q.Child) && !(q.Child is IRGroup)) childStr = $"(?:{childStr})";
                    return childStr + EmitQuantSuffix(q.Min, q.Max, q.Mode);
                case IRGroup g:
                    return EmitGroupOpen(g) + EmitNode(g.Body, "Group") + ")";
                case IRLook look:
                    string op;
                    if (look.Dir == "Ahead" && !look.Neg) op = "?=";
                    else if (look.Dir == "Ahead" && look.Neg) op = "?!";
                    else if (look.Dir == "Behind" && !look.Neg) op = "?<=";
                    else op = "?!";
                    return "(" + op + EmitNode(look.Body, "Look") + ")";
                default:
                    throw new Exception($"Emitter missing for {node.GetType().Name}");
            }
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
            var prefix = flags != null ? EmitPrefixFromFlags(flags) : string.Empty;
            var body = EmitNode(irRoot, "");
            return prefix + body;
        }
    }
}
