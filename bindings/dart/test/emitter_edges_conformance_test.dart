/// Emitter Edges Conformance — Dart bridge.
///
/// Drives the global pathological-AST fixture
/// `tests/conformance/inputs/emitter_edges/pathological.json` through
/// the Dart [Pcre2Emitter] and asserts each safety guard fires:
///   1. Variable-Length Lookbehind Rejection — STRlingCompilationError
///   2. AST Depth Limit Exceeded             — STRlingCompilationError
///   3. ReDoS Risk Warning (`(a+)+`)         — non-fatal STRlingWarning
///
/// The local [astToIr] mirrors the TypeScript bridge so the test targets
/// the emitter without coupling to the parser/compiler stages. Keep it
/// minimal — supporting only node types currently appearing in
/// `pathological.json` — so adapter omissions cannot mask emitter bugs
/// by silently dropping nodes.
library;

import 'dart:convert';
import 'dart:io';
import 'package:test/test.dart';
import 'package:strling/src/emitters/pcre2.dart';
import 'package:strling/src/core/diagnostics.dart';

String _findFixture() {
  var dir = Directory.current.path;
  for (var i = 0; i < 12; i++) {
    if (File('$dir${Platform.pathSeparator}toolchain.json').existsSync()) {
      return [
        dir,
        'tests',
        'conformance',
        'inputs',
        'emitter_edges',
        'pathological.json'
      ].join(Platform.pathSeparator);
    }
    final parent = Directory(dir).parent.path;
    if (parent == dir) break;
    dir = parent;
  }
  throw StateError(
      'could not locate workspace root from ${Directory.current.path}');
}

Map<String, dynamic> astToIr(Map<String, dynamic> node) {
  final type = node['type'] as String;
  switch (type) {
    case 'Literal':
      return {'ir': 'Lit', 'value': (node['value'] ?? '').toString()};
    case 'Group':
      return {
        'ir': 'Group',
        'capturing': false,
        'body': astToIr(node['content'] as Map<String, dynamic>),
      };
    case 'Quantifier':
      final rawMax = node['max'];
      // null/missing in the user-facing AST means unbounded → IR sentinel "Inf".
      final max = rawMax == null ? 'Inf' : rawMax;
      return {
        'ir': 'Quant',
        'child': astToIr(node['content'] as Map<String, dynamic>),
        'min': (node['min'] as num).toInt(),
        'max': max,
        'mode': 'Greedy',
      };
    case 'Lookbehind':
      return {
        'ir': 'Look',
        'dir': 'Behind',
        'neg': false,
        'body': astToIr(node['content'] as Map<String, dynamic>),
      };
    case 'NegativeLookbehind':
      return {
        'ir': 'Look',
        'dir': 'Behind',
        'neg': true,
        'body': astToIr(node['content'] as Map<String, dynamic>),
      };
    case 'Lookahead':
      return {
        'ir': 'Look',
        'dir': 'Ahead',
        'neg': false,
        'body': astToIr(node['content'] as Map<String, dynamic>),
      };
    case 'NegativeLookahead':
      return {
        'ir': 'Look',
        'dir': 'Ahead',
        'neg': true,
        'body': astToIr(node['content'] as Map<String, dynamic>),
      };
  }
  throw StateError(
    'astToIr: unsupported pathological AST node type "$type". '
    'Extend the adapter when new pathological vectors are added.',
  );
}

String _expectedSubstring(String prefixed) {
  if (prefixed.startsWith('STRlingCompilationError:')) {
    return prefixed.substring('STRlingCompilationError:'.length).trimLeft();
  }
  if (prefixed.startsWith('STRlingWarning')) {
    final idx = prefixed.indexOf(']');
    if (idx >= 0) {
      return prefixed.substring(idx + 1).replaceFirst(RegExp(r'^[: ]+'), '');
    }
  }
  return prefixed;
}

void main() {
  group('EmitterEdgesConformance — pathological.json', () {
    final raw = File(_findFixture()).readAsStringSync();
    final doc = json.decode(raw) as Map<String, dynamic>;
    final cases = doc['tests'] as List;

    test('fixture is non-empty', () {
      expect(cases, isNotEmpty);
    });

    for (final tcDyn in cases) {
      final tc = tcDyn as Map<String, dynamic>;
      final name = tc['name']?.toString() ?? '<unnamed>';
      test(name, () {
        final ir = astToIr(tc['ast'] as Map<String, dynamic>);
        final maxDepth = (tc['depth_override_for_test'] as num?)?.toInt() ?? 0;

        if (tc.containsKey('expected_error')) {
          final needle = _expectedSubstring(tc['expected_error'].toString());
          STRlingCompilationError? caught;
          try {
            Pcre2Emitter().emitWithDiagnostics(ir, null, maxDepth);
          } on STRlingCompilationError catch (e) {
            caught = e;
          }
          expect(caught, isNotNull,
              reason: '[$name] expected STRlingCompilationError');
          expect(caught!.message, contains(needle), reason: '[$name]');
        } else if (tc.containsKey('expected_warning')) {
          final needle = _expectedSubstring(tc['expected_warning'].toString());
          final result = Pcre2Emitter().emitWithDiagnostics(ir, null, maxDepth);
          // Warnings must NOT abort emission — the pattern is still produced.
          expect(result.pattern, isNotEmpty,
              reason:
                  '[$name] expected non-empty pattern when only a warning fires');
          final hit = result.warnings
              .any((w) => w.code == 'REDOS_RISK' && w.message.contains(needle));
          expect(hit, isTrue,
              reason:
                  '[$name] missing REDOS_RISK warning containing "$needle"');
        } else {
          fail('[$name] declares neither expected_error nor expected_warning');
        }
      });
    }
  });

  group('EmitterEdgesConformance — negative controls', () {
    test('non-pathological emits no warnings', () {
      final result =
          Pcre2Emitter().emitWithDiagnostics({'ir': 'Lit', 'value': 'abc'});
      expect(result.pattern, equals('abc'));
      expect(result.warnings, isEmpty);
    });

    test('depth cap does not fire under limit', () {
      final ir = {
        'ir': 'Group',
        'capturing': false,
        'body': {
          'ir': 'Group',
          'capturing': false,
          'body': {'ir': 'Lit', 'value': 'ok'},
        },
      };
      final result = Pcre2Emitter().emitWithDiagnostics(ir, null, 5);
      expect(result.warnings, isEmpty);
      expect(result.pattern, contains('ok'));
    });
  });
}
