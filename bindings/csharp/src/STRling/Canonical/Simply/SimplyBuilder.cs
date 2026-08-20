using System.Text.Json;

namespace Strling.Simply;

/// <summary>Records host-neutral Simply 1.1 operations without evaluating semantics.</summary>
public sealed class SimplyBuilder
{
    private readonly object owner = new();
    private readonly List<Dictionary<string, object?>> steps = [];

    public SimplyBuilder(
        string identityNamespace,
        string specificationVersion = "1.0-draft.1",
        IReadOnlyDictionary<string, object?>? semanticOptions = null)
    {
        IdentityNamespace = identityNamespace ?? throw new ArgumentNullException(nameof(identityNamespace));
        SpecificationVersion = specificationVersion ?? throw new ArgumentNullException(nameof(specificationVersion));
        SemanticOptions = semanticOptions is null
            ? DefaultSemanticOptions()
            : new Dictionary<string, object?>(semanticOptions);
    }

    public string IdentityNamespace { get; }
    public string SpecificationVersion { get; }
    public IReadOnlyDictionary<string, object?> SemanticOptions { get; }

    public Value Empty(string stepId) => Append(stepId, "empty", []);
    public Value Literal(string stepId, string text) => Append(stepId, "literal", new() { ["text"] = text });
    public Value Wildcard(string stepId) => Append(stepId, "wildcard", []);
    public Value CharacterSet(string stepId, IReadOnlyList<IReadOnlyDictionary<string, object?>> members, bool negated) =>
        Append(stepId, "character_set", new() { ["negated"] = negated, ["members"] = members });
    public Value Sequence(string stepId, IReadOnlyList<Value> values) =>
        Append(stepId, "sequence", new() { ["values"] = StepIds(values) });
    public Value Alternation(string stepId, IReadOnlyList<Value> values) =>
        Append(stepId, "alternation", new() { ["values"] = StepIds(values) });
    public Value Group(string stepId, Value value) => Append(stepId, "group", new() { ["value"] = StepId(value) });
    public Value Capture(string stepId, string captureKey, Value value, string? name = null)
    {
        var arguments = new Dictionary<string, object?> { ["value"] = StepId(value), ["capture_key"] = captureKey };
        if (name is not null) arguments["name"] = name;
        return Append(stepId, "capture", arguments);
    }
    public Value Backreference(string stepId, string captureKey) =>
        Append(stepId, "backreference", new() { ["capture_key"] = captureKey });
    public Value Position(string stepId, string position) => Append(stepId, "position", new() { ["position"] = position });
    public Value Lookaround(string stepId, string direction, string polarity, Value value) =>
        Append(stepId, "lookaround", new() { ["value"] = StepId(value), ["direction"] = direction, ["polarity"] = polarity });
    public Value Atomic(string stepId, Value value) => Append(stepId, "atomic", new() { ["value"] = StepId(value) });
    public Value Repeat(string stepId, Value value, int minimum, int? maximum, string mode = "greedy") =>
        Append(stepId, "repeat", new() { ["value"] = StepId(value), ["min"] = minimum, ["max"] = maximum, ["mode"] = mode });
    public Value StdlibHelper(string stepId, string helperId, IReadOnlyDictionary<string, object?> parameters) =>
        Append(stepId, "stdlib_helper", new() { ["helper_id"] = helperId, ["parameters"] = parameters });

    public JsonElement BuildRequest(Value root, JsonElement compileProjection) => JsonSerializer.SerializeToElement(
        new Dictionary<string, object?>
        {
            ["protocol_version"] = "1.1.0",
            ["contract_version"] = "1.0.0",
            ["specification_version"] = SpecificationVersion,
            ["identity_namespace"] = IdentityNamespace,
            ["semantic_options"] = SemanticOptions,
            ["steps"] = steps,
            ["root_step_id"] = StepId(root),
            ["compile"] = compileProjection,
        });

    public static IReadOnlyDictionary<string, object?> DefaultSemanticOptions() => new Dictionary<string, object?>
    {
        ["case_matching"] = "sensitive",
        ["text_model"] = "unicode_scalar_values",
        ["builtin_character_domain"] = "unicode",
        ["wildcard_line_terminators"] = "exclude",
    };

    private Value Append(string stepId, string operation, Dictionary<string, object?> arguments)
    {
        if (string.IsNullOrWhiteSpace(stepId)) throw new STRlingError("step id cannot be empty");
        steps.Add(new() { ["step_id"] = stepId, ["operation"] = operation, ["arguments"] = arguments });
        return new Value(stepId, owner);
    }

    private string StepId(Value value)
    {
        if (value is null || !ReferenceEquals(value.Owner, owner))
            throw new STRlingError("Simply values belong to exactly one builder");
        return value.StepId;
    }

    private IReadOnlyList<string> StepIds(IReadOnlyList<Value> values) => values.Select(StepId).ToArray();

    public sealed class Value
    {
        internal Value(string stepId, object owner) { StepId = stepId; Owner = owner; }
        public string StepId { get; }
        internal object Owner { get; }
    }
}
