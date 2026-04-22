using System.Collections.Generic;

namespace Strling.Core
{
    /// <summary>
    /// Result of an emit pass: the produced PCRE2 pattern plus any
    /// non-fatal diagnostics collected during emission.
    ///
    /// Returned by <c>Pcre2Emitter.EmitWithDiagnostics(...)</c>. The
    /// companion back-compat entry point <c>Pcre2Emitter.Emit(...)</c>
    /// discards warnings for callers that only care about the pattern.
    /// </summary>
    public sealed class CompileResult
    {
        public string Pattern { get; }
        public IReadOnlyList<STRlingWarning> Warnings { get; }

        public CompileResult(string pattern, IReadOnlyList<STRlingWarning> warnings)
        {
            Pattern = pattern;
            Warnings = warnings ?? new List<STRlingWarning>();
        }
    }
}
