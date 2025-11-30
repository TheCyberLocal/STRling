# frozen_string_literal: true

require_relative 'core/nodes'
require_relative 'ir'
require_relative 'emitters/pcre2'

module Strling
  # Fluent API for building STRling patterns
  class Simply
    attr_reader :node

    def initialize(node)
      @node = node
    end

    # Class methods (Constructors)

    def self.merge(*patterns)
      parts = patterns.map { |p| to_node(p) }
      new(Strling::Core::Seq.new(parts))
    end

    def self.capture(pattern)
      new(Strling::Core::Group.new(true, to_node(pattern)))
    end

    def self.may(pattern)
      new(Strling::Core::Quant.new(to_node(pattern), 0, 1, 'Greedy'))
    end

    def self.digit
      new(Strling::Core::Esc.new('d'))
    end

    def self.start
      new(Strling::Core::Anchor.new('Start'))
    end

    def self.end
      new(Strling::Core::Anchor.new('End'))
    end

    def self.any_of(*patterns)
      branches = patterns.map { |p| to_node(p) }
      new(Strling::Core::Alt.new(branches))
    end

    # Helper to convert input to Node
    def self.to_node(pattern)
      if pattern.is_a?(Simply)
        pattern.node
      elsif pattern.is_a?(String)
        Strling::Core::Lit.new(pattern)
      else
        raise ArgumentError, "Expected Simply instance or String, got #{pattern.class}"
      end
    end

    # Instance methods (Chainable)

    def merge(*others)
      parts = [@node] + others.map { |p| Simply.to_node(p) }
      Simply.new(Strling::Core::Seq.new(parts))
    end

    def capture
      Simply.new(Strling::Core::Group.new(true, @node))
    end

    def may
      Simply.new(Strling::Core::Quant.new(@node, 0, 1, 'Greedy'))
    end

    def any_of(*others)
      branches = [@node] + others.map { |p| Simply.to_node(p) }
      Simply.new(Strling::Core::Alt.new(branches))
    end

    def times(min, max = nil)
      max = min if max.nil?
      Simply.new(Strling::Core::Quant.new(@node, min, max, 'Greedy'))
    end

    def to_s
      ir = Strling::IR::Compiler.compile(@node)
      flags = Strling::Core::Flags.new
      Strling::Emitters::PCRE2.emit(ir, flags)
    end
  end
end
