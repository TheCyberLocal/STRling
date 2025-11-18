namespace Strling;

using Strling.Core;

/// <summary>
/// The main entry point for parsing STRling patterns and compiling them to target regex flavors.
/// </summary>
public static class Parser
{
    /// <summary>
    /// Parse a STRling pattern into an AST.
    /// </summary>
    /// <param name="src">The STRling pattern text to parse</param>
    /// <returns>A tuple of (Flags, AST root node)</returns>
    public static (Flags, Node) Parse(string src)
    {
        return Core.Parser.Parse(src);
    }
}

/// <summary>
/// Compiles STRling AST nodes to IR (Intermediate Representation).
/// </summary>
public class Compiler
{
    // Compiler implementation will be added in Task 2
}
