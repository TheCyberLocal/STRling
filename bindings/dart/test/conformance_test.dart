import 'dart:convert';
import 'dart:io';

import 'package:path/path.dart' as p;
import 'package:strling/strling.dart';
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
    print('Warning: Spec directory not found at ${specDir.path} or ../../tests/spec');
    return;
  }

  final files = specDir.listSync().whereType<File>().where((f) => f.path.endsWith('.json'));

  for (final file in files) {
    final filename = p.basename(file.path);
    final content = file.readAsStringSync();
    final json = jsonDecode(content) as Map<String, dynamic>;

    if (!json.containsKey('input_ast') || !json.containsKey('expected_ir')) {
      continue;
    }

    test('Conformance: $filename', () {
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
        rethrow;
      }
    });
  }
}
