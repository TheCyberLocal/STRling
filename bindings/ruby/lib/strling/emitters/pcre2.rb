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

module Strling
  module Emitters
    # PCRE2 emitter class
    class PCRE2
      # Emit IR as a PCRE2 regex pattern
      #
      # @param ir_root [IROp] The root IR node
      # @param flags [Flags] The pattern flags
      # @return [String] The PCRE2 regex pattern
      def self.emit(ir_root, flags)
        emitter = new(flags)
        pattern = emitter.emit_node(ir_root)
        
        # Add flag modifiers if any
        flag_str = build_flags(flags)
        flag_str.empty? ? pattern : "(?#{flag_str})#{pattern}"
      end

      def initialize(flags)
        @flags = flags
      end

      # Emit a single IR node
      #
      # @param node [IROp] The IR node to emit
      # @return [String] The PCRE2 pattern fragment
      def emit_node(node)
        case node
        when Strling::Core::IRAlt
          # (branch1|branch2|...)
          branches = node.branches.map { |b| emit_node(b) }
          branches.length == 1 ? branches[0] : "(#{branches.join('|')})"
        when Strling::Core::IRSeq
          # Concatenate parts
          node.parts.map { |p| emit_node(p) }.join
        when Strling::Core::IRLit
          # Escape metacharacters
          escape_literal(node.value)
        when Strling::Core::IRDot
          '.'
        when Strling::Core::IRAnchor
          emit_anchor(node.at)
        when Strling::Core::IRCharClass
          emit_char_class(node)
        when Strling::Core::IRQuant
          emit_quantifier(node)
        when Strling::Core::IRGroup
          emit_group(node)
        when Strling::Core::IRBackref
          emit_backref(node)
        when Strling::Core::IRLook
          emit_lookaround(node)
        else
          raise "Unknown IR node type: #{node.class}"
        end
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
        when Strling::Core::IRClassLiteral
          # Escape special characters in character class context
          case item.ch
          when ']', '\\', '^', '-'
            "\\#{item.ch}"
          else
            item.ch
          end
        when Strling::Core::IRClassEscape
          if %w[p P].include?(item.type)
            "\\#{item.type}{#{item.property}}"
          else
            "\\#{item.type}"
          end
        else
          raise "Unknown class item type: #{item.class}"
        end
      end

      # Emit a quantifier
      def emit_quantifier(node)
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
        body_str = emit_node(node.body)
        
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
  end
end
