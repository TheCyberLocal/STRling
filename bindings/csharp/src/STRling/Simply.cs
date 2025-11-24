using System.Collections.Generic;
using Strling.Core;

namespace Strling.Simply
{
    /// <summary>
    /// Shorthand entry points for the fluent API. Short name 'S' keeps usage concise.
    /// </summary>
    public static class S
    {
        /// <summary>
        /// Creates a literal pattern that matches the exact text.
        /// </summary>
        /// <param name="text">The literal text to match.</param>
        /// <returns>A Pattern that matches the literal text.</returns>
        public static Pattern Literal(string text) => new Pattern(new Lit(text));

        /// <summary>
        /// Creates a pattern that matches exactly 'count' digits (\d).
        /// </summary>
        /// <param name="count">The number of digits to match.</param>
        /// <returns>A Pattern that matches the specified number of digits.</returns>
        public static Pattern Digit(int count)
        {
            return new Pattern(new Quant(new Lit("\\d"), count, count, true, false, false));
        }

        /// <summary>
        /// Creates a character class pattern that matches any one of the provided characters.
        /// </summary>
        /// <param name="chars">A string containing the characters to match.</param>
        /// <returns>A Pattern that matches any single character from the input string.</returns>
        public static Pattern AnyOf(string chars)
        {
            var members = new List<ClassItem>();
            foreach (var ch in chars)
            {
                members.Add(new ClassLiteral(ch.ToString()));
            }
            return new Pattern(new CharClass(false, members));
        }

        /// <summary>
        /// Creates an anchor pattern that matches the start of the string (^).
        /// </summary>
        /// <returns>A Pattern that matches the start of the string.</returns>
        public static Pattern Start() => new Pattern(new Anchor("Start"));

        /// <summary>
        /// Creates an anchor pattern that matches the end of the string ($).
        /// </summary>
        /// <returns>A Pattern that matches the end of the string.</returns>
        public static Pattern End() => new Pattern(new Anchor("End"));

        /// <summary>
        /// Creates a pattern that matches any character (.).
        /// </summary>
        /// <returns>A Pattern that matches any character.</returns>
        public static Pattern Dot() => new Pattern(new Dot());

        /// <summary>
        /// Creates a sequence pattern that matches the provided patterns in order.
        /// </summary>
        /// <param name="parts">The patterns to match in sequence.</param>
        /// <returns>A Pattern that matches all the input patterns in order.</returns>
        public static Pattern Sequence(params Pattern[] parts)
        {
            var list = new List<Node>();
            foreach (var p in parts) list.Add(p.Node);
            return new Pattern(new Seq(list));
        }
    }
}
