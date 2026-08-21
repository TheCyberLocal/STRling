# frozen_string_literal: true

require_relative 'strling/native_client'
require_relative 'strling/requests'
require_relative 'strling/stdlib_generated'

# Thin Ruby projection of the versioned canonical STRling interop protocol.
module Strling
  VERSION = '3.0.0'
  INTEROP_PROTOCOL_VERSION = '1.0.0'
  NATIVE_ABI_VERSION = 1
  MAX_INTEROP_REQUEST_BYTES = 10_485_760
  MAX_INTEROP_RESPONSE_BYTES = 33_554_432

  class Error < StandardError; end

  class NativeAdapterError < Error
    attr_reader :kind, :status

    def initialize(kind, message, status: nil)
      @kind = kind
      @status = status
      super(status.nil? ? message : "#{message} (status #{status})")
    end
  end

  class InteropProtocolError < Error
    attr_reader :code, :path, :operation

    def initialize(response)
      error = response.fetch('error')
      @code = error.fetch('code')
      @path = error.fetch('path')
      @operation = response['operation']
      super("#{code} at #{path}")
    end
  end

  module_function

  def load_native(library_path)
    NativeClient.load(library_path)
  end
end
