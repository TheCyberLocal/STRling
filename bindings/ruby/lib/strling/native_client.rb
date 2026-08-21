# frozen_string_literal: true

require 'fiddle'
require 'json'
require 'pathname'
require 'thread'

module Strling
  # Reentrant native client over caller-selected strling.c-abi v1.
  class NativeClient
    STATUS_RESPONSE_WRITTEN = 0
    private_constant :STATUS_RESPONSE_WRITTEN

    def self.load(library_path)
      path = Pathname.new(String(library_path))
      raise NativeAdapterError.new(:native_load, 'native STRling library path must be absolute') unless path.absolute?

      normalized = path.cleanpath
      unless normalized.file?
        raise NativeAdapterError.new(:native_load, "native STRling library not found: #{normalized}")
      end

      new(normalized.to_s)
    rescue NativeAdapterError
      raise
    rescue StandardError => e
      raise NativeAdapterError.new(:native_load, "invalid native STRling library path: #{e.message}")
    end

    attr_reader :library_path

    def initialize(library_path)
      @library_path = library_path.freeze
      @mutex = Mutex.new
      @condition = ConditionVariable.new
      @active_calls = 0
      @closed = false
      load_functions
    end

    def closed?
      @mutex.synchronize { @closed }
    end

    def execute(request)
      encoded = JSON.generate(request, allow_nan: false).encode(Encoding::UTF_8)
      raise NativeAdapterError.new(:transport, 'interop request is not valid UTF-8') unless encoded.valid_encoding?
      if encoded.bytesize > MAX_INTEROP_REQUEST_BYTES
        raise NativeAdapterError.new(:transport, "interop request exceeds #{MAX_INTEROP_REQUEST_BYTES} bytes")
      end

      begin_call
      begin
        execute_bytes(encoded)
      ensure
        end_call
      end
    rescue JSON::GeneratorError, EncodingError, TypeError => e
      raise NativeAdapterError.new(:transport, "interop request is not strict JSON: #{e.message}")
    end

    def describe
      completed_result(envelope('describe', {}))
    end

    def compile(compile_request, target_profile: nil)
      payload = { 'compile_request' => compile_request }
      payload['target_profile'] = target_profile unless target_profile.nil?
      completed_result(envelope('compile', payload))
    end

    def inspect_target_profile(target_profile)
      completed_result(envelope('target_profile.inspect', 'target_profile' => target_profile))
    end

    def simply_compile(builder_request, target_profile: nil)
      payload = { 'builder_request' => builder_request }
      payload['target_profile'] = target_profile unless target_profile.nil?
      completed_result(envelope('simply.compile', payload))
    end

    def close
      handle = @mutex.synchronize do
        return nil if @closed

        @closed = true
        @condition.wait(@mutex) until @active_calls.zero?
        selected = @handle
        @handle = nil
        selected
      end
      handle.close if handle&.respond_to?(:close)
      nil
    end

    private

    def load_functions
      # Fiddle does not expose RTLD_LOCAL on every supported Ruby even though
      # local visibility is the native loader default when RTLD_GLOBAL is absent.
      @handle = Fiddle::Handle.new(@library_path, Fiddle::RTLD_NOW)
      @abi = function('strling_interop_abi_version_v1', [], Fiddle::TYPE_UINT)
      @execute = function(
        'strling_interop_execute_v1',
        [Fiddle::TYPE_VOIDP, Fiddle::TYPE_SIZE_T, Fiddle::TYPE_VOIDP],
        Fiddle::TYPE_UINT
      )
      @free = function(
        'strling_interop_owned_bytes_free_v1',
        [Fiddle::TYPE_VOIDP],
        Fiddle::TYPE_UINT
      )
      actual = @abi.call
      return if actual == NATIVE_ABI_VERSION

      @handle.close
      @handle = nil
      raise NativeAdapterError.new(:native_abi, "expected strling.c-abi #{NATIVE_ABI_VERSION}", status: actual)
    rescue Fiddle::DLError => e
      @handle&.close
      @handle = nil
      raise NativeAdapterError.new(:native_load, "cannot load native STRling library: #{e.message}")
    end

    def function(symbol, arguments, result)
      Fiddle::Function.new(@handle[symbol], arguments, result)
    end

    def begin_call
      @mutex.synchronize do
        raise NativeAdapterError.new(:closed_client, 'native STRling client is closed') if @closed

        @active_calls += 1
      end
    end

    def end_call
      @mutex.synchronize do
        @active_calls -= 1
        @condition.broadcast if @active_calls.zero?
      end
    end

    def execute_bytes(encoded)
      input = Fiddle::Pointer.malloc(encoded.bytesize, Fiddle::RUBY_FREE)
      input[0, encoded.bytesize] = encoded unless encoded.empty?
      descriptor_size = Fiddle::SIZEOF_VOIDP + Fiddle::SIZEOF_SIZE_T
      output = Fiddle::Pointer.malloc(descriptor_size, Fiddle::RUBY_FREE)
      output[0, descriptor_size] = "\0" * descriptor_size
      primary_error = nil
      begin
        status = @execute.call(encoded.empty? ? 0 : input, encoded.bytesize, output)
        unless status == STATUS_RESPONSE_WRITTEN
          raise NativeAdapterError.new(:native_abi, 'native STRling execution failed', status: status)
        end
        address = output[0, Fiddle::SIZEOF_VOIDP].unpack1(pointer_pack)
        length = output[Fiddle::SIZEOF_VOIDP, Fiddle::SIZEOF_SIZE_T].unpack1(size_pack)
        if address.zero? || length.zero? || length > MAX_INTEROP_RESPONSE_BYTES
          raise NativeAdapterError.new(:transport, 'native STRling returned an invalid or oversized response')
        end
        raw = Fiddle::Pointer.new(address)[0, length]
        decode_response(raw)
      rescue StandardError => e
        primary_error = e
        raise
      ensure
        release_status = @free.call(output)
        if primary_error.nil? && release_status != STATUS_RESPONSE_WRITTEN
          raise NativeAdapterError.new(:native_abi, 'native STRling response release failed', status: release_status)
        end
      end
    end

    def pointer_pack
      Fiddle::SIZEOF_VOIDP == 8 ? 'Q' : 'L'
    end

    def size_pack
      Fiddle::SIZEOF_SIZE_T == 8 ? 'Q' : 'L'
    end

    class StrictObject < Hash
      def []=(key, value)
        raise JSON::ParserError, "duplicate property #{key.inspect}" if key?(key)

        super
      end
    end
    private_constant :StrictObject

    def decode_response(raw)
      text = raw.dup.force_encoding(Encoding::UTF_8)
      raise NativeAdapterError.new(:transport, 'native STRling response is not strict UTF-8') unless text.valid_encoding?

      value = JSON.parse(text, object_class: StrictObject, create_additions: false)
      unless value.is_a?(Hash) && value['interop_protocol_version'] == INTEROP_PROTOCOL_VERSION
        raise NativeAdapterError.new(:transport, 'interop response has an unsupported version')
      end
      status = value['status']
      unless %w[completed error].include?(status)
        raise NativeAdapterError.new(:transport, 'interop response has an unsupported status')
      end
      if status == 'completed'
        raise NativeAdapterError.new(:transport, 'completed interop response has no result') unless value.key?('result')
      else
        error = value['error']
        unless error.is_a?(Hash) && error['code'].is_a?(String) && error['path'].is_a?(String)
          raise NativeAdapterError.new(:transport, 'failed interop response has no stable code and path')
        end
      end
      value
    rescue JSON::ParserError => e
      raise NativeAdapterError.new(:transport, "native STRling response is not strict JSON: #{e.message}")
    end

    def envelope(operation, payload)
      {
        'interop_protocol_version' => INTEROP_PROTOCOL_VERSION,
        'operation' => operation,
        'payload' => payload
      }
    end

    def completed_result(request)
      response = execute(request)
      raise InteropProtocolError, response if response['status'] == 'error'

      response['result']
    end
  end
end
