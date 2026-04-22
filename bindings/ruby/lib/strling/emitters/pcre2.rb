# frozen_string_literal: true

# STRling PCRE2 Emitter - IR to PCRE2 Regex Translation
#
# This module transforms Intermediate Representation (IR) nodes into
# PCRE2-compatible regex pattern strings. It handles:
#   - Proper escaping of metacharacters
#   - Flag modifiers
#   - Character class syntax
#   - Quantifier notation
#   - Group and lookaround syntax

require_relative '../core/ir'
require_relative '../core/nodes'
require_relative '../core/diagnostics'
require_relative '../ir'

module Strling
  module Emitters
    # PCRE2 emitter class
    class PCRE2
      # Default upper bound on IR nesting depth before the emitter aborts.
      # Mirrors the SSOT in the TypeScript reference.
      DEFAULT_MAX_DEPTH = 250

      REDOS_MESSAGE = 'The pattern contains overlapping alternations or nested unbounded quantifiers ' \
        '(e.g., (a+)+). This can lead to catastrophic backtracking and exponential CPU spikes. ' \
        'Consider using possessive quantifiers (++ or *+) or atomic groups to guarantee execution safety.'

      # Emit IR as a PCRE2 regex pattern.
      #
      # @param ir_root [IROp] The root IR node
      # @param flags [Flags] The pattern flags
      # @return [String] The PCRE2 regex pattern
      def self.emit(ir_root, flags)
        emit_with_diagnostics(ir_root, flags).pattern
      end

      # Emit IR as a PCRE2 pattern AND surface any non-fatal diagnostics
      # collected during emission. Pass `max_depth <= 0` to use
      # {DEFAULT_MAX_DEPTH}.
      #
      # @param ir_root [IROp] The root IR node
      # @param flags [Flags] The pattern flags
      # @param max_depth [Integer] Override for {DEFAULT_MAX_DEPTH}
      # @return [Strling::Core::CompileResult]
      def self.emit_with_diagnostics(ir_root, flags, max_depth = 0)
        emitter = new(flags, max_depth)
        body = emitter.emit_node(ir_root)
        flag_str = build_flags(flags)
        pattern = flag_str.empty? ? body : "(?#{flag_str})#{body}"
        Strling::Core::CompileResult.new(pattern, emitter.warnings)
      end

      attr_reader :warnings

      def initialize(flags, max_depth = 0)
        @flags = flags
        @depth = 0
        @max_depth = max_depth.positive? ? max_depth : DEFAULT_MAX_DEPTH
        @in_lookbehind = false
        @warnings = []
      end

      # --- Safety predicates -------------------------------------------------

      def unbounded_quant?(node)
        node.max == 'Inf'
      end

      def variable_length_quant?(node)
        node.min != node.max
      end

      # Mirror of `_isFixedLengthBody` in the TS SSOT. Returns true when
      # the node consumes a fixed number of characters and is therefore
      # safe inside a PCRE2 lookbehind.
      def fixed_length_body?(node)
        case node
        when Strling::Core::IRQuant, Strling::IR::Quant
          !variable_length_quant?(node) && fixed_length_body?(node.child)
        when Strling::Core::IRSeq, Strling::IR::Seq
          node.parts.all? { |p| fixed_length_body?(p) }
        when Strling::Core::IRAlt, Strling::IR::Alt
          node.branches.all? { |b| fixed_length_body?(b) }
        when Strling::Core::IRGroup, Strling::IR::Group
          fixed_length_body?(node.body)
        when Strling::Core::IRLook, Strling::IR::Look
          true
        else
          true
        end
      end

      # Mirror of `_hasNestedUnboundedQuant`: only single-child wrappers
      # are pierced; an Alternation propagates the search to every branch.
      def nested_unbounded_quant?(node)
        case node
        when Strling::Core::IRQuant, Strling::IR::Quant
          unbounded_quant?(node)
        when Strling::Core::IRGroup, Strling::IR::Group
          nested_unbounded_quant?(node.body)
        when Strling::Core::IRSeq, Strling::IR::Seq
          node.parts.length == 1 && nested_unbounded_quant?(node.parts[0])
        when Strling::Core::IRAlt, Strling::IR::Alt
          node.branches.any? { |b| nested_unbounded_quant?(b) }
        else
          false
        end
      end

      def push_redos_warning
        return if @warnings.any? { |w| w.code == 'REDOS_RISK' }
        @warnings << Strling::Core::STRlingWarning.new('REDOS_RISK', REDOS_MESSAGE)
      end

      # Emit a single IR node
      #
      # @param node [IROp] The IR node to emit
      # @return [String] The PCRE2 pattern fragment
      def emit_node(node)
        @depth += 1
        if @depth > @max_depth
          raise Strling::Core::STRlingCompilationError.new(
            "Maximum AST depth exceeded (limit: #{@max_depth}). " \
            'This pattern is too deeply nested and risks host stack ' \
            'exhaustion during emission. Refactor the pattern to reduce ' \
            'nesting, or flatten capturing groups where possible.',
            'MAX_DEPTH'
          )
        end

        result = case node
        when Strling::Core::IRAlt, Strling::IR::Alt
          # (branch1|branch2|...)
          branches = node.branches.map { |b| emit_node(b) }
          branches.length == 1 ? branches[0] : "(#{branches.join('|')})"
        when Strling::Core::IRSeq, Strling::IR::Seq
          # Concatenate parts
          node.parts.map { |p| emit_node(p) }.join
        when Strling::Core::IRLit, Strling::IR::Lit
          # Escape metacharacters
          escape_literal(node.value)
        when Strling::Core::IRDot, Strling::IR::Dot
          '.'
        when Strling::Core::IRAnchor, Strling::IR::Anchor
          emit_anchor(node.at)
        when Strling::Core::IRCharClass, Strling::IR::CharClass
          emit_char_class(node)
        when Strling::Core::IRQuant, Strling::IR::Quant
          emit_quantifier(node)
        when Strling::Core::IRGroup, Strling::IR::Group
          emit_group(node)
        when Strling::Core::IRBackref
          emit_backref(node)
        when Strling::IR::BackRef
          emit_backref(node)
        when Strling::Core::IRLook, Strling::IR::Look
          emit_lookaround(node)
        when Strling::IR::Esc
          emit_escape(node)
        else
          raise "Unknown IR node type: #{node.class}"
        end
        result
      ensure
        @depth -= 1
      end

      private

      # Build flag string from Flags object
      def self.build_flags(flags)
        str = ''
        str += 'i' if flags.ignore_case
        str += 'm' if flags.multiline
        str += 's' if flags.dot_all
        str += 'u' if flags.unicode
        str += 'x' if flags.extended
        str
      end

      # Escape a literal string for PCRE2
      def escape_literal(str)
        str.chars.map do |ch|
          case ch
          when '^', '$', '.', '*', '+', '?', '{', '}', '[', ']', '(', ')', '|', '\\'
            "\\#{ch}"
          else
            ch
          end
        end.join
      end

      # Emit an anchor
      def emit_anchor(at)
        case at
        when 'Start'
          '^'
        when 'End'
          '$'
        when 'WordBoundary'
          '\\b'
        when 'NotWordBoundary'
          '\\B'
        when 'AbsoluteStart'
          '\\A'
        when 'EndBeforeFinalNewline'
          '\\Z'
        when 'AbsoluteEnd'
          '\\z'
        else
          raise "Unknown anchor type: #{at}"
        end
      end

      # Emit a character class
      def emit_char_class(node)
        items_str = node.items.map { |item| emit_class_item(item) }.join
        node.negated ? "[^#{items_str}]" : "[#{items_str}]"
      end

      # Emit a character class item
      def emit_class_item(item)
        case item
        when Strling::Core::IRClassRange
          "#{item.from_ch}-#{item.to_ch}"
        when Strling::IR::Range
          "#{item.from}-#{item.to}"
        when Strling::Core::IRClassLiteral
          emit_class_literal(item.ch)
        when Strling::IR::Char
          emit_class_literal(item.char)
        when Strling::Core::IRClassEscape
          emit_escape(item)
        when Strling::IR::Esc
          emit_escape(item)
        else
          raise "Unknown class item type: #{item.class}"
        end
      end

      def emit_class_literal(ch)
        case ch
        when ']', '\\', '^', '-'
          "\\#{ch}"
        else
          ch
        end
      end

      def emit_escape(item)
        if %w[p P].include?(item.type)
          "\\#{item.type}{#{item.property}}"
        else
          "\\#{item.type}"
        end
      end

      # Emit a quantifier
      def emit_quantifier(node)
        # ReDoS guard: only flag when the *outer* quantifier is itself
        # unbounded (e.g. `(a+)+`). A bounded outer like `(a+){0,3}`
        # cannot produce exponential backtracking on its own.
        if unbounded_quant?(node) && nested_unbounded_quant?(node.child)
          push_redos_warning
        end
        child_str = emit_node(node.child)
        
        # Determine quantifier syntax
        quant_str = if node.min == 0 && node.max == 'Inf'
                      '*'
                    elsif node.min == 1 && node.max == 'Inf'
                      '+'
                    elsif node.min == 0 && node.max == 1
                      '?'
                    elsif node.max == 'Inf'
                      "{#{node.min},}"
                    elsif node.min == node.max
                      "{#{node.min}}"
                    else
                      "{#{node.min},#{node.max}}"
                    end

        # Add lazy or possessive modifier
        modifier = case node.mode
                   when 'Lazy'
                     '?'
                   when 'Possessive'
                     '+'
                   else
                     ''
                   end

        "#{child_str}#{quant_str}#{modifier}"
      end

      # Emit a group
      def emit_group(node)
        body_str = emit_node(node.body)
        
        if node.atomic
          "(?>#{body_str})"
        elsif !node.capturing
          "(?:#{body_str})"
        elsif node.name
          "(?<#{node.name}>#{body_str})"
        else
          "(#{body_str})"
        end
      end

      # Emit a backreference
      def emit_backref(node)
        if node.by_name
          "\\k<#{node.by_name}>"
        elsif node.by_index
          "\\#{node.by_index}"
        else
          raise 'Backref must specify either by_index or by_name'
        end
      end

      # Emit a lookaround
      def emit_lookaround(node)
        # Variable-length lookbehind guard: PCRE2 mandates a fixed-width
        # lookbehind body. Detect the violation here so the user sees a
        # Signpost-pattern error rather than an opaque PCRE2 compile
        # failure leaking from the runtime.
        if node.dir == 'Behind' && !fixed_length_body?(node.body)
          raise Strling::Core::STRlingCompilationError.new(
            'PCRE2 does not support variable-length lookbehinds. The ' \
            'lookbehind body contains a quantifier that makes its length ' \
            'unpredictable. Rewrite the assertion using a fixed-length ' \
            'range (e.g. `{1,8}` instead of `+`), or restructure the ' \
            'pattern using a Lookahead, or extract the quantified portion ' \
            'outside the assertion.',
            'VLB_NOT_SUPPORTED'
          )
        end

        was_in_lb = @in_lookbehind
        @in_lookbehind = true if node.dir == 'Behind'
        body_str = emit_node(node.body)
        @in_lookbehind = was_in_lb

        if node.dir == 'Ahead'
          node.neg ? "(?!#{body_str})" : "(?=#{body_str})"
        else # Behind
          node.neg ? "(?<!#{body_str})" : "(?<=#{body_str})"
        end
      end
    end

    # Module-level emit function
    def self.emit_pcre2(ir_root, flags)
      PCRE2.emit(ir_root, flags)
    end

    # Alias for backward compatibility
    Pcre2 = PCRE2
  end
end
