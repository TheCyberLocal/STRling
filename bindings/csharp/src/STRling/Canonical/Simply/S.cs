using System.Text;

namespace Strling.Simply;

/// <summary>Idiomatic C# constructors for canonical Simply recipes.</summary>
public static class S
{
    public static Pattern Empty() => new(context => context.Builder.Empty(context.Next("empty")));

    public static Pattern Literal(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        return text.Length == 0 ? Empty() : new(context => context.Builder.Literal(context.Next("literal"), text));
    }

    public static Pattern Dot() => new(context => context.Builder.Wildcard(context.Next("wildcard")));
    public static Pattern Anything() => Dot();
    public static Pattern Digit() => Builtin("digit");
    public static Pattern Digit(int count) => Digit().Repeat(count);
    public static Pattern Word() => Builtin("word");
    public static Pattern Whitespace() => Builtin("whitespace");

    public static Pattern AnyOf(string characters)
    {
        ArgumentException.ThrowIfNullOrEmpty(characters);
        var members = characters.EnumerateRunes()
            .Select(rune => (IReadOnlyDictionary<string, object?>)new Dictionary<string, object?>
            {
                ["kind"] = "literal",
                ["value"] = rune.ToString(),
            }).ToArray();
        return CharacterSet(members, false);
    }

    public static Pattern Between(Rune start, Rune end)
    {
        if (start.Value > end.Value) throw new STRlingError("character range must be ordered Unicode scalars");
        IReadOnlyDictionary<string, object?> member = new Dictionary<string, object?>
        {
            ["kind"] = "range",
            ["start"] = start.ToString(),
            ["end"] = end.ToString(),
        };
        return CharacterSet([member], false);
    }

    public static Pattern Merge(params Pattern[] patterns)
    {
        if (patterns is null || patterns.Length == 0) throw new STRlingError("at least one Pattern is required");
        if (patterns.Length == 1) return patterns[0];
        return new(context => context.Builder.Sequence(
            context.Next("sequence"), patterns.Select(pattern => pattern.Record(context)).ToArray()));
    }

    public static Pattern AnyOf(params Pattern[] patterns)
    {
        if (patterns is null || patterns.Length == 0) throw new STRlingError("at least one Pattern is required");
        return new(context => context.Builder.Alternation(
            context.Next("alternation"), patterns.Select(pattern => pattern.Record(context)).ToArray()));
    }

    public static Pattern Start() => Position("start_of_text");
    public static Pattern End() => Position("end_of_text");
    public static Pattern StartsWith(params Pattern[] values) => Merge(Start(), Merge(values));
    public static Pattern EndsWith(params Pattern[] values) => Merge(Merge(values), End());
    public static Pattern FollowedBy(params Pattern[] values) => Lookaround("ahead", "positive", Merge(values));
    public static Pattern NotFollowedBy(params Pattern[] values) => Lookaround("ahead", "negative", Merge(values));
    public static Pattern PrecededBy(params Pattern[] values) => Lookaround("behind", "positive", Merge(values));
    public static Pattern NotPrecededBy(params Pattern[] values) => Lookaround("behind", "negative", Merge(values));
    public static Pattern Ref(string captureKey) => new(context => context.Builder.Backreference(context.Next("backreference"), captureKey));
    public static Pattern Atomic(params Pattern[] values)
    {
        var pattern = Merge(values);
        return new(context => context.Builder.Atomic(context.Next("atomic"), pattern.Record(context)));
    }

    private static Pattern Builtin(string name)
    {
        IReadOnlyDictionary<string, object?> member = new Dictionary<string, object?>
        {
            ["kind"] = "builtin",
            ["name"] = name,
            ["domain"] = "target_native",
            ["negated"] = false,
        };
        return CharacterSet([member], false);
    }

    private static Pattern CharacterSet(IReadOnlyList<IReadOnlyDictionary<string, object?>> members, bool negated) =>
        new(context => context.Builder.CharacterSet(context.Next("character-set"), members, negated));
    private static Pattern Position(string position) => new(context => context.Builder.Position(context.Next("position"), position));
    private static Pattern Lookaround(string direction, string polarity, Pattern value) =>
        new(context => context.Builder.Lookaround(context.Next("lookaround"), direction, polarity, value.Record(context)));
}
