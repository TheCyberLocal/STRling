using System.Text.Json.Serialization;
using System.Collections.Generic;

namespace Strling.Core;

public record Flags
{
    public bool IgnoreCase { get; init; } = false;
    public bool Multiline { get; init; } = false;
    public bool DotAll { get; init; } = false;
    public bool Unicode { get; init; } = false;
    public bool Extended { get; init; } = false;

    public static Flags FromLetters(string letters)
    {
        var f = new Flags();
        foreach (var c in letters)
        {
            if (c == 'i') f = f with { IgnoreCase = true };
            else if (c == 'm') f = f with { Multiline = true };
            else if (c == 's') f = f with { DotAll = true };
            else if (c == 'u') f = f with { Unicode = true };
            else if (c == 'x') f = f with { Extended = true };
        }
        return f;
    }
}

[JsonPolymorphic(TypeDiscriminatorPropertyName = "type")]
[JsonDerivedType(typeof(Alt), typeDiscriminator: "Alternation")]
[JsonDerivedType(typeof(Seq), typeDiscriminator: "Sequence")]
[JsonDerivedType(typeof(Lit), typeDiscriminator: "Literal")]
[JsonDerivedType(typeof(Dot), typeDiscriminator: "Dot")]
[JsonDerivedType(typeof(Anchor), typeDiscriminator: "Anchor")]
[JsonDerivedType(typeof(CharClass), typeDiscriminator: "CharacterClass")]
[JsonDerivedType(typeof(Quant), typeDiscriminator: "Quantifier")]
[JsonDerivedType(typeof(Group), typeDiscriminator: "Group")]
[JsonDerivedType(typeof(Backref), typeDiscriminator: "Backreference")]
[JsonDerivedType(typeof(Lookahead), typeDiscriminator: "Lookahead")]
[JsonDerivedType(typeof(NegativeLookahead), typeDiscriminator: "NegativeLookahead")]
[JsonDerivedType(typeof(Lookbehind), typeDiscriminator: "Lookbehind")]
[JsonDerivedType(typeof(NegativeLookbehind), typeDiscriminator: "NegativeLookbehind")]
public abstract record Node;

public record Alt([property: JsonPropertyName("alternatives")] List<Node> Alternatives) : Node;

public record Seq([property: JsonPropertyName("parts")] List<Node> Parts) : Node;

public record Lit([property: JsonPropertyName("value")] string Value) : Node;

public record Dot : Node;

public record Anchor([property: JsonPropertyName("at")] string At) : Node;

public record CharClass(
    [property: JsonPropertyName("negated")] bool Negated,
    [property: JsonPropertyName("members")] List<ClassItem> Members
) : Node;

[JsonPolymorphic(TypeDiscriminatorPropertyName = "type")]
[JsonDerivedType(typeof(ClassRange), typeDiscriminator: "Range")]
[JsonDerivedType(typeof(ClassLiteral), typeDiscriminator: "Literal")]
[JsonDerivedType(typeof(ClassEscape), typeDiscriminator: "Escape")]
[JsonDerivedType(typeof(ClassUnicodeProperty), typeDiscriminator: "UnicodeProperty")]
public abstract record ClassItem;

public record ClassRange(
    [property: JsonPropertyName("from")] string From,
    [property: JsonPropertyName("to")] string To
) : ClassItem;

public record ClassLiteral(
    [property: JsonPropertyName("value")] string Value
) : ClassItem;

public record ClassEscape(
    [property: JsonPropertyName("kind")] string Kind
) : ClassItem;

public record ClassUnicodeProperty(
    [property: JsonPropertyName("name")] string? Name,
    [property: JsonPropertyName("value")] string Value,
    [property: JsonPropertyName("negated")] bool Negated
) : ClassItem;

public record Quant(
    [property: JsonPropertyName("target")] Node Target,
    [property: JsonPropertyName("min")] int Min,
    [property: JsonPropertyName("max")] int? Max,
    [property: JsonPropertyName("greedy")] bool Greedy,
    [property: JsonPropertyName("lazy")] bool Lazy,
    [property: JsonPropertyName("possessive")] bool Possessive
) : Node;

public record Group(
    [property: JsonPropertyName("capturing")] bool Capturing,
    [property: JsonPropertyName("body")] Node Body,
    [property: JsonPropertyName("name")] string? Name,
    [property: JsonPropertyName("atomic")] bool Atomic
) : Node;

public record Backref(
    [property: JsonPropertyName("index")] int? Index,
    [property: JsonPropertyName("name")] string? Name
) : Node;

public record Lookahead([property: JsonPropertyName("body")] Node Body) : Node;
public record NegativeLookahead([property: JsonPropertyName("body")] Node Body) : Node;
public record Lookbehind([property: JsonPropertyName("body")] Node Body) : Node;
public record NegativeLookbehind([property: JsonPropertyName("body")] Node Body) : Node;



