using System;

namespace Strling.Core
{
    /// <summary>
    /// Fatal emitter-stage failure raised by an IR safety guard.
    ///
    /// Carries a stable <c>Code</c> (e.g. <c>"VLB_NOT_SUPPORTED"</c>,
    /// <c>"MAX_DEPTH"</c>) and the offending <c>Engine</c> so cross-binding
    /// parity tests can match on shared substrings without coupling to a
    /// specific message wording.
    ///
    /// Mirrors <c>STRlingCompilationError</c> in the TypeScript reference
    /// and the matching Python / Java / Rust / C / C++ types.
    /// </summary>
    public class STRlingCompilationError : Exception
    {
        public string Code { get; }
        public string Engine { get; }

        public STRlingCompilationError(string message, string code, string engine = "pcre2")
            : base(message)
        {
            Code = code;
            Engine = engine;
        }
    }
}
