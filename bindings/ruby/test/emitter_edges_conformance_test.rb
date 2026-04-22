# frozen_string_literal: true

require 'minitest/autorun'
require 'json'
require_relative '../lib/strling/core/ir'
require_relative '../lib/strling/core/diagnostics'
require_relative '../lib/strling/emitters/pcre2'

# Emitter Edges Conformance — Ruby bridge.
#
# Drives the global pathological-AST fixture
# `tests/conformance/inputs/emitter_edges/pathological.json` through the
# Ruby PCRE2 emitter and asserts each safety guard fires:
#   1. Variable-Length Lookbehind Rejection — STRlingCompilationError
#   2. AST Depth Limit Exceeded             — STRlingCompilationError
#   3. ReDoS Risk Warning (`(a+)+`)         — non-fatal STRlingWarning
#
# The local {ast_to_ir} mirrors the TypeScript bridge so the test targets
# the emitter without coupling to the parser/compiler stages. Keep it
# minimal — supporting only node types currently appearing in
# `pathological.json` — so adapter omissions cannot mask emitter bugs by
# silently dropping nodes.
class EmitterEdgesConformanceTest < Minitest::Test
  FIXTURE = begin
    dir = File.expand_path(__dir__)
    found = nil
    12.times do
      if File.exist?(File.join(dir, 'toolchain.json'))
        found = File.join(dir, 'tests', 'conformance', 'inputs', 'emitter_edges', 'pathological.json')
        break
      end
      parent = File.dirname(dir)
      break if parent == dir
      dir = parent
    end
    raise 'could not locate workspace root' unless found
    found
  end

  def ast_to_ir(node)
    case node['type']
    when 'Literal'
      Strling::Core::IRLit.new(node['value'].to_s)
    when 'Group'
      Strling::Core::IRGroup.new(false, ast_to_ir(node['content']))
    when 'Quantifier'
      child = ast_to_ir(node['content'])
      raw_max = node['max']
      max = raw_max.nil? ? 'Inf' : raw_max
      Strling::Core::IRQuant.new(child, node['min'].to_i, max, 'Greedy')
    when 'Lookbehind'
      Strling::Core::IRLook.new('Behind', false, ast_to_ir(node['content']))
    when 'NegativeLookbehind'
      Strling::Core::IRLook.new('Behind', true, ast_to_ir(node['content']))
    when 'Lookahead'
      Strling::Core::IRLook.new('Ahead', false, ast_to_ir(node['content']))
    when 'NegativeLookahead'
      Strling::Core::IRLook.new('Ahead', true, ast_to_ir(node['content']))
    else
      raise "ast_to_ir: unsupported pathological AST node type \"#{node['type']}\". " \
        'Extend the adapter when new pathological vectors are added.'
    end
  end

  def expected_substring(prefixed)
    if prefixed.start_with?('STRlingCompilationError:')
      return prefixed.sub('STRlingCompilationError:', '').strip
    end
    if prefixed.start_with?('STRlingWarning')
      idx = prefixed.index(']')
      return prefixed[(idx + 1)..].sub(/^[: ]+/, '') if idx
    end
    prefixed
  end

  # NullFlags satisfies the `flags.ignore_case` etc. accesses in
  # PCRE2.build_flags without dragging in the full Flags class.
  class NullFlags
    %i[ignore_case multiline dot_all unicode extended].each do |m|
      define_method(m) { false }
    end
  end

  def test_pathological_cases
    doc = JSON.parse(File.read(FIXTURE))
    cases = doc['tests']
    refute_nil cases
    refute_empty cases

    cases.each do |tc|
      name = tc['name'] || '<unnamed>'
      ir = ast_to_ir(tc['ast'])
      max_depth = tc['depth_override_for_test'] || 0

      if tc.key?('expected_error')
        needle = expected_substring(tc['expected_error'].to_s)
        err = assert_raises(Strling::Core::STRlingCompilationError, "[#{name}] expected error") do
          Strling::Emitters::PCRE2.emit_with_diagnostics(ir, NullFlags.new, max_depth)
        end
        assert_includes err.message, needle, "[#{name}]"
      elsif tc.key?('expected_warning')
        needle = expected_substring(tc['expected_warning'].to_s)
        result = Strling::Emitters::PCRE2.emit_with_diagnostics(ir, NullFlags.new, max_depth)
        # Warnings must NOT abort emission — the pattern is still produced.
        refute_empty result.pattern, "[#{name}] expected non-empty pattern when only a warning fires"
        match = result.warnings.any? { |w| w.code == 'REDOS_RISK' && w.message.include?(needle) }
        assert match, "[#{name}] missing REDOS_RISK warning containing \"#{needle}\". Got: #{result.warnings.map(&:to_s)}"
      else
        flunk "[#{name}] declares neither expected_error nor expected_warning"
      end
    end
  end

  def test_non_pathological_emits_no_warnings
    ir = Strling::Core::IRLit.new('abc')
    result = Strling::Emitters::PCRE2.emit_with_diagnostics(ir, NullFlags.new)
    assert_equal 'abc', result.pattern
    assert_empty result.warnings
  end

  def test_depth_cap_does_not_fire_under_limit
    inner = Strling::Core::IRGroup.new(false, Strling::Core::IRLit.new('ok'))
    outer = Strling::Core::IRGroup.new(false, inner)
    result = Strling::Emitters::PCRE2.emit_with_diagnostics(outer, NullFlags.new, 5)
    assert_empty result.warnings
    assert_includes result.pattern, 'ok'
  end
end
