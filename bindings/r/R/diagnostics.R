#' STRling Diagnostics — Safety Guards
#'
#' Provides the cross-binding diagnostic types raised and surfaced by
#' the emitter when a pattern would compile to something dangerous
#' (variable length lookbehind, host-stack-exhausting depth, or
#' catastrophic backtracking risk). Mirrors the SSOT in
#' `bindings/typescript/`.

#' Construct a fatal compilation error condition.
#'
#' Carries a stable `code` (`VLB_NOT_SUPPORTED`, `MAX_DEPTH`) and the
#' offending `engine` so cross-binding parity tests can match on shared
#' substrings without coupling to a specific message wording.
#'
#' @param message Human-readable error text.
#' @param code Stable diagnostic code.
#' @param engine Target engine (defaults to "pcre2").
#' @export
STRlingCompilationError <- function(message, code, engine = "pcre2") {
  structure(
    class = c("STRlingCompilationError", "error", "condition"),
    list(message = message, code = code, engine = engine, call = sys.call(-1))
  )
}

#' Construct a non-fatal warning record.
#'
#' `format()` matches the SSOT format `STRlingWarning [CODE]: message`
#' so the global pathological fixture's `expected_warning` substring
#' compares 1:1 across bindings.
#'
#' @param code Stable diagnostic code.
#' @param message Human-readable warning text.
#' @export
STRlingWarning <- function(code, message) {
  structure(
    class = "STRlingWarning",
    list(code = code, message = message)
  )
}

#' @export
format.STRlingWarning <- function(x, ...) {
  paste0("STRlingWarning [", x$code, "]: ", x$message)
}

#' @export
print.STRlingWarning <- function(x, ...) {
  cat(format(x), "\n", sep = "")
  invisible(x)
}

#' Container for an emit pass result.
#'
#' @param pattern Compiled PCRE2 pattern string.
#' @param warnings List of [STRlingWarning] records.
#' @export
CompileResult <- function(pattern, warnings = list()) {
  structure(class = "CompileResult", list(pattern = pattern, warnings = warnings))
}
