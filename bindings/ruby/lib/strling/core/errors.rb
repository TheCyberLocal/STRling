# frozen_string_literal: true

# STRling Error Classes - Rich Error Handling for Instructional Diagnostics
#
# This module provides enhanced error classes that deliver context-aware,
# instructional error messages. The STRlingParseError class stores detailed
# information about syntax errors including position, context, and beginner-friendly
# hints for resolution.

module Strling
  module Core
    # Rich parse error with position tracking and instructional hints.
    #
    # This error class transforms parse failures into learning opportunities by
    # providing:
    # - The specific error message
    # - The exact position where the error occurred
    # - The full line of text containing the error
    # - A beginner-friendly hint explaining how to fix the issue
    class STRlingParseError < StandardError
      # @return [String] A concise description of what went wrong
      attr_reader :message

      # @return [Integer] The character position (0-indexed) where the error occurred
      attr_reader :pos

      # @return [String] The full input text being parsed
      attr_reader :text

      # @return [String, nil] An instructional hint explaining how to fix the error
      attr_reader :hint

      # Initialize a STRlingParseError.
      #
      # @param message [String] A concise description of what went wrong
      # @param pos [Integer] The character position (0-indexed) where the error occurred
      # @param text [String] The full input text being parsed (default: "")
      # @param hint [String, nil] An instructional hint explaining how to fix the error (default: nil)
      def initialize(message, pos, text: '', hint: nil)
        @message = message
        @pos = pos
        @text = text
        @hint = hint

        # Call parent constructor with formatted message
        super(format_error)
      end

      # Format the error in the visionary state format.
      #
      # @return [String] A formatted error message with context and hints
      def format_error
        if text.empty?
          # Fallback to simple format if no text provided
          return "#{message} at position #{pos}"
        end

        # Find the line containing the error
        lines = text.lines(chomp: true)
        current_pos = 0
        line_num = 1
        line_text = ''
        col = pos

        lines.each_with_index do |line, i|
          line_len = line.length + 1 # +1 for newline
          if current_pos + line_len > pos
            line_num = i + 1
            line_text = line
            col = pos - current_pos
            break
          end
          current_pos += line_len
        end

        # Error is beyond the last line
        if line_text.empty?
          if !lines.empty?
            line_num = lines.length
            line_text = lines[-1]
            col = line_text.length
          else
            line_text = text
            col = pos
          end
        end

        # Build the formatted error message
        parts = ["STRling Parse Error: #{message}", '']
        parts << "> #{line_num} | #{line_text}"
        parts << ">   | #{' ' * col}^"

        if hint
          parts << ''
          parts << "Hint: #{hint}"
        end

        parts.join("\n")
      end

      # Return the formatted error message.
      #
      # @return [String] The formatted error message
      def to_s
        format_error
      end

      # Backwards/JS-friendly alias for getting the formatted error string.
      #
      # @return [String] The formatted error message (same as `to_s`)
      def to_formatted_string
        format_error
      end

      # Convert the error to LSP Diagnostic format.
      #
      # Returns a hash compatible with the Language Server Protocol
      # Diagnostic specification, which can be serialized to JSON for
      # communication with LSP clients.
      #
      # @return [Hash] A hash containing:
      #   - range: The line/column range where the error occurred
      #   - severity: Error severity (1 = Error)
      #   - message: The error message with hint if available
      #   - source: "STRling"
      #   - code: A normalized error code derived from the message
      def to_lsp_diagnostic
        # Find the line and column containing the error
        lines = text.empty? ? [] : text.lines(chomp: true)
        current_pos = 0
        line_num = 0 # 0-indexed for LSP
        col = pos

        lines.each_with_index do |line, i|
          line_len = line.length + 1 # +1 for newline
          if current_pos + line_len > pos
            line_num = i
            col = pos - current_pos
            break
          end
          current_pos += line_len
        end

        # Error is beyond the last line
        if col == pos && !lines.empty?
          line_num = lines.length - 1
          col = lines[-1].length
        end

        # Build the diagnostic message
        diagnostic_message = message
        diagnostic_message += "\n\nHint: #{hint}" if hint

        # Create error code from message (normalize to snake_case)
        error_code = message.downcase
        [' ', "'", '"', '(', ')', '[', ']', '{', '}', '\\', '/'].each do |char|
          error_code = error_code.gsub(char, '_')
        end
        error_code = error_code.split('_').reject(&:empty?).join('_')

        {
          range: {
            start: { line: line_num, character: col },
            end: { line: line_num, character: col + 1 }
          },
          severity: 1, # 1 = Error, 2 = Warning, 3 = Information, 4 = Hint
          message: diagnostic_message,
          source: 'STRling',
          code: error_code
        }
      end
    end
  end
end
