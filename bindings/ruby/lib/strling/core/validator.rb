# frozen_string_literal: true

# STRling Validator - Semantic Validation of AST
#
# This module performs semantic validation of parsed AST nodes to catch
# errors that are syntactically valid but semantically problematic, such as:
#   - Invalid backreference numbers
#   - Duplicate named capture groups
#   - Invalid character class ranges
#   - Lookbehind assertions with variable-length patterns (flavor-specific)

require_relative 'nodes'
require_relative 'errors'

module Strling
  module Core
    # Validator class for semantic AST validation
    class Validator
      # Validate an AST node tree
      #
      # @param node [Node] The root AST node to validate
      # @param flags [Flags] The flags for this pattern
      # @return [Boolean] True if valid
      # @raise [STRlingParseError] If validation fails
      def self.validate(node, flags)
        new(flags).validate_node(node)
        true
      end

      def initialize(flags)
        @flags = flags
        @capture_count = 0
        @capture_names = Set.new
      end

      # Validate a single node and its children
      #
      # @param node [Node] The AST node to validate
      # @return [void]
      def validate_node(node)
        case node
        when Alt
          node.branches.each { |b| validate_node(b) }
        when Seq
          node.parts.each { |p| validate_node(p) }
        when CharClass
          node.items.each { |item| validate_class_item(item) }
        when Quant
          validate_node(node.child)
        when Group
          if node.capturing
            @capture_count += 1
            if node.name
              if @capture_names.include?(node.name)
                raise STRlingParseError.new(
                  "Duplicate capture group name: #{node.name}",
                  0,
                  text: '',
                  hint: 'Each named capture group must have a unique name'
                )
              end
              @capture_names.add(node.name)
            end
          end
          validate_node(node.body)
        when Backref
          # TODO: Validate backreference numbers and names
        when Look
          validate_node(node.body)
        when Lit, Dot, Anchor
          # No validation needed for these leaf nodes
        end
      end

      private

      # Validate a character class item
      def validate_class_item(item)
        case item
        when ClassRange
          # Validate range is valid (from <= to)
          if item.from_ch.ord > item.to_ch.ord
            raise STRlingParseError.new(
              "Invalid character class range: #{item.from_ch}-#{item.to_ch}",
              0,
              text: '',
              hint: 'Character class ranges must be in ascending order'
            )
          end
        when ClassLiteral, ClassEscape
          # No validation needed
        end
      end
    end

    # Module-level validate function for convenience
    def self.validate(node, flags)
      Validator.validate(node, flags)
    end
  end
end
