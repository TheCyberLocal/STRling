using System.Collections.Generic;
using Strling.Core;

namespace Strling.Simply
{
    /// <summary>
    /// A small wrapper around the core AST Node to provide a fluent API surface.
    /// </summary>
    public sealed class Pattern
    {
        internal Node Node { get; }

        public Pattern(Node node)
        {
            Node = node;
        }

        /// <summary>
        /// Make this pattern optional (quantifier 0..1).
        /// </summary>
        public Pattern Optional()
        {
            return new Pattern(new Quant(Node, 0, 1, true, false, false));
        }

        /// <summary>
        /// Wrap this pattern in a capturing group.
        /// </summary>
        public Pattern Capture()
        {
            return new Pattern(new Group(true, Node, null, false));
        }

        /// <summary>
        /// Concatenate this pattern with the provided one(s).
        /// </summary>
        public Pattern Then(params Pattern[] parts)
        {
            var list = new List<Node> { Node };
            foreach (var p in parts) list.Add(p.Node);
            return new Pattern(new Seq(list));
        }

        /// <summary>
        /// Expose the underlying Node for internal use only.
        /// This is intentionally not public to prevent leaking internal AST types in the public API.
        /// </summary>
        internal Node ToNode() => Node;

        /// <summary>
        /// Compile this Pattern to a PCRE2 regex string using the built-in emitter.
        /// </summary>
        public string Compile()
		{
			return CompileWithFlags(null);
		}

		internal string CompileWithFlags(Flags? flags = null)
		{
			var ir = Core.Compiler.Compile(Node);
			return Emit.Pcre2Emitter.Emit(ir, flags);
		}
    }
}
