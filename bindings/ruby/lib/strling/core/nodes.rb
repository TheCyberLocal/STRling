# frozen_string_literal: true

# STRling AST Node Definitions
#
# This module defines the complete set of Abstract Syntax Tree (AST) node classes
# that represent the parsed structure of STRling patterns. The AST is the direct
# output of the parser and represents the syntactic structure of the pattern before
# optimization and lowering to IR.
#
# AST nodes are designed to:
#   - Closely mirror the source pattern syntax
#   - Be easily serializable to the Base TargetArtifact schema
#   - Provide a clean separation between parsing and compilation
#   - Support multiple target regex flavors through the compilation pipeline
#
# Each AST node type corresponds to a syntactic construct in the STRling DSL
# (alternation, sequencing, character classes, anchors, etc.) and can be
# serialized to a hash representation for debugging or storage.

module Strling
  module Core
    # Container for regex flags/modifiers.
    #
    # Flags control the behavior of pattern matching (case sensitivity, multiline
    # mode, etc.). This class encapsulates all standard regex flags.
    class Flags
      # @return [Boolean] Case-insensitive matching
      attr_accessor :ignore_case

      # @return [Boolean] Multiline mode (^ and $ match line boundaries)
      attr_accessor :multiline

      # @return [Boolean] Dot matches all characters including newlines
      attr_accessor :dot_all

      # @return [Boolean] Unicode mode
      attr_accessor :unicode

      # @return [Boolean] Extended/free-spacing mode (ignore whitespace)
      attr_accessor :extended

      def initialize(ignore_case: false, multiline: false, dot_all: false, unicode: false, extended: false)
        @ignore_case = ignore_case
        @multiline = multiline
        @dot_all = dot_all
        @unicode = unicode
        @extended = extended
      end

      # Convert flags to hash representation.
      #
      # @return [Hash] Hash representation of flags
      def to_dict
        {
          'ignoreCase' => ignore_case,
          'multiline' => multiline,
          'dotAll' => dot_all,
          'unicode' => unicode,
          'extended' => extended
        }
      end

      # Create Flags from flag letters.
      #
      # @param letters [String] Flag letters (i, m, s, u, x)
      # @return [Flags] New Flags instance
      def self.from_letters(letters)
        flags = new
        letters.gsub(/[,\s]/, '').each_char do |ch|
          case ch
          when 'i'
            flags.ignore_case = true
          when 'm'
            flags.multiline = true
          when 's'
            flags.dot_all = true
          when 'u'
            flags.unicode = true
          when 'x'
            flags.extended = true
          when ''
            # Empty character, skip
          else
            # Unknown flags are ignored at parser stage; may be warned later
          end
        end
        flags
      end
    end

    # Base class for all AST nodes.
    class Node
      # Serialize the node to hash representation.
      #
      # @return [Hash] Hash representation of the node
      # @raise [NotImplementedError] Must be implemented by subclasses
      def to_dict
        raise NotImplementedError, 'Subclasses must implement to_dict'
      end
    end

    # Represents an alternation (OR) operation in the AST.
    #
    # Matches any one of the provided branches. Equivalent to the | operator
    # in traditional regex syntax.
    class Alt < Node
      # @return [Array<Node>] The alternative branches
      attr_accessor :branches

      # @param branches [Array<Node>] The alternative branches
      def initialize(branches)
        @branches = branches
      end

      def to_dict
        { 'kind' => 'Alt', 'branches' => branches.map(&:to_dict) }
      end
    end

    # Represents a sequence of pattern elements.
    #
    # Matches each part in order. Equivalent to simple concatenation in
    # traditional regex syntax.
    class Seq < Node
      # @return [Array<Node>] The sequence parts
      attr_accessor :parts

      # @param parts [Array<Node>] The sequence parts
      def initialize(parts)
        @parts = parts
      end

      def to_dict
        { 'kind' => 'Seq', 'parts' => parts.map(&:to_dict) }
      end
    end

    # Represents a literal string match.
    #
    # Matches the exact string value provided.
    class Lit < Node
      # @return [String] The literal string value
      attr_accessor :value

      # @param value [String] The literal string value
      def initialize(value)
        @value = value
      end

      def to_dict
        { 'kind' => 'Lit', 'value' => value }
      end
    end

    # Represents the dot metacharacter.
    #
    # Matches any single character (behavior depends on flags).
    class Dot < Node
      def to_dict
        { 'kind' => 'Dot' }
      end
    end

    # Represents an anchor position assertion.
    #
    # Anchors match positions rather than characters (start/end of string,
    # word boundaries, etc.).
    class Anchor < Node
      # @return [String] The anchor type: "Start", "End", "WordBoundary",
      #   "NotWordBoundary", or Absolute* variants
      attr_accessor :at

      # @param at [String] The anchor type
      def initialize(at)
        @at = at
      end

      def to_dict
        { 'kind' => 'Anchor', 'at' => at }
      end
    end

    # Base class for character class items.
    class ClassItem
      # Serialize the item to hash representation.
      #
      # @return [Hash] Hash representation of the item
      # @raise [NotImplementedError] Must be implemented by subclasses
      def to_dict
        raise NotImplementedError, 'Subclasses must implement to_dict'
      end
    end

    # Represents a character range in a character class.
    #
    # Matches characters from from_ch to to_ch (inclusive).
    class ClassRange < ClassItem
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
        { 'kind' => 'Range', 'from' => from_ch, 'to' => to_ch }
      end
    end

    # Represents a literal character in a character class.
    #
    # Matches the exact character.
    class ClassLiteral < ClassItem
      # @return [String] The character
      attr_accessor :ch

      # @param ch [String] The character
      def initialize(ch)
        @ch = ch
      end

      def to_dict
        { 'kind' => 'Char', 'char' => ch }
      end
    end

    # Represents an escape sequence in a character class.
    #
    # Matches predefined character classes (\d, \w, \s, etc.) or Unicode
    # property escapes (\p{...}, \P{...}).
    class ClassEscape < ClassItem
      # @return [String] The escape type (d, D, w, W, s, S, p, P)
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
        data = { 'kind' => 'Esc', 'type' => type }
        data['property'] = property if %w[p P].include?(type) && property
        data
      end
    end

    # Represents a character class.
    #
    # Matches any character from the set defined by items. Can be negated
    # to match any character NOT in the set.
    class CharClass < Node
      # @return [Boolean] Whether the class is negated
      attr_accessor :negated

      # @return [Array<ClassItem>] The items in the character class
      attr_accessor :items

      # @param negated [Boolean] Whether the class is negated
      # @param items [Array<ClassItem>] The items in the character class
      def initialize(negated, items)
        @negated = negated
        @items = items
      end

      def to_dict
        {
          'kind' => 'CharClass',
          'negated' => negated,
          'items' => items.map(&:to_dict)
        }
      end
    end

    # Represents a quantifier (repetition operator).
    #
    # Specifies how many times a pattern element should match (min to max times).
    # Supports greedy, lazy, and possessive modes.
    class Quant < Node
      # @return [Node] The child node being quantified
      attr_accessor :child

      # @return [Integer] The minimum number of matches
      attr_accessor :min

      # @return [Integer, String] The maximum number of matches ("Inf" for unbounded)
      attr_accessor :max

      # @return [String] The quantifier mode: "Greedy", "Lazy", or "Possessive"
      attr_accessor :mode

      # @param child [Node] The child node being quantified
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
          'kind' => 'Quant',
          'child' => child.to_dict,
          'min' => min,
          'max' => max,
          'mode' => mode
        }
      end
    end

    # Represents a capturing or non-capturing group.
    #
    # Groups pattern elements together and optionally captures the matched text
    # for later reference.
    class Group < Node
      # @return [Boolean] Whether the group is capturing
      attr_accessor :capturing

      # @return [Node] The body of the group
      attr_accessor :body

      # @return [String, nil] The name of the group (for named captures)
      attr_accessor :name

      # @return [Boolean, nil] Whether the group is atomic (extension)
      attr_accessor :atomic

      # @param capturing [Boolean] Whether the group is capturing
      # @param body [Node] The body of the group
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
          'kind' => 'Group',
          'capturing' => capturing,
          'body' => body.to_dict
        }
        data['name'] = name unless name.nil?
        data['atomic'] = atomic unless atomic.nil?
        data
      end
    end

    # Represents a backreference.
    #
    # Matches the same text as previously captured by a group, referenced
    # either by index or by name.
    class Backref < Node
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
        data = { 'kind' => 'Backref' }
        data['byIndex'] = by_index unless by_index.nil?
        data['byName'] = by_name unless by_name.nil?
        data
      end
    end

    # Represents a lookaround assertion.
    #
    # Asserts that a pattern does (or does not) match ahead of or behind
    # the current position, without consuming characters.
    class Look < Node
      # @return [String] The direction: "Ahead" or "Behind"
      attr_accessor :dir

      # @return [Boolean] Whether the assertion is negative
      attr_accessor :neg

      # @return [Node] The body of the assertion
      attr_accessor :body

      # @param dir [String] The direction
      # @param neg [Boolean] Whether the assertion is negative
      # @param body [Node] The body of the assertion
      def initialize(dir, neg, body)
        @dir = dir
        @neg = neg
        @body = body
      end

      def to_dict
        {
          'kind' => 'Look',
          'dir' => dir,
          'neg' => neg,
          'body' => body.to_dict
        }
      end
    end
  end
end
