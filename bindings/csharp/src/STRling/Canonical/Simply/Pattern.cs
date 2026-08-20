using System.Text.Json;
using Strling.Native;

namespace Strling.Simply;

/// <summary>Immutable recipe that records canonical Simply operations on demand.</summary>
public sealed class Pattern
{
    internal delegate SimplyBuilder.Value Recipe(Context context);
    internal sealed class Context(SimplyBuilder builder)
    {
        private int sequence;
        internal SimplyBuilder Builder { get; } = builder;
        internal string Next(string prefix) => $"{prefix}-{++sequence}";
    }

    private readonly Recipe recipe;
    private readonly Pattern? repeatedValue;
    private readonly int? repeatedMinimum;
    private readonly int? repeatedMaximum;

    internal Pattern(Recipe recipe, Pattern? repeatedValue = null, int? repeatedMinimum = null, int? repeatedMaximum = null)
    {
        this.recipe = recipe ?? throw new ArgumentNullException(nameof(recipe));
        this.repeatedValue = repeatedValue;
        this.repeatedMinimum = repeatedMinimum;
        this.repeatedMaximum = repeatedMaximum;
    }

    internal SimplyBuilder.Value Record(Context context) => recipe(context);

    public Pattern Repeat(int minimum, int? maximum = null)
    {
        if (minimum < 0 || (maximum.HasValue && maximum.Value < minimum))
            throw new STRlingError("repetition bounds must be non-negative and ordered");
        var source = this;
        return new Pattern(
            context => context.Builder.Repeat(context.Next("repeat"), source.Record(context), minimum, maximum, "greedy"),
            source,
            minimum,
            maximum);
    }

    public Pattern Repeat(int count) => Repeat(count, count);
    public Pattern May() => Repeat(0, 1);
    public Pattern Lazy()
    {
        if (repeatedValue is null || !repeatedMinimum.HasValue) throw new STRlingError("Lazy requires a repeated pattern");
        return new Pattern(context => context.Builder.Repeat(
            context.Next("repeat"), repeatedValue.Record(context), repeatedMinimum.Value, repeatedMaximum, "lazy"));
    }

    public Pattern Capture()
    {
        var source = this;
        return new Pattern(context => context.Builder.Capture(
            context.Next("capture"), context.Next("capture-key"), source.Record(context)));
    }

    public Pattern AsGroup(string name)
    {
        if (string.IsNullOrEmpty(name)) throw new STRlingError("capture group name cannot be empty");
        var source = this;
        return new Pattern(context => context.Builder.Capture(context.Next("capture"), name, source.Record(context), name));
    }

    public Pattern Then(params Pattern[] parts) => S.Merge([this, .. parts]);

    public JsonElement BuildRequest(
        JsonElement compileProjection,
        string identityNamespace = "csharp-simply",
        IReadOnlyDictionary<string, object?>? semanticOptions = null)
    {
        var builder = new SimplyBuilder(identityNamespace, "1.0-draft.1", semanticOptions);
        var context = new Context(builder);
        return builder.BuildRequest(Record(context), compileProjection);
    }

    public JsonElement Compile(NativeClient client, JsonElement compileProjection, JsonElement? targetProfile = null) =>
        client.SimplyCompile(BuildRequest(compileProjection), targetProfile);

    public object Exec(string ignoredText) => throw new STRlingError(
        "Pattern.Exec was retired: canonical adapters do not simulate runtime regex execution");

    public override string ToString() => throw new STRlingError(
        "implicit regex rendering was retired: compile through the canonical adapter");

    internal static Pattern StdlibHelper(string helperId, IReadOnlyDictionary<string, object?> parameters) =>
        new(context => context.Builder.StdlibHelper(context.Next("stdlib"), helperId, parameters));
}
