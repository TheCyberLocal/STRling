// Generated from the canonical standard-library registry. Do not edit.
// These lexical helpers record Simply recipes; they do not validate semantics.
import 'requests.dart';

const stdlibSurfaceSourceSha256 =
    '94f28b16873abd0b57b324b76e236cbe17706f5310758e066a88a776e4930a3d';
const stdlibRegistryVersion = '1.0.0';
const stdlibHelperIds = <String>[
  'stdlib.date_time',
  'stdlib.email',
  'stdlib.ip',
  'stdlib.url',
  'stdlib.uuid',
];

SimplyStep dateTime(String stepId) =>
    stdlibHelper(stepId, 'stdlib.date_time', const <String, Object?>{});

SimplyStep email(String stepId) =>
    stdlibHelper(stepId, 'stdlib.email', const <String, Object?>{});

SimplyStep ip(String stepId, {int? version}) => stdlibHelper(
      stepId,
      'stdlib.ip',
      <String, Object?>{'version': version},
    );

SimplyStep url(String stepId) =>
    stdlibHelper(stepId, 'stdlib.url', const <String, Object?>{});

SimplyStep uuid(String stepId, {int? version}) => stdlibHelper(
      stepId,
      'stdlib.uuid',
      <String, Object?>{'version': version},
    );
