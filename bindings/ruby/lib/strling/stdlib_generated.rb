# frozen_string_literal: true

# Generated from the canonical standard-library registry. Do not edit.
# These lexical helpers record Simply recipes; they do not validate semantics.
module Strling
  STDLIB_SURFACE_SOURCE_SHA256 = '36779a57c8016a0ff4a1ba00e9c6cb198246bf8e170edb1e0d627c0ed91f19a0'
  STDLIB_REGISTRY_VERSION = '1.0.0'
  STDLIB_HELPER_IDS = %w[stdlib.date_time stdlib.email stdlib.ip stdlib.url stdlib.uuid].freeze

  module_function

  def date_time(step_id)
    stdlib_helper(step_id, 'stdlib.date_time')
  end

  def email(step_id)
    stdlib_helper(step_id, 'stdlib.email')
  end

  def ip(step_id, version: nil)
    stdlib_helper(step_id, 'stdlib.ip', 'version' => version)
  end

  def url(step_id)
    stdlib_helper(step_id, 'stdlib.url')
  end

  def uuid(step_id, version: nil)
    stdlib_helper(step_id, 'stdlib.uuid', 'version' => version)
  end

end
