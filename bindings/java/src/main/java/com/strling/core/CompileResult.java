package com.strling.core;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;

/**
 * Result of an emit pass: the produced PCRE2 pattern plus any non-fatal
 * diagnostics collected during emission.
 *
 * <p>Returned by {@code Pcre2Emitter.emitWithDiagnostics(...)}. The
 * companion back-compat entry point {@code Pcre2Emitter.emit(...)}
 * discards warnings for callers that only care about the pattern.</p>
 *
 * <p>Mirrors {@code EmitResult} in the TypeScript reference and the
 * Python {@code EmitResult} dataclass.</p>
 */
public final class CompileResult {

    private final String pattern;
    private final List<STRlingWarning> warnings;

    public CompileResult(String pattern, List<STRlingWarning> warnings) {
        this.pattern = pattern;
        this.warnings = warnings == null
            ? Collections.emptyList()
            : Collections.unmodifiableList(new ArrayList<>(warnings));
    }

    public String getPattern() {
        return pattern;
    }

    public List<STRlingWarning> getWarnings() {
        return warnings;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof CompileResult)) return false;
        CompileResult that = (CompileResult) o;
        return Objects.equals(pattern, that.pattern)
            && Objects.equals(warnings, that.warnings);
    }

    @Override
    public int hashCode() {
        return Objects.hash(pattern, warnings);
    }
}
