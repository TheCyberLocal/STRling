package com.strling.jvm;

/** The explicitly selected native STRling library could not be loaded. */
public final class NativeLoadException extends NativeAdapterException {
    public NativeLoadException(String message) {
        super(message);
    }

    public NativeLoadException(String message, Throwable cause) {
        super(message, cause);
    }
}
