/// STRling PCRE2 Emitter
///
/// Transforms STRling IR into PCRE2-compatible regex strings.
/// Iron Law: Emitters are pure functions with signature emit(ir, flags) → string.

import '../core/parser.dart' show Flags;
import '../core/diagnostics.dart';

export '../core/diagnostics.dart'
    show STRlingCompilationError, STRlingWarning, CompileResult;

/// Special characters that need escaping in PCRE2
const _literalSpecial = r'[\]^$.|?*+(){}';

/// Special characters inside character class
const _classSpecial = r'[\]^-';

/// Escape a literal string for use outside character classes
String _escapeLiteral(String s) {
  final buf = StringBuffer();
  for (final ch in s.split('')) {
    if (_literalSpecial.contains(ch)) {
      buf.write('\\');
    }
    buf.write(ch);
  }
  return buf.toString();
}

/// Escape a character for use inside character classes
String _escapeClassChar(String ch) {
  if (_classSpecial.contains(ch)) {
    return '\\$ch';
  }
  return ch;
}

/// PCRE2 Emitter class
class Pcre2Emitter {
  /// Default upper bound on IR nesting depth before the emitter aborts.
  /// Mirrors the SSOT in the TypeScript reference.
  static const int defaultMaxDepth = 250;

  static const String _redosMessage =
      'The pattern contains overlapping alternations or nested unbounded '
      'quantifiers (e.g., (a+)+). This can lead to catastrophic backtracking '
      'and exponential CPU spikes. Consider using possessive quantifiers '
      '(++ or *+) or atomic groups to guarantee execution safety.';

  int _depth = 0;
  int _maxDepth = defaultMaxDepth;
  bool _inLookbehind = false;
  final List<STRlingWarning> _warnings = [];

  /// Emit PCRE2 pattern from IR
  ///
  /// [ir] is a Map representation of the STRling IR
  /// [flags] optional compilation flags
  /// Returns the compiled PCRE2 regex string
  String emit(Map<String, dynamic> ir, [Flags? flags]) {
    return emitWithDiagnostics(ir, flags).pattern;
  }

  /// Emit PCRE2 pattern AND surface any non-fatal diagnostics collected
  /// during emission. Pass `maxDepth <= 0` to use [defaultMaxDepth].
  CompileResult emitWithDiagnostics(Map<String, dynamic> ir,
      [Flags? flags, int maxDepth = 0]) {
    _depth = 0;
    _maxDepth = maxDepth > 0 ? maxDepth : defaultMaxDepth;
    _inLookbehind = false;
    _warnings.clear();
    final pattern = _emitNode(ir);
    return CompileResult(pattern, List.unmodifiable(_warnings));
  }

  // --- Safety predicates -------------------------------------------------

  bool _isUnboundedQuant(Map<String, dynamic> q) {
    final m = q['max'];
    return m == null || m == 'Inf';
  }

  bool _isVariableLengthQuant(Map<String, dynamic> q) {
    if (_isUnboundedQuant(q)) return true;
    return q['max'] != q['min'];
  }

  /// Mirror of `_isFixedLengthBody` in the TS SSOT.
  bool _isFixedLengthBody(Map<String, dynamic> node) {
    final t = node['ir'] as String?;
    switch (t) {
      case 'Quant':
        return !_isVariableLengthQuant(node) &&
            _isFixedLengthBody(node['child'] as Map<String, dynamic>);
      case 'Seq':
        final parts = node['parts'] as List;
        return parts
            .every((p) => _isFixedLengthBody(p as Map<String, dynamic>));
      case 'Alt':
        final branches = node['branches'] as List;
        return branches
            .every((b) => _isFixedLengthBody(b as Map<String, dynamic>));
      case 'Group':
        return _isFixedLengthBody(node['body'] as Map<String, dynamic>);
      case 'Look':
        return true;
      default:
        return true;
    }
  }

  /// Mirror of `_hasNestedUnboundedQuant`.
  bool _hasNestedUnboundedQuant(Map<String, dynamic> child) {
    final t = child['ir'] as String?;
    switch (t) {
      case 'Quant':
        return _isUnboundedQuant(child);
      case 'Group':
        return _hasNestedUnboundedQuant(child['body'] as Map<String, dynamic>);
      case 'Seq':
        final parts = child['parts'] as List;
        return parts.length == 1 &&
            _hasNestedUnboundedQuant(parts[0] as Map<String, dynamic>);
      case 'Alt':
        final branches = child['branches'] as List;
        return branches
            .any((b) => _hasNestedUnboundedQuant(b as Map<String, dynamic>));
      default:
        return false;
    }
  }

  void _pushReDoSWarning() {
    if (_warnings.any((w) => w.code == 'REDOS_RISK')) return;
    _warnings.add(const STRlingWarning('REDOS_RISK', _redosMessage));
  }

  String _emitNode(Map<String, dynamic> ir) {
    _depth++;
    try {
      if (_depth > _maxDepth) {
        throw STRlingCompilationError(
          'Maximum AST depth exceeded (limit: $_maxDepth). '
              'This pattern is too deeply nested and risks host stack '
              'exhaustion during emission. Refactor the pattern to reduce '
              'nesting, or flatten capturing groups where possible.',
          'MAX_DEPTH',
        );
      }
      return _dispatch(ir);
    } finally {
      _depth--;
    }
  }

  String _dispatch(Map<String, dynamic> ir) {
    final irType = ir['ir'] as String;

    switch (irType) {
      case 'Lit':
        return _emitLit(ir);
      case 'Seq':
        return _emitSeq(ir);
      case 'Alt':
        return _emitAlt(ir);
      case 'Group':
        return _emitGroup(ir);
      case 'Quant':
        return _emitQuant(ir);
      case 'CharClass':
        return _emitCharClass(ir);
      case 'Anchor':
        return _emitAnchor(ir);
      case 'Dot':
        return '.';
      case 'Backref':
        return _emitBackref(ir);
      case 'Look':
        return _emitLook(ir);
      case 'Esc':
        return _emitEsc(ir);
      default:
        throw FormatException('Unknown IR type: $irType');
    }
  }

  String _emitLit(Map<String, dynamic> ir) {
    final value = ir['value'] as String;
    return _escapeLiteral(value);
  }

  String _emitSeq(Map<String, dynamic> ir) {
    final parts = ir['parts'] as List;
    return parts.map((p) => _emitNode(p as Map<String, dynamic>)).join();
  }

  String _emitAlt(Map<String, dynamic> ir) {
    final branches = ir['branches'] as List;
    return branches.map((b) => _emitNode(b as Map<String, dynamic>)).join('|');
  }

  String _emitGroup(Map<String, dynamic> ir) {
    final body = _emitNode(ir['body'] as Map<String, dynamic>);
    final capturing = ir['capturing'] as bool? ?? false;
    final name = ir['name'] as String?;
    final atomic = ir['atomic'] as bool? ?? false;

    if (atomic) {
      return '(?>$body)';
    }
    if (name != null) {
      return '(?<$name>$body)';
    }
    if (capturing) {
      return '($body)';
    }
    return '(?:$body)';
  }

  String _emitQuant(Map<String, dynamic> ir) {
    final child = ir['child'] as Map<String, dynamic>;
    final min = ir['min'] as int;
    final max = ir['max'];
    final mode = ir['mode'] as String? ?? 'Greedy';

    // ReDoS guard: only flag when the *outer* quantifier is itself
    // unbounded. A bounded outer like `(a+){0,3}` cannot produce
    // exponential backtracking on its own.
    if (_isUnboundedQuant(ir) && _hasNestedUnboundedQuant(child)) {
      _pushReDoSWarning();
    }

    var childStr = _emitNode(child);

    // Wrap if needed (sequences, alternations, multi-char literals)
    final needsParens = _needsQuantifierParens(child, childStr);
    if (needsParens) {
      childStr = '(?:$childStr)';
    }

    // Build quantifier suffix
    String quantStr;
    if (max == 'Inf' || max == null) {
      if (min == 0) {
        quantStr = '*';
      } else if (min == 1) {
        quantStr = '+';
      } else {
        quantStr = '{$min,}';
      }
    } else if (min == max) {
      if (min == 0) {
        return ''; // Matches nothing, effectively empty
      } else if (min == 1) {
        quantStr = '';
      } else {
        quantStr = '{$min}';
      }
    } else if (min == 0 && max == 1) {
      quantStr = '?';
    } else {
      quantStr = '{$min,$max}';
    }

    // Add mode suffix
    if (mode == 'Lazy') {
      quantStr += '?';
    } else if (mode == 'Possessive') {
      quantStr += '+';
    }

    return '$childStr$quantStr';
  }

  bool _needsQuantifierParens(Map<String, dynamic> child, String childStr) {
    final irType = child['ir'] as String;
    switch (irType) {
      case 'Seq':
        return true;
      case 'Alt':
        return true;
      case 'Lit':
        return childStr.length > 1 && !childStr.startsWith('\\');
      case 'Quant':
        return true;
      default:
        return false;
    }
  }

  String _emitCharClass(Map<String, dynamic> ir) {
    final negated = ir['negated'] as bool? ?? false;
    final items = ir['items'] as List;

    // Single-item shorthand optimization
    if (items.length == 1) {
      final item = items[0] as Map<String, dynamic>;
      final itemIr = item['ir'] as String;

      if (itemIr == 'Esc') {
        final type = item['type'] as String;

        // Handle d, w, s with negation flipping
        if ('dws'.contains(type)) {
          if (negated) {
            return '\\${type.toUpperCase()}';
          }
          return '\\$type';
        }

        // Handle D, W, S
        if ('DWS'.contains(type)) {
          if (negated) {
            return '\\${type.toLowerCase()}';
          }
          return '\\$type';
        }

        // Handle \p{...} and \P{...}
        if (type == 'p' || type == 'P') {
          final prop = item['property'] as String?;
          if (prop != null) {
            final shouldNegate = negated != (type == 'P');
            final use = shouldNegate ? 'P' : 'p';
            return '\\$use{$prop}';
          }
        }
      }
    }

    // Build bracket class
    final parts = <String>[];
    var hasHyphen = false;

    for (final item in items) {
      final itemMap = item as Map<String, dynamic>;
      final itemIr = itemMap['ir'] as String;

      switch (itemIr) {
        case 'Char':
          final ch = itemMap['char'] as String;
          if (ch == '-') {
            hasHyphen = true;
          } else {
            parts.add(_escapeClassChar(ch));
          }
          break;
        case 'Range':
          final from = itemMap['from'] as String;
          final to = itemMap['to'] as String;
          parts.add('${_escapeClassChar(from)}-${_escapeClassChar(to)}');
          break;
        case 'Esc':
          final type = itemMap['type'] as String;
          final prop = itemMap['property'] as String?;
          if (prop != null) {
            parts.add('\\$type{$prop}');
          } else {
            parts.add('\\$type');
          }
          break;
      }
    }

    // Hyphen at start to avoid ambiguity
    final inner = hasHyphen ? '-${parts.join()}' : parts.join();
    return '[${negated ? '^' : ''}$inner]';
  }

  String _emitAnchor(Map<String, dynamic> ir) {
    final at = ir['at'] as String;
    switch (at) {
      case 'Start':
        return '^';
      case 'End':
        return r'$';
      case 'WordBoundary':
        return r'\b';
      case 'NotWordBoundary':
        return r'\B';
      case 'AbsoluteStart':
        return r'\A';
      case 'AbsoluteEnd':
        return r'\z';
      case 'EndBeforeFinalNewline':
        return r'\Z';
      default:
        throw FormatException('Unknown anchor type: $at');
    }
  }

  String _emitBackref(Map<String, dynamic> ir) {
    final byIndex = ir['byIndex'] as int?;
    final byName = ir['byName'] as String?;

    if (byName != null) {
      return '\\k<$byName>';
    }
    if (byIndex != null) {
      return '\\$byIndex';
    }
    throw FormatException('Backref must have byIndex or byName');
  }

  String _emitLook(Map<String, dynamic> ir) {
    final dir = ir['dir'] as String;
    final neg = ir['neg'] as bool? ?? false;
    final bodyMap = ir['body'] as Map<String, dynamic>;

    // Variable-length lookbehind guard: PCRE2 mandates a fixed-width
    // lookbehind body. Detect the violation here so the user sees a
    // Signpost-pattern error rather than an opaque PCRE2 compile failure
    // leaking from the runtime.
    if (dir == 'Behind' && !_isFixedLengthBody(bodyMap)) {
      throw STRlingCompilationError(
        'PCRE2 does not support variable-length lookbehinds. The lookbehind '
            'body contains a quantifier that makes its length unpredictable. '
            'Rewrite the assertion using a fixed-length range (e.g. `{1,8}` '
            'instead of `+`), or restructure the pattern using a Lookahead, or '
            'extract the quantified portion outside the assertion.',
        'VLB_NOT_SUPPORTED',
      );
    }

    final wasInLb = _inLookbehind;
    if (dir == 'Behind') _inLookbehind = true;
    final body = _emitNode(bodyMap);
    _inLookbehind = wasInLb;

    if (dir == 'Ahead') {
      return neg ? '(?!$body)' : '(?=$body)';
    } else {
      return neg ? '(?<!$body)' : '(?<=$body)';
    }
  }

  String _emitEsc(Map<String, dynamic> ir) {
    final type = ir['type'] as String;
    final prop = ir['property'] as String?;

    if (prop != null) {
      return '\\$type{$prop}';
    }
    return '\\$type';
  }
}

/// Convenience function to emit PCRE2 from IR
String emitPcre2(Map<String, dynamic> ir, [Flags? flags]) {
  return Pcre2Emitter().emit(ir, flags);
}
