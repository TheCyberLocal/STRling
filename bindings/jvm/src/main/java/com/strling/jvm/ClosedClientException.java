package com.strling.jvm;

/** A call was attempted after the client was closed. */
public final class ClosedClientException extends NativeAdapterException {
    public ClosedClientException() {
        super("native STRling client is closed");
    }
}
