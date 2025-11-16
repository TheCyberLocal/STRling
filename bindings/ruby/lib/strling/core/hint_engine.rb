# frozen_string_literal: true

# STRling Hint Engine - Context-Aware Error Hints
#
# This module provides intelligent, beginner-friendly hints for parse errors.
# It analyzes error messages and context to suggest likely fixes and
# explanations for common mistakes.

module Strling
  module Core
    # Generate a helpful hint for a parse error
    #
    # @param message [String] The error message
    # @param text [String] The full input text being parsed
    # @param pos [Integer] The position where the error occurred
    # @return [String, nil] A helpful hint, or nil if no specific hint applies
    def self.get_hint(message, text, pos)
      # Extract key parts of the error message
      case message
      when /Invalid quantifier/
        "Quantifiers (*, +, ?, {m,n}) must follow something to repeat. They can't appear at the start of a pattern or immediately after another quantifier."
      when /Cannot quantify anchor/
        "Anchors (^, $, \\b, \\B, etc.) match positions, not characters, so they can't be repeated with quantifiers like * or +."
      when /Unclosed/
        "Make sure every opening bracket has a matching closing bracket. Check for: ( ), [ ], { }"
      when /Unmatched/
        "This closing bracket doesn't have a matching opening bracket. Did you mean to escape it?"
      when /Unknown escape sequence/
        "This escape sequence isn't recognized. Common escapes include: \\n (newline), \\t (tab), \\d (digit), \\w (word character), \\s (whitespace)."
      when /Invalid flag/
        "Valid flags are: i (case-insensitive), m (multiline), s (dotall), u (unicode), x (extended/free-spacing)."
      when /Alternation lacks/
        "Alternation (|) requires a pattern on both sides. Example: 'cat|dog', not 'cat|' or '|dog'."
      when /Unexpected trailing input/
        "The pattern ended but there's still input remaining. Check for extra characters or unmatched brackets."
      when /Directive after pattern content/
        "Directives like %flags must appear before the pattern content, not after."
      else
        nil
      end
    end
  end
end
