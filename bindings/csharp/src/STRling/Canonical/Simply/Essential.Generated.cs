#nullable enable

namespace Strling.Simply;

/// <summary>
/// Generated canonical standard-library identities for Simply 1.1.
/// These lexical helpers record registry identity; they do not validate semantics.
/// </summary>
public static class Essential
{
    public const string SourceSha256 = "db3d1fc6ddd1b0ef83cb7bfb4a9bd84c8bcc547d5a6649a6747cc4b94fb4edff";
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
