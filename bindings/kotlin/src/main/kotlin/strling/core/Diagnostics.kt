package strling.core

/**
 * Fatal emitter-stage failure raised by an IR safety guard.
 *
 * Mirrors the `STRlingCompilationError` type in the TypeScript reference
 * and the matching types in every other binding. Carries a stable
 * [code] (`VLB_NOT_SUPPORTED`, `MAX_DEPTH`) and the offending [engine]
 * so cross-binding parity tests can match on shared substrings without
 * coupling to a specific message wording.
 */
class STRlingCompilationError(
    message: String,
    val code: String,
    val engine: String = "pcre2",
) : Exception(message)

/**
 * Non-fatal diagnostic emitted alongside a compiled pattern. Currently
 * used for `REDOS_RISK` (nested unbounded quantifiers).
 *
 * [toString] matches the SSOT `STRlingWarning [CODE]: message` format
 * so the global pathological fixture's `expected_warning` substring
 * compares 1:1 across bindings.
 */
data class STRlingWarning(val code: String, val message: String) {
    override fun toString(): String = "STRlingWarning [$code]: $message"
}

/**
 * Result of an emit pass: the produced PCRE2 pattern plus any non-fatal
 * diagnostics collected during emission.
 */
data class CompileResult(val pattern: String, val warnings: List<STRlingWarning>)
