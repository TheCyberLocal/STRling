# frozen_string_literal: true

require_relative 'core/nodes'

module Strling
  module IR
    Lit = Data.define(:ir, :value)
    Quant = Data.define(:ir, :child, :min, :max, :mode)
    CharClass = Data.define(:ir, :negated, :items)
    Char = Data.define(:ir, :char)
    Group = Data.define(:ir, :capturing, :body, :name, :atomic)
    Alt = Data.define(:ir, :branches)
    Esc = Data.define(:ir, :type, :property)
    Seq = Data.define(:ir, :parts)
    Look = Data.define(:ir, :dir, :neg, :body)
    Anchor = Data.define(:ir, :at)
    BackRef = Data.define(:ir, :byIndex, :byName)
    Range = Data.define(:ir, :from, :to)
    Dot = Data.define(:ir)
    # Add others as needed

    class Compiler
      def self.compile(ast_node)
        return nil if ast_node.nil?

        case ast_node
        # Core Nodes
        when Strling::Core::Lit
          Lit.new(ir: 'Lit', value: ast_node.value)
        when Strling::Core::Quant
          Quant.new(
            ir: 'Quant',
            child: compile(ast_node.child),
            min: ast_node.min,
            max: ast_node.max,
            mode: ast_node.mode
          )
        when Strling::Core::Group
          Group.new(
            ir: 'Group',
            capturing: ast_node.capturing,
            body: compile(ast_node.body),
            name: ast_node.name,
            atomic: ast_node.atomic
          )
        when Strling::Core::Alt
          Alt.new(
            ir: 'Alt',
            branches: ast_node.branches.map { |b| compile(b) }
          )
        when Strling::Core::Seq
          parts = ast_node.parts.map { |p| compile(p) }
          merged_parts = []
          parts.each do |part|
            if part.is_a?(Lit) && merged_parts.last.is_a?(Lit)
              last = merged_parts.pop
              merged_parts << Lit.new(ir: 'Lit', value: last.value + part.value)
            else
              merged_parts << part
            end
          end
          if merged_parts.size == 1
            merged_parts.first
          else
            Seq.new(ir: 'Seq', parts: merged_parts)
          end
        when Strling::Core::Esc
          Esc.new(ir: 'Esc', type: ast_node.type, property: ast_node.property)
        when Strling::Core::Anchor
          at = ast_node.at == 'NonWordBoundary' ? 'NotWordBoundary' : ast_node.at
          Anchor.new(ir: 'Anchor', at: at)
        when Strling::Core::Look
          Look.new(
            ir: 'Look',
            dir: ast_node.dir,
            neg: ast_node.neg,
            body: compile(ast_node.body)
          )
        # Legacy Nodes
        when Strling::Nodes::Literal
          Lit.new(ir: 'Lit', value: ast_node.value)
        when Strling::Nodes::Quantifier
          mode = if ast_node.possessive
                   'Possessive'
                 elsif ast_node.lazy
                   'Lazy'
                 else
                   'Greedy'
                 end
          
          # Handle max being null/nil -> "Inf"
          max_val = ast_node.max.nil? ? 'Inf' : ast_node.max

          Quant.new(
            ir: 'Quant',
            child: compile(ast_node.target),
            min: ast_node.min,
            max: max_val,
            mode: mode
          )
        when Strling::Nodes::CharacterClass
          items = ast_node.members.map do |member|
            if member.is_a?(Strling::Nodes::Literal)
              Char.new(ir: 'Char', char: member.value)
            elsif member.is_a?(Strling::Nodes::UnicodeProperty)
               type = member.negated ? 'P' : 'p'
               Esc.new(ir: 'Esc', type: type, property: member.value)
            elsif member.is_a?(Strling::Nodes::Escape)
               compile(member)
            else
              # Fallback or recursive compile if members can be other things
              compile(member)
            end
          end
          CharClass.new(ir: 'CharClass', negated: ast_node.negated, items: items)
        when Strling::Nodes::Group
          Group.new(
            ir: 'Group',
            capturing: ast_node.capturing,
            body: compile(ast_node.body),
            name: ast_node.name,
            atomic: ast_node.atomic ? true : nil
          )
        when Strling::Nodes::Alternation
          Alt.new(
            ir: 'Alt',
            branches: ast_node.alternatives.map { |a| compile(a) }
          )
        when Strling::Nodes::UnicodeProperty
          # If it appears standalone (not in CharClass), it might still be Esc?
          # In unicode_property_short.json it was inside CharacterClass.
          # Let's assume it maps to Esc.
          type = ast_node.negated ? 'P' : 'p'
          Esc.new(ir: 'Esc', type: type, property: ast_node.value)
        when Strling::Nodes::Sequence
          parts = ast_node.parts.map { |p| compile(p) }
          
          # Merge adjacent Lit nodes
          merged_parts = []
          parts.each do |part|
            if part.is_a?(Lit) && merged_parts.last.is_a?(Lit)
              last = merged_parts.pop
              merged_parts << Lit.new(ir: 'Lit', value: last.value + part.value)
            else
              merged_parts << part
            end
          end

          if merged_parts.size == 1
            merged_parts.first
          else
            Seq.new(ir: 'Seq', parts: merged_parts)
          end
        when Strling::Nodes::Lookahead
          Look.new(
            ir: 'Look',
            dir: 'Ahead',
            neg: ast_node.negative || false, # AST might not have negative if it's a separate node type "NegativeLookahead"
            body: compile(ast_node.body)
          )
        when Strling::Nodes::Lookbehind
          Look.new(
            ir: 'Look',
            dir: 'Behind',
            neg: ast_node.negative || false,
            body: compile(ast_node.body)
          )
        when Strling::Nodes::Anchor
          at = ast_node.at == 'NonWordBoundary' ? 'NotWordBoundary' : ast_node.at
          Anchor.new(ir: 'Anchor', at: at)
        when Strling::Nodes::Escape
          type = case ast_node.kind
                 when 'digit' then 'd'
                 when 'not-digit' then 'D'
                 when 'space' then 's'
                 when 'not-space' then 'S'
                 when 'word' then 'w'
                 when 'not-word' then 'W'
                 # Add others if needed
                 else ast_node.kind # Fallback
                 end
          Esc.new(ir: 'Esc', type: type, property: nil)
        when Strling::Nodes::BackReference
          BackRef.new(
            ir: 'Backref',
            byIndex: ast_node.index,
            byName: ast_node.name
          )
        when Strling::Nodes::Range
          Range.new(ir: 'Range', from: ast_node.from, to: ast_node.to)
        when Strling::Nodes::Dot
          Dot.new(ir: 'Dot')
        else
          # Fallback
          # puts "Warning: Unknown AST node for compilation: #{ast_node.class}"
          nil
        end
      end
    end
  end
end
