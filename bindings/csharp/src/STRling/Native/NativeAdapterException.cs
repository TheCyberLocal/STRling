namespace Strling.Native;

/// <summary>Base type for stable failures at the .NET/native adapter boundary.</summary>
public abstract class NativeAdapterException : Exception
{
    protected NativeAdapterException(string code, string message, Exception? inner = null)
        : base(message, inner) => Code = code;

    public string Code { get; }
}

public sealed class NativeLoadException : NativeAdapterException
{
    public NativeLoadException(string message, Exception? inner = null)
        : base("STRLING_DOTNET_NATIVE_LOAD", message, inner) { }
}

public sealed class AbiMismatchException : NativeAdapterException
{
    public AbiMismatchException(uint expected, uint actual)
        : base("STRLING_DOTNET_ABI_MISMATCH", $"native STRling ABI {actual} does not match required ABI {expected}")
    {
        Expected = expected;
        Actual = actual;
    }

    public uint Expected { get; }
    public uint Actual { get; }
}

public sealed class TransportException : NativeAdapterException
{
    public TransportException(string message, Exception? inner = null)
        : base("STRLING_DOTNET_TRANSPORT", message, inner) { }
}

public sealed class ClosedClientException : NativeAdapterException
{
    public ClosedClientException()
        : base("STRLING_DOTNET_CLOSED", "native STRling client is disposed") { }
}

public sealed class ProtocolException : NativeAdapterException
{
    public ProtocolException(string code, string path, string? operation)
        : base("STRLING_DOTNET_PROTOCOL", $"{code} at {path}")
    {
        ProtocolCode = code;
        Path = path;
        Operation = operation;
    }

    public string ProtocolCode { get; }
    public string Path { get; }
    public string? Operation { get; }
}
