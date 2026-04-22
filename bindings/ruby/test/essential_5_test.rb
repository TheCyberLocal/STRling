# frozen_string_literal: true

require 'minitest/autorun'
require 'json'
require_relative '../lib/strling'

class Essential5Test < Minitest::Test
  def setup
    @spec ||= load_spec
  end

  def load_spec
    dir = File.expand_path('..', __dir__)
    until File.file?(File.join(dir, 'spec/stdlib/essential_5.json'))
      parent = File.expand_path('..', dir)
      raise 'essential_5.json not found' if parent == dir
      dir = parent
    end
    JSON.parse(File.read(File.join(dir, 'spec/stdlib/essential_5.json')))
  end

  def values(pattern, field)
    @spec['patterns'][pattern]['fixtures'][field]
  end

  def compile_full(simply_pat)
    re = simply_pat.to_s
    Regexp.new("\\A(?:#{re})\\z")
  end

  def assert_all_match(re, vals, label)
    vals.each { |v| assert re.match?(v), "#{label} expected match: #{v}" }
  end

  def assert_none_match(re, vals, label)
    vals.each { |v| refute re.match?(v), "#{label} expected NO match: #{v}" }
  end

  def test_email_valid
    assert_all_match(compile_full(Strling::Essential.email), values('email', 'valid'), 'email')
  end

  def test_email_invalid
    assert_none_match(compile_full(Strling::Essential.email), values('email', 'invalid'), 'email')
  end

  def test_url_valid
    assert_all_match(compile_full(Strling::Essential.url), values('url', 'valid'), 'url')
  end

  def test_url_invalid
    assert_none_match(compile_full(Strling::Essential.url), values('url', 'invalid'), 'url')
  end

  def test_uuid_default_valid
    assert_all_match(compile_full(Strling::Essential.uuid), values('uuid', 'valid_default'), 'uuid')
  end

  def test_uuid_default_invalid
    assert_none_match(compile_full(Strling::Essential.uuid), values('uuid', 'invalid_default'), 'uuid')
  end

  def test_uuid_v4_valid
    assert_all_match(compile_full(Strling::Essential.uuid(4)), values('uuid', 'valid_v4'), 'uuid4')
  end

  def test_uuid_v4_invalid
    assert_none_match(compile_full(Strling::Essential.uuid(4)), values('uuid', 'invalid_v4'), 'uuid4')
  end

  def test_ipv4_valid
    assert_all_match(compile_full(Strling::Essential.ip(4)), values('ip', 'valid_v4'), 'ipv4')
  end

  def test_ipv4_invalid
    assert_none_match(compile_full(Strling::Essential.ip(4)), values('ip', 'invalid_v4'), 'ipv4')
  end

  def test_ipv6_valid
    assert_all_match(compile_full(Strling::Essential.ip(6)), values('ip', 'valid_v6'), 'ipv6')
  end

  def test_ipv6_invalid
    assert_none_match(compile_full(Strling::Essential.ip(6)), values('ip', 'invalid_v6'), 'ipv6')
  end

  def test_ip_default_both
    re = compile_full(Strling::Essential.ip)
    assert_all_match(re, values('ip', 'valid_v4'), 'ip')
    assert_all_match(re, values('ip', 'valid_v6'), 'ip')
  end

  def test_date_time_valid
    assert_all_match(compile_full(Strling::Essential.date_time), values('dateTime', 'valid'), 'dateTime')
  end

  def test_date_time_invalid
    assert_none_match(compile_full(Strling::Essential.date_time), values('dateTime', 'invalid'), 'dateTime')
  end
end
