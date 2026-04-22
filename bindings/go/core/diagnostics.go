package core

import "fmt"

// STRlingCompilationError is a fatal emitter-stage failure raised by an
// IR safety guard. Mirrors the `STRlingCompilationError` type in the
// TypeScript reference and the matching types in the C / C++ / C# /
// Python / Java / Rust bindings.
//
// Carries a stable Code (e.g. "VLB_NOT_SUPPORTED", "MAX_DEPTH") and the
// offending Engine so cross-binding parity tests can match on shared
// substrings without coupling to a specific message wording.
type STRlingCompilationError struct {
	Message string
	Code    string
	Engine  string
}

// Error implements the error interface.
func (e *STRlingCompilationError) Error() string {
	return e.Message
}

// NewSTRlingCompilationError constructs a compilation error. Engine
// defaults to "pcre2" when empty.
func NewSTRlingCompilationError(message, code, engine string) *STRlingCompilationError {
	if engine == "" {
		engine = "pcre2"
	}
	return &STRlingCompilationError{Message: message, Code: code, Engine: engine}
}

// STRlingWarning is a non-fatal diagnostic emitted alongside a compiled
// pattern. Currently used for REDOS_RISK (nested unbounded quantifiers).
//
// The String() form matches the SSOT `STRlingWarning [CODE]: message`
// shape so the global pathological fixture's `expected_warning`
// substring compares 1:1 across bindings.
type STRlingWarning struct {
	Code    string
	Message string
}

// String returns the canonical SSOT formatting.
func (w STRlingWarning) String() string {
	return fmt.Sprintf("STRlingWarning [%s]: %s", w.Code, w.Message)
}

// CompileResult is the result of an emit pass: the produced PCRE2
// pattern plus any non-fatal diagnostics collected during emission.
type CompileResult struct {
	Pattern  string
	Warnings []STRlingWarning
}
