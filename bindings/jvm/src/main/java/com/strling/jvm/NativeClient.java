package com.strling.jvm;

import com.fasterxml.jackson.core.JsonFactory;
import com.fasterxml.jackson.core.StreamReadFeature;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.jna.Memory;
import com.sun.jna.Native;
import com.sun.jna.Pointer;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.CharBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.locks.ReentrantReadWriteLock;

/**
 * Immutable, reentrant JVM client for the governed {@code strling.c-abi} v1.
 *
 * <p>The client records no language semantics and performs no target selection.
 * Closing prevents future calls but does not claim deterministic JVM native-library unload.</p>
 */
public final class NativeClient implements AutoCloseable {
    public static final String INTEROP_PROTOCOL_VERSION = "1.0.0";
    public static final long NATIVE_ABI_VERSION = 1L;
    public static final long MAX_INTEROP_REQUEST_BYTES = 10_485_760L;
    public static final long MAX_INTEROP_RESPONSE_BYTES = 33_554_432L;

    private static final int STATUS_RESPONSE_WRITTEN = 0;
    private static final ObjectMapper JSON = new ObjectMapper(
            JsonFactory.builder().enable(StreamReadFeature.STRICT_DUPLICATE_DETECTION).build())
            .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS);

    private final Path libraryPath;
    private final InteropLibrary library;
    private final ReentrantReadWriteLock lifecycle = new ReentrantReadWriteLock();
    private boolean closed;

    private NativeClient(Path libraryPath, InteropLibrary library) {
        this.libraryPath = libraryPath;
        this.library = library;
        long actual = Integer.toUnsignedLong(library.strling_interop_abi_version_v1());
        if (actual != NATIVE_ABI_VERSION) {
            throw new AbiMismatchException(NATIVE_ABI_VERSION, actual);
        }
    }

    NativeClient(InteropLibrary library) {
        this(null, Objects.requireNonNull(library, "library"));
    }

    /** Load exactly one absolute native-library path without ambient lookup. */
    public static NativeClient load(Path libraryPath) {
        Objects.requireNonNull(libraryPath, "libraryPath");
        Path normalized = libraryPath.toAbsolutePath().normalize();
        if (!libraryPath.isAbsolute()) {
            throw new NativeLoadException("native STRling library path must be absolute: "
                    + libraryPath);
        }
        if (!Files.isRegularFile(normalized)) {
            throw new NativeLoadException("native STRling library not found: " + normalized);
        }
        try {
            InteropLibrary loaded = Native.load(normalized.toString(), InteropLibrary.class);
            return new NativeClient(normalized, loaded);
        } catch (AbiMismatchException exception) {
            throw exception;
        } catch (LinkageError | RuntimeException exception) {
            throw new NativeLoadException("cannot load native STRling library: " + normalized,
                    exception);
        }
    }

    public Path getLibraryPath() {
        return libraryPath;
    }

    /** Execute one strict protocol request and return its immutable envelope. */
    public Map<String, Object> execute(Map<String, ?> request) {
        Objects.requireNonNull(request, "request");
        rejectNonFinite(request, "$");
        final byte[] encoded;
        try {
            encoded = JSON.writeValueAsBytes(request);
        } catch (IOException | RuntimeException exception) {
            throw new TransportException("interop request is not strict JSON", exception);
        }
        return executeBytes(encoded);
    }

    Map<String, Object> executeBytes(byte[] request) {
        Objects.requireNonNull(request, "request");
        if (request.length > MAX_INTEROP_REQUEST_BYTES) {
            throw new TransportException("interop request exceeds "
                    + MAX_INTEROP_REQUEST_BYTES + " bytes");
        }

        lifecycle.readLock().lock();
        try {
            if (closed) {
                throw new ClosedClientException();
            }
            Memory input = null;
            Pointer inputPointer = Pointer.NULL;
            if (request.length != 0) {
                input = new Memory(request.length);
                input.write(0L, request, 0, request.length);
                inputPointer = input;
            }
            InteropLibrary.OwnedBytes output = new InteropLibrary.OwnedBytes();
            NativeAdapterException primary = null;
            try {
                int status = library.strling_interop_execute_v1(
                        inputPointer, new InteropLibrary.SizeT(request.length), output);
                output.read();
                if (status != STATUS_RESPONSE_WRITTEN) {
                    throw new TransportException("native STRling execution failed", status);
                }
                long length = output.len.longValue();
                if (output.data == null || Pointer.nativeValue(output.data) == 0L
                        || length <= 0L || length > MAX_INTEROP_RESPONSE_BYTES
                        || length > Integer.MAX_VALUE) {
                    throw new TransportException(
                            "native STRling returned an invalid or oversized response");
                }
                byte[] raw = output.data.getByteArray(0L, (int) length);
                return decodeEnvelope(raw);
            } catch (NativeAdapterException exception) {
                primary = exception;
                throw exception;
            } catch (RuntimeException | LinkageError exception) {
                TransportException wrapped = new TransportException(
                        "native STRling call failed", exception);
                primary = wrapped;
                throw wrapped;
            } finally {
                int freeStatus;
                try {
                    freeStatus = library.strling_interop_owned_bytes_free_v1(output);
                } catch (RuntimeException | LinkageError exception) {
                    if (primary == null) {
                        throw new TransportException(
                                "native STRling response release failed", exception);
                    }
                    primary.addSuppressed(exception);
                    freeStatus = STATUS_RESPONSE_WRITTEN;
                }
                if (primary == null && freeStatus != STATUS_RESPONSE_WRITTEN) {
                    throw new TransportException(
                            "native STRling response release failed", freeStatus);
                }
                if (input != null) {
                    input.clear();
                }
            }
        } finally {
            lifecycle.readLock().unlock();
        }
    }

    public Object describe() {
        return completedResult(envelope("describe", Collections.emptyMap()));
    }

    public Object compile(Map<String, ?> compileRequest, Map<String, ?> targetProfile) {
        Objects.requireNonNull(compileRequest, "compileRequest");
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("compile_request", compileRequest);
        if (targetProfile != null) {
            payload.put("target_profile", targetProfile);
        }
        return completedResult(envelope("compile", payload));
    }

    public Object compile(Map<String, ?> compileRequest) {
        return compile(compileRequest, null);
    }

    public Object inspectTargetProfile(Map<String, ?> targetProfile) {
        Objects.requireNonNull(targetProfile, "targetProfile");
        return completedResult(envelope(
                "target_profile.inspect", Collections.singletonMap("target_profile", targetProfile)));
    }

    public Object simplyCompile(Map<String, ?> builderRequest, Map<String, ?> targetProfile) {
        Objects.requireNonNull(builderRequest, "builderRequest");
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("builder_request", builderRequest);
        if (targetProfile != null) {
            payload.put("target_profile", targetProfile);
        }
        return completedResult(envelope("simply.compile", payload));
    }

    public Object simplyCompile(Map<String, ?> builderRequest) {
        return simplyCompile(builderRequest, null);
    }

    public boolean isClosed() {
        lifecycle.readLock().lock();
        try {
            return closed;
        } finally {
            lifecycle.readLock().unlock();
        }
    }

    @Override
    public void close() {
        lifecycle.writeLock().lock();
        try {
            closed = true;
        } finally {
            lifecycle.writeLock().unlock();
        }
    }

    private static Map<String, Object> envelope(String operation, Map<String, ?> payload) {
        Map<String, Object> request = new LinkedHashMap<>();
        request.put("interop_protocol_version", INTEROP_PROTOCOL_VERSION);
        request.put("operation", operation);
        request.put("payload", payload);
        return request;
    }

    private Object completedResult(Map<String, Object> request) {
        Map<String, Object> response = execute(request);
        if ("error".equals(response.get("status"))) {
            @SuppressWarnings("unchecked")
            Map<String, Object> error = (Map<String, Object>) response.get("error");
            Object operation = response.get("operation");
            throw new ProtocolException(
                    (String) error.get("code"),
                    (String) error.get("path"),
                    operation instanceof String ? (String) operation : null);
        }
        return response.get("result");
    }

    private static Map<String, Object> decodeEnvelope(byte[] raw) {
        final String text;
        try {
            CharBuffer decoded = StandardCharsets.UTF_8.newDecoder()
                    .onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT)
                    .decode(ByteBuffer.wrap(raw));
            text = decoded.toString();
        } catch (CharacterCodingException exception) {
            throw new TransportException(
                    "native STRling response is not strict UTF-8", exception);
        }
        final JsonNode node;
        try {
            node = JSON.readTree(text);
        } catch (IOException | RuntimeException exception) {
            throw new TransportException(
                    "native STRling response is not strict JSON", exception);
        }
        if (node == null || !node.isObject()) {
            throw new TransportException("interop response must be an object");
        }
        Object frozen = freeze(node);
        @SuppressWarnings("unchecked")
        Map<String, Object> response = (Map<String, Object>) frozen;
        Object version = response.get("interop_protocol_version");
        Object status = response.get("status");
        if (!INTEROP_PROTOCOL_VERSION.equals(version)
                || !("completed".equals(status) || "error".equals(status))) {
            throw new TransportException(
                    "interop response has an unsupported version or status");
        }
        if ("completed".equals(status) && !response.containsKey("result")) {
            throw new TransportException("completed interop response has no result");
        }
        if ("error".equals(status)) {
            Object value = response.get("error");
            if (!(value instanceof Map)) {
                throw new TransportException(
                        "failed interop response has no stable code and path");
            }
            Map<?, ?> error = (Map<?, ?>) value;
            if (!(error.get("code") instanceof String)
                    || !(error.get("path") instanceof String)) {
                throw new TransportException(
                        "failed interop response has no stable code and path");
            }
        }
        return response;
    }

    private static Object freeze(JsonNode node) {
        if (node.isObject()) {
            Map<String, Object> values = new LinkedHashMap<>();
            node.fields().forEachRemaining(entry -> values.put(entry.getKey(), freeze(entry.getValue())));
            return Collections.unmodifiableMap(values);
        }
        if (node.isArray()) {
            List<Object> values = new ArrayList<>();
            node.elements().forEachRemaining(value -> values.add(freeze(value)));
            return Collections.unmodifiableList(values);
        }
        if (node.isTextual()) {
            return node.textValue();
        }
        if (node.isBoolean()) {
            return node.booleanValue();
        }
        if (node.isIntegralNumber()) {
            return node.canConvertToLong() ? Long.valueOf(node.longValue()) : node.bigIntegerValue();
        }
        if (node.isFloatingPointNumber()) {
            return node.decimalValue();
        }
        return null;
    }

    private static void rejectNonFinite(Object value, String path) {
        if (value instanceof Double && !Double.isFinite(((Double) value).doubleValue())) {
            throw new TransportException("interop request is not strict JSON at " + path);
        }
        if (value instanceof Float && !Float.isFinite(((Float) value).floatValue())) {
            throw new TransportException("interop request is not strict JSON at " + path);
        }
        if (value instanceof Map) {
            for (Map.Entry<?, ?> entry : ((Map<?, ?>) value).entrySet()) {
                if (!(entry.getKey() instanceof String)) {
                    throw new TransportException("interop request object key is not a string at " + path);
                }
                rejectNonFinite(entry.getValue(), path + "." + entry.getKey());
            }
        } else if (value instanceof Iterable) {
            int index = 0;
            for (Object item : (Iterable<?>) value) {
                rejectNonFinite(item, path + "[" + index + "]");
                index += 1;
            }
        }
    }
}
