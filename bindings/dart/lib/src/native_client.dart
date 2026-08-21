import 'dart:convert';
import 'dart:ffi';
import 'dart:io';
import 'dart:typed_data';

import 'package:ffi/ffi.dart';
import 'package:path/path.dart' as path;

const interopProtocolVersion = '1.0.0';
const nativeAbiVersion = 1;
const maxInteropRequestBytes = 10485760;
const maxInteropResponseBytes = 33554432;

final class _OwnedBytes extends Struct {
  external Pointer<Uint8> data;

  @UintPtr()
  external int length;
}

typedef _AbiNative = Uint32 Function();
typedef _AbiDart = int Function();
typedef _ExecuteNative = Uint32 Function(
  Pointer<Uint8>,
  UintPtr,
  Pointer<_OwnedBytes>,
);
typedef _ExecuteDart = int Function(Pointer<Uint8>, int, Pointer<_OwnedBytes>);
typedef _FreeNative = Uint32 Function(Pointer<_OwnedBytes>);
typedef _FreeDart = int Function(Pointer<_OwnedBytes>);

enum NativeErrorKind { load, abi, closed, transport }

class NativeAdapterException implements Exception {
  NativeAdapterException(this.kind, this.message, {this.status});

  final NativeErrorKind kind;
  final String message;
  final int? status;

  @override
  String toString() => status == null
      ? 'NativeAdapterException(${kind.name}): $message'
      : 'NativeAdapterException(${kind.name}, status $status): $message';
}

class InteropProtocolException implements Exception {
  InteropProtocolException(this.code, this.path, this.operation);

  final String code;
  final String path;
  final String? operation;

  @override
  String toString() => 'InteropProtocolException: $code at $path';
}

class NativeClient {
  NativeClient._(
    this.libraryPath,
    this._execute,
    this._free,
  );

  factory NativeClient.load(String libraryPath) {
    if (libraryPath.isEmpty || !path.isAbsolute(libraryPath)) {
      throw NativeAdapterException(
        NativeErrorKind.load,
        'native STRling library path must be absolute',
      );
    }
    final normalized = path.normalize(libraryPath);
    if (!File(normalized).existsSync()) {
      throw NativeAdapterException(
        NativeErrorKind.load,
        'native STRling library not found: $normalized',
      );
    }
    try {
      final library = DynamicLibrary.open(normalized);
      final abi = library.lookupFunction<_AbiNative, _AbiDart>(
        'strling_interop_abi_version_v1',
      );
      final execute = library.lookupFunction<_ExecuteNative, _ExecuteDart>(
        'strling_interop_execute_v1',
      );
      final free = library.lookupFunction<_FreeNative, _FreeDart>(
        'strling_interop_owned_bytes_free_v1',
      );
      final actual = abi();
      if (actual != nativeAbiVersion) {
        throw NativeAdapterException(
          NativeErrorKind.abi,
          'expected strling.c-abi $nativeAbiVersion',
          status: actual,
        );
      }
      return NativeClient._(normalized, execute, free);
    } on NativeAdapterException {
      rethrow;
    } catch (error) {
      throw NativeAdapterException(
        NativeErrorKind.load,
        'cannot load native STRling library: $error',
      );
    }
  }

  final String libraryPath;
  final _ExecuteDart _execute;
  final _FreeDart _free;
  bool _closed = false;

  bool get isClosed => _closed;

  Map<String, Object?> execute(Object? request) {
    if (_closed) {
      throw NativeAdapterException(
        NativeErrorKind.closed,
        'native STRling client is closed',
      );
    }
    final Uint8List encoded;
    try {
      encoded = Uint8List.fromList(utf8.encode(jsonEncode(request)));
    } catch (error) {
      throw NativeAdapterException(
        NativeErrorKind.transport,
        'interop request is not strict JSON: $error',
      );
    }
    if (encoded.length > maxInteropRequestBytes) {
      throw NativeAdapterException(
        NativeErrorKind.transport,
        'interop request exceeds $maxInteropRequestBytes bytes',
      );
    }

    final input = encoded.isEmpty ? nullptr : calloc<Uint8>(encoded.length);
    if (encoded.isNotEmpty) {
      input.asTypedList(encoded.length).setAll(0, encoded);
    }
    final output = calloc<_OwnedBytes>();
    Object? primaryError;
    try {
      final status = _execute(input, encoded.length, output);
      if (status != 0) {
        throw NativeAdapterException(
          NativeErrorKind.abi,
          'native STRling execution failed',
          status: status,
        );
      }
      final length = output.ref.length;
      if (output.ref.data == nullptr ||
          length == 0 ||
          length > maxInteropResponseBytes) {
        throw NativeAdapterException(
          NativeErrorKind.transport,
          'native STRling returned an invalid or oversized response',
        );
      }
      final bytes = Uint8List.fromList(output.ref.data.asTypedList(length));
      return _decodeResponse(bytes);
    } catch (error) {
      primaryError = error;
      rethrow;
    } finally {
      final freeStatus = _free(output);
      calloc.free(output);
      if (input != nullptr) {
        calloc.free(input);
      }
      if (primaryError == null && freeStatus != 0) {
        throw NativeAdapterException(
          NativeErrorKind.abi,
          'native STRling response release failed',
          status: freeStatus,
        );
      }
    }
  }

  Object? describe() => _completedResult(_envelope('describe', const {}));

  Object? compile(
    Map<String, Object?> compileRequest, {
    Map<String, Object?>? targetProfile,
  }) {
    final payload = <String, Object?>{'compile_request': compileRequest};
    if (targetProfile != null) {
      payload['target_profile'] = targetProfile;
    }
    return _completedResult(_envelope('compile', payload));
  }

  Object? inspectTargetProfile(Map<String, Object?> targetProfile) =>
      _completedResult(
        _envelope(
          'target_profile.inspect',
          <String, Object?>{'target_profile': targetProfile},
        ),
      );

  Object? simplyCompile(
    Map<String, Object?> builderRequest, {
    Map<String, Object?>? targetProfile,
  }) {
    final payload = <String, Object?>{'builder_request': builderRequest};
    if (targetProfile != null) {
      payload['target_profile'] = targetProfile;
    }
    return _completedResult(_envelope('simply.compile', payload));
  }

  void close() {
    _closed = true;
    // Dart owns DynamicLibrary handle lifetime and exposes no deterministic unload.
    // Resolved native functions retain the library for this object's lifetime.
  }

  Object? _completedResult(Map<String, Object?> request) {
    final response = execute(request);
    if (response['status'] == 'error') {
      final error = response['error']! as Map<String, Object?>;
      throw InteropProtocolException(
        error['code']! as String,
        error['path']! as String,
        response['operation'] as String?,
      );
    }
    return response['result'];
  }
}

Map<String, Object?> _envelope(
  String operation,
  Map<String, Object?> payload,
) =>
    <String, Object?>{
      'interop_protocol_version': interopProtocolVersion,
      'operation': operation,
      'payload': payload,
    };

Map<String, Object?> _decodeResponse(Uint8List bytes) {
  final Object? decoded;
  try {
    final text = utf8.decode(bytes, allowMalformed: false);
    decoded = jsonDecode(text);
    _DuplicateKeyScanner(text).validate();
  } catch (error) {
    throw NativeAdapterException(
      NativeErrorKind.transport,
      'native STRling response is not strict UTF-8 JSON: $error',
    );
  }
  if (decoded is! Map<String, Object?> ||
      decoded['interop_protocol_version'] != interopProtocolVersion) {
    throw NativeAdapterException(
      NativeErrorKind.transport,
      'interop response has an unsupported version',
    );
  }
  final status = decoded['status'];
  if (status != 'completed' && status != 'error') {
    throw NativeAdapterException(
      NativeErrorKind.transport,
      'interop response has an unsupported status',
    );
  }
  if (status == 'completed' && !decoded.containsKey('result')) {
    throw NativeAdapterException(
      NativeErrorKind.transport,
      'completed interop response has no result',
    );
  }
  if (status == 'error') {
    final error = decoded['error'];
    if (error is! Map<String, Object?> ||
        error['code'] is! String ||
        error['path'] is! String) {
      throw NativeAdapterException(
        NativeErrorKind.transport,
        'failed interop response has no stable code and path',
      );
    }
  }
  return decoded;
}

final class _DuplicateKeyScanner {
  _DuplicateKeyScanner(this.source);

  final String source;
  int _index = 0;

  void validate() {
    _skipWhitespace();
    _value();
    _skipWhitespace();
    if (_index != source.length) {
      throw const FormatException('trailing JSON content');
    }
  }

  void _value() {
    _skipWhitespace();
    if (_index >= source.length) throw const FormatException('missing JSON value');
    switch (source.codeUnitAt(_index)) {
      case 0x7b:
        _object();
        return;
      case 0x5b:
        _array();
        return;
      case 0x22:
        _string();
        return;
      default:
        while (_index < source.length &&
            !const <int>{0x2c, 0x5d, 0x7d, 0x20, 0x09, 0x0a, 0x0d}
                .contains(source.codeUnitAt(_index))) {
          _index++;
        }
        return;
    }
  }

  void _object() {
    _index++;
    _skipWhitespace();
    final names = <String>{};
    if (_take(0x7d)) return;
    while (true) {
      _skipWhitespace();
      final name = _string();
      if (!names.add(name)) {
        throw FormatException('duplicate JSON property: $name');
      }
      _skipWhitespace();
      _expect(0x3a);
      _value();
      _skipWhitespace();
      if (_take(0x7d)) return;
      _expect(0x2c);
    }
  }

  void _array() {
    _index++;
    _skipWhitespace();
    if (_take(0x5d)) return;
    while (true) {
      _value();
      _skipWhitespace();
      if (_take(0x5d)) return;
      _expect(0x2c);
    }
  }

  String _string() {
    final start = _index;
    _expect(0x22);
    var escaped = false;
    while (_index < source.length) {
      final character = source.codeUnitAt(_index++);
      if (escaped) {
        escaped = false;
      } else if (character == 0x5c) {
        escaped = true;
      } else if (character == 0x22) {
        return jsonDecode(source.substring(start, _index)) as String;
      }
    }
    throw const FormatException('unterminated JSON string');
  }

  void _skipWhitespace() {
    while (_index < source.length &&
        const <int>{0x20, 0x09, 0x0a, 0x0d}
            .contains(source.codeUnitAt(_index))) {
      _index++;
    }
  }

  bool _take(int expected) {
    if (_index < source.length && source.codeUnitAt(_index) == expected) {
      _index++;
      return true;
    }
    return false;
  }

  void _expect(int expected) {
    if (!_take(expected)) {
      throw FormatException('expected JSON token 0x${expected.toRadixString(16)}');
    }
  }
}
