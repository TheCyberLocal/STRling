using System.Text.Json;

namespace Strling;

/// <summary>Immutable host projection for canonical source CompileRequests.</summary>
public sealed record SourceCompileOptions
{
    public string SourceId { get; init; } = "src:csharp.adapter";
    public string FrontendId { get; init; } = "semantic_strling";
    public string FrontendVersion { get; init; } = "1.0-draft.1";
    public string MediaType { get; init; } = "text/strling";
    public string SpecificationVersion { get; init; } = "1.0-draft.1";
    public IReadOnlyList<string>? RequestedOutputs { get; init; }
    public JsonElement CompilerOptions { get; init; } = Defaults.CompilerOptions();
    public JsonElement? TargetProfileReference { get; init; }
    public JsonElement? TargetProfile { get; init; }

    private static class Defaults
    {
        internal static JsonElement CompilerOptions() => JsonSerializer.SerializeToElement(
            new Dictionary<string, object?>
            {
                ["partial_semantics"] = "forbid",
                ["diagnostic_policy"] = new Dictionary<string, object?> { ["minimum_severity"] = "hint" },
            });
    }
}
