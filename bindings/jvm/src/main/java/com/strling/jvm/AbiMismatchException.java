package com.strling.jvm;

/** The selected native library does not implement the required ABI major. */
public final class AbiMismatchException extends NativeAdapterException {
    private final long expectedVersion;
    private final long actualVersion;

    public AbiMismatchException(long expectedVersion, long actualVersion) {
        super("unsupported strling.c-abi version " + actualVersion
                + "; expected " + expectedVersion);
        this.expectedVersion = expectedVersion;
        this.actualVersion = actualVersion;
    }

    public long getExpectedVersion() {
        return expectedVersion;
    }

    public long getActualVersion() {
        return actualVersion;
    }
}
