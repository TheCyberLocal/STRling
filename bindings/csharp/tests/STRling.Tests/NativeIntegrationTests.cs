using System.Text.Json;
using Strling;
using Strling.Native;
using Strling.Simply;

namespace STRling.Tests;

public sealed class NativeIntegrationTests
{
    [Fact]
    public void SharedClientExecutesCanonicalOperationsAndLifecycle()
    {
        var configured = Environment.GetEnvironmentVariable("STRLING_NATIVE_LIBRARY");
        if (string.IsNullOrWhiteSpace(configured)) return;

        using var client = NativeClient.Load(Path.GetFullPath(configured));
        var describe = client.Describe();
        var compile = new Compiler(client).Parse(
            "literal \"hello\"",
            new SourceCompileOptions { SourceId = "src:dotnet.parity" });
        var simply = client.SimplyCompile(Essential.Ip().BuildRequest(Projection(), "dotnet-parity"));
        Assert.Contains(compile.GetProperty("outcome").GetString(), new[] { "succeeded", "failed" });
        Assert.Equal(JsonValueKind.Object, simply.ValueKind);

        Parallel.For(0, 16, _ => Assert.Equal(describe.GetRawText(), client.Describe().GetRawText()));
        WriteEvidence(describe, compile, simply);

        client.Dispose();
        client.Dispose();
        Assert.Throws<ClosedClientException>(() => client.Describe());
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

    private static void WriteEvidence(JsonElement describe, JsonElement compile, JsonElement simply)
    {
        var configured = Environment.GetEnvironmentVariable("STRLING_DOTNET_EVIDENCE_DIR");
        if (string.IsNullOrWhiteSpace(configured)) return;
        var directory = Directory.CreateDirectory(Path.Combine(configured, "csharp")).FullName;
        File.WriteAllText(Path.Combine(directory, "describe.json"), describe.GetRawText());
        File.WriteAllText(Path.Combine(directory, "compile.json"), compile.GetRawText());
        File.WriteAllText(Path.Combine(directory, "simply.json"), simply.GetRawText());
    }
}
