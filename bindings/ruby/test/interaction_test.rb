# frozen_string_literal: true

# Interaction Tests - Parser → Compiler → Emitter handoffs
#
# This test suite validates the handoff between pipeline stages:
# - Parser → Compiler: Ensures AST is correctly consumed
# - Compiler → Emitter: Ensures IR is correctly transformed to regex

require 'minitest/autorun'
require_relative '../lib/strling/core/parser'
require_relative '../lib/strling/core/compiler'
require_relative '../lib/strling/emitters/pcre2'

class InteractionTest < Minitest::Test

  # ============================================================================
  # Parser → Compiler Handoff Tests
  # ============================================================================

  def test_parser_compiler_simple_literal
    parser = Strling::Core::Parser.new("hello")
    flags, ast = parser.parse

    ir = Strling::Core::Compiler.compile(ast)

    assert_not_nil ir
    serialized = serialize(ir)
    assert_equal 'Lit', serialized['ir']
  end

  def test_parser_compiler_quantifier
    parser = Strling::Core::Parser.new("a+")
    flags, ast = parser.parse

    ir = Strling::Core::Compiler.compile(ast)
    serialized = serialize(ir)

    assert_equal 'Quant', serialized['ir']
  end

  def test_parser_compiler_character_class
    parser = Strling::Core::Parser.new("[abc]")
    flags, ast = parser.parse

    ir = Strling::Core::Compiler.compile(ast)
    serialized = serialize(ir)

    assert_equal 'CharClass', serialized['ir']
  end

  def test_parser_compiler_capturing_group
    parser = Strling::Core::Parser.new("(abc)")
    flags, ast = parser.parse

    ir = Strling::Core::Compiler.compile(ast)
    serialized = serialize(ir)

    assert_equal 'Group', serialized['ir']
  end

  def test_parser_compiler_alternation
    parser = Strling::Core::Parser.new("a|b")
    flags, ast = parser.parse

    ir = Strling::Core::Compiler.compile(ast)
    serialized = serialize(ir)

    assert_equal 'Alt', serialized['ir']
  end

  def test_parser_compiler_named_group
    parser = Strling::Core::Parser.new("(?<name>abc)")
    flags, ast = parser.parse

    ir = Strling::Core::Compiler.compile(ast)
    serialized = serialize(ir)

    assert_equal 'Group', serialized['ir']
  end

  def test_parser_compiler_lookahead
    parser = Strling::Core::Parser.new("(?=abc)")
    flags, ast = parser.parse

    ir = Strling::Core::Compiler.compile(ast)
    serialized = serialize(ir)

    assert_equal 'Look', serialized['ir']
  end

  def test_parser_compiler_lookbehind
    parser = Strling::Core::Parser.new("(?<=abc)")
    flags, ast = parser.parse

    ir = Strling::Core::Compiler.compile(ast)
    serialized = serialize(ir)

    assert_equal 'Look', serialized['ir']
  end

  # ============================================================================
  # Compiler → Emitter Handoff Tests
  # ============================================================================

  def test_compiler_emitter_simple_literal
    regex = compile_to_regex("hello")
    assert_equal "hello", regex
  end

  def test_compiler_emitter_digit_shorthand
    regex = compile_to_regex("\\d+")
    assert_equal "\\d+", regex
  end

  def test_compiler_emitter_character_class
    regex = compile_to_regex("[abc]")
    assert_equal "[abc]", regex
  end

  def test_compiler_emitter_character_class_range
    regex = compile_to_regex("[a-z]")
    assert_equal "[a-z]", regex
  end

  def test_compiler_emitter_negated_class
    regex = compile_to_regex("[^abc]")
    assert_equal "[^abc]", regex
  end

  def test_compiler_emitter_quantifier_plus
    regex = compile_to_regex("a+")
    assert_equal "a+", regex
  end

  def test_compiler_emitter_quantifier_star
    regex = compile_to_regex("a*")
    assert_equal "a*", regex
  end

  def test_compiler_emitter_quantifier_optional
    regex = compile_to_regex("a?")
    assert_equal "a?", regex
  end

  def test_compiler_emitter_quantifier_exact
    regex = compile_to_regex("a{3}")
    assert_equal "a{3}", regex
  end

  def test_compiler_emitter_quantifier_range
    regex = compile_to_regex("a{2,5}")
    assert_equal "a{2,5}", regex
  end

  def test_compiler_emitter_quantifier_lazy
    regex = compile_to_regex("a+?")
    assert_equal "a+?", regex
  end

  def test_compiler_emitter_capturing_group
    regex = compile_to_regex("(abc)")
    assert_equal "(abc)", regex
  end

  def test_compiler_emitter_non_capturing_group
    regex = compile_to_regex("(?:abc)")
    assert_equal "(?:abc)", regex
  end

  def test_compiler_emitter_named_group
    regex = compile_to_regex("(?<name>abc)")
    assert_equal "(?<name>abc)", regex
  end

  def test_compiler_emitter_alternation
    regex = compile_to_regex("cat|dog")
    assert_equal "cat|dog", regex
  end

  def test_compiler_emitter_anchors
    regex = compile_to_regex("^abc$")
    assert_equal "^abc$", regex
  end

  def test_compiler_emitter_positive_lookahead
    regex = compile_to_regex("foo(?=bar)")
    assert_equal "foo(?=bar)", regex
  end

  def test_compiler_emitter_negative_lookahead
    regex = compile_to_regex("foo(?!bar)")
    assert_equal "foo(?!bar)", regex
  end

  def test_compiler_emitter_positive_lookbehind
    regex = compile_to_regex("(?<=foo)bar")
    assert_equal "(?<=foo)bar", regex
  end

  def test_compiler_emitter_negative_lookbehind
    regex = compile_to_regex("(?<!foo)bar")
    assert_equal "(?<!foo)bar", regex
  end

  # ============================================================================
  # Semantic Edge Case Tests
  # ============================================================================

  def test_semantic_duplicate_capture_group
    assert_raises(Strling::Core::STRlingParseError) do
      parser = Strling::Core::Parser.new("(?<name>a)(?<name>b)")
      parser.parse
    end
  end

  def test_semantic_ranges
    # Invalid range [z-a] should produce an error
    assert_raises(Strling::Core::STRlingParseError) do
      parser = Strling::Core::Parser.new("[z-a]")
      parser.parse
    end
  end

  # ============================================================================
  # Full Pipeline Tests
  # ============================================================================

  def test_full_pipeline_phone_number
    regex = compile_to_regex("(\\d{3})[-. ]?(\\d{3})[-. ]?(\\d{4})")
    assert_equal "(\\d{3})[-. ]?(\\d{3})[-. ]?(\\d{4})", regex
  end

  def test_full_pipeline_ipv4
    regex = compile_to_regex("(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})")
    assert_equal "(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})", regex
  end

  private

  def compile_to_regex(dsl)
    parser = Strling::Core::Parser.new(dsl)
    flags, ast = parser.parse
    ir = Strling::Core::Compiler.compile(ast)
    Strling::Emitters::Pcre2.emit(ir, flags)
  end

  def serialize(obj)
    case obj
    when Data
      obj.to_h.transform_keys(&:to_s).transform_values { |v| serialize(v) }.compact
    when Array
      obj.map { |v| serialize(v) }
    when Hash
      obj.transform_keys(&:to_s).transform_values { |v| serialize(v) }.compact
    else
      obj
    end
  end
end
