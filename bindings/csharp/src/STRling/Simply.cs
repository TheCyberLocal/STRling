using System.Collections.Generic;
using Strling.Core;

namespace Strling.Simply
{
    /// <summary>
    /// Shorthand entry points for the fluent API. Short name 'S' keeps usage concise.
    /// </summary>
    public static class S
    {
        public static Pattern Literal(string text) => new Pattern(new Lit(text));

        public static Pattern Digit(int count)
        {
            return new Pattern(new Quant(new Lit("\\d"), count, count, true, false, false));
        }

        public static Pattern AnyOf(string chars)
        {
            var members = new List<ClassItem>();
            foreach (var ch in chars)
            {
                members.Add(new ClassLiteral(ch.ToString()));
            }
            return new Pattern(new CharClass(false, members));
        }

        public static Pattern Start() => new Pattern(new Anchor("Start"));

        public static Pattern End() => new Pattern(new Anchor("End"));

        public static Pattern Dot() => new Pattern(new Dot());

        public static Pattern Sequence(params Pattern[] parts)
        {
            var list = new List<Node>();
            foreach (var p in parts) list.Add(p.Node);
            return new Pattern(new Seq(list));
        }
    }
}
