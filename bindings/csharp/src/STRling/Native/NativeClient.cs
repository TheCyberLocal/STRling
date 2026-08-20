using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;

namespace Strling.Native;

/// <summary>
/// Immutable, reentrant client for the governed <c>strling.c-abi</c> v1.
/// The client performs transport only: it does not interpret Semantic IR,
/// select a target, or implement regex semantics.
/// </summary>
public sealed class NativeClient : IDisposable
{
    public const string InteropProtocolVersion = "1.0.0";
    public const uint NativeAbiVersion = 1;
    public const int MaxInteropRequestBytes = 10_485_760;
    public const int MaxInteropResponseBytes = 33_554_432;

    private const uint ResponseWritten = 0;
    private static readonly UTF8Encoding StrictUtf8 = new(false, true);
    private readonly ReaderWriterLockSlim lifecycle = new();
    private readonly nint libraryHandle;
    private readonly AbiVersion abiVersion;
    private readonly ExecuteNative execute;
    private readonly FreeOwnedBytes free;
    private bool disposed;

    private NativeClient(
        string libraryPath,
        nint libraryHandle,
        AbiVersion abiVersion,
        ExecuteNative execute,
        FreeOwnedBytes free)
    {
        LibraryPath = libraryPath;
        this.libraryHandle = libraryHandle;
        this.abiVersion = abiVersion;
        this.execute = execute;
        this.free = free;
        var actual = abiVersion();
        if (actual != NativeAbiVersion)
        {
            throw new AbiMismatchException(NativeAbiVersion, actual);
        }
    }

    /// <summary>Absolute path used to load the single native handle.</summary>
    public string LibraryPath { get; }

    public bool IsDisposed
    {
        get
        {
            lifecycle.EnterReadLock();
            try { return disposed; }
            finally { lifecycle.ExitReadLock(); }
        }
    }

    /// <summary>Load exactly one absolute file path. No ambient probing is performed.</summary>
    public static NativeClient Load(string libraryPath)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(libraryPath);
        if (!Path.IsPathFullyQualified(libraryPath))
        {
            throw new NativeLoadException($"native STRling library path must be absolute: {libraryPath}");
        }

        var normalized = Path.GetFullPath(libraryPath);
        if (!File.Exists(normalized))
        {
            throw new NativeLoadException($"native STRling library not found: {normalized}");
        }

        nint handle = 0;
        try
        {
            handle = NativeLibrary.Load(normalized);
            var abi = Resolve<AbiVersion>(handle, "strling_interop_abi_version_v1");
            var execute = Resolve<ExecuteNative>(handle, "strling_interop_execute_v1");
            var free = Resolve<FreeOwnedBytes>(handle, "strling_interop_owned_bytes_free_v1");
            return new NativeClient(normalized, handle, abi, execute, free);
        }
        catch (AbiMismatchException)
        {
            if (handle != 0) NativeLibrary.Free(handle);
            throw;
        }
        catch (Exception error) when (error is not NativeAdapterException)
        {
            if (handle != 0) NativeLibrary.Free(handle);
            throw new NativeLoadException($"cannot load native STRling library: {normalized}", error);
        }
    }

    /// <summary>Execute one strict JSON protocol request.</summary>
    public JsonElement Execute(JsonElement request)
    {
        byte[] encoded;
        try
        {
            encoded = JsonSerializer.SerializeToUtf8Bytes(request);
            _ = StrictUtf8.GetString(encoded);
        }
        catch (Exception error) when (error is JsonException or EncoderFallbackException)
        {
            throw new TransportException("interop request is not strict JSON/UTF-8", error);
        }

        if (encoded.Length > MaxInteropRequestBytes)
        {
            throw new TransportException($"interop request exceeds {MaxInteropRequestBytes} bytes");
        }

        lifecycle.EnterReadLock();
        try
        {
            if (disposed) throw new ClosedClientException();
            return ExecuteLocked(encoded);
        }
        finally
        {
            lifecycle.ExitReadLock();
        }
    }

    public JsonElement Describe() => CompletedResult(Envelope("describe", EmptyObject()));

    public JsonElement Compile(JsonElement compileRequest, JsonElement? targetProfile = null)
    {
        var payload = new Dictionary<string, object?> { ["compile_request"] = compileRequest };
        if (targetProfile.HasValue) payload["target_profile"] = targetProfile.Value;
        return CompletedResult(Envelope("compile", payload));
    }

    public JsonElement InspectTargetProfile(JsonElement targetProfile) => CompletedResult(
        Envelope("target_profile.inspect", new Dictionary<string, object?> { ["target_profile"] = targetProfile }));

    public JsonElement SimplyCompile(JsonElement builderRequest, JsonElement? targetProfile = null)
    {
        var payload = new Dictionary<string, object?> { ["builder_request"] = builderRequest };
        if (targetProfile.HasValue) payload["target_profile"] = targetProfile.Value;
        return CompletedResult(Envelope("simply.compile", payload));
    }

    public void Dispose()
    {
        lifecycle.EnterWriteLock();
        try
        {
            if (disposed) return;
            disposed = true;
            NativeLibrary.Free(libraryHandle);
        }
        finally
        {
            lifecycle.ExitWriteLock();
        }
    }

    private unsafe JsonElement ExecuteLocked(byte[] request)
    {
        OwnedBytes output = default;
        Exception? primary = null;
        try
        {
            fixed (byte* input = request)
            {
                var status = execute(request.Length == 0 ? null : input, (nuint)request.Length, ref output);
                if (status != ResponseWritten)
                {
                    throw new TransportException($"native STRling execution failed with status {status}");
                }
            }

            if (output.Data == 0 || output.Length == 0 || output.Length > MaxInteropResponseBytes || output.Length > int.MaxValue)
            {
                throw new TransportException("native STRling returned an invalid or oversized response");
            }

            var bytes = new byte[(int)output.Length];
            Marshal.Copy(output.Data, bytes, 0, bytes.Length);
            return DecodeEnvelope(bytes);
        }
        catch (Exception error)
        {
            primary = error;
            throw;
        }
        finally
        {
            try
            {
                var status = free(ref output);
                if (primary is null && status != ResponseWritten)
                {
                    throw new TransportException($"native STRling response release failed with status {status}");
                }
            }
            catch (Exception releaseError) when (primary is not null)
            {
                primary.Data["release_error"] = releaseError.Message;
            }
        }
    }

    private static JsonElement DecodeEnvelope(byte[] bytes)
    {
        string text;
        try { text = StrictUtf8.GetString(bytes); }
        catch (DecoderFallbackException error)
        {
            throw new TransportException("native STRling response is not strict UTF-8", error);
        }

        try
        {
            using var document = JsonDocument.Parse(text, new JsonDocumentOptions
            {
                AllowTrailingCommas = false,
                CommentHandling = JsonCommentHandling.Disallow,
                MaxDepth = 128,
            });
            RejectDuplicateProperties(document.RootElement, "$");
            if (document.RootElement.ValueKind != JsonValueKind.Object)
                throw new TransportException("interop response must be an object");
            var root = document.RootElement;
            if (!root.TryGetProperty("interop_protocol_version", out var version)
                || version.GetString() != InteropProtocolVersion
                || !root.TryGetProperty("status", out var status)
                || (status.GetString() is not ("completed" or "error")))
                throw new TransportException("interop response has an unsupported version or status");
            if (status.GetString() == "completed" && !root.TryGetProperty("result", out _))
                throw new TransportException("completed interop response has no result");
            if (status.GetString() == "error"
                && (!root.TryGetProperty("error", out var error)
                    || error.ValueKind != JsonValueKind.Object
                    || !error.TryGetProperty("code", out var code)
                    || code.ValueKind != JsonValueKind.String
                    || !error.TryGetProperty("path", out var path)
                    || path.ValueKind != JsonValueKind.String))
                throw new TransportException("failed interop response has no stable code and path");
            return root.Clone();
        }
        catch (JsonException error)
        {
            throw new TransportException("native STRling response is not strict JSON", error);
        }
    }

    private static void RejectDuplicateProperties(JsonElement value, string path)
    {
        if (value.ValueKind == JsonValueKind.Object)
        {
            var names = new HashSet<string>(StringComparer.Ordinal);
            foreach (var property in value.EnumerateObject())
            {
                if (!names.Add(property.Name))
                    throw new TransportException($"native STRling response contains duplicate property at {path}.{property.Name}");
                RejectDuplicateProperties(property.Value, $"{path}.{property.Name}");
            }
        }
        else if (value.ValueKind == JsonValueKind.Array)
        {
            var index = 0;
            foreach (var item in value.EnumerateArray())
                RejectDuplicateProperties(item, $"{path}[{index++}]");
        }
    }

    private JsonElement CompletedResult(JsonElement request)
    {
        var response = Execute(request);
        if (response.GetProperty("status").GetString() == "error")
        {
            var error = response.GetProperty("error");
            throw new ProtocolException(
                error.GetProperty("code").GetString()!,
                error.GetProperty("path").GetString()!,
                response.TryGetProperty("operation", out var operation) ? operation.GetString() : null);
        }
        return response.GetProperty("result").Clone();
    }

    private static JsonElement Envelope(string operation, object payload) => JsonSerializer.SerializeToElement(
        new Dictionary<string, object?>
        {
            ["interop_protocol_version"] = InteropProtocolVersion,
            ["operation"] = operation,
            ["payload"] = payload,
        });

    private static JsonElement EmptyObject() => JsonSerializer.SerializeToElement(new Dictionary<string, object?>());

    private static T Resolve<T>(nint handle, string symbol) where T : Delegate =>
        Marshal.GetDelegateForFunctionPointer<T>(NativeLibrary.GetExport(handle, symbol));

    [StructLayout(LayoutKind.Sequential)]
    private struct OwnedBytes
    {
        public nint Data;
        public nuint Length;
    }

    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    private delegate uint AbiVersion();

    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    private unsafe delegate uint ExecuteNative(byte* input, nuint inputLength, ref OwnedBytes output);

    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    private delegate uint FreeOwnedBytes(ref OwnedBytes output);
}
