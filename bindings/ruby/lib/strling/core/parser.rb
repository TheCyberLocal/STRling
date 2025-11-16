# frozen_string_literal: true

# STRling Parser - Recursive Descent Parser for STRling DSL
#
# This module implements a hand-rolled recursive-descent parser that transforms
# STRling pattern syntax into Abstract Syntax Tree (AST) nodes. The parser handles:
#   - Alternation and sequencing
#   - Character classes and ranges
#   - Quantifiers (greedy, lazy, possessive)
#   - Groups (capturing, non-capturing, named, atomic)
#   - Lookarounds (lookahead and lookbehind, positive and negative)
#   - Anchors and special escapes
#   - Extended/free-spacing mode with comments
#
# The parser produces AST nodes (defined in nodes.rb) that can be compiled
# to IR and ultimately emitted as target-specific regex patterns. It includes
# comprehensive error handling with position tracking for helpful diagnostics.

require_relative 'nodes'
require_relative 'errors'

module Strling
  module Core
    # Alias for backward compatibility
    ParseError = STRlingParseError

    # Cursor for tracking parser position and state
    class Cursor
      attr_accessor :text, :i, :extended_mode, :in_class

      def initialize(text, i = 0, extended_mode = false, in_class = 0)
        @text = text
        @i = i
        @extended_mode = extended_mode
        @in_class = in_class
      end

      def eof?
        @i >= @text.length
      end

      def peek(n = 0)
        j = @i + n
        j >= @text.length ? '' : @text[j]
      end

      def take
        return '' if eof?

        ch = @text[@i]
        @i += 1
        ch
      end

      def match(s)
        if @text[@i...(@i + s.length)] == s
          @i += s.length
          true
        else
          false
        end
      end

      def skip_ws_and_comments
        return if !@extended_mode || @in_class > 0

        # In free-spacing mode, ignore spaces/tabs/newlines and #-to-EOL comments
        until eof?
          ch = peek
          if " \t\r\n".include?(ch)
            @i += 1
            next
          end
          if ch == '#'
            # skip comment to end of line
            @i += 1 until eof? || "\r\n".include?(peek)
            next
          end
          break
        end
      end
    end

    # Main parser class
    class Parser
      attr_reader :flags, :src, :cur

      # Control character escapes mapping
      CONTROL_ESCAPES = {
        'n' => "\n",
        'r' => "\r",
        't' => "\t",
        'f' => "\f",
        'v' => "\v"
      }.freeze

      def initialize(text)
        # Store original text for error reporting
        @original_text = text
        # Extract directives first
        @flags, @src = parse_directives(text)
        @cur = Cursor.new(@src, 0, @flags.extended, 0)
        @cap_count = 0
        @cap_names = Set.new
      end

      # Main parsing entry point
      # Returns the root AST node
      def parse
        node = parse_alt
        @cur.skip_ws_and_comments
        unless @cur.eof?
          if @cur.peek == ')'
            raise STRlingParseError.new(
              "Unmatched ')'",
              @cur.i,
              text: @src,
              hint: "This ')' character does not have a matching opening '('. Did you mean to escape it with '\\)'?"
            )
          end
          if @cur.peek == '|'
            raise_error('Alternation lacks right-hand side', @cur.i)
          else
            raise_error('Unexpected trailing input', @cur.i)
          end
        end
        node
      end

      private

      def raise_error(message, pos)
        # TODO: Implement hint engine
        hint = nil # get_hint(message, @src, pos)
        raise STRlingParseError.new(message, pos, text: @src, hint: hint)
      end

      # Parse directives (%flags, etc.) from the start of the text
      def parse_directives(text)
        flags = Flags.new
        lines = text.lines
        pattern_lines = []
        in_pattern = false
        line_num = 0

        lines.each do |line|
          line_num += 1
          stripped = line.strip

          # Skip leading blank lines or comments
          if !in_pattern && (stripped.empty? || stripped.start_with?('#'))
            next
          end

          # Process %flags directive
          if !in_pattern && stripped.start_with?('%flags')
            idx = line.index('%flags')
            after = line[(idx + 7)..]
            # Extract flags
            letters = after.gsub(/[,\[\]\s]+/, ' ').strip.downcase
            valid_flags = Set.new(%w[i m s u x])

            letters.delete(' ').each_char do |ch|
              next if ch.empty?

              unless valid_flags.include?(ch)
                pos = lines[0...line_num - 1].join.length + idx
                raise STRlingParseError.new(
                  "Invalid flag '#{ch}'",
                  pos,
                  text: @original_text,
                  hint: nil
                )
              end
            end

            flags = Flags.from_letters(letters)
            # Check for pattern content on same line
            remainder = after.gsub(/[imsux,\[\]\s]+/, '')
            if !remainder.empty?
              in_pattern = true
              pattern_lines << line[(idx + 7 + after.index(remainder))..] if after.index(remainder)
            end
            next
          end

          # Skip other directives
          next if !in_pattern && stripped.start_with?('%')

          # Check for misplaced %flags
          if line.include?('%flags')
            pos = lines[0...line_num - 1].join.length + line.index('%flags')
            raise STRlingParseError.new(
              'Directive after pattern content',
              pos,
              text: @original_text,
              hint: nil
            )
          end

          # All other lines are pattern content
          in_pattern = true
          pattern_lines << line
        end

        pattern = pattern_lines.join
        [flags, pattern]
      end

      # Parse alternation: alt := seq ('|' seq)+ | seq
      def parse_alt
        @cur.skip_ws_and_comments
        raise_error('Alternation lacks left-hand side', @cur.i) if @cur.peek == '|'

        branches = [parse_seq]
        @cur.skip_ws_and_comments

        while @cur.peek == '|'
          pipe_pos = @cur.i
          @cur.take
          @cur.skip_ws_and_comments

          raise_error('Alternation lacks right-hand side', pipe_pos) if @cur.peek.empty?
          raise_error('Empty alternation branch', pipe_pos) if @cur.peek == '|'

          branches << parse_seq
          @cur.skip_ws_and_comments
        end

        branches.length == 1 ? branches[0] : Alt.new(branches)
      end

      # Parse sequence: seq := { term }
      def parse_seq
        parts = []
        prev_had_failed_quant = false

        loop do
          @cur.skip_ws_and_comments
          ch = @cur.peek

          # Invalid quantifier at start
          if !ch.empty? && '*+?{'.include?(ch) && parts.empty?
            raise_error("Invalid quantifier '#{ch}'", @cur.i)
          end

          # Stop parsing sequence
          break if ch.empty? || ')|'.include?(ch)

          # Parse atom
          atom = parse_atom

          # Parse quantifier if present
          quantified_atom, had_failed_quant = parse_quant_if_any(atom)

          # Coalesce adjacent literals (simplified logic)
          should_coalesce = quantified_atom.is_a?(Lit) &&
                            !parts.empty? &&
                            parts.last.is_a?(Lit) &&
                            !@cur.extended_mode &&
                            !prev_had_failed_quant

          if should_coalesce
            parts[-1] = Lit.new(parts.last.value + quantified_atom.value)
          else
            parts << quantified_atom
          end

          prev_had_failed_quant = had_failed_quant
        end

        parts.length == 1 ? parts[0] : Seq.new(parts)
      end

      # Parse individual atom (literal, group, class, anchor, etc.)
      def parse_atom
        ch = @cur.peek

        case ch
        when '('
          parse_group
        when '['
          parse_char_class
        when '\\'
          parse_escape
        when '.'
          @cur.take
          Dot.new
        when '^'
          @cur.take
          Anchor.new('Start')
        when '$'
          @cur.take
          Anchor.new('End')
        when '*', '+', '?', '{', ')', '|'
          raise_error("Unexpected '#{ch}'", @cur.i)
        else
          parse_literal
        end
      end

      # Parse group: (pattern) or (?:pattern) or (?<name>pattern) etc.
      def parse_group
        raise_error("Expected '('", @cur.i) unless @cur.take == '('

        # Simplified group parsing
        # TODO: Handle all group types (?:...), (?<name>...), (?=...), etc.
        
        # Check for special group syntax
        if @cur.peek == '?'
          @cur.take
          case @cur.peek
          when ':'
            @cur.take
            body = parse_alt
            raise_error("Unclosed group", @cur.i) unless @cur.take == ')'
            return Group.new(false, body)
          when '='
            @cur.take
            body = parse_alt
            raise_error("Unclosed lookahead", @cur.i) unless @cur.take == ')'
            return Look.new('Ahead', false, body)
          when '!'
            @cur.take
            body = parse_alt
            raise_error("Unclosed lookahead", @cur.i) unless @cur.take == ')'
            return Look.new('Ahead', true, body)
          when '<'
            @cur.take
            if @cur.peek == '='
              @cur.take
              body = parse_alt
              raise_error("Unclosed lookbehind", @cur.i) unless @cur.take == ')'
              return Look.new('Behind', false, body)
            elsif @cur.peek == '!'
              @cur.take
              body = parse_alt
              raise_error("Unclosed lookbehind", @cur.i) unless @cur.take == ')'
              return Look.new('Behind', true, body)
            else
              # Named capture: (?<name>...)
              name = ''
              until @cur.peek == '>' || @cur.eof?
                name += @cur.take
              end
              raise_error("Unclosed named group", @cur.i) if @cur.eof?
              @cur.take # consume '>'
              @cap_count += 1
              @cap_names.add(name)
              body = parse_alt
              raise_error("Unclosed group", @cur.i) unless @cur.take == ')'
              return Group.new(true, body, name: name)
            end
          when '>'
            # Atomic group
            @cur.take
            body = parse_alt
            raise_error("Unclosed atomic group", @cur.i) unless @cur.take == ')'
            return Group.new(false, body, atomic: true)
          else
            raise_error("Unknown group syntax", @cur.i - 1)
          end
        end

        # Capturing group
        @cap_count += 1
        body = parse_alt
        raise_error("Unclosed group", @cur.i) unless @cur.take == ')'
        Group.new(true, body)
      end

      # Parse character class: [abc] or [^abc] or [a-z]
      def parse_char_class
        raise_error("Expected '['", @cur.i) unless @cur.take == '['

        @cur.in_class += 1
        negated = false

        if @cur.peek == '^'
          negated = true
          @cur.take
        end

        items = []

        # Simplified character class parsing
        # TODO: Handle ranges, escapes, nested classes
        until @cur.peek == ']' || @cur.eof?
          if @cur.peek == '\\'
            @cur.take
            type_ch = @cur.take
            case type_ch
            when 'd', 'D', 'w', 'W', 's', 'S'
              items << ClassEscape.new(type_ch)
            when 'b'
              # \b in class means backspace
              items << ClassLiteral.new("\b")
            else
              # Escaped literal
              items << ClassLiteral.new(type_ch)
            end
          elsif @cur.peek(1) == '-' && @cur.peek(2) != ']' && !@cur.eof?
            # Range
            from_ch = @cur.take
            @cur.take # consume '-'
            to_ch = @cur.take
            items << ClassRange.new(from_ch, to_ch)
          else
            items << ClassLiteral.new(@cur.take)
          end
        end

        raise_error("Unclosed character class", @cur.i) if @cur.eof?

        @cur.take # consume ']'
        @cur.in_class -= 1

        CharClass.new(negated, items)
      end

      # Parse escape sequence: \d, \w, \b, \123, \x41, etc.
      def parse_escape
        raise_error("Expected '\\'", @cur.i) unless @cur.take == '\\'

        ch = @cur.take
        raise_error("Unexpected end after '\\'", @cur.i) if ch.empty?

        case ch
        when 'd', 'D', 'w', 'W', 's', 'S'
          # Shorthand character classes
          CharClass.new(
            ch == ch.upcase,
            [ClassEscape.new(ch.downcase)]
          )
        when 'b'
          Anchor.new('WordBoundary')
        when 'B'
          Anchor.new('NotWordBoundary')
        when 'A'
          Anchor.new('AbsoluteStart')
        when 'Z'
          Anchor.new('EndBeforeFinalNewline')
        when 'n', 'r', 't', 'f', 'v'
          # Control escapes
          Lit.new(CONTROL_ESCAPES[ch])
        when '0'..'9'
          # Backreference
          num = ch
          while @cur.peek =~ /[0-9]/ && !@cur.eof?
            num += @cur.take
          end
          Backref.new(by_index: num.to_i)
        else
          # Handle other escapes or literal
          if 'nrtfv'.include?(ch)
            Lit.new(CONTROL_ESCAPES[ch])
          elsif '^$.*+?{}[]()|\\/'.include?(ch)
            # Escaped metacharacter
            Lit.new(ch)
          else
            # Unknown escape - raise error
            raise_error("Unknown escape sequence \\#{ch}", @cur.i - 2)
          end
        end
      end

      # Parse literal character(s)
      def parse_literal
        value = ''
        loop do
          ch = @cur.peek
          # Stop at metacharacters or end
          break if ch.empty? || '\\[](){}.*+?|^$'.include?(ch)

          value += @cur.take
          # Only take one character at a time in normal mode
          break unless @cur.extended_mode
        end

        value.empty? ? raise_error('Empty literal', @cur.i) : Lit.new(value)
      end

      # Parse quantifier if present
      def parse_quant_if_any(child)
        @cur.skip_ws_and_comments
        ch = @cur.peek
        had_failed_quant = false

        # Check if child can be quantified
        # Note: Must check ch is not empty first, as ''.include?('') is true in Ruby
        if !ch.empty? && '*+?{'.include?(ch)
          if child.is_a?(Anchor)
            raise_error('Cannot quantify anchor', @cur.i)
          end

          min = 0
          max = 'Inf'

          case ch
          when '*'
            @cur.take
            min = 0
            max = 'Inf'
          when '+'
            @cur.take
            min = 1
            max = 'Inf'
          when '?'
            @cur.take
            min = 0
            max = 1
          when '{'
            # Parse {m,n} quantifier
            # Simplified - just consume for now
            # TODO: Implement full brace quantifier parsing
            return [child, false]
          end

          # Check for lazy (?) or possessive (+) modifier
          mode = 'Greedy'
          if @cur.peek == '?'
            @cur.take
            mode = 'Lazy'
          elsif @cur.peek == '+'
            @cur.take
            mode = 'Possessive'
          end

          return [Quant.new(child, min, max, mode), had_failed_quant]
        end

        [child, had_failed_quant]
      end
    end

    # Module-level parse function for convenience
    def self.parse(text)
      parser = Parser.new(text)
      [parser.flags, parser.parse]
    end
  end
end
