import 'dart:convert';
import 'dart:io';

import 'package:strling/essential.dart';
import 'package:test/test.dart';

String _findSpec() {
  var dir = Directory.current.path;
  for (var i = 0; i < 10; i++) {
    final p = '$dir/spec/stdlib/essential_5.json';
    if (File(p).existsSync()) return p;
    dir = '$dir/..';
  }
  throw StateError('essential_5.json not found');
}

RegExp _re(node) => RegExp('^(?:${Essential.compile(node)})\$');

void _allMatch(node, List samples) {
  final re = _re(node);
  for (final s in samples) {
    expect(re.hasMatch(s as String), isTrue, reason: 'expected match: $s');
  }
}

void _noneMatch(node, List samples) {
  final re = _re(node);
  for (final s in samples) {
    expect(re.hasMatch(s as String), isFalse, reason: 'unexpected match: $s');
  }
}

void main() {
  final spec = jsonDecode(File(_findSpec()).readAsStringSync()) as Map;
  final patterns = spec['patterns'] as Map;
  List fx(String p, String k) => patterns[p]['fixtures'][k] as List;

  group('Essential 5', () {
    test('email valid',   () => _allMatch(Essential.email(), fx('email', 'valid')));
    test('email invalid', () => _noneMatch(Essential.email(), fx('email', 'invalid')));
    test('url valid',     () => _allMatch(Essential.url(), fx('url', 'valid')));
    test('url invalid',   () => _noneMatch(Essential.url(), fx('url', 'invalid')));
    test('uuid default valid',   () => _allMatch(Essential.uuid(), fx('uuid', 'valid_default')));
    test('uuid default invalid', () => _noneMatch(Essential.uuid(), fx('uuid', 'invalid_default')));
    test('uuid v4 valid',   () => _allMatch(Essential.uuid(version: 4), fx('uuid', 'valid_v4')));
    test('uuid v4 invalid', () => _noneMatch(Essential.uuid(version: 4), fx('uuid', 'invalid_v4')));
    test('ip v4 valid',   () => _allMatch(Essential.ip(version: 4), fx('ip', 'valid_v4')));
    test('ip v4 invalid', () => _noneMatch(Essential.ip(version: 4), fx('ip', 'invalid_v4')));
    test('ip v6 valid',   () => _allMatch(Essential.ip(version: 6), fx('ip', 'valid_v6')));
    test('ip v6 invalid', () => _noneMatch(Essential.ip(version: 6), fx('ip', 'invalid_v6')));
    test('ip any v4',     () => _allMatch(Essential.ip(), fx('ip', 'valid_v4')));
    test('ip any v6',     () => _allMatch(Essential.ip(), fx('ip', 'valid_v6')));
    test('dateTime valid',   () => _allMatch(Essential.dateTime(), fx('dateTime', 'valid')));
    test('dateTime invalid', () => _noneMatch(Essential.dateTime(), fx('dateTime', 'invalid')));
  });
}
