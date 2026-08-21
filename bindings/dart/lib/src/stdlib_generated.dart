// Generated from the canonical standard-library registry. Do not edit.
// These lexical helpers record Simply recipes; they do not validate semantics.
import 'requests.dart';

const stdlibSurfaceSourceSha256 =
    '36779a57c8016a0ff4a1ba00e9c6cb198246bf8e170edb1e0d627c0ed91f19a0';
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
