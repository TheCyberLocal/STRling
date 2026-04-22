import Foundation

/// Fatal emitter-stage failure raised by an IR safety guard.
///
/// Mirrors the `STRlingCompilationError` type in the TypeScript reference
/// and the matching types in the C / C++ / C# / F# / Python / Java / Rust
/// / Go bindings. Carries a stable `code` (`VLB_NOT_SUPPORTED`,
/// `MAX_DEPTH`) and the offending `engine` so cross-binding parity tests
/// can match on shared substrings without coupling to a specific message
/// wording.
public struct STRlingCompilationError: Error {
    public let message: String
    public let code: String
    public let engine: String

    public init(message: String, code: String, engine: String = "pcre2") {
        self.message = message
        self.code = code
        self.engine = engine
    }
}

/// Non-fatal diagnostic emitted alongside a compiled pattern. Currently
/// used for `REDOS_RISK` (nested unbounded quantifiers).
///
/// `description` matches the SSOT `STRlingWarning [CODE]: message`
/// format so the global pathological fixture's `expected_warning`
/// substring compares 1:1 across bindings.
public struct STRlingWarning: CustomStringConvertible, Equatable {
    public let code: String
    public let message: String

    public init(code: String, message: String) {
        self.code = code
        self.message = message
    }

    public var description: String {
        return "STRlingWarning [\(code)]: \(message)"
    }
}

/// Result of an emit pass: the produced PCRE2 pattern plus any
/// non-fatal diagnostics collected during emission.
public struct CompileResult {
    public let pattern: String
    public let warnings: [STRlingWarning]

    public init(pattern: String, warnings: [STRlingWarning]) {
        self.pattern = pattern
        self.warnings = warnings
    }
}
