<?php

declare(strict_types=1);

namespace STRling;

final class Requests
{
    /** @param array<string, mixed> $options
     *  @return array<string, mixed>
     */
    public static function sourceCompileRequest(string $source, array $options = []): array
    {
        $specification = (string) ($options['specification_version'] ?? '1.0-draft.1');
        $frontend = (string) ($options['frontend_id'] ?? 'semantic_strling');
        $request = [
            'contract_version' => '1.0.0',
            'specification_version' => $specification,
            'input' => [
                'kind' => 'source',
                'document' => [
                    'contract_version' => '1.0.0',
                    'source_id' => (string) ($options['source_id'] ?? 'src:php.adapter'),
                    'specification_version' => $specification,
                    'frontend' => [
                        'id' => $frontend,
                        'dialect_version' => (string) ($options['frontend_version'] ?? $specification),
                    ],
                    'content' => [
                        'kind' => 'inline',
                        'encoding' => 'utf-8',
                        'media_type' => (string) ($options['media_type'] ?? 'text/strling'),
                        'text' => $source,
                    ],
                    'provenance' => ['kind' => 'authored'],
                ],
            ],
            'requested_outputs' => $options['requested_outputs'] ?? ['semantic', 'analysis'],
            'compiler_options' => $options['compiler_options'] ?? [
                'partial_semantics' => 'forbid',
                'diagnostic_policy' => ['minimum_severity' => 'hint'],
            ],
        ];
        if (isset($options['target_profile_reference'])) {
            $request['target_profile'] = $options['target_profile_reference'];
        }
        return $request;
    }

    /** @param array<string, mixed> $parameters
     *  @return array<string, mixed>
     */
    public static function stdlibHelper(string $stepId, string $helperId, array $parameters = []): array
    {
        return [
            'step_id' => $stepId,
            'operation' => 'stdlib_helper',
            'arguments' => [
                'helper_id' => $helperId,
                'parameters' => $parameters === [] ? new \stdClass() : $parameters,
            ],
        ];
    }

    /** @param list<array<string, mixed>> $steps
     *  @return array<string, mixed>
     */
    public static function simplyBuilderRequest(array $steps, string $rootStepId, string $identityNamespace = 'php.adapter'): array
    {
        return [
            'protocol_version' => '1.1.0',
            'contract_version' => '1.0.0',
            'specification_version' => '1.0-draft.1',
            'identity_namespace' => $identityNamespace,
            'semantic_options' => [
                'case_matching' => 'sensitive',
                'text_model' => 'unicode_scalar_values',
                'builtin_character_domain' => 'unicode',
                'wildcard_line_terminators' => 'exclude',
            ],
            'steps' => $steps,
            'root_step_id' => $rootStepId,
            'compile' => [
                'requested_outputs' => ['semantic', 'analysis'],
                'compiler_options' => [
                    'partial_semantics' => 'forbid',
                    'diagnostic_policy' => ['minimum_severity' => 'hint'],
                ],
            ],
        ];
    }
}
