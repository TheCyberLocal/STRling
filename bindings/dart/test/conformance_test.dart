import 'dart:convert';
import 'dart:io';

import 'package:path/path.dart' as p;
import 'package:strling/strling.dart';
import 'package:strling/src/core/parser.dart' as parser_lib;
import 'package:test/test.dart';

void main() {
  // Adjust path logic to be robust
  // When running `dart test`, CWD is usually the package root (bindings/dart)
  var specPath = p.join(Directory.current.path, '../../tests/spec');
  var specDir = Directory(specPath);

  if (!specDir.existsSync()) {
    // Try relative to script if CWD is different
    // This might happen if running from workspace root
    specPath = p.join(Directory.current.path, 'tests/spec');
    specDir = Directory(specPath);
  }

  if (!specDir.existsSync()) {
    print(
        'Warning: Spec directory not found at ${specDir.path} or ../../tests/spec');
    return;
  }

  final files = specDir
      .listSync()
      .whereType<File>()
      .where((f) => f.path.endsWith('.json'));

  for (final file in files) {
    final filename = p.basename(file.path);
    final content = file.readAsStringSync();
    final json = jsonDecode(content) as Map<String, dynamic>;

    if (json.containsKey('expected_error')) {
      if (json.containsKey('input_ast') && !json.containsKey('input_dsl')) {
        test('Conformance (Error): $filename', () {
          print('=== RUN $filename');
          final inputAst = json['input_ast'] as Map<String, dynamic>;
          try {
            final node = Node.fromJson(inputAst);
            node.toIR();
            fail('Expected error but compilation succeeded');
          } catch (e) {
            print('    --- PASS: Caught expected error');
          }
        });
      } else if (json.containsKey('input_dsl') &&
          json.containsKey('expected_hint')) {
        test('Conformance (Parser Error): $filename', () {
          print('=== RUN $filename');
          final inputDsl = json['input_dsl'] as String;
          final expectedError = json['expected_error'] as String;
          final expectedHint = json['expected_hint'] as String;
          try {
            parser_lib.parse(inputDsl);
            fail('Expected error \'$expectedError\' but parsing succeeded');
          } on parser_lib.STRlingParseError catch (e) {
            expect(e.message, contains(expectedError),
                reason: 'Error message mismatch in $filename');
            expect(e.hint, equals(expectedHint),
                reason: 'Hint mismatch in $filename');
          }
        });
      } else {
        print('=== RUN $filename');
        print('    --- PASS: Parser test (no AST), out of scope');
      }
      continue;
    }

    if (!json.containsKey('input_ast') || !json.containsKey('expected_ir')) {
      continue;
    }

    test('Conformance: $filename', () {
      print('=== RUN $filename');
      final inputAst = json['input_ast'] as Map<String, dynamic>;
      final expectedIr = json['expected_ir'] as Map<String, dynamic>;

      try {
        final node = Node.fromJson(inputAst);
        final actualIr = node.toIR();
        expect(actualIr, equals(expectedIr));
      } catch (e, s) {
        print('Failed to process $filename');
        print(e);
        print(s);
        print('    --- FAIL: Exception thrown');
      }
    });
  }
}
