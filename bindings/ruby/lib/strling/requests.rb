# frozen_string_literal: true

module Strling
  module_function

  def source_compile_request(source, options = {})
    prepared = options.transform_keys(&:to_sym)
    specification = prepared.fetch(:specification_version, '1.0-draft.1').to_s
    frontend = prepared.fetch(:frontend_id, 'semantic_strling').to_s
    request = {
      'contract_version' => '1.0.0',
      'specification_version' => specification,
      'input' => {
        'kind' => 'source',
        'document' => {
          'contract_version' => '1.0.0',
          'source_id' => prepared.fetch(:source_id, 'src:ruby.adapter').to_s,
          'specification_version' => specification,
          'frontend' => {
            'id' => frontend,
            'dialect_version' => prepared.fetch(:frontend_version, specification).to_s
          },
          'content' => {
            'kind' => 'inline',
            'encoding' => 'utf-8',
            'media_type' => prepared.fetch(:media_type, 'text/strling').to_s,
            'text' => String(source)
          },
          'provenance' => { 'kind' => 'authored' }
        }
      },
      'requested_outputs' => prepared.fetch(:requested_outputs, %w[semantic analysis]),
      'compiler_options' => prepared.fetch(
        :compiler_options,
        {
          'partial_semantics' => 'forbid',
          'diagnostic_policy' => { 'minimum_severity' => 'hint' }
        }
      )
    }
    target = prepared[:target_profile_reference]
    request['target_profile'] = target unless target.nil?
    request
  end

  def stdlib_helper(step_id, helper_id, parameters = {})
    {
      'step_id' => String(step_id),
      'operation' => 'stdlib_helper',
      'arguments' => {
        'helper_id' => String(helper_id),
        'parameters' => parameters
      }
    }
  end

  def simply_builder_request(steps, root_step_id, identity_namespace: 'ruby.adapter')
    {
      'protocol_version' => '1.1.0',
      'contract_version' => '1.0.0',
      'specification_version' => '1.0-draft.1',
      'identity_namespace' => identity_namespace,
      'semantic_options' => {
        'case_matching' => 'sensitive',
        'text_model' => 'unicode_scalar_values',
        'builtin_character_domain' => 'unicode',
        'wildcard_line_terminators' => 'exclude'
      },
      'steps' => steps,
      'root_step_id' => String(root_step_id),
      'compile' => {
        'requested_outputs' => %w[semantic analysis],
        'compiler_options' => {
          'partial_semantics' => 'forbid',
          'diagnostic_policy' => { 'minimum_severity' => 'hint' }
        }
      }
    }
  end
end
