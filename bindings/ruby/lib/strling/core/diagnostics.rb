# frozen_string_literal: true

# STRling Diagnostics — Safety Guards
#
# Provides the cross-binding diagnostic types raised and surfaced by the
# emitter when a pattern would compile to something dangerous (variable
# length lookbehind, host-stack-exhausting depth, or catastrophic
# backtracking risk). Mirrors the SSOT in `bindings/typescript/`.

module Strling
  module Core
    # Fatal emitter-stage failure raised by an IR safety guard.
    #
    # Carries a stable {#code} (`VLB_NOT_SUPPORTED`, `MAX_DEPTH`) and the
    # offending {#engine} so cross-binding parity tests can match on
    # shared substrings without coupling to a specific message wording.
    class STRlingCompilationError < StandardError
      attr_reader :code, :engine

      def initialize(message, code, engine: 'pcre2')
        super(message)
        @code = code
        @engine = engine
      end
    end

    # Non-fatal diagnostic emitted alongside a compiled pattern.
    # Currently used for `REDOS_RISK`.
    #
    # `to_s` matches the SSOT format `STRlingWarning [CODE]: message` so
    # the global pathological fixture's `expected_warning` substring
    # compares 1:1 across bindings.
    class STRlingWarning
      attr_reader :code, :message

      def initialize(code, message)
        @code = code
        @message = message
      end

      def to_s
        "STRlingWarning [#{code}]: #{message}"
      end
    end

    # Result of an emit pass: the produced PCRE2 pattern plus any
    # non-fatal diagnostics collected during emission.
    class CompileResult
      attr_reader :pattern, :warnings

      def initialize(pattern, warnings)
        @pattern = pattern
        @warnings = warnings
      end
    end
  end
end
