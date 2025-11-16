# frozen_string_literal: true

# STRling Compiler - AST to IR Transformation
#
# This module transforms Abstract Syntax Tree (AST) nodes from the parser
# into Intermediate Representation (IR) nodes. The IR is a simplified,
# language-agnostic representation that can be easily emitted to various
# target regex flavors.
#
# The compiler performs:
#   - AST node type transformation (Node → IROp)
#   - Semantic validation
#   - Optimization opportunities (future)

require_relative 'nodes'
require_relative 'ir'

module Strling
  module Core
    # Compiler class for transforming AST to IR
    class Compiler
      # Compile an AST node tree to IR
      #
      # @param node [Node] The root AST node to compile
      # @return [IROp] The compiled IR root node
      def self.compile(node)
        new.compile_node(node)
      end

      # Compile a single AST node to its IR equivalent
      #
      # @param node [Node] The AST node to compile
      # @return [IROp] The corresponding IR node
      def compile_node(node)
        case node
        when Alt
          IRAlt.new(node.branches.map { |b| compile_node(b) })
        when Seq
          IRSeq.new(node.parts.map { |p| compile_node(p) })
        when Lit
          IRLit.new(node.value)
        when Dot
          IRDot.new
        when Anchor
          IRAnchor.new(node.at)
        when CharClass
          IRCharClass.new(
            node.negated,
            node.items.map { |item| compile_class_item(item) }
          )
        when Quant
          IRQuant.new(
            compile_node(node.child),
            node.min,
            node.max,
            node.mode
          )
        when Group
          IRGroup.new(
            node.capturing,
            compile_node(node.body),
            name: node.name,
            atomic: node.atomic
          )
        when Backref
          IRBackref.new(by_index: node.by_index, by_name: node.by_name)
        when Look
          IRLook.new(node.dir, node.neg, compile_node(node.body))
        else
          raise "Unknown AST node type: #{node.class}"
        end
      end

      private

      # Compile a character class item
      def compile_class_item(item)
        case item
        when ClassRange
          IRClassRange.new(item.from_ch, item.to_ch)
        when ClassLiteral
          IRClassLiteral.new(item.ch)
        when ClassEscape
          IRClassEscape.new(item.type, property: item.property)
        else
          raise "Unknown class item type: #{item.class}"
        end
      end
    end

    # Module-level compile function for convenience
    def self.compile(node)
      Compiler.compile(node)
    end
  end
end
