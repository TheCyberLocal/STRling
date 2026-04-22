/// STRling Diagnostics — Safety Guards
///
/// Provides the cross-binding diagnostic types raised and surfaced by
/// the emitter when a pattern would compile to something dangerous
/// (variable length lookbehind, host-stack-exhausting depth, or
/// catastrophic backtracking risk). Mirrors the SSOT in
/// `bindings/typescript/`.

/// Fatal emitter-stage failure raised by an IR safety guard.
///
/// Carries a stable [code] (`VLB_NOT_SUPPORTED`, `MAX_DEPTH`) and the
/// offending [engine] so cross-binding parity tests can match on shared
/// substrings without coupling to a specific message wording.
class STRlingCompilationError implements Exception {
  final String message;
  final String code;
  final String engine;

  STRlingCompilationError(this.message, this.code, [this.engine = 'pcre2']);

  @override
  String toString() => 'STRlingCompilationError: $message';
}

/// Non-fatal diagnostic emitted alongside a compiled pattern.
/// Currently used for `REDOS_RISK`.
///
/// `toString` matches the SSOT format `STRlingWarning [CODE]: message`
/// so the global pathological fixture's `expected_warning` substring
/// compares 1:1 across bindings.
class STRlingWarning {
  final String code;
  final String message;

  const STRlingWarning(this.code, this.message);

  @override
  String toString() => 'STRlingWarning [$code]: $message';
}

/// Result of an emit pass: the produced PCRE2 pattern plus any
/// non-fatal diagnostics collected during emission.
class CompileResult {
  final String pattern;
  final List<STRlingWarning> warnings;

  const CompileResult(this.pattern, this.warnings);
}
