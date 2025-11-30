require 'minitest/autorun'
require 'json'
require_relative '../lib/strling/nodes'
require_relative '../lib/strling/ir'

class ConformanceTest < Minitest::Test
  SPEC_DIR = File.expand_path('../../../../tests/spec', __FILE__)

  Dir.glob(File.join(SPEC_DIR, '*.json')).each do |file|
    # Pre-check to filter invalid specs
    begin
      pre_spec = JSON.parse(File.read(file))
      next unless pre_spec['input_ast'] && pre_spec['expected_ir']
    rescue JSON::ParserError
      next
    end

    test_name = "test_conformance_#{File.basename(file, '.json').gsub(/[^a-zA-Z0-9_]/, '_')}"
    
    define_method(test_name) do
      spec = JSON.parse(File.read(file))
      
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
