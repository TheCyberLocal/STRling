package com.strling.jvm;

/** Native-call, ownership, byte-limit, UTF-8, or strict-JSON transport failure. */
public final class TransportException extends NativeAdapterException {
    private final Integer status;

    public TransportException(String message) {
        this(message, null, null);
    }

    public TransportException(String message, Throwable cause) {
        this(message, null, cause);
    }

    public TransportException(String message, int status) {
        this(message, Integer.valueOf(status), null);
    }

    private TransportException(String message, Integer status, Throwable cause) {
        super(status == null ? message : message + " (status "
                + Integer.toUnsignedString(status.intValue()) + ")", cause);
        this.status = status;
    }

    public Integer getStatus() {
        return status;
    }
}
