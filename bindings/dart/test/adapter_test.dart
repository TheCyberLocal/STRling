import 'dart:convert';
import 'dart:io';
import 'dart:isolate';

import 'package:path/path.dart' as path;
import 'package:strling/strling.dart';
import 'package:test/test.dart';

void main() {
  test('source request contains canonical envelope data', () {
    final request = sourceCompileRequest("'hello'");
    expect(request['contract_version'], '1.0.0');
    final input = request['input']! as Map<String, Object?>;
    final document = input['document']! as Map<String, Object?>;
    expect(document['source_id'], 'src:dart.adapter');
  });

  test('stdlib helper records identity without semantics', () {
    expect(email('root'), {
      'step_id': 'root',
      'operation': 'stdlib_helper',
      'arguments': {
        'helper_id': 'stdlib.email',
        'parameters': <String, Object?>{},
      },
    });
  });

  test('relative native path fails closed', () {
    expect(
      () => NativeClient.load('relative/strling'),
      throwsA(
        isA<NativeAdapterException>().having(
          (error) => error.kind,
          'kind',
          NativeErrorKind.load,
        ),
      ),
    );
  });

  test('native adapter preserves canonical operations and lifecycle', () async {
    final configured = Platform.environment['STRLING_NATIVE_LIBRARY'];
    if (configured == null || configured.isEmpty) {
      markTestSkipped(
        'STRLING_NATIVE_LIBRARY is required for governed integration execution',
      );
      return;
    }
    final nativePath = path.normalize(path.absolute(configured));
    final client = NativeClient.load(nativePath);
    final describe = client.describe();
    final compile = client.compile(
      sourceCompileRequest(
        'literal "héllo\u0000世界"',
        sourceId: 'src:adapter.parity',
      ),
    );
    final profileFile = File(
      path.normalize(
        path.join(
          Directory.current.path,
          '..',
          '..',
          'spec',
          'targets',
          'profiles',
          'pcre2-10.43.json',
        ),
      ),
    );
    final profile = jsonDecode(profileFile.readAsStringSync())
        as Map<String, Object?>;
    final inspected = client.inspectTargetProfile(profile);
    final builder = simplyBuilderRequest([email('parity-root')], 'parity-root')
      ..['identity_namespace'] = 'adapter-parity';
    final simply = client.simplyCompile(builder);

    final concurrent = await Future.wait(
      List.generate(
        8,
        (_) => Isolate.run(() {
          final isolated = NativeClient.load(nativePath);
          try {
            return isolated.describe() is Map<String, Object?>;
          } finally {
            isolated.close();
          }
        }),
      ),
    );
    expect(concurrent, everyElement(isTrue));

    _writeEvidence({
      'describe': describe,
      'compile': compile,
      'target_profile': inspected,
      'simply': simply,
    });
    client.close();
    client.close();
    expect(
      client.describe,
      throwsA(
        isA<NativeAdapterException>().having(
          (error) => error.kind,
          'kind',
          NativeErrorKind.closed,
        ),
      ),
    );
  }, timeout: const Timeout(Duration(minutes: 2)));

  test('native release probe requires same-descriptor free', () {
    final configured = Platform.environment['STRLING_GDS_RELEASE_PROBE'];
    if (configured == null || configured.isEmpty) {
      markTestSkipped(
        'STRLING_GDS_RELEASE_PROBE is required for governed lifecycle execution',
      );
      return;
    }
    final client = NativeClient.load(path.normalize(path.absolute(configured)));
    try {
      expect(client.describe(), isA<Map<String, Object?>>());
      expect(client.describe(), isA<Map<String, Object?>>());
    } finally {
      client.close();
    }
  });

  test('native ABI mismatch fails before execution', () {
    final configured = Platform.environment['STRLING_GDS_ABI_PROBE'];
    if (configured == null || configured.isEmpty) {
      markTestSkipped('STRLING_GDS_ABI_PROBE is required for governed ABI execution');
      return;
    }
    expect(
      () => NativeClient.load(path.normalize(path.absolute(configured))),
      throwsA(
        isA<NativeAdapterException>()
            .having((error) => error.kind, 'kind', NativeErrorKind.abi)
            .having((error) => error.status, 'status', 2),
      ),
    );
  });

  test('native oversized response fails closed', () {
    final configured = Platform.environment['STRLING_GDS_OVERSIZE_PROBE'];
    if (configured == null || configured.isEmpty) {
      markTestSkipped(
        'STRLING_GDS_OVERSIZE_PROBE is required for governed bounds execution',
      );
      return;
    }
    final client = NativeClient.load(path.normalize(path.absolute(configured)));
    try {
      expect(
        client.describe,
        throwsA(
          isA<NativeAdapterException>().having(
            (error) => error.kind,
            'kind',
            NativeErrorKind.transport,
          ),
        ),
      );
    } finally {
      client.close();
    }
  });

  test('native duplicate response fails closed', () {
    _expectTransportProbe('STRLING_GDS_DUPLICATE_PROBE');
  });

  test('native invalid UTF-8 response fails closed', () {
    _expectTransportProbe('STRLING_GDS_INVALID_UTF8_PROBE');
  });
}

void _expectTransportProbe(String environmentName) {
  final configured = Platform.environment[environmentName];
  if (configured == null || configured.isEmpty) {
    markTestSkipped('$environmentName is required for governed transport execution');
    return;
  }
  final client = NativeClient.load(path.normalize(path.absolute(configured)));
  try {
    expect(
      client.describe,
      throwsA(
        isA<NativeAdapterException>().having(
          (error) => error.kind,
          'kind',
          NativeErrorKind.transport,
        ),
      ),
    );
  } finally {
    client.close();
  }
}

void _writeEvidence(Map<String, Object?> observations) {
  final root = Platform.environment['STRLING_GDS_EVIDENCE_DIR'];
  if (root == null || root.isEmpty) return;
  final directory = Directory(path.join(root, 'dart'))..createSync(recursive: true);
  for (final entry in observations.entries) {
    File(path.join(directory.path, '${entry.key}.json'))
        .writeAsStringSync(jsonEncode(entry.value));
  }
}
