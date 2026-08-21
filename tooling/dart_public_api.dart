import 'dart:convert';
import 'dart:io';

import 'package:analyzer/dart/analysis/analysis_context_collection.dart';
import 'package:analyzer/dart/analysis/results.dart';
import 'package:analyzer/dart/element/element.dart';

Future<void> main(List<String> arguments) async {
  if (arguments.length != 1) {
    stderr.writeln('usage: dart_public_api.dart <library-entrypoint>');
    exitCode = 2;
    return;
  }
  final entry = File(arguments.single).absolute.path;
  if (!File(entry).existsSync()) {
    stderr.writeln('Dart public library is unavailable: $entry');
    exitCode = 2;
    return;
  }
  final packageRoot = File(entry).parent.parent.path;
  final collection = AnalysisContextCollection(includedPaths: [packageRoot]);
  final context = collection.contextFor(entry);
  final result = await context.currentSession.getResolvedLibrary(entry);
  if (result is! ResolvedLibraryResult) {
    stderr.writeln('Dart public library did not resolve: $result');
    exitCode = 2;
    return;
  }

  final symbols = <String, String>{};
  final entries = result.element.exportNamespace.definedNames.entries.toList()
    ..sort((left, right) => left.key.compareTo(right.key));
  for (final entry in entries) {
    _record(symbols, entry.value, 'export::${entry.key}');
  }
  if (symbols.isEmpty) {
    stderr.writeln('Dart analyzer returned no public symbols');
    exitCode = 2;
    return;
  }
  stdout.write(jsonEncode(Map<String, String>.fromEntries(
    symbols.entries.toList()..sort((left, right) => left.key.compareTo(right.key)),
  )));
}

void _record(Map<String, String> symbols, Element element, String owner) {
  if (element.displayName.startsWith('_')) return;
  final kind = element.kind.displayName;
  final key = '$owner::$kind::${element.displayName}';
  symbols[key] = element.getDisplayString(withNullability: true);

  if (element is InterfaceElement) {
    for (final constructor in element.constructors) {
      _recordMember(symbols, constructor, key);
    }
    for (final field in element.fields.where((field) => !field.isSynthetic)) {
      _recordMember(symbols, field, key);
    }
    for (final accessor in element.accessors.where((item) => !item.isSynthetic)) {
      _recordMember(symbols, accessor, key);
    }
    for (final method in element.methods) {
      _recordMember(symbols, method, key);
    }
  } else if (element is ExtensionElement) {
    for (final field in element.fields.where((field) => !field.isSynthetic)) {
      _recordMember(symbols, field, key);
    }
    for (final accessor in element.accessors.where((item) => !item.isSynthetic)) {
      _recordMember(symbols, accessor, key);
    }
    for (final method in element.methods) {
      _recordMember(symbols, method, key);
    }
  }
}

void _recordMember(Map<String, String> symbols, Element element, String owner) {
  if (element.displayName.startsWith('_')) return;
  final kind = element.kind.displayName;
  final key = '$owner::$kind::${element.displayName}';
  symbols[key] = element.getDisplayString(withNullability: true);
}
