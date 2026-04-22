namespace Strling.Core
{
    /// <summary>
    /// Non-fatal diagnostic emitted alongside a compiled pattern.
    ///
    /// Currently used for <c>REDOS_RISK</c> (nested unbounded quantifiers).
    /// Plain value object — not an exception — so it can be collected and
    /// surfaced to the caller without aborting compilation.
    ///
    /// <see cref="ToString"/> matches the TypeScript SSOT's
    /// <c>STRlingWarning [CODE]: message</c> format so the global
    /// pathological fixture's <c>expected_warning</c> substring compares
    /// 1:1 across bindings.
    /// </summary>
    public sealed class STRlingWarning
    {
        public string Code { get; }
        public string Message { get; }

        public STRlingWarning(string code, string message)
        {
            Code = code;
            Message = message;
        }

        public override string ToString() => $"STRlingWarning [{Code}]: {Message}";
    }
}
