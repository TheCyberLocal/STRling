#nullable enable

namespace Strling.Simply;

/// <summary>
/// Generated canonical standard-library identities for Simply 1.1.
/// These lexical helpers record registry identity; they do not validate semantics.
/// </summary>
public static class Essential
{
    public const string SourceSha256 = "94f28b16873abd0b57b324b76e236cbe17706f5310758e066a88a776e4930a3d";
    public const string RegistryVersion = "1.0.0";
    public static IReadOnlyList<string> HelperIds { get; } =
        ["stdlib.date_time", "stdlib.email", "stdlib.ip", "stdlib.url", "stdlib.uuid"];

    public static Pattern DateTime() => Pattern.StdlibHelper("stdlib.date_time", new Dictionary<string, object?>());
    public static Pattern Email() => Pattern.StdlibHelper("stdlib.email", new Dictionary<string, object?>());
    public static Pattern Ip(int? version = null) => Pattern.StdlibHelper(
        "stdlib.ip", new Dictionary<string, object?> { ["version"] = version });
    public static Pattern Url() => Pattern.StdlibHelper("stdlib.url", new Dictionary<string, object?>());
    public static Pattern Uuid(int? version = null) => Pattern.StdlibHelper(
        "stdlib.uuid", new Dictionary<string, object?> { ["version"] = version });
}
