using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Text.RegularExpressions;
using Strling.Simply;
using Xunit;

namespace STRling.Tests;

public class Essential5Tests
{
    private static readonly JsonElement Spec = LoadSpec();

    private static JsonElement LoadSpec()
    {
        var dir = AppContext.BaseDirectory;
        // Walk up to repository root by searching for "spec/stdlib/essential_5.json"
        var current = new DirectoryInfo(dir);
        while (current != null)
        {
            var candidate = Path.Combine(current.FullName, "spec", "stdlib", "essential_5.json");
            if (File.Exists(candidate))
            {
                using var fs = File.OpenRead(candidate);
                return JsonDocument.Parse(fs).RootElement;
            }
            current = current.Parent;
        }
        throw new FileNotFoundException("essential_5.json not found in any ancestor directory");
    }

    private static IEnumerable<string> Strings(string pattern, string field)
    {
        var arr = Spec.GetProperty("patterns").GetProperty(pattern)
            .GetProperty("fixtures").GetProperty(field);
        foreach (var item in arr.EnumerateArray()) yield return item.GetString()!;
    }

    private static void AssertAccepts(Pattern pattern, string text)
    {
        var re = new Regex("^(?:" + pattern.Compile() + ")$");
        Assert.True(re.IsMatch(text), $"Expected match for {text}");
    }

    private static void AssertRejects(Pattern pattern, string text)
    {
        var re = new Regex("^(?:" + pattern.Compile() + ")$");
        Assert.False(re.IsMatch(text), $"Expected NO match for {text}");
    }

    [Fact]
    public void Email_AcceptsAllValidFixtures()
    {
        foreach (var v in Strings("email", "valid")) AssertAccepts(Essential.Email(), v);
    }

    [Fact]
    public void Email_RejectsAllInvalidFixtures()
    {
        foreach (var v in Strings("email", "invalid")) AssertRejects(Essential.Email(), v);
    }

    [Fact]
    public void Url_AcceptsAllValidFixtures()
    {
        foreach (var v in Strings("url", "valid")) AssertAccepts(Essential.Url(), v);
    }

    [Fact]
    public void Url_RejectsAllInvalidFixtures()
    {
        foreach (var v in Strings("url", "invalid")) AssertRejects(Essential.Url(), v);
    }

    [Fact]
    public void Uuid_AcceptsAllValidDefaultFixtures()
    {
        foreach (var v in Strings("uuid", "valid_default")) AssertAccepts(Essential.Uuid(), v);
    }

    [Fact]
    public void Uuid_RejectsAllInvalidDefaultFixtures()
    {
        foreach (var v in Strings("uuid", "invalid_default")) AssertRejects(Essential.Uuid(), v);
    }

    [Fact]
    public void Uuid_V4AcceptsAllValidV4Fixtures()
    {
        foreach (var v in Strings("uuid", "valid_v4")) AssertAccepts(Essential.Uuid(4), v);
    }

    [Fact]
    public void Uuid_V4RejectsAllInvalidV4Fixtures()
    {
        foreach (var v in Strings("uuid", "invalid_v4")) AssertRejects(Essential.Uuid(4), v);
    }

    [Fact]
    public void Ip_V4AcceptsAllValidFixtures()
    {
        foreach (var v in Strings("ip", "valid_v4")) AssertAccepts(Essential.Ip(4), v);
    }

    [Fact]
    public void Ip_V4RejectsAllInvalidFixtures()
    {
        foreach (var v in Strings("ip", "invalid_v4")) AssertRejects(Essential.Ip(4), v);
    }

    [Fact]
    public void Ip_V6AcceptsAllValidFixtures()
    {
        foreach (var v in Strings("ip", "valid_v6")) AssertAccepts(Essential.Ip(6), v);
    }

    [Fact]
    public void Ip_V6RejectsAllInvalidFixtures()
    {
        foreach (var v in Strings("ip", "invalid_v6")) AssertRejects(Essential.Ip(6), v);
    }

    [Fact]
    public void Ip_DefaultAcceptsBothFamilies()
    {
        foreach (var v in Strings("ip", "valid_v4")) AssertAccepts(Essential.Ip(), v);
        foreach (var v in Strings("ip", "valid_v6")) AssertAccepts(Essential.Ip(), v);
    }

    [Fact]
    public void DateTime_AcceptsAllValidFixtures()
    {
        foreach (var v in Strings("dateTime", "valid")) AssertAccepts(Essential.DateTime(), v);
    }

    [Fact]
    public void DateTime_RejectsAllInvalidFixtures()
    {
        foreach (var v in Strings("dateTime", "invalid")) AssertRejects(Essential.DateTime(), v);
    }
}
