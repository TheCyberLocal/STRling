# frozen_string_literal: true

# STRling Intermediate Representation (IR) Node Definitions
#
# This module defines the complete set of IR node classes that represent
# language-agnostic regex constructs. The IR serves as an intermediate layer
# between the parsed AST and the target-specific emitters (e.g., PCRE2).
#
# IR nodes are designed to be:
#   - Simple and composable
#   - Easy to serialize (via to_dict methods)
#   - Independent of any specific regex flavor
#   - Optimized for transformation and analysis
#
# Each IR node corresponds to a fundamental regex operation (alternation,
# sequencing, character classes, quantification, etc.) and can be serialized
# to a hash representation for further processing or debugging.

module Strling
  module Core
    # Base class for all IR operations.
    #
    # All IR nodes extend this base class and must implement the to_dict() method
    # for serialization to a hash representation.
    class IROp
      # Serialize the IR node to a hash representation.
      #
      # @return [Hash] The hash representation of this IR node.
      # @raise [NotImplementedError] If not implemented by subclass.
      def to_dict
        raise NotImplementedError, 'Subclasses must implement to_dict'
      end
    end

    # Represents an alternation (OR) operation in the IR.
    #
    # Matches any one of the provided branches. Equivalent to the | operator
    # in traditional regex syntax.
    class IRAlt < IROp
      # @return [Array<IROp>] The alternative branches
      attr_accessor :branches

      # @param branches [Array<IROp>] The alternative branches
      def initialize(branches)
        @branches = branches
      end

      def to_dict
        { 'ir' => 'Alt', 'branches' => branches.map(&:to_dict) }
      end
    end

    # Represents a sequence of IR operations.
    #
    # Matches each part in order.
    class IRSeq < IROp
      # @return [Array<IROp>] The sequence parts
      attr_accessor :parts

      # @param parts [Array<IROp>] The sequence parts
      def initialize(parts)
        @parts = parts
      end

      def to_dict
        { 'ir' => 'Seq', 'parts' => parts.map(&:to_dict) }
      end
    end

    # Represents a literal string match in the IR.
    #
    # Matches the exact string value provided.
    class IRLit < IROp
      # @return [String] The literal string value
      attr_accessor :value

      # @param value [String] The literal string value
      def initialize(value)
        @value = value
      end

      def to_dict
        { 'ir' => 'Lit', 'value' => value }
      end
    end

    # Represents the dot metacharacter in the IR.
    #
    # Matches any single character.
    class IRDot < IROp
      def to_dict
        { 'ir' => 'Dot' }
      end
    end

    # Represents an anchor position assertion in the IR.
    #
    # Anchors match positions rather than characters.
    class IRAnchor < IROp
      # @return [String] The anchor type
      attr_accessor :at

      # @param at [String] The anchor type
      def initialize(at)
        @at = at
      end

      def to_dict
        { 'ir' => 'Anchor', 'at' => at }
      end
    end

    # Base class for character class items in the IR.
    class IRClassItem
      # Serialize the item to hash representation.
      #
      # @return [Hash] Hash representation of the item
      # @raise [NotImplementedError] Must be implemented by subclasses
      def to_dict
        raise NotImplementedError, 'Subclasses must implement to_dict'
      end
    end

    # Represents a character range in a character class in the IR.
    #
    # Matches characters from from_ch to to_ch (inclusive).
    class IRClassRange < IRClassItem
      # @return [String] The starting character
      attr_accessor :from_ch

      # @return [String] The ending character
      attr_accessor :to_ch

      # @param from_ch [String] The starting character
      # @param to_ch [String] The ending character
      def initialize(from_ch, to_ch)
        @from_ch = from_ch
        @to_ch = to_ch
      end

      def to_dict
        { 'ir' => 'Range', 'from' => from_ch, 'to' => to_ch }
      end
    end

    # Represents a literal character in a character class in the IR.
    #
    # Matches the exact character.
    class IRClassLiteral < IRClassItem
      # @return [String] The character
      attr_accessor :ch

      # @param ch [String] The character
      def initialize(ch)
        @ch = ch
      end

      def to_dict
        { 'ir' => 'Char', 'char' => ch }
      end
    end

    # Represents an escape sequence in a character class in the IR.
    #
    # Matches predefined character classes or Unicode properties.
    class IRClassEscape < IRClassItem
      # @return [String] The escape type
      attr_accessor :type

      # @return [String, nil] The Unicode property name (for \p and \P)
      attr_accessor :property

      # @param type [String] The escape type
      # @param property [String, nil] The Unicode property name
      def initialize(type, property: nil)
        @type = type
        @property = property
      end

      def to_dict
        data = { 'ir' => 'Esc', 'type' => type }
        data['property'] = property if property
        data
      end
    end

    # Represents a character class in the IR.
    #
    # Matches any character from the set defined by items.
    class IRCharClass < IROp
      # @return [Boolean] Whether the class is negated
      attr_accessor :negated

      # @return [Array<IRClassItem>] The items in the character class
      attr_accessor :items

      # @param negated [Boolean] Whether the class is negated
      # @param items [Array<IRClassItem>] The items in the character class
      def initialize(negated, items)
        @negated = negated
        @items = items
      end

      def to_dict
        {
          'ir' => 'CharClass',
          'negated' => negated,
          'items' => items.map(&:to_dict)
        }
      end
    end

    # Represents a quantifier (repetition operator) in the IR.
    #
    # Specifies how many times a pattern element should match.
    class IRQuant < IROp
      # @return [IROp] The child node being quantified
      attr_accessor :child

      # @return [Integer] The minimum number of matches
      attr_accessor :min

      # @return [Integer, String] The maximum number of matches ("Inf" for unbounded)
      attr_accessor :max

      # @return [String] The quantifier mode: "Greedy", "Lazy", or "Possessive"
      attr_accessor :mode

      # @param child [IROp] The child node being quantified
      # @param min [Integer] The minimum number of matches
      # @param max [Integer, String] The maximum number of matches
      # @param mode [String] The quantifier mode
      def initialize(child, min, max, mode)
        @child = child
        @min = min
        @max = max
        @mode = mode
      end

      def to_dict
        {
          'ir' => 'Quant',
          'child' => child.to_dict,
          'min' => min,
          'max' => max,
          'mode' => mode
        }
      end
    end

    # Represents a capturing or non-capturing group in the IR.
    #
    # Groups pattern elements together.
    class IRGroup < IROp
      # @return [Boolean] Whether the group is capturing
      attr_accessor :capturing

      # @return [IROp] The body of the group
      attr_accessor :body

      # @return [String, nil] The name of the group (for named captures)
      attr_accessor :name

      # @return [Boolean, nil] Whether the group is atomic
      attr_accessor :atomic

      # @param capturing [Boolean] Whether the group is capturing
      # @param body [IROp] The body of the group
      # @param name [String, nil] The name of the group
      # @param atomic [Boolean, nil] Whether the group is atomic
      def initialize(capturing, body, name: nil, atomic: nil)
        @capturing = capturing
        @body = body
        @name = name
        @atomic = atomic
      end

      def to_dict
        data = {
          'ir' => 'Group',
          'capturing' => capturing,
          'body' => body.to_dict
        }
        data['name'] = name unless name.nil?
        data['atomic'] = atomic unless atomic.nil?
        data
      end
    end

    # Represents a backreference in the IR.
    #
    # Matches the same text as previously captured by a group.
    class IRBackref < IROp
      # @return [Integer, nil] The group index to reference
      attr_accessor :by_index

      # @return [String, nil] The group name to reference
      attr_accessor :by_name

      # @param by_index [Integer, nil] The group index to reference
      # @param by_name [String, nil] The group name to reference
      def initialize(by_index: nil, by_name: nil)
        @by_index = by_index
        @by_name = by_name
      end

      def to_dict
        data = { 'ir' => 'Backref' }
        data['byIndex'] = by_index unless by_index.nil?
        data['byName'] = by_name unless by_name.nil?
        data
      end
    end

    # Represents a lookaround assertion in the IR.
    #
    # Asserts that a pattern does (or does not) match ahead of or behind
    # the current position.
    class IRLook < IROp
      # @return [String] The direction: "Ahead" or "Behind"
      attr_accessor :dir

      # @return [Boolean] Whether the assertion is negative
      attr_accessor :neg

      # @return [IROp] The body of the assertion
      attr_accessor :body

      # @param dir [String] The direction
      # @param neg [Boolean] Whether the assertion is negative
      # @param body [IROp] The body of the assertion
      def initialize(dir, neg, body)
        @dir = dir
        @neg = neg
        @body = body
      end

      def to_dict
        {
          'ir' => 'Look',
          'dir' => dir,
          'neg' => neg,
          'body' => body.to_dict
        }
      end
    end
  end
end
