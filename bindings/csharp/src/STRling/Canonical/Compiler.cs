using System.Text.Json;
using Strling.Native;

namespace Strling;

/// <summary>Canonical compile conveniences over a supplied native client.</summary>
public sealed class Compiler
{
    private readonly NativeClient client;

    public Compiler(NativeClient client) => this.client = client ?? throw new ArgumentNullException(nameof(client));

    public JsonElement Compile(JsonElement request, JsonElement? targetProfile = null) =>
        client.Compile(request, targetProfile);

    public JsonElement Check(JsonElement request, JsonElement? targetProfile = null) =>
        Compile(request, targetProfile);

    /// <summary>Compatibility name returning canonical compile data, never a local AST.</summary>
    public JsonElement Parse(string source, SourceCompileOptions? options = null)
    {
        var selected = options ?? new SourceCompileOptions();
        return Compile(SourceCompileRequest(source, selected, ["semantic"]), selected.TargetProfile);
    }

    /// <summary>Compatibility name requesting a canonical TargetArtifact.</summary>
    public JsonElement ParseToArtifact(string source, SourceCompileOptions options)
    {
        ArgumentNullException.ThrowIfNull(options);
        if (!options.TargetProfile.HasValue || !options.TargetProfileReference.HasValue)
            throw new ArgumentException("ParseToArtifact requires an exact target profile and reference", nameof(options));
        return Compile(
            SourceCompileRequest(source, options, ["semantic", "portability", "target_artifact"]),
            options.TargetProfile);
    }

    public JsonElement Describe() => client.Describe();
    public JsonElement InspectTargetProfile(JsonElement targetProfile) => client.InspectTargetProfile(targetProfile);

    public static JsonElement SourceCompileRequest(
        string source,
        SourceCompileOptions? options = null,
        IReadOnlyList<string>? fallbackOutputs = null)
    {
        ArgumentNullException.ThrowIfNull(source);
        var selected = options ?? new SourceCompileOptions();
        var mediaType = selected.MediaType;
        if (selected.FrontendId == "legacy_regex" && mediaType == "text/strling") mediaType = "text/x-regex";
        var request = new Dictionary<string, object?>
        {
            ["contract_version"] = "1.0.0",
            ["specification_version"] = selected.SpecificationVersion,
            ["input"] = new Dictionary<string, object?>
            {
                ["kind"] = "source",
                ["document"] = new Dictionary<string, object?>
                {
                    ["contract_version"] = "1.0.0",
                    ["source_id"] = selected.SourceId,
                    ["specification_version"] = selected.SpecificationVersion,
                    ["frontend"] = new Dictionary<string, object?>
                    {
                        ["id"] = selected.FrontendId,
                        ["dialect_version"] = selected.FrontendVersion,
                    },
                    ["content"] = new Dictionary<string, object?>
                    {
                        ["kind"] = "inline",
                        ["encoding"] = "utf-8",
                        ["media_type"] = mediaType,
                        ["text"] = source,
                    },
                    ["provenance"] = new Dictionary<string, object?> { ["kind"] = "authored" },
                },
            },
            ["requested_outputs"] = selected.RequestedOutputs ?? fallbackOutputs ?? ["semantic"],
            ["compiler_options"] = selected.CompilerOptions,
        };
        if (selected.TargetProfileReference.HasValue)
            request["target_profile"] = selected.TargetProfileReference.Value;
        return JsonSerializer.SerializeToElement(request);
    }
}
