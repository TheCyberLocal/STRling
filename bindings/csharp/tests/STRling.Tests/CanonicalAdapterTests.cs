using System.Text.Json;
using Strling;
using Strling.Native;
using Strling.Simply;

namespace STRling.Tests;

public sealed class CanonicalAdapterTests
{
    private static JsonElement CompatibilityProjection()
    {
        for (var current = new DirectoryInfo(AppContext.BaseDirectory); current is not null; current = current.Parent)
        {
            var candidate = Path.Combine(current.FullName, "spec", "stdlib", "essential_5.json");
            if (File.Exists(candidate))
            {
                using var document = JsonDocument.Parse(File.ReadAllText(candidate));
                return document.RootElement.Clone();
            }
        }

        throw new FileNotFoundException("spec/stdlib/essential_5.json was not found from the test output path");
    }

    private static JsonElement Projection() => JsonSerializer.SerializeToElement(new
    {
        requested_outputs = new[] { "semantic" },
        compiler_options = new
        {
            partial_semantics = "forbid",
            diagnostic_policy = new { minimum_severity = "hint" },
        },
    });

    [Fact]
    public void SourceRequestUsesCanonicalContractsAndNoAmbientTarget()
    {
        var request = Compiler.SourceCompileRequest("literal \"hello\"", fallbackOutputs: ["semantic", "analysis"]);
        Assert.Equal("1.0.0", request.GetProperty("contract_version").GetString());
        Assert.Equal(2, request.GetProperty("requested_outputs").GetArrayLength());
        Assert.False(request.TryGetProperty("target_profile", out _));
    }

    [Fact]
    public void ExactTargetReferenceIsProjectedWithoutSelectingIt()
    {
        var reference = JsonSerializer.SerializeToElement(new { profile_id = "pcre2-10.43", profile_version = "1.0.0" });
        var options = new SourceCompileOptions { TargetProfileReference = reference };
        var request = Compiler.SourceCompileRequest("literal \"x\"", options);
        Assert.Equal(reference.GetRawText(), request.GetProperty("target_profile").GetRawText());
    }

    [Fact]
    public void ArtifactCompatibilityRequiresExactProfileAndReference()
    {
        var constructor = typeof(Compiler).GetConstructors().Single();
        Assert.Single(constructor.GetParameters());
        Assert.Equal(typeof(NativeClient), constructor.GetParameters()[0].ParameterType);
        Assert.Contains("exact target profile", new ArgumentException(
            "ParseToArtifact requires an exact target profile and reference").Message);
    }

    [Fact]
    public void SimplyRecordsProtocolOperationsWithoutRenderingRegex()
    {
        var pattern = S.Merge(S.StartsWith(S.Literal("ab")), S.Digit(2), S.EndsWith(Essential.Email()));
        var request = pattern.BuildRequest(Projection());
        Assert.Equal("1.1.0", request.GetProperty("protocol_version").GetString());
        Assert.Contains(request.GetProperty("steps").EnumerateArray(),
            step => step.GetProperty("operation").GetString() == "stdlib_helper");
        Assert.Throws<STRlingError>(() => pattern.ToString());
        Assert.Throws<STRlingError>(() => pattern.Exec("input"));
    }

    [Fact]
    public void LexicalHelpersExposeFiveIdentitiesAndEightVariants()
    {
        Assert.Equal(5, Essential.HelperIds.Count);
        var variants = new[]
        {
            Essential.DateTime(), Essential.Email(), Essential.Ip(), Essential.Ip(4),
            Essential.Ip(6), Essential.Url(), Essential.Uuid(), Essential.Uuid(4),
        };
        Assert.Equal(8, variants.Length);
        foreach (var variant in variants)
        {
            var step = variant.BuildRequest(Projection()).GetProperty("steps")[0];
            Assert.Equal("stdlib_helper", step.GetProperty("operation").GetString());
        }
        var parameters = Essential.Ip().BuildRequest(Projection()).GetProperty("steps")[0]
            .GetProperty("arguments").GetProperty("parameters");
        Assert.Equal(JsonValueKind.Null, parameters.GetProperty("version").ValueKind);
    }

    [Fact]
    public void CompatibilityProjectionCoversEveryCanonicalHelper()
    {
        var projectedNames = CompatibilityProjection().GetProperty("patterns")
            .EnumerateObject().Select(pattern => pattern.Name).Order().ToArray();
        Assert.Equal(new[] { "dateTime", "email", "ip", "url", "uuid" }, projectedNames);
        Assert.Equal(projectedNames.Length, Essential.HelperIds.Count);
    }

    [Fact]
    public void BuilderValuesCannotCrossOwners()
    {
        var left = new SimplyBuilder("left");
        var right = new SimplyBuilder("right");
        var value = left.Literal("left-1", "x");
        Assert.Throws<STRlingError>(() => right.Group("right-1", value));
    }

    [Fact]
    public void NativeLoadingRejectsAmbientAndMissingPaths()
    {
        Assert.Throws<NativeLoadException>(() => NativeClient.Load("strling_interop.dll"));
        Assert.Throws<NativeLoadException>(() => NativeClient.Load(Path.GetFullPath("missing-strling-interop.dll")));
    }

    [Fact]
    public void StableHostErrorIdentitiesAreDistinct()
    {
        Assert.Equal("STRLING_DOTNET_NATIVE_LOAD", new NativeLoadException("x").Code);
        Assert.Equal("STRLING_DOTNET_ABI_MISMATCH", new AbiMismatchException(1, 2).Code);
        Assert.Equal("STRLING_DOTNET_TRANSPORT", new TransportException("x").Code);
        Assert.Equal("STRLING_DOTNET_CLOSED", new ClosedClientException().Code);
        Assert.Equal("STRLING_DOTNET_PROTOCOL", new ProtocolException("E", "$", null).Code);
    }
}
