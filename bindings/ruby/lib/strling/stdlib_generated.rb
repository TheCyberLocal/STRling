# frozen_string_literal: true

# Generated from the canonical standard-library registry. Do not edit.
# These lexical helpers record Simply recipes; they do not validate semantics.
module Strling
  STDLIB_SURFACE_SOURCE_SHA256 = '94f28b16873abd0b57b324b76e236cbe17706f5310758e066a88a776e4930a3d'
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
