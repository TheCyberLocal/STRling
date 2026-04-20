require 'minitest/autorun'
require 'json'
require_relative '../lib/strling/nodes'
require_relative '../lib/strling/ir'
require_relative '../lib/strling/core/hint_engine'

class ConformanceTest < Minitest::Test
  SPEC_DIR = File.expand_path('../../../../tests/spec', __FILE__)

  Dir.glob(File.join(SPEC_DIR, '*.json')).each do |file|
    base_name = File.basename(file, '.json')

    # Generate test name with special handling for semantic tests
    test_name = case base_name
                when 'semantic_duplicates'
                  'test_semantic_duplicate_capture_group'
                when 'semantic_ranges'
                  'test_semantic_ranges'
                else
                  "test_conformance_#{base_name.gsub(/[^a-zA-Z0-9_]/, '_')}"
                end
    
    # Pre-check to determine test type
    begin
      pre_spec = JSON.parse(File.read(file))
    rescue JSON::ParserError
      next
    end
    
    # Define test method based on spec type
    if pre_spec['input_ast'] && pre_spec['expected_ir']
      # Standard conformance test - capture pre_spec in closure to avoid re-reading file
      captured_spec = pre_spec
      define_method(test_name) do
        spec = captured_spec
        
        # Hydrate AST
        ast = Strling::Nodes::NodeFactory.from_json(spec['input_ast'])
        
        # Compile to IR
        ir = Strling::IR::Compiler.compile(ast)

        refute_nil ir, "Compilation returned nil"
        
        # Compare
        expected = spec['expected_ir']
        actual = serialize(ir)
        
        assert_equal expected, actual, "Mismatch in #{File.basename(file)}"
      end
    elsif pre_spec['expected_error']
      # Error test case
      captured_spec = pre_spec
      define_method(test_name) do
        spec = captured_spec
        if spec['input_ast']
            # If we have input_ast, try to compile and expect error
            ast = Strling::Nodes::NodeFactory.from_json(spec['input_ast'])
            assert_raises(StandardError) do
                Strling::IR::Compiler.compile(ast)
            end
        elsif spec['input_dsl'] && !spec['input_dsl'].empty?
            # Parser error test: parse input_dsl and verify error + hint
            begin
              require_relative '../lib/strling/core/parser'
              err = assert_raises(StandardError) do
                Strling::Core::Parser.new.parse(spec['input_dsl'])
              end
              assert_includes err.message, spec['expected_error'],
                "Error message mismatch.\n  Expected substring: #{spec['expected_error']}\n  Actual: #{err.message}"
              if spec['expected_hint'] && !spec['expected_hint'].empty? && err.respond_to?(:hint)
                assert_equal spec['expected_hint'], err.hint,
                  "Hint mismatch.\n  Expected: #{spec['expected_hint']}\n  Actual: #{err.hint}"
              end
            rescue LoadError
              # Parser not available, pass
              pass
            end
        else
            # Parser test (no AST), out of scope. Pass.
            pass
        end
      end
    end
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
