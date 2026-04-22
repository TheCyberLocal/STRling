package com.strling.core;

/**
 * Raised by IR emitters when a safety guard rejects a pattern.
 *
 * <p>Used by the PCRE2 emitter for fatal structural problems such as
 * variable-length lookbehinds or AST nesting that exceeds the depth
 * ceiling. Carries a stable {@code code} (e.g. {@code "VLB_NOT_SUPPORTED"},
 * {@code "MAX_DEPTH"}) and the offending {@code engine} name so
 * cross-binding parity tests can match on substrings without coupling to
 * exact wording.</p>
 *
 * <p>Mirrors {@code STRlingCompilationError} in the TypeScript reference
 * and the matching Python and Rust types.</p>
 */
public class STRlingCompilationError extends RuntimeException {

    private static final long serialVersionUID = 1L;

    private final String code;
    private final String engine;

    public STRlingCompilationError(String message, String code, String engine) {
        super(message);
        this.code = code;
        this.engine = engine;
    }

    public STRlingCompilationError(String message, String code) {
        this(message, code, "pcre2");
    }

    public String getCode() {
        return code;
    }

    public String getEngine() {
        return engine;
    }
}
