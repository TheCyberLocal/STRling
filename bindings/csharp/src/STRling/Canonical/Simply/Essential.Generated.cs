#nullable enable

namespace Strling.Simply;

/// <summary>
/// Generated canonical standard-library identities for Simply 1.1.
/// These lexical helpers record registry identity; they do not validate semantics.
/// </summary>
public static class Essential
{
    public const string SourceSha256 = "3539cc50744c492ee617f9c836c83e040ad3af2f32dd8fe3b1e329c5b14bc719";
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
