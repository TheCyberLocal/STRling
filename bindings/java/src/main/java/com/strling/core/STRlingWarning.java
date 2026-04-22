package com.strling.core;

import java.util.Objects;

/**
 * Non-fatal diagnostic emitted alongside a compiled pattern.
 *
 * <p>Currently used for {@code "REDOS_RISK"} (nested unbounded
 * quantifiers). Plain value object — not an exception — so it can be
 * collected and surfaced to the caller without aborting compilation.</p>
 *
 * <p>The {@link #toString()} format matches the TypeScript SSOT's
 * {@code STRlingWarning [CODE]: message} shape so the global pathological
 * fixture's {@code expected_warning} substring compares 1:1 across
 * bindings.</p>
 */
public final class STRlingWarning {

    private final String code;
    private final String message;

    public STRlingWarning(String code, String message) {
        this.code = code;
        this.message = message;
    }

    public String getCode() {
        return code;
    }

    public String getMessage() {
        return message;
    }

    @Override
    public String toString() {
        return "STRlingWarning [" + code + "]: " + message;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof STRlingWarning)) return false;
        STRlingWarning that = (STRlingWarning) o;
        return Objects.equals(code, that.code) && Objects.equals(message, that.message);
    }

    @Override
    public int hashCode() {
        return Objects.hash(code, message);
    }
}
