package com.strling.simply;

/** Invalid host-side recipe construction; canonical failures remain values. */
public final class STRlingError extends IllegalArgumentException {
    public STRlingError(String message) {
        super(message);
    }
}
