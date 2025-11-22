using System.Text.Json.Serialization;
using System.Collections.Generic;

namespace Strling.Core;

[JsonPolymorphic(TypeDiscriminatorPropertyName = "ir")]
[JsonDerivedType(typeof(IRAlt), typeDiscriminator: "Alt")]
[JsonDerivedType(typeof(IRSeq), typeDiscriminator: "Seq")]
[JsonDerivedType(typeof(IRLit), typeDiscriminator: "Lit")]
[JsonDerivedType(typeof(IRDot), typeDiscriminator: "Dot")]
[JsonDerivedType(typeof(IRAnchor), typeDiscriminator: "Anchor")]
[JsonDerivedType(typeof(IRCharClass), typeDiscriminator: "CharClass")]
[JsonDerivedType(typeof(IRQuant), typeDiscriminator: "Quant")]
[JsonDerivedType(typeof(IRGroup), typeDiscriminator: "Group")]
[JsonDerivedType(typeof(IRBackref), typeDiscriminator: "Backref")]
[JsonDerivedType(typeof(IRLook), typeDiscriminator: "Look")]
public abstract record IROp;

public record IRAlt([property: JsonPropertyName("branches")] List<IROp> Branches) : IROp;

public record IRSeq([property: JsonPropertyName("parts")] List<IROp> Parts) : IROp;

public record IRLit([property: JsonPropertyName("value")] string Value) : IROp;

public record IRDot : IROp;

public record IRAnchor([property: JsonPropertyName("at")] string At) : IROp;

public record IRCharClass(
    [property: JsonPropertyName("negated")] bool Negated,
    [property: JsonPropertyName("items")] List<IRClassItem> Items
) : IROp;

[JsonPolymorphic(TypeDiscriminatorPropertyName = "ir")]
[JsonDerivedType(typeof(IRClassRange), typeDiscriminator: "Range")]
[JsonDerivedType(typeof(IRClassLiteral), typeDiscriminator: "Char")]
[JsonDerivedType(typeof(IRClassEscape), typeDiscriminator: "Esc")]
public abstract record IRClassItem;

public record IRClassRange(
    [property: JsonPropertyName("from")] string FromCh,
    [property: JsonPropertyName("to")] string ToCh
) : IRClassItem;

public record IRClassLiteral(
    [property: JsonPropertyName("char")] string Ch
) : IRClassItem;

public record IRClassEscape(
    [property: JsonPropertyName("type")] string Type,
    [property: JsonPropertyName("property")][property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? Property
) : IRClassItem;

public record IRQuant(
    [property: JsonPropertyName("child")] IROp Child,
    [property: JsonPropertyName("min")] int Min,
    [property: JsonPropertyName("max")] object Max,
    [property: JsonPropertyName("mode")] string Mode
) : IROp;

public record IRGroup(
    [property: JsonPropertyName("capturing")] bool Capturing,
    [property: JsonPropertyName("body")] IROp Body,
    [property: JsonPropertyName("name")][property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? Name,
    [property: JsonPropertyName("atomic")][property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingDefault)] bool Atomic
) : IROp;

public record IRBackref(
    [property: JsonPropertyName("byIndex")][property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] int? ByIndex,
    [property: JsonPropertyName("byName")][property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? ByName
) : IROp;

public record IRLook(
    [property: JsonPropertyName("dir")] string Dir,
    [property: JsonPropertyName("neg")] bool Neg,
    [property: JsonPropertyName("body")] IROp Body
) : IROp;
