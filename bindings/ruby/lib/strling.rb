# frozen_string_literal: true

# STRling Binding - Main Entry Point
#
# This is the root module for the STRling binding. It provides the foundation
# for the STRling DSL and compiler, offering a readable, maintainable
# alternative to traditional regular expressions.
#
# The STRling module serves as the namespace for all STRling functionality,
# including core data structures (nodes, IR, errors) and the parser/compiler
# pipeline.

require_relative 'strling/core/errors'
require_relative 'strling/core/nodes'
require_relative 'strling/core/ir'
require_relative 'strling/core/parser'

module Strling
  # Version constant
  VERSION = '3.0.0-alpha'

  # Convenience method for parsing
  def self.parse(text)
    Core.parse(text)
  end
end
