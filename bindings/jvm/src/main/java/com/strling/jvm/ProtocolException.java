package com.strling.jvm;

/** A stable error envelope returned by the versioned interop protocol. */
public final class ProtocolException extends NativeAdapterException {
    private final String code;
    private final String path;
    private final String operation;

    public ProtocolException(String code, String path, String operation) {
        super(code + " at " + path);
        this.code = code;
        this.path = path;
        this.operation = operation;
    }

    public String getCode() {
        return code;
    }

    public String getPath() {
        return path;
    }

    public String getOperation() {
        return operation;
    }
}
