namespace Strling.Core;

/// <summary>
/// STRling Intermediate Representation (IR) Node Definitions
/// 
/// This module defines the complete set of IR node classes that represent
/// language-agnostic regex constructs. The IR serves as an intermediate layer
/// between the parsed AST and the target-specific emitters (e.g., PCRE2).
/// 
/// IR nodes are designed to be:
///   - Simple and composable
///   - Easy to serialize (via ToDict methods)
///   - Independent of any specific regex flavor
///   - Optimized for transformation and analysis
/// 
/// Each IR node corresponds to a fundamental regex operation (alternation,
/// sequencing, character classes, quantification, etc.) and can be serialized
/// to a dictionary representation for further processing or debugging.
/// </summary>

using System.Collections.Generic;

/// <summary>
/// Base class for all IR operations.
/// 
/// All IR nodes extend this base class and must implement the ToDict() method
/// for serialization to a dictionary representation.
/// </summary>
public abstract class IROp
{
    /// <summary>
    /// Serialize the IR node to a dictionary representation.
    /// </summary>
    /// <returns>The dictionary representation of this IR node.</returns>
    public abstract Dictionary<string, object> ToDict();
}

/// <summary>
/// Represents an alternation (OR) operation in the IR.
/// 
/// Matches any one of the provided branches. Equivalent to the | operator
/// in traditional regex syntax.
/// </summary>
public class IRAlt : IROp
{
    public required List<IROp> Branches { get; init; }

    public override Dictionary<string, object> ToDict()
    {
        return new Dictionary<string, object>
        {
            ["ir"] = "Alt",
            ["branches"] = Branches.ConvertAll(b => b.ToDict())
        };
    }
}

/// <summary>
/// Represents a sequence of IR operations to be matched in order.
/// </summary>
public class IRSeq : IROp
{
    public required List<IROp> Parts { get; init; }

    public override Dictionary<string, object> ToDict()
    {
        return new Dictionary<string, object>
        {
            ["ir"] = "Seq",
            ["parts"] = Parts.ConvertAll(p => p.ToDict())
        };
    }
}

/// <summary>
/// Represents a literal string in the IR.
/// </summary>
public class IRLit : IROp
{
    public required string Value { get; init; }

    public override Dictionary<string, object> ToDict()
    {
        return new Dictionary<string, object>
        {
            ["ir"] = "Lit",
            ["value"] = Value
        };
    }
}

/// <summary>
/// Represents the dot (.) metacharacter in the IR.
/// </summary>
public class IRDot : IROp
{
    public override Dictionary<string, object> ToDict()
    {
        return new Dictionary<string, object>
        {
            ["ir"] = "Dot"
        };
    }
}

/// <summary>
/// Represents an anchor position in the IR.
/// </summary>
public class IRAnchor : IROp
{
    public required string At { get; init; }

    public override Dictionary<string, object> ToDict()
    {
        return new Dictionary<string, object>
        {
            ["ir"] = "Anchor",
            ["at"] = At
        };
    }
}

/// <summary>
/// Base class for character class items in the IR.
/// </summary>
public abstract class IRClassItem
{
    /// <summary>
    /// Convert the class item to a dictionary representation.
    /// </summary>
    public abstract Dictionary<string, object> ToDict();
}

/// <summary>
/// Represents a character range in a character class.
/// </summary>
public class IRClassRange : IRClassItem
{
    public required string FromCh { get; init; }
    public required string ToCh { get; init; }

    public override Dictionary<string, object> ToDict()
    {
        return new Dictionary<string, object>
        {
            ["ir"] = "Range",
            ["from"] = FromCh,
            ["to"] = ToCh
        };
    }
}

/// <summary>
/// Represents a single literal character in a character class.
/// </summary>
public class IRClassLiteral : IRClassItem
{
    public required string Ch { get; init; }

    public override Dictionary<string, object> ToDict()
    {
        return new Dictionary<string, object>
        {
            ["ir"] = "Char",
            ["char"] = Ch
        };
    }
}

/// <summary>
/// Represents an escape sequence in a character class.
/// </summary>
public class IRClassEscape : IRClassItem
{
    public required string Type { get; init; }
    public string? Property { get; init; }

    public override Dictionary<string, object> ToDict()
    {
        var d = new Dictionary<string, object>
        {
            ["ir"] = "Esc",
            ["type"] = Type
        };
        
        if (Property != null)
        {
            d["property"] = Property;
        }
        
        return d;
    }
}

/// <summary>
/// Represents a character class in the IR.
/// </summary>
public class IRCharClass : IROp
{
    public required bool Negated { get; init; }
    public required List<IRClassItem> Items { get; init; }

    public override Dictionary<string, object> ToDict()
    {
        return new Dictionary<string, object>
        {
            ["ir"] = "CharClass",
            ["negated"] = Negated,
            ["items"] = Items.ConvertAll(i => i.ToDict())
        };
    }
}

/// <summary>
/// Represents a quantifier in the IR.
/// </summary>
public class IRQuant : IROp
{
    public required IROp Child { get; init; }
    public required int Min { get; init; }
    
    /// <summary>
    /// Maximum repetitions. Can be an integer or "Inf" for unbounded.
    /// </summary>
    public required object Max { get; init; }  // int or string "Inf"
    
    /// <summary>
    /// Quantifier mode: "Greedy"|"Lazy"|"Possessive"
    /// </summary>
    public required string Mode { get; init; }

    public override Dictionary<string, object> ToDict()
    {
        return new Dictionary<string, object>
        {
            ["ir"] = "Quant",
            ["child"] = Child.ToDict(),
            ["min"] = Min,
            ["max"] = Max,
            ["mode"] = Mode
        };
    }
}

/// <summary>
/// Represents a group in the IR.
/// </summary>
public class IRGroup : IROp
{
    public required bool Capturing { get; init; }
    public required IROp Body { get; init; }
    public string? Name { get; init; }
    public bool? Atomic { get; init; }

    public override Dictionary<string, object> ToDict()
    {
        var d = new Dictionary<string, object>
        {
            ["ir"] = "Group",
            ["capturing"] = Capturing,
            ["body"] = Body.ToDict()
        };
        
        if (Name != null)
        {
            d["name"] = Name;
        }
        
        if (Atomic != null)
        {
            d["atomic"] = Atomic;
        }
        
        return d;
    }
}

/// <summary>
/// Represents a backreference in the IR.
/// </summary>
public class IRBackref : IROp
{
    public int? ByIndex { get; init; }
    public string? ByName { get; init; }

    public override Dictionary<string, object> ToDict()
    {
        var d = new Dictionary<string, object>
        {
            ["ir"] = "Backref"
        };
        
        if (ByIndex != null)
        {
            d["byIndex"] = ByIndex;
        }
        
        if (ByName != null)
        {
            d["byName"] = ByName;
        }
        
        return d;
    }
}

/// <summary>
/// Represents a lookaround assertion in the IR.
/// </summary>
public class IRLook : IROp
{
    public required string Dir { get; init; }
    public required bool Neg { get; init; }
    public required IROp Body { get; init; }

    public override Dictionary<string, object> ToDict()
    {
        return new Dictionary<string, object>
        {
            ["ir"] = "Look",
            ["dir"] = Dir,
            ["neg"] = Neg,
            ["body"] = Body.ToDict()
        };
    }
}
