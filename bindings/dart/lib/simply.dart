/// STRling Simply API - Fluent Pattern Builder for Dart
///
/// This library provides a fluent, chainable API for building regex patterns
/// without dealing with raw AST node classes. It mirrors the TypeScript reference
/// implementation while following Dart idioms and conventions.
///
/// Example:
/// ```dart
/// import 'package:strling/simply.dart';
///
/// final pattern = Simply.merge([
///   Simply.start(),
///   Simply.digit(3).asCapture(),
///   Simply.inChars('-. ').optional(),
///   Simply.digit(3).asCapture(),
///   Simply.inChars('-. ').optional(),
///   Simply.digit(4).asCapture(),
///   Simply.end(),
/// ]);
///
/// print(pattern.toIR()); // Outputs the IR representation
/// ```

library simply;

import 'src/nodes.dart' as nodes;

/// Custom error class for STRling pattern errors.
///
/// Provides formatted, user-friendly error messages when invalid patterns
/// are constructed or invalid arguments are provided.
class STRlingError extends Error {
  final String _message;

  STRlingError(this._message);

  @override
  String toString() {
    return '\n\nSTRlingError: Invalid Pattern Attempted.\n\n\t$_message';
  }
}

/// Represents a regex pattern with fluent chainable methods.
///
/// Pattern objects are immutable - all modifier methods return new Pattern
/// instances. Patterns can be combined using static methods like Simply.merge(),
/// and compiled to IR using toIR().
class Pattern {
  final nodes.Node _node;
  final List<String> _namedGroups;

  Pattern._(this._node, {List<String>? namedGroups})
      : _namedGroups = namedGroups ?? [];

  /// Returns the IR representation of this pattern
  Map<String, dynamic> toIR() => _node.toIR();

  /// Makes this pattern optional (matches 0 or 1 times)
  Pattern may() {
    return Pattern._(
      nodes.Quantifier(
        target: _node,
        min: 0,
        max: 1,
        greedy: true,
        lazy: false,
        possessive: false,
      ),
      namedGroups: _namedGroups,
    );
  }

  /// Wraps this pattern in a capturing group
  Pattern asCapture() {
    return Pattern._(
      nodes.Group(capturing: true, body: _node),
      namedGroups: _namedGroups,
    );
  }

  /// Wraps this pattern in a named capturing group
  Pattern asGroup(String name) {
    return Pattern._(
      nodes.Group(capturing: true, body: _node, name: name),
      namedGroups: [..._namedGroups, name],
    );
  }

  /// Makes this pattern repeat between min and max times.
  ///
  /// If [max] is null, repeats exactly [min] times (equivalent to `{min}`).
  /// If [max] is 0, repeats [min] or more times (unbounded, equivalent to `{min,}`).
  /// Otherwise, repeats between [min] and [max] times (inclusive, equivalent to `{min,max}`).
  ///
  /// Examples:
  /// - `repeat(3)` - exactly 3 times `{3}`
  /// - `repeat(2, 5)` - between 2 and 5 times `{2,5}`
  /// - `repeat(1, 0)` - 1 or more times `{1,}`
  Pattern repeat(int min, [int? max]) {
    if (min < 0 || (max != null && max < 0)) {
      throw STRlingError(
          'Pattern.repeat(min, max): min and max must be 0 or greater.');
    }

    if (max != null && max != 0 && max < min) {
      throw STRlingError(
          'Pattern.repeat(min, max): max must be greater than or equal to min (use 0 for unbounded).');
    }

    // Convert max to actual value for validation
    final actualMax = max == null ? min : (max == 0 ? double.infinity : max);
    if (_namedGroups.isNotEmpty && actualMax > 1) {
      throw STRlingError(
          'Pattern.repeat(min, max): Named groups cannot be repeated more than once as they must be unique. '
          'Consider using asCapture() or Simply.merge() instead.');
    }

    final qMax = max == null ? min : (max == 0 ? 'Inf' : max);

    return Pattern._(
      nodes.Quantifier(
        target: _node,
        min: min,
        max: qMax,
        greedy: true,
        lazy: false,
        possessive: false,
      ),
      namedGroups: _namedGroups,
    );
  }

  /// Makes this pattern lazy (non-greedy)
  ///
  /// Lazy quantifiers match as few characters as possible, unlike greedy
  /// quantifiers which match as many as possible. For example, `a.*?b`
  /// (lazy) matches the shortest string starting with 'a' and ending with 'b',
  /// while `a.*b` (greedy) matches the longest such string.
  ///
  /// Can only be applied to quantified patterns (created with optional() or repeat()).
  Pattern lazy() {
    if (_node is! nodes.Quantifier) {
      throw STRlingError(
          'Pattern.lazy(): Can only make quantified patterns lazy. '
          'Use optional() or repeat() first.');
    }
    
    final quant = _node as nodes.Quantifier;
    return Pattern._(
      nodes.Quantifier(
        target: quant.target,
        min: quant.min,
        max: quant.max,
        greedy: false,
        lazy: true,
        possessive: false,
      ),
      namedGroups: _namedGroups,
    );
  }

  /// Makes this pattern possessive
  ///
  /// Possessive quantifiers are like greedy quantifiers, but they never
  /// backtrack. Once they match, they keep what they matched even if this
  /// causes the overall pattern to fail. This can improve performance but
  /// may prevent some matches that would succeed with greedy or lazy quantifiers.
  ///
  /// Can only be applied to quantified patterns (created with optional() or repeat()).
  Pattern possessive() {
    if (_node is! nodes.Quantifier) {
      throw STRlingError(
          'Pattern.possessive(): Can only make quantified patterns possessive. '
          'Use optional() or repeat() first.');
    }
    
    final quant = _node as nodes.Quantifier;
    return Pattern._(
      nodes.Quantifier(
        target: quant.target,
        min: quant.min,
        max: quant.max,
        greedy: true,
        lazy: false,
        possessive: true,
      ),
      namedGroups: _namedGroups,
    );
  }
}

/// Main entry point for the Simply API
///
/// Provides static methods for creating patterns using a fluent interface.
class Simply {
  // Prevent instantiation
  Simply._();

  // =========================================================================
  // Static Character Classes
  // =========================================================================

  /// Matches any digit (0-9)
  static Pattern digit([int? min, int? max]) {
    final node = nodes.CharacterClass(
      negated: false,
      members: [nodes.Escape('digit')],
    );
    final pattern = Pattern._(node);
    return (min != null) ? pattern.repeat(min, max) : pattern;
  }

  /// Matches any non-digit character
  static Pattern notDigit([int? min, int? max]) {
    final node = nodes.CharacterClass(
      negated: false,
      members: [nodes.Escape('not-digit')],
    );
    final pattern = Pattern._(node);
    return (min != null) ? pattern.repeat(min, max) : pattern;
  }

  /// Matches any letter (A-Z, a-z)
  static Pattern letter([int? min, int? max]) {
    final node = nodes.CharacterClass(
      negated: false,
      members: [
        nodes.Range(from: 'A', to: 'Z'),
        nodes.Range(from: 'a', to: 'z'),
      ],
    );
    final pattern = Pattern._(node);
    return (min != null) ? pattern.repeat(min, max) : pattern;
  }

  /// Matches any non-letter character
  static Pattern notLetter([int? min, int? max]) {
    final node = nodes.CharacterClass(
      negated: true,
      members: [
        nodes.Range(from: 'A', to: 'Z'),
        nodes.Range(from: 'a', to: 'z'),
      ],
    );
    final pattern = Pattern._(node);
    return (min != null) ? pattern.repeat(min, max) : pattern;
  }

  /// Matches any alphanumeric character (A-Z, a-z, 0-9)
  static Pattern alphaNum([int? min, int? max]) {
    final node = nodes.CharacterClass(
      negated: false,
      members: [
        nodes.Range(from: 'A', to: 'Z'),
        nodes.Range(from: 'a', to: 'z'),
        nodes.Range(from: '0', to: '9'),
      ],
    );
    final pattern = Pattern._(node);
    return (min != null) ? pattern.repeat(min, max) : pattern;
  }

  /// Matches any non-alphanumeric character
  static Pattern notAlphaNum([int? min, int? max]) {
    final node = nodes.CharacterClass(
      negated: true,
      members: [
        nodes.Range(from: 'A', to: 'Z'),
        nodes.Range(from: 'a', to: 'z'),
        nodes.Range(from: '0', to: '9'),
      ],
    );
    final pattern = Pattern._(node);
    return (min != null) ? pattern.repeat(min, max) : pattern;
  }

  /// Matches any uppercase letter (A-Z)
  static Pattern upper([int? min, int? max]) {
    final node = nodes.CharacterClass(
      negated: false,
      members: [nodes.Range(from: 'A', to: 'Z')],
    );
    final pattern = Pattern._(node);
    return (min != null) ? pattern.repeat(min, max) : pattern;
  }

  /// Matches any non-uppercase character
  static Pattern notUpper([int? min, int? max]) {
    final node = nodes.CharacterClass(
      negated: true,
      members: [nodes.Range(from: 'A', to: 'Z')],
    );
    final pattern = Pattern._(node);
    return (min != null) ? pattern.repeat(min, max) : pattern;
  }

  /// Matches any lowercase letter (a-z)
  static Pattern lower([int? min, int? max]) {
    final node = nodes.CharacterClass(
      negated: false,
      members: [nodes.Range(from: 'a', to: 'z')],
    );
    final pattern = Pattern._(node);
    return (min != null) ? pattern.repeat(min, max) : pattern;
  }

  /// Matches any non-lowercase character
  static Pattern notLower([int? min, int? max]) {
    final node = nodes.CharacterClass(
      negated: true,
      members: [nodes.Range(from: 'a', to: 'z')],
    );
    final pattern = Pattern._(node);
    return (min != null) ? pattern.repeat(min, max) : pattern;
  }

  /// Matches any whitespace character
  static Pattern whitespace([int? min, int? max]) {
    final node = nodes.CharacterClass(
      negated: false,
      members: [nodes.Escape('space')],
    );
    final pattern = Pattern._(node);
    return (min != null) ? pattern.repeat(min, max) : pattern;
  }

  /// Matches any non-whitespace character
  static Pattern notWhitespace([int? min, int? max]) {
    final node = nodes.CharacterClass(
      negated: false,
      members: [nodes.Escape('not-space')],
    );
    final pattern = Pattern._(node);
    return (min != null) ? pattern.repeat(min, max) : pattern;
  }

  /// Matches any word character (alphanumeric + underscore)
  static Pattern word([int? min, int? max]) {
    final node = nodes.CharacterClass(
      negated: false,
      members: [nodes.Escape('word')],
    );
    final pattern = Pattern._(node);
    return (min != null) ? pattern.repeat(min, max) : pattern;
  }

  /// Matches any non-word character
  static Pattern notWord([int? min, int? max]) {
    final node = nodes.CharacterClass(
      negated: false,
      members: [nodes.Escape('not-word')],
    );
    final pattern = Pattern._(node);
    return (min != null) ? pattern.repeat(min, max) : pattern;
  }

  /// Matches any hex digit (0-9, A-F, a-f)
  static Pattern hexDigit([int? min, int? max]) {
    final node = nodes.CharacterClass(
      negated: false,
      members: [
        nodes.Range(from: '0', to: '9'),
        nodes.Range(from: 'A', to: 'F'),
        nodes.Range(from: 'a', to: 'f'),
      ],
    );
    final pattern = Pattern._(node);
    return (min != null) ? pattern.repeat(min, max) : pattern;
  }

  /// Matches any non-hex digit
  static Pattern notHexDigit([int? min, int? max]) {
    final node = nodes.CharacterClass(
      negated: true,
      members: [
        nodes.Range(from: '0', to: '9'),
        nodes.Range(from: 'A', to: 'F'),
        nodes.Range(from: 'a', to: 'f'),
      ],
    );
    final pattern = Pattern._(node);
    return (min != null) ? pattern.repeat(min, max) : pattern;
  }

  // =========================================================================
  // Anchors and Special Patterns
  // =========================================================================

  /// Matches the start of the string/line
  static Pattern start() => Pattern._(nodes.Anchor('Start'));

  /// Matches the end of the string/line
  static Pattern end() => Pattern._(nodes.Anchor('End'));

  /// Matches a word boundary
  static Pattern wordBoundary() => Pattern._(nodes.Anchor('WordBoundary'));

  /// Matches a non-word boundary
  static Pattern notWordBoundary() =>
      Pattern._(nodes.Anchor('NonWordBoundary'));

  /// Matches any single character (except newline in most modes)
  static Pattern dot([int? min, int? max]) {
    final pattern = Pattern._(nodes.Dot());
    return (min != null) ? pattern.repeat(min, max) : pattern;
  }

  // =========================================================================
  // Character Sets
  // =========================================================================

  /// Validates range arguments for between() and notBetween()
  static (String, String) _validateRange(dynamic start, dynamic end, String methodName) {
    String startStr, endStr;

    if (start is int && end is int) {
      if (start < 0 || start > 9 || end < 0 || end > 9) {
        throw STRlingError(
            '$methodName: Integer arguments must be single digits (0-9)');
      }
      if (start > end) {
        throw STRlingError(
            '$methodName: start must not be greater than end');
      }
      startStr = start.toString();
      endStr = end.toString();
    } else if (start is String && end is String) {
      if (start.length != 1 || end.length != 1) {
        throw STRlingError('$methodName: String arguments must be single characters');
      }
      if (!RegExp(r'^[a-zA-Z]$').hasMatch(start) ||
          !RegExp(r'^[a-zA-Z]$').hasMatch(end)) {
        throw STRlingError(
            '$methodName: String arguments must be alphabetical characters');
      }
      // Check same case
      if ((start.toLowerCase() == start && end.toLowerCase() != end) ||
          (start.toUpperCase() == start && end.toUpperCase() != end)) {
        throw STRlingError(
            '$methodName: Letter arguments must be the same case');
      }
      if (start.codeUnitAt(0) > end.codeUnitAt(0)) {
        throw STRlingError(
            '$methodName: start must not be greater than end');
      }
      startStr = start;
      endStr = end;
    } else {
      throw STRlingError(
          '$methodName: Arguments must both be integers (0-9) or letters of the same case');
    }

    return (startStr, endStr);
  }

  /// Helper method to parse character members from various input types
  static List<nodes.Node> _parseCharMembers(dynamic charsOrPatterns, List<dynamic>? rest, String methodName) {
    final List<dynamic> items = rest != null
        ? [charsOrPatterns, ...rest]
        : (charsOrPatterns is List ? charsOrPatterns : [charsOrPatterns]);

    final members = <nodes.Node>[];
    for (final item in items) {
      if (item is String) {
        for (final char in item.split('')) {
          members.add(nodes.Literal(char));
        }
      } else if (item is Pattern) {
        if (item._node is nodes.CharacterClass) {
          final cc = item._node as nodes.CharacterClass;
          members.addAll(cc.members);
        } else {
          throw STRlingError('$methodName: Pattern arguments must be character classes');
        }
      } else {
        throw STRlingError('$methodName: Arguments must be strings or Patterns');
      }
    }
    return members;
  }

  /// Creates a literal pattern from a string
  static Pattern literal(String text) => Pattern._(nodes.Literal(text));

  /// Matches any character in the given string or patterns
  static Pattern anyOf(dynamic charsOrPatterns, [List<dynamic>? rest]) {
    final members = _parseCharMembers(charsOrPatterns, rest, 'anyOf');
    return Pattern._(nodes.CharacterClass(negated: false, members: members));
  }

  /// Matches any character NOT in the given string or patterns
  static Pattern notInChars(dynamic charsOrPatterns, [List<dynamic>? rest]) {
    final members = _parseCharMembers(charsOrPatterns, rest, 'notInChars');
    return Pattern._(nodes.CharacterClass(negated: true, members: members));
  }

  /// Matches characters in a range (e.g., 'a' to 'z', or 0 to 9)
  static Pattern between(dynamic start, dynamic end, [int? min, int? max]) {
    final (startStr, endStr) = _validateRange(start, end, 'between');

    final node = nodes.CharacterClass(
      negated: false,
      members: [nodes.Range(from: startStr, to: endStr)],
    );
    final pattern = Pattern._(node);
    return (min != null) ? pattern.repeat(min, max) : pattern;
  }

  /// Matches characters NOT in a range
  static Pattern notBetween(dynamic start, dynamic end, [int? min, int? max]) {
    final (startStr, endStr) = _validateRange(start, end, 'notBetween');

    final node = nodes.CharacterClass(
      negated: true,
      members: [nodes.Range(from: startStr, to: endStr)],
    );
    final pattern = Pattern._(node);
    return (min != null) ? pattern.repeat(min, max) : pattern;
  }

  // =========================================================================
  // Constructors (Composition)
  // =========================================================================

  /// Helper method to convert dynamic items to Pattern objects
  static List<Pattern> _convertToPatterns(List<dynamic> items, String methodName) {
    final cleanPatterns = <Pattern>[];
    for (final item in items) {
      if (item is String) {
        cleanPatterns.add(literal(item));
      } else if (item is Pattern) {
        cleanPatterns.add(item);
      } else {
        throw STRlingError('$methodName: Arguments must be strings or Patterns');
      }
    }
    return cleanPatterns;
  }

  /// Helper method to validate unique named groups
  static void _validateUniqueNamedGroups(List<String> namedGroups, String methodName) {
    final seen = <String>{};
    for (final name in namedGroups) {
      if (seen.contains(name)) {
        throw STRlingError('$methodName: Named groups must be unique. Duplicate found: $name');
      }
      seen.add(name);
    }
  }

  /// Concatenates patterns into a sequence
  static Pattern merge(List<dynamic> patterns) {
    if (patterns.isEmpty) {
      throw STRlingError('merge: At least one pattern is required');
    }

    final cleanPatterns = _convertToPatterns(patterns, 'merge');
    final namedGroups = cleanPatterns.expand((p) => p._namedGroups).toList();
    _validateUniqueNamedGroups(namedGroups, 'merge');

    if (cleanPatterns.length == 1) {
      return cleanPatterns[0];
    }

    final childNodes = cleanPatterns.map((p) => p._node).toList();
    return Pattern._(nodes.Sequence(childNodes), namedGroups: namedGroups);
  }

  /// Creates an alternation (OR) of patterns
  static Pattern anyOf(List<dynamic> patterns) {
    if (patterns.isEmpty) {
      throw STRlingError('anyOf: At least one pattern is required');
    }

    final cleanPatterns = _convertToPatterns(patterns, 'anyOf');
    final namedGroups = cleanPatterns.expand((p) => p._namedGroups).toList();
    _validateUniqueNamedGroups(namedGroups, 'anyOf');

    final childNodes = cleanPatterns.map((p) => p._node).toList();
    return Pattern._(nodes.Alternation(childNodes), namedGroups: namedGroups);
  }

  /// Makes patterns optional (matches 0 or 1 times)
  static Pattern may(List<dynamic> patterns) {
    if (patterns.isEmpty) {
      throw STRlingError('may: At least one pattern is required');
    }

    final cleanPatterns = _convertToPatterns(patterns, 'may');
    final namedGroups = cleanPatterns.expand((p) => p._namedGroups).toList();
    _validateUniqueNamedGroups(namedGroups, 'may');

    nodes.Node bodyNode;
    if (cleanPatterns.length == 1) {
      bodyNode = cleanPatterns[0]._node;
    } else {
      bodyNode = nodes.Sequence(cleanPatterns.map((p) => p._node).toList());
    }

    return Pattern._(
      nodes.Quantifier(
        target: bodyNode,
        min: 0,
        max: 1,
        greedy: true,
        lazy: false,
        possessive: false,
      ),
      namedGroups: namedGroups,
    );
  }

  /// Creates a capturing group
  static Pattern capture(List<dynamic> patterns) {
    if (patterns.isEmpty) {
      throw STRlingError('capture: At least one pattern is required');
    }

    final cleanPatterns = _convertToPatterns(patterns, 'capture');
    final namedGroups = cleanPatterns.expand((p) => p._namedGroups).toList();
    _validateUniqueNamedGroups(namedGroups, 'capture');

    nodes.Node bodyNode;
    if (cleanPatterns.length == 1) {
      bodyNode = cleanPatterns[0]._node;
    } else {
      bodyNode = nodes.Sequence(cleanPatterns.map((p) => p._node).toList());
    }

    return Pattern._(
      nodes.Group(capturing: true, body: bodyNode),
      namedGroups: namedGroups,
    );
  }

  /// Creates a named capturing group
  static Pattern group(String name, List<dynamic> patterns) {
    if (patterns.isEmpty) {
      throw STRlingError('group: At least one pattern is required');
    }

    final cleanPatterns = _convertToPatterns(patterns, 'group');
    final namedGroups = cleanPatterns.expand((p) => p._namedGroups).toList();
    _validateUniqueNamedGroups(namedGroups, 'group');

    if (namedGroups.contains(name)) {
      throw STRlingError('group: Named groups must be unique. Duplicate found: $name');
    }

    nodes.Node bodyNode;
    if (cleanPatterns.length == 1) {
      bodyNode = cleanPatterns[0]._node;
    } else {
      bodyNode = nodes.Sequence(cleanPatterns.map((p) => p._node).toList());
    }

    return Pattern._(
      nodes.Group(capturing: true, body: bodyNode, name: name),
      namedGroups: [...namedGroups, name],
    );
  }

  // =========================================================================
  // Lookarounds
  // =========================================================================

  /// Positive lookahead - matches if pattern follows
  static Pattern ahead(dynamic pattern) {
    final p = pattern is String ? literal(pattern) : pattern as Pattern;
    return Pattern._(
      nodes.Lookaround(dir: 'Ahead', neg: false, body: p._node),
      namedGroups: p._namedGroups,
    );
  }

  /// Negative lookahead - matches if pattern does not follow
  static Pattern notAhead(dynamic pattern) {
    final p = pattern is String ? literal(pattern) : pattern as Pattern;
    return Pattern._(
      nodes.Lookaround(dir: 'Ahead', neg: true, body: p._node),
      namedGroups: p._namedGroups,
    );
  }

  /// Positive lookbehind - matches if pattern precedes
  static Pattern behind(dynamic pattern) {
    final p = pattern is String ? literal(pattern) : pattern as Pattern;
    return Pattern._(
      nodes.Lookaround(dir: 'Behind', neg: false, body: p._node),
      namedGroups: p._namedGroups,
    );
  }

  /// Negative lookbehind - matches if pattern does not precede
  static Pattern notBehind(dynamic pattern) {
    final p = pattern is String ? literal(pattern) : pattern as Pattern;
    return Pattern._(
      nodes.Lookaround(dir: 'Behind', neg: true, body: p._node),
      namedGroups: p._namedGroups,
    );
  }
}
