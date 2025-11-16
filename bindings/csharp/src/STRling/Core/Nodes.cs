namespace Strling.Core;

/// <summary>
/// STRling AST Node Definitions
/// 
/// This module defines the complete set of Abstract Syntax Tree (AST) node classes
/// that represent the parsed structure of STRling patterns. The AST is the direct
/// output of the parser and represents the syntactic structure of the pattern before
/// optimization and lowering to IR.
/// 
/// AST nodes are designed to:
///   - Closely mirror the source pattern syntax
///   - Be easily serializable to the Base TargetArtifact schema
///   - Provide a clean separation between parsing and compilation
///   - Support multiple target regex flavors through the compilation pipeline
/// 
/// Each AST node type corresponds to a syntactic construct in the STRling DSL
/// (alternation, sequencing, character classes, anchors, etc.) and can be
/// serialized to a dictionary representation for debugging or storage.
/// </summary>

using System.Collections.Generic;

// ---- Flags container ----
/// <summary>
/// Container for regex flags/modifiers.
/// 
/// Flags control the behavior of pattern matching (case sensitivity, multiline
/// mode, etc.). This class encapsulates all standard regex flags.
/// </summary>
public record Flags
{
    public bool IgnoreCase { get; init; } = false;
    public bool Multiline { get; init; } = false;
    public bool DotAll { get; init; } = false;
    public bool Unicode { get; init; } = false;
    public bool Extended { get; init; } = false;

    /// <summary>
    /// Convert flags to a dictionary representation.
    /// </summary>
    public Dictionary<string, bool> ToDict()
    {
        return new Dictionary<string, bool>
        {
            ["ignoreCase"] = IgnoreCase,
            ["multiline"] = Multiline,
            ["dotAll"] = DotAll,
            ["unicode"] = Unicode,
            ["extended"] = Extended,
        };
    }

    /// <summary>
    /// Create Flags from a string of flag letters.
    /// </summary>
    /// <param name="letters">Flag letters (e.g., "im" for ignoreCase and multiline)</param>
    public static Flags FromLetters(string letters)
    {
        var flags = new Flags();
        var ignoreCase = false;
        var multiline = false;
        var dotAll = false;
        var unicode = false;
        var extended = false;

        foreach (var ch in letters.Replace(",", "").Replace(" ", ""))
        {
            switch (ch)
            {
                case 'i':
                    ignoreCase = true;
                    break;
                case 'm':
                    multiline = true;
                    break;
                case 's':
                    dotAll = true;
                    break;
                case 'u':
                    unicode = true;
                    break;
                case 'x':
                    extended = true;
                    break;
                default:
                    // Unknown flags are ignored at parser stage; may be warned later
                    break;
            }
        }

        return flags with 
        { 
            IgnoreCase = ignoreCase,
            Multiline = multiline,
            DotAll = dotAll,
            Unicode = unicode,
            Extended = extended
        };
    }
}

// ---- Base node ----
/// <summary>
/// Base class for all AST nodes.
/// </summary>
public abstract class Node
{
    /// <summary>
    /// Convert the node to a dictionary representation for serialization.
    /// </summary>
    public abstract Dictionary<string, object> ToDict();
}

// ---- Concrete nodes matching Base Schema ----

/// <summary>
/// Represents an alternation (OR) operation in the AST.
/// Matches any one of the provided branches.
/// </summary>
public class Alt : Node
{
    public required List<Node> Branches { get; init; }

    public override Dictionary<string, object> ToDict()
    {
        return new Dictionary<string, object>
        {
            ["kind"] = "Alt",
            ["branches"] = Branches.ConvertAll(b => b.ToDict())
        };
    }
}

/// <summary>
/// Represents a sequence of nodes to be matched in order.
/// </summary>
public class Seq : Node
{
    public required List<Node> Parts { get; init; }

    public override Dictionary<string, object> ToDict()
    {
        return new Dictionary<string, object>
        {
            ["kind"] = "Seq",
            ["parts"] = Parts.ConvertAll(p => p.ToDict())
        };
    }
}

/// <summary>
/// Represents a literal string to be matched.
/// </summary>
public class Lit : Node
{
    public required string Value { get; init; }

    public override Dictionary<string, object> ToDict()
    {
        return new Dictionary<string, object>
        {
            ["kind"] = "Lit",
            ["value"] = Value
        };
    }
}

/// <summary>
/// Represents the dot (.) metacharacter that matches any character.
/// </summary>
public class Dot : Node
{
    public override Dictionary<string, object> ToDict()
    {
        return new Dictionary<string, object>
        {
            ["kind"] = "Dot"
        };
    }
}

/// <summary>
/// Represents an anchor that matches a position in the input.
/// </summary>
public class Anchor : Node
{
    /// <summary>
    /// The anchor type: "Start"|"End"|"WordBoundary"|"NotWordBoundary"|Absolute* variants
    /// </summary>
    public required string At { get; init; }

    public override Dictionary<string, object> ToDict()
    {
        return new Dictionary<string, object>
        {
            ["kind"] = "Anchor",
            ["at"] = At
        };
    }
}

// --- CharClass --

/// <summary>
/// Base class for character class items.
/// </summary>
public abstract class ClassItem
{
    /// <summary>
    /// Convert the class item to a dictionary representation.
    /// </summary>
    public abstract Dictionary<string, object> ToDict();
}

/// <summary>
/// Represents a range of characters in a character class (e.g., a-z).
/// </summary>
public class ClassRange : ClassItem
{
    public required string FromCh { get; init; }
    public required string ToCh { get; init; }

    public override Dictionary<string, object> ToDict()
    {
        return new Dictionary<string, object>
        {
            ["kind"] = "Range",
            ["from"] = FromCh,
            ["to"] = ToCh
        };
    }
}

/// <summary>
/// Represents a single literal character in a character class.
/// </summary>
public class ClassLiteral : ClassItem
{
    public required string Ch { get; init; }

    public override Dictionary<string, object> ToDict()
    {
        return new Dictionary<string, object>
        {
            ["kind"] = "Char",
            ["char"] = Ch
        };
    }
}

/// <summary>
/// Represents an escape sequence in a character class (e.g., \d, \w, \s).
/// </summary>
public class ClassEscape : ClassItem
{
    /// <summary>
    /// The escape type: d, D, w, W, s, S, p, P
    /// </summary>
    public required string Type { get; init; }
    
    /// <summary>
    /// For \p and \P escapes, the Unicode property name.
    /// </summary>
    public string? Property { get; init; }

    public override Dictionary<string, object> ToDict()
    {
        var data = new Dictionary<string, object>
        {
            ["kind"] = "Esc",
            ["type"] = Type
        };
        
        if ((Type == "p" || Type == "P") && Property != null)
        {
            data["property"] = Property;
        }
        
        return data;
    }
}

/// <summary>
/// Represents a character class (e.g., [a-z], [^0-9]).
/// </summary>
public class CharClass : Node
{
    public required bool Negated { get; init; }
    public required List<ClassItem> Items { get; init; }

    public override Dictionary<string, object> ToDict()
    {
        return new Dictionary<string, object>
        {
            ["kind"] = "CharClass",
            ["negated"] = Negated,
            ["items"] = Items.ConvertAll(it => it.ToDict())
        };
    }
}

/// <summary>
/// Represents a quantifier (e.g., *, +, ?, {n,m}).
/// </summary>
public class Quant : Node
{
    public required Node Child { get; init; }
    public required int Min { get; init; }
    
    /// <summary>
    /// Maximum repetitions. Can be an integer or "Inf" for unbounded.
    /// </summary>
    public required object Max { get; init; }  // int or string "Inf"
    
    /// <summary>
    /// Quantifier mode: "Greedy" | "Lazy" | "Possessive"
    /// </summary>
    public required string Mode { get; init; }

    public override Dictionary<string, object> ToDict()
    {
        return new Dictionary<string, object>
        {
            ["kind"] = "Quant",
            ["child"] = Child.ToDict(),
            ["min"] = Min,
            ["max"] = Max,
            ["mode"] = Mode
        };
    }
}

/// <summary>
/// Represents a group (capturing or non-capturing).
/// </summary>
public class Group : Node
{
    public required bool Capturing { get; init; }
    public required Node Body { get; init; }
    
    /// <summary>
    /// For named capturing groups, the group name.
    /// </summary>
    public string? Name { get; init; }
    
    /// <summary>
    /// Extension: whether this is an atomic group.
    /// </summary>
    public bool? Atomic { get; init; }

    public override Dictionary<string, object> ToDict()
    {
        var data = new Dictionary<string, object>
        {
            ["kind"] = "Group",
            ["capturing"] = Capturing,
            ["body"] = Body.ToDict()
        };
        
        if (Name != null)
        {
            data["name"] = Name;
        }
        
        if (Atomic != null)
        {
            data["atomic"] = Atomic;
        }
        
        return data;
    }
}

/// <summary>
/// Represents a backreference to a capturing group.
/// </summary>
public class Backref : Node
{
    /// <summary>
    /// Reference by numeric index (1-based).
    /// </summary>
    public int? ByIndex { get; init; }
    
    /// <summary>
    /// Reference by group name.
    /// </summary>
    public string? ByName { get; init; }

    public override Dictionary<string, object> ToDict()
    {
        var data = new Dictionary<string, object>
        {
            ["kind"] = "Backref"
        };
        
        if (ByIndex != null)
        {
            data["byIndex"] = ByIndex;
        }
        
        if (ByName != null)
        {
            data["byName"] = ByName;
        }
        
        return data;
    }
}

/// <summary>
/// Represents a lookahead or lookbehind assertion.
/// </summary>
public class Look : Node
{
    /// <summary>
    /// Direction: "Ahead" | "Behind"
    /// </summary>
    public required string Dir { get; init; }
    
    /// <summary>
    /// Whether this is a negative lookaround.
    /// </summary>
    public required bool Neg { get; init; }
    
    public required Node Body { get; init; }

    public override Dictionary<string, object> ToDict()
    {
        return new Dictionary<string, object>
        {
            ["kind"] = "Look",
            ["dir"] = Dir,
            ["neg"] = Neg,
            ["body"] = Body.ToDict()
        };
    }
}
