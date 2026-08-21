# frozen_string_literal: true

require 'minitest/autorun'
require 'json'
require 'strling'

class AdapterTest < Minitest::Test
  def test_canonical_request_and_lexical_helper_shapes
    request = Strling.source_compile_request('literal "hello"')
    assert_equal '1.0.0', request['contract_version']
    assert_equal 'semantic_strling', request.dig('input', 'document', 'frontend', 'id')
    assert_equal 'stdlib.email', Strling.email('root').dig('arguments', 'helper_id')
    assert_nil Strling.uuid('root').dig('arguments', 'parameters', 'version')
  end

  def test_stdlib_helpers_consume_canonical_essential_fixture
    fixture_path = File.expand_path('../../../spec/stdlib/essential_5.json', __dir__)
    patterns = JSON.parse(File.read(fixture_path, encoding: 'UTF-8')).fetch('patterns')
    helpers = {
      'dateTime' => Strling.date_time('date-time'),
      'email' => Strling.email('email'),
      'ip' => Strling.ip('ip'),
      'url' => Strling.url('url'),
      'uuid' => Strling.uuid('uuid')
    }

    assert_equal helpers.keys.sort, patterns.keys.sort
    helpers.each do |name, step|
      helper_id = name == 'dateTime' ? 'date_time' : name
      assert_equal "stdlib.#{helper_id}", step.dig('arguments', 'helper_id')
    end
  end

  def test_relative_path_fails_closed
    error = assert_raises(Strling::NativeAdapterError) { Strling.load_native('libstrling_interop.so') }
    assert_equal :native_load, error.kind
    nul_error = assert_raises(Strling::NativeAdapterError) { Strling.load_native("/tmp/strling\0invalid") }
    assert_equal :native_load, nul_error.kind
  end

  def test_live_native_transport_when_certification_probe_is_supplied
    path = ENV['STRLING_DYNAMIC_PROBE']
    skip 'certification probe unavailable' if path.nil?

    client = Strling.load_native(path)
    expected = { 'unicode' => '雪' }
    results = {
      'describe' => client.describe,
      'compile' => client.compile(Strling.source_compile_request('literal "雪"')),
      'target_profile.inspect' => client.inspect_target_profile('contract_version' => '1.0.0'),
      'simply.compile' => client.simply_compile(Strling.simply_builder_request([Strling.email('root')], 'root'))
    }
    results.each_value { |result| assert_equal expected, result }
    evidence_dir = ENV['STRLING_DYNAMIC_EVIDENCE_DIR']
    File.write(File.join(evidence_dir, 'ruby.json'), JSON.generate(results)) unless evidence_dir.nil?
    concurrent = Strling.load_native(ENV.fetch('STRLING_DYNAMIC_CONCURRENCY_PROBE', path))
    workers = Array.new(4) do
      Thread.new do
        4.times do
          raise 'concurrent canonical result drifted' unless concurrent.describe == expected
        end
        true
      end
    end
    workers.each { |worker| assert worker.value }
    concurrent.close
    client.close
    assert client.closed?
    client.close
    assert_raises(Strling::NativeAdapterError) { client.describe }
  end

  def test_transport_probes_fail_closed
    {
      'STRLING_DYNAMIC_ABI_PROBE' => :native_abi,
      'STRLING_DYNAMIC_OVERSIZE_PROBE' => :transport,
      'STRLING_DYNAMIC_DUPLICATE_PROBE' => :transport,
      'STRLING_DYNAMIC_INVALID_UTF8_PROBE' => :transport,
      'STRLING_DYNAMIC_RELEASE_FAILURE_PROBE' => :native_abi
    }.each do |name, kind|
      path = ENV[name]
      next if path.nil?

      error = assert_raises(Strling::NativeAdapterError) do
        client = Strling.load_native(path)
        client.describe
      end
      assert_equal kind, error.kind
    end
  end
end
