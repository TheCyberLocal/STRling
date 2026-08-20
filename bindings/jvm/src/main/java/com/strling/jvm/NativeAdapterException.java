package com.strling.jvm;

/** Base type for failures in the JVM/native adapter boundary. */
public class NativeAdapterException extends RuntimeException {
    public NativeAdapterException(String message) {
        super(message);
    }

    public NativeAdapterException(String message, Throwable cause) {
        super(message, cause);
    }
}
