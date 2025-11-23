# frozen_string_literal: true

module Strling
  module Nodes
    Literal = Data.define(:value)
    Quantifier = Data.define(:target, :min, :max, :greedy, :lazy, :possessive)
    CharacterClass = Data.define(:negated, :members)
    Group = Data.define(:capturing, :body, :name, :atomic)
    Alternation = Data.define(:alternatives)
    UnicodeProperty = Data.define(:name, :value, :negated)
    Sequence = Data.define(:parts)
    Lookahead = Data.define(:body, :negative)
    Lookbehind = Data.define(:body, :negative)
    Anchor = Data.define(:at)
    Escape = Data.define(:kind)
    BackReference = Data.define(:name, :index)
    Dot = Data.define(:value) # Placeholder
    Range = Data.define(:from, :to)

    class NodeFactory
      def self.from_json(hash)
        return nil if hash.nil?

        case hash['type']
        when 'Literal'
          Literal.new(value: hash['value'])
        when 'Quantifier'
          Quantifier.new(
            target: from_json(hash['target']),
            min: hash['min'],
            max: hash['max'],
            greedy: hash['greedy'],
            lazy: hash['lazy'],
            possessive: hash['possessive']
          )
        when 'CharacterClass'
          CharacterClass.new(
            negated: hash['negated'],
            members: hash['members'].map { |m| from_json(m) }
          )
        when 'Group'
          # Note: 'expression' field in JSON seems redundant or specific, using 'body'
          Group.new(
            capturing: hash['capturing'],
            body: from_json(hash['body'] || hash['expression']),
            name: hash['name'],
            atomic: hash['atomic']
          )
        when 'Alternation'
          Alternation.new(
            alternatives: hash['alternatives'].map { |a| from_json(a) }
          )
        when 'UnicodeProperty'
          UnicodeProperty.new(
            name: hash['name'],
            value: hash['value'],
            negated: hash['negated']
          )
        when 'Sequence'
          Sequence.new(
            parts: hash['parts'].map { |p| from_json(p) }
          )
        when 'Lookahead'
          Lookahead.new(
            body: from_json(hash['body']),
            negative: hash['negative'] || false
          )
        when 'NegativeLookahead'
          Lookahead.new(
            body: from_json(hash['body']),
            negative: true
          )
        when 'Lookbehind'
          Lookbehind.new(
            body: from_json(hash['body']),
            negative: hash['negative'] || false
          )
        when 'NegativeLookbehind'
          Lookbehind.new(
            body: from_json(hash['body']),
            negative: true
          )
        when 'Anchor'
          Anchor.new(at: hash['at'])
        when 'Escape'
          Escape.new(kind: hash['kind'])
        when 'BackReference', 'Backreference'
            BackReference.new(name: hash['name'], index: hash['index'])
        when 'Dot'
            Dot.new(value: nil)
        when 'Range'
            Range.new(from: hash['from'], to: hash['to'])
        else
          # Generic fallback for unknown nodes to avoid crashing immediately, 
          # allowing us to see what's missing
          # puts "Warning: Unknown node type #{hash['type']}"
          Data.define(:type, :raw).new(type: hash['type'], raw: hash)
        end
      end
    end
  end
end
