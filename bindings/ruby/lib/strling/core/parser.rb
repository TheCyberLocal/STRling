# frozen_string_literal: true

# STRling Parser - Recursive Descent Parser for STRling DSL

require 'set'
require_relative 'nodes'
require_relative 'errors'
require_relative 'hint_engine'

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

        until eof?
          ch = peek
          if " \t\r\n".include?(ch)
            @i += 1
            next
          end
          if ch == '#'
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

      CONTROL_ESCAPES = {
        'n' => "\n",
        'r' => "\r",
        't' => "\t",
        'f' => "\f",
        'v' => "\v"
      }.freeze

      def initialize(text = nil)
        return unless text

        @original_text = text
        @flags, @src = parse_directives(text)
        @cur = Cursor.new(@src, 0, @flags.extended, 0)
        @cap_count = 0
        @cap_names = Set.new
      end

      def parse(text = nil)
        if text
          @original_text = text
          @flags, @src = parse_directives(text)
          @cur = Cursor.new(@src, 0, @flags.extended, 0)
          @cap_count = 0
          @cap_names = Set.new
        end
        node = parse_alt
        @cur.skip_ws_and_comments
        unless @cur.eof?
          if @cur.peek == ')'
            raise_error("Unmatched ')'", @cur.i)
          elsif @cur.peek == '|'
            raise_error('Alternation lacks right-hand side', @cur.i)
          else
            raise_error('Unexpected trailing input', @cur.i)
          end
        end
        [@flags, node]
      end

      private

      def raise_error(message, pos)
        hint = Strling::Core.get_hint(message, @src, pos)
        raise STRlingParseError.new(message, pos, text: @src, hint: hint)
      end

      def raise_error_with_text(message, pos, text)
        hint = Strling::Core.get_hint(message, text, pos)
        raise STRlingParseError.new(message, pos, text: text, hint: hint)
      end

      def parse_directives(text)
        flags = Flags.new
        lines = text.lines
        pattern_lines = []
        in_pattern = false

        lines.each do |line|
          stripped = line.strip

          next if !in_pattern && (stripped.empty? || stripped.start_with?('#'))

          if stripped.start_with?('%')
            if in_pattern
              raise_error_with_text('Directive after pattern', 0, text)
            end

            unless stripped.start_with?('%flags')
              raise_error_with_text('Malformed directive', 0, text)
            end

            idx = line.index('%flags')
            after = line[(idx + 6)..]
            valid_flags = Set.new(%w[i m s u x])
            allowed = Set.new(" ,\t[]imsuxIMSUX".chars)

            j = 0
            after.each_char.with_index do |c, k|
              if allowed.include?(c)
                j = k + 1
              else
                break
              end
            end

            flags_token = after[0...j]
            remainder = after[j..]

            letters = flags_token.gsub(/[^a-zA-Z]/, '').downcase

            letters.each_char do |ch|
              unless valid_flags.include?(ch)
                raise_error_with_text("Invalid flag '#{ch}'", 0, text)
              end
            end

            if !letters.empty?
              flags = Flags.from_letters(letters)
            elsif remainder && !remainder.strip.empty?
              ch = remainder.strip[0]
              raise_error_with_text("Invalid flag '#{ch}'", 0, text)
            end

            if remainder && !remainder.strip.empty?
              pattern_lines << remainder
              in_pattern = true
            end
            next
          end

          if line.include?('%flags')
            raise_error_with_text('Directive after pattern', 0, text)
          end

          in_pattern = true
          pattern_lines << line
        end

        pattern = pattern_lines.join
        [flags, pattern]
      end

      def parse_alt
        @cur.skip_ws_and_comments

        if @cur.peek == '|'
          raise_error('Alternation lacks left-hand side', @cur.i)
        end

        branches = [parse_seq]
        @cur.skip_ws_and_comments

        while @cur.peek == '|'
          pipe_pos = @cur.i
          @cur.take
          @cur.skip_ws_and_comments

          if @cur.eof?
            raise_error('Alternation lacks right-hand side', pipe_pos)
          end
          if @cur.peek == '|'
            raise_error('Empty alternation', pipe_pos)
          end
          if @cur.peek == ')'
            raise_error('Alternation lacks right-hand side', pipe_pos)
          end

          branches << parse_seq
          @cur.skip_ws_and_comments
        end

        branches.length == 1 ? branches[0] : Alt.new(branches)
      end

      def parse_seq
        parts = []

        loop do
          @cur.skip_ws_and_comments
          ch = @cur.peek
          break if ch.empty? || ')|'.include?(ch)

          atom = parse_atom
          @cur.skip_ws_and_comments

          quantified_atom = parse_quant_if_any(atom)
          parts << quantified_atom
        end

        if parts.empty?
          Lit.new('')
        elsif parts.length == 1
          parts[0]
        else
          Seq.new(parts)
        end
      end

      def parse_atom
        ch = @cur.peek
        raise_error('Unexpected end of input', @cur.i) if ch.empty?

        case ch
        when '.'
          @cur.take
          Dot.new
        when '^'
          @cur.take
          Anchor.new('Start')
        when '$'
          @cur.take
          Anchor.new('End')
        when '('
          parse_group
        when '['
          parse_char_class
        when '\\'
          parse_escape
        when '*', '+', '?'
          raise_error("Invalid quantifier '#{ch}'", @cur.i)
        when '{'
          # Check for invalid brace content
          save = @cur.i
          look = ''
          j = @cur.i + 1
          while j < @cur.text.length && @cur.text[j] != '}'
            look += @cur.text[j]
            j += 1
          end
          if j < @cur.text.length && !look.empty? && look !~ /^\d+(,\d*)?$/
            raise_error('Brace quantifier: Invalid brace quantifier content', save)
          end
          raise_error("Invalid quantifier '#{ch}'", @cur.i)
        else
          parse_literal
        end
      end

      def parse_literal
        ch = @cur.take
        raise_error('Unexpected end of input', @cur.i) if ch.empty?
        Lit.new(ch)
      end

      def parse_escape
        start_pos = @cur.i
        @cur.take # consume backslash
        raise_error('Incomplete escape sequence', start_pos) if @cur.eof?

        ch = @cur.take

        case ch
        when 'b'
          Anchor.new('WordBoundary')
        when 'B'
          Anchor.new('NotWordBoundary')
        when 'A'
          Anchor.new('AbsoluteStart')
        when 'Z'
          Anchor.new('EndBeforeFinalNewline')
        # NOTE: lowercase \z is intentionally NOT an anchor

        when 'd', 'D', 'w', 'W', 's', 'S'
          CharClass.new(false, [ClassEscape.new(ch)])

        when 'n', 'r', 't', 'f', 'v'
          Lit.new(CONTROL_ESCAPES[ch])

        when '0'
          # Check for forbidden octal - \0 followed by more digits
          if @cur.peek =~ /[0-9]/
            raise_error("Forbidden octal escape \\0#{@cur.peek}", start_pos)
          end
          Lit.new("\x00")

        when '1', '2', '3', '4', '5', '6', '7', '8', '9'
          num_str = ch
          while @cur.peek =~ /[0-9]/ && !@cur.eof?
            num_str += @cur.take
          end
          num = num_str.to_i
          if num > @cap_count
            raise_error("Backreference to undefined group \\#{num}", start_pos)
          end
          Backref.new(by_index: num)

        when 'k'
          raise_error("Expected '<' after \\k", @cur.i) unless @cur.peek == '<'
          @cur.take # consume <
          name = ''
          until @cur.peek == '>' || @cur.eof?
            name += @cur.take
          end
          raise_error('Unterminated named backref', @cur.i) if @cur.eof?
          @cur.take # consume >
          unless @cap_names.include?(name)
            raise_error("Backreference to undefined group <#{name}>", start_pos)
          end
          Backref.new(by_name: name)

        when 'x'
          parse_hex_escape(start_pos)

        when 'u'
          parse_unicode_escape('u', start_pos)

        when 'U'
          parse_unicode_escape('U', start_pos)

        when 'p', 'P'
          raise_error("Expected { after \\p/\\P", start_pos) unless @cur.peek == '{'
          @cur.take # consume {
          prop = ''
          until @cur.peek == '}' || @cur.eof?
            prop += @cur.take
          end
          raise_error("Unterminated \\p{...}", start_pos) if @cur.eof?
          @cur.take # consume }
          CharClass.new(false, [ClassEscape.new(ch, property: prop)])

        else
          if ch =~ /[a-zA-Z0-9]/
            raise_error("Unknown escape sequence \\#{ch}", start_pos)
          end
          Lit.new(ch)
        end
      end

      def parse_hex_escape(start_pos)
        if @cur.peek == '{'
          @cur.take # consume {
          hex = ''
          while @cur.peek =~ /[0-9a-fA-F]/ && !@cur.eof?
            hex += @cur.take
          end
          unless @cur.match('}')
            raise_error("Unterminated \\x{...}", start_pos)
          end
          cp = hex.to_i(16)
          return Lit.new([cp].pack('U'))
        end

        hex = ''
        2.times { hex += @cur.take unless @cur.eof? }
        if hex.length != 2 || hex !~ /^[0-9a-fA-F]{2}$/
          raise_error("Invalid \\xHH escape", start_pos)
        end
        cp = hex.to_i(16)
        Lit.new([cp].pack('U'))
      end

      def parse_unicode_escape(tp, start_pos)
        if tp == 'u' && @cur.peek == '{'
          @cur.take
          hex = ''
          while @cur.peek =~ /[0-9a-fA-F]/ && !@cur.eof?
            hex += @cur.take
          end
          unless @cur.match('}')
            raise_error("Unterminated \\u{...}", start_pos)
          end
          cp = hex.to_i(16)
          return Lit.new([cp].pack('U'))
        end

        if tp == 'u'
          hex = ''
          4.times { hex += @cur.take unless @cur.eof? }
          if hex.length != 4 || hex !~ /^[0-9a-fA-F]{4}$/
            raise_error("Invalid \\uHHHH escape", start_pos)
          end
          cp = hex.to_i(16)
          return Lit.new([cp].pack('U'))
        end

        if tp == 'U'
          hex = ''
          8.times { hex += @cur.take unless @cur.eof? }
          if hex.length != 8 || hex !~ /^[0-9a-fA-F]{8}$/
            raise_error("Invalid \\UHHHHHHHH escape", start_pos)
          end
          cp = hex.to_i(16)
          return Lit.new([cp].pack('U'))
        end

        raise_error('Invalid unicode escape', start_pos)
      end

      def parse_group
        start_pos = @cur.i
        @cur.take # consume '('

        if @cur.peek == '?'
          @cur.take

          case @cur.peek
          when ':'
            @cur.take
            body = parse_alt
            expect_char(')', 'Unterminated group')
            return Group.new(false, body)
          when '='
            @cur.take
            body = parse_alt
            expect_char(')', 'Unterminated lookahead')
            return Look.new('Ahead', false, body)
          when '!'
            @cur.take
            body = parse_alt
            expect_char(')', 'Unterminated lookahead')
            return Look.new('Ahead', true, body)
          when '<'
            @cur.take
            if @cur.peek == '='
              @cur.take
              body = parse_alt
              expect_char(')', 'Unterminated lookbehind')
              return Look.new('Behind', false, body)
            elsif @cur.peek == '!'
              @cur.take
              body = parse_alt
              expect_char(')', 'Unterminated lookbehind')
              return Look.new('Behind', true, body)
            else
              # Named group
              name = ''
              until @cur.peek == '>' || @cur.eof?
                name += @cur.take
              end
              raise_error('Unterminated group name', @cur.i) if @cur.eof?
              @cur.take # consume >

              unless name =~ /^[a-zA-Z_][a-zA-Z0-9_]*$/
                raise_error("Invalid group name '#{name}'", start_pos)
              end

              if @cap_names.include?(name)
                raise_error("Duplicate group name '#{name}'", start_pos)
              end

              @cap_names.add(name)
              @cap_count += 1
              body = parse_alt
              expect_char(')', 'Unterminated group')
              return Group.new(true, body, name: name)
            end
          when '>'
            @cur.take
            body = parse_alt
            expect_char(')', 'Unterminated atomic group')
            return Group.new(false, body, atomic: true)
          else
            # Check for inline modifiers like (?i), (?im)
            save = @cur.i
            scan = ''
            j = save
            while j < @cur.text.length && 'imsux'.include?(@cur.text[j])
              scan += @cur.text[j]
              j += 1
            end
            if !scan.empty? && j < @cur.text.length && @cur.text[j] == ')'
              raise_error("Inline modifiers like (?#{scan}...) are not supported", start_pos)
            end
            raise_error("Unknown group modifier: ?#{@cur.peek}", @cur.i - 1)
          end
        end

        # Regular capturing group
        @cap_count += 1
        body = parse_alt
        expect_char(')', 'Unterminated group')
        Group.new(true, body)
      end

      def parse_char_class
        start_pos = @cur.i
        @cur.take # consume '['
        @cur.in_class += 1

        negated = false
        if @cur.peek == '^'
          negated = true
          @cur.take
        end

        # Empty/unterminated char class: [] or [^]
        if @cur.peek == ']'
          @cur.in_class -= 1
          raise_error('Unterminated character class', start_pos)
        end

        items = []

        loop do
          if @cur.eof?
            @cur.in_class -= 1
            raise_error('Unterminated character class', start_pos)
          end

          break if @cur.peek == ']'

          item = parse_class_item

          # Check for range
          if @cur.peek == '-' && @cur.peek(1) != ']' && !@cur.eof?
            if item.is_a?(ClassLiteral)
              from_ch = item.ch
              @cur.take # consume -

              if @cur.eof? || @cur.peek == ']'
                items << item
                items << ClassLiteral.new('-')
                next
              end

              to_item = parse_class_item
              if to_item.is_a?(ClassLiteral)
                to_ch = to_item.ch
                if to_ch < from_ch
                  @cur.in_class -= 1
                  raise_error('Invalid character range', start_pos)
                end
                items << ClassRange.new(from_ch, to_ch)
                next
              else
                items << item
                items << ClassLiteral.new('-')
                items << to_item
                next
              end
            end
          end

          items << item
        end

        @cur.take # consume ']'
        @cur.in_class -= 1

        CharClass.new(negated, items)
      end

      def parse_class_item
        if @cur.peek == '\\'
          start_pos = @cur.i
          @cur.take # consume backslash
          raise_error('Incomplete escape sequence', start_pos) if @cur.eof?

          ch = @cur.take

          case ch
          when 'd', 'D', 'w', 'W', 's', 'S'
            ClassEscape.new(ch)
          when 'b'
            ClassLiteral.new("\b")
          when '0'
            ClassLiteral.new("\x00")
          when 'n'
            ClassLiteral.new("\n")
          when 'r'
            ClassLiteral.new("\r")
          when 't'
            ClassLiteral.new("\t")
          when 'f'
            ClassLiteral.new("\f")
          when 'v'
            ClassLiteral.new("\v")
          when 'x'
            if @cur.peek == '{'
              @cur.take
              hex = ''
              while @cur.peek =~ /[0-9a-fA-F]/ && !@cur.eof?
                hex += @cur.take
              end
              unless @cur.match('}')
                raise_error("Unterminated \\x{...}", start_pos)
              end
              cp = hex.to_i(16)
              ClassLiteral.new([cp].pack('U'))
            else
              hex = ''
              2.times { hex += @cur.take unless @cur.eof? }
              if hex.length != 2 || hex !~ /^[0-9a-fA-F]{2}$/
                raise_error("Invalid \\xHH escape", start_pos)
              end
              ClassLiteral.new([hex.to_i(16)].pack('U'))
            end
          when 'u'
            if @cur.peek == '{'
              @cur.take
              hex = ''
              while @cur.peek =~ /[0-9a-fA-F]/ && !@cur.eof?
                hex += @cur.take
              end
              unless @cur.match('}')
                raise_error("Unterminated \\u{...}", start_pos)
              end
              cp = hex.to_i(16)
              ClassLiteral.new([cp].pack('U'))
            else
              hex = ''
              4.times { hex += @cur.take unless @cur.eof? }
              if hex.length != 4 || hex !~ /^[0-9a-fA-F]{4}$/
                raise_error("Invalid \\uHHHH escape", start_pos)
              end
              ClassLiteral.new([hex.to_i(16)].pack('U'))
            end
          when 'p', 'P'
            raise_error("Expected { after \\p/\\P", start_pos) unless @cur.peek == '{'
            @cur.take
            prop = ''
            until @cur.peek == '}' || @cur.eof?
              prop += @cur.take
            end
            raise_error("Unterminated \\p{...}", start_pos) if @cur.eof?
            @cur.take
            ClassEscape.new(ch, property: prop)
          else
            if ch =~ /[a-zA-Z0-9]/
              raise_error("Unknown escape sequence \\#{ch}", start_pos)
            end
            ClassLiteral.new(ch)
          end
        else
          ClassLiteral.new(@cur.take)
        end
      end

      def parse_quant_if_any(child)
        @cur.skip_ws_and_comments
        ch = @cur.peek
        return child if ch.empty? || !'*+?{'.include?(ch)

        start_pos = @cur.i

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
          save = @cur.i
          @cur.take # consume {

          # Look ahead for invalid brace content
          look = ''
          j = @cur.i
          while j < @cur.text.length && @cur.text[j] != '}'
            look += @cur.text[j]
            j += 1
          end

          if j < @cur.text.length && !look.empty? && look !~ /^\d+(,\d*)?$/
            raise_error('Brace quantifier: Invalid brace quantifier content', save)
          end

          min_str = ''
          while @cur.peek =~ /\d/
            min_str += @cur.take
          end

          if min_str.empty?
            raise_error('Expected number in quantifier', @cur.i)
          end
          min = min_str.to_i

          if @cur.match(',')
            max_str = ''
            while @cur.peek =~ /\d/
              max_str += @cur.take
            end
            max = max_str.empty? ? 'Inf' : max_str.to_i
          else
            max = min
          end

          unless @cur.match('}')
            raise_error('Incomplete quantifier', @cur.i)
          end

          if max != 'Inf' && min > max
            raise_error('Invalid quantifier range', save)
          end
        else
          return child
        end

        # Cannot quantify anchor
        if child.is_a?(Anchor)
          raise_error('Cannot quantify anchor', start_pos)
        end

        mode = 'Greedy'
        if @cur.peek == '?'
          @cur.take
          mode = 'Lazy'
        elsif @cur.peek == '+'
          @cur.take
          mode = 'Possessive'
        end

        Quant.new(child, min, max, mode)
      end

      def expect_char(expected, error_msg)
        ch = @cur.take
        unless ch == expected
          raise_error(error_msg, @cur.i - (ch.empty? ? 0 : 1))
        end
      end
    end

    # Module-level parse function for convenience
    def self.parse(text)
      parser = Parser.new(text)
      parser.parse
    end
  end
end
