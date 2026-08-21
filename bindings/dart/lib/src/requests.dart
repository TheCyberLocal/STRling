const _contractVersion = '1.0.0';
const _specificationVersion = '1.0-draft.1';

typedef SimplyStep = Map<String, Object?>;

Map<String, Object?> sourceCompileRequest(
  String source, {
  String specificationVersion = _specificationVersion,
  String frontendId = 'semantic_strling',
  String? frontendVersion,
  String sourceId = 'src:dart.adapter',
  String mediaType = 'text/strling',
  List<String> requestedOutputs = const ['semantic', 'analysis'],
  Map<String, Object?>? compilerOptions,
  Map<String, Object?>? targetProfileReference,
}) {
  final request = <String, Object?>{
    'contract_version': _contractVersion,
    'specification_version': specificationVersion,
    'input': <String, Object?>{
      'kind': 'source',
      'document': <String, Object?>{
        'contract_version': _contractVersion,
        'source_id': sourceId,
        'specification_version': specificationVersion,
        'frontend': <String, Object?>{
          'id': frontendId,
          'dialect_version': frontendVersion ?? specificationVersion,
        },
        'content': <String, Object?>{
          'kind': 'inline',
          'encoding': 'utf-8',
          'media_type': mediaType,
          'text': source,
        },
        'provenance': const <String, Object?>{'kind': 'authored'},
      },
    },
    'requested_outputs': List<String>.of(requestedOutputs),
    'compiler_options': compilerOptions ??
        const <String, Object?>{
          'partial_semantics': 'forbid',
          'diagnostic_policy': <String, Object?>{'minimum_severity': 'hint'},
        },
  };
  if (targetProfileReference != null) {
    request['target_profile'] = targetProfileReference;
  }
  return request;
}

SimplyStep stdlibHelper(
  String stepId,
  String helperId,
  Map<String, Object?> parameters,
) =>
    <String, Object?>{
      'step_id': stepId,
      'operation': 'stdlib_helper',
      'arguments': <String, Object?>{
        'helper_id': helperId,
        'parameters': parameters,
      },
    };

Map<String, Object?> simplyBuilderRequest(
  List<SimplyStep> steps,
  String rootStepId,
) =>
    <String, Object?>{
      'protocol_version': '1.1.0',
      'contract_version': _contractVersion,
      'specification_version': _specificationVersion,
      'identity_namespace': 'dart.adapter',
      'semantic_options': const <String, Object?>{
        'case_matching': 'sensitive',
        'text_model': 'unicode_scalar_values',
        'builtin_character_domain': 'unicode',
        'wildcard_line_terminators': 'exclude',
      },
      'steps': steps,
      'root_step_id': rootStepId,
      'compile': const <String, Object?>{
        'requested_outputs': <String>['semantic', 'analysis'],
        'compiler_options': <String, Object?>{
          'partial_semantics': 'forbid',
          'diagnostic_policy': <String, Object?>{'minimum_severity': 'hint'},
        },
      },
    };
