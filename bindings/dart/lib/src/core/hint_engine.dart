/// STRling Hint Engine - Context-Aware Error Hints
///
/// Provides intelligent, beginner-friendly hints for common syntax errors.
/// Maps specific error types and contexts to instructional messages that
/// help users understand and fix their mistakes.
///
/// Mirrors the TypeScript reference: bindings/typescript/src/STRling/core/hint_engine.ts

/// Stateless hint engine that derives instructional guidance from parse failure context.
class HintEngine {
  HintEngine._();

  /// Get a hint for the given error.
  ///
  /// Returns a helpful hint string (never null — returns a generic fallback).
  static String getHint(String errorMessage, String text, int pos) {
    for (final entry in _hintGenerators) {
      if (errorMessage.contains(entry.$1)) {
        return entry.$2(errorMessage, text, pos);
      }
    }
    return 'Check your pattern syntax near position $pos. Refer to the STRling documentation for correct usage.';
  }

  static final List<(String, String Function(String, String, int))>
      _hintGenerators = [
    ('Unterminated group', _hintUnterminatedGroup),
    ('Empty character class', _hintEmptyCharacterClass),
    ('Unterminated character class', _hintUnterminatedCharClass),
    ('Unterminated named backref', _hintUnterminatedNamedBackref),
    ('Unterminated group name', _hintUnterminatedGroupName),
    ('Unterminated lookahead', _hintUnterminatedLookahead),
    ('Unterminated lookbehind', _hintUnterminatedLookbehind),
    ('Unterminated atomic group', _hintUnterminatedAtomicGroup),
    ('Unterminated {m,n}', _hintUnterminatedBraceQuant),
    ('Unterminated {n}', _hintUnterminatedBraceQuant),
    ('Incomplete quantifier', _hintUnterminatedBraceQuant),
    ('Unexpected token', _hintUnexpectedToken),
    ('Unexpected trailing input', _hintUnexpectedTrailing),
    ('Cannot quantify anchor', _hintCannotQuantifyAnchor),
    ('Backreference to undefined group', _hintUndefinedBackref),
    ('Duplicate group name', _hintDuplicateGroupName),
    ('Alternation lacks left-hand side', _hintAlternationNoLhs),
    ('Alternation lacks right-hand side', _hintAlternationNoRhs),
    ('Empty alternation', _hintEmptyAlternation),
    ('Inline modifiers', _hintInlineModifiers),
    (r'Invalid \xHH escape', _hintInvalidHex),
    (r'Invalid \uHHHH', _hintInvalidUnicode),
    (r'Unterminated \x{...}', _hintUnterminatedHexBrace),
    (r'Unterminated \u{...}', _hintUnterminatedUnicodeBrace),
    (r'Unterminated \p{...}', _hintUnterminatedUnicodeProperty),
    (r"Expected { after \p/\P", _hintUnicodePropertyMissingBrace),
    (r"Expected '<' after \p/\P", _hintUnicodePropertyMissingBrace),
    ('Invalid brace quantifier content', _hintInvalidBraceQuantContent),
    ('Invalid group name', _hintInvalidGroupName),
    ('Invalid quantifier range', _hintInvalidQuantifierRange),
    ('Invalid character range', _hintInvalidCharacterRange),
    ('Invalid flag', _hintInvalidFlag),
    ('Directive after pattern', _hintDirectiveAfterPattern),
    ('Directive must appear', _hintDirectiveAfterPattern),
    ('Malformed directive', _hintMalformedDirective),
    ('Unknown escape sequence', _hintUnknownEscape),
    ('Invalid quantifier', _hintInvalidQuantifier),
    (r"Expected '<' after \k", _hintUnterminatedNamedBackref),
    (r'Invalid \UHHHHHHHH escape', _hintInvalidUnicodeLong),
    ("Unmatched ')'", _hintUnmatchedCloseParen),
  ];

  static String _hintUnterminatedGroup(String msg, String text, int pos) =>
      "This group was opened with '(' but never closed. Add a matching ')' to close the group.";

  static String _hintEmptyCharacterClass(String msg, String text, int pos) =>
      "Empty character class '[]' detected. Character classes must contain at least one element (e.g., [a-z]) — do not leave them empty. If you meant a literal '[', escape it with '\\['.";

  static String _hintUnterminatedCharClass(String msg, String text, int pos) =>
      "This character class was opened with '[' but never closed. Add a matching ']' to close the character class.";

  static String _hintUnterminatedNamedBackref(
          String msg, String text, int pos) =>
      r"Named backreferences use the syntax \k<name>. Make sure to close the '<name>' with '>'.";

  static String _hintUnterminatedGroupName(String msg, String text, int pos) =>
      "Named groups use the syntax (?<name>...). Make sure to close the '<name>' with '>' before the group content.";

  static String _hintUnterminatedLookahead(String msg, String text, int pos) =>
      "This lookahead was opened with '(?=' or '(?!' but never closed. Add a matching ')' to close the lookahead.";

  static String _hintUnterminatedLookbehind(String msg, String text, int pos) =>
      "This lookbehind was opened with '(?<=' or '(?<!' but never closed. Add a matching ')' to close the lookbehind.";

  static String _hintUnterminatedAtomicGroup(
          String msg, String text, int pos) =>
      "This atomic group was opened with '(?>' but never closed. Add a matching ')' to close the atomic group.";

  static String _hintUnterminatedBraceQuant(String msg, String text, int pos) =>
      "Brace quantifiers require a complete form: {n}, {m,n}, or {m,}. Make sure to close the quantifier with '}' and provide valid numbers.";

  static String _hintUnexpectedToken(String msg, String text, int pos) {
    if (pos < text.length) {
      final ch = text[pos];
      if (ch == ')') {
        return "This ')' does not have a matching opening '('. Remove the extra ')' or add an opening '(' earlier in the pattern.";
      } else if (ch == '|') {
        return "The alternation operator '|' requires expressions on both sides. Use 'a|b' to match either 'a' or 'b'.";
      }
    }
    return 'This character appeared in an unexpected context.';
  }

  static String _hintUnexpectedTrailing(String msg, String text, int pos) =>
      'There is unexpected content after the pattern ended. Check for unmatched parentheses or extra characters.';

  static String _hintCannotQuantifyAnchor(String msg, String text, int pos) =>
      r'Anchors like ^, $, \b, \B match positions, not characters, so they cannot be quantified with *, +, ?, or {}.';

  static String _hintUndefinedBackref(String msg, String text, int pos) =>
      'Backreferences refer to previously captured groups. Make sure the group is defined before referencing it. STRling does not support forward references.';

  static String _hintDuplicateGroupName(String msg, String text, int pos) =>
      'Each named group must have a unique name. Use different names for different groups, or use unnamed groups ().';

  static String _hintAlternationNoLhs(String msg, String text, int pos) =>
      "The alternation operator '|' requires an expression on the left side. Use 'a|b' to match either 'a' or 'b'.";

  static String _hintAlternationNoRhs(String msg, String text, int pos) =>
      "The alternation operator '|' requires an expression on the right side. Use 'a|b' to match either 'a' or 'b'.";

  static String _hintEmptyAlternation(String msg, String text, int pos) =>
      "One of the alternation branches is empty. Remove the empty branch or provide an expression, e.g., 'a|b' instead of 'a||b'.";

  static String _hintInlineModifiers(String msg, String text, int pos) =>
      "STRling does not support inline modifiers like (?i) for case-insensitivity. Instead, use the %flags directive at the start of your pattern: '%flags i'";

  static String _hintInvalidHex(String msg, String text, int pos) =>
      "Hex escapes must use valid hexadecimal digits (0-9, A-F). Use \\xHH for 2-digit hex codes (e.g., \\x41 for 'A').";

  static String _hintInvalidUnicode(String msg, String text, int pos) =>
      r'Unicode escapes must use valid hexadecimal digits (0-9, A-F). Use \uHHHH for 4-digit codes or \u{...} for variable-length codes.';

  static String _hintUnterminatedHexBrace(String msg, String text, int pos) =>
      "Variable-length hex escapes use the syntax \\x{...}. Make sure to close the escape with '}'.";

  static String _hintUnterminatedUnicodeBrace(
          String msg, String text, int pos) =>
      "Variable-length unicode escapes use the syntax \\u{...}. Make sure to close the escape with '}'.";

  static String _hintUnterminatedUnicodeProperty(
          String msg, String text, int pos) =>
      "Unicode property escapes use the syntax \\p{Property} or \\P{Property}. Make sure to close the property name with '}'.";

  static String _hintUnicodePropertyMissingBrace(
          String msg, String text, int pos) =>
      r'Unicode property escapes require braces: \p{Letter} or \P{Letter}. Use \p{L} for letters, \p{N} for numbers, etc.';

  static String _hintInvalidBraceQuantContent(
          String msg, String text, int pos) =>
      r"Brace quantifiers require numeric digits: use {n}, {m,n}, or {m,}. Only numbers are valid inside braces — to match a literal '{', escape it with '\{'.";

  static String _hintInvalidGroupName(String msg, String text, int pos) =>
      "Named groups require identifiers: IDENTIFIER = letter or '_' followed by letters, digits or '_'. Choose a name that starts with a letter or underscore and contains only letters, digits, or underscores.";

  static String _hintInvalidQuantifierRange(String msg, String text, int pos) =>
      "Quantifier ranges must have the minimum less than or equal to the maximum (m <= n). For example, use '{2,5}' or '{2,2}', not '{5,2}'.";

  static String _hintInvalidCharacterRange(String msg, String text, int pos) =>
      "Character ranges must be ascending, e.g., '[a-z]' or '[0-9]'. Reversed ranges like '[z-a]' are invalid.";

  static String _hintInvalidFlag(String msg, String text, int pos) =>
      'Unknown flag. Valid flags are: i (case-insensitive), m (multiline), s (dotAll), u (unicode), x (extended/free-spacing).';

  static String _hintDirectiveAfterPattern(String msg, String text, int pos) =>
      "Directives such as '%flags' must appear at the start of the pattern (before any pattern content). Move the directive to the top of the input on its own line.";

  static String _hintMalformedDirective(String msg, String text, int pos) =>
      "This directive looks malformed. Directives begin with '%' and must be one of the supported forms, for example '%flags i' on a line by itself.";

  static String _hintUnknownEscape(String msg, String text, int pos) {
    final m = RegExp(r'Unknown escape sequence \\?(.)').firstMatch(msg);
    if (m != null) {
      final ch = m.group(1) ?? 'z';
      if (ch == 'z') {
        return r"'\z' is not a recognized escape sequence. Did you mean '\Z' (end of string) or escape the literal 'z' as 'z'?";
      }
      return "Unknown escape sequence '\\$ch'. If you intended a literal '$ch', remove the backslash or use a recognized escape.";
    }
    return 'Unknown escape sequence. If you intended a literal character, remove the backslash or use a recognized escape.';
  }

  static String _hintInvalidQuantifier(String msg, String text, int pos) {
    final m = RegExp(r"Invalid quantifier '(.)'").firstMatch(msg);
    final ch = m?.group(1) ?? '*';
    return "The quantifier '$ch' must follow an atom (a character or group). Place '$ch' after the thing it should quantify, e.g., 'a$ch'.";
  }

  static String _hintUnmatchedCloseParen(String msg, String text, int pos) =>
      "This ')' does not have a matching opening '('. Remove the extra ')' or add an opening '(' earlier in the pattern.";

  static String _hintInvalidUnicodeLong(String msg, String text, int pos) =>
      '8-digit Unicode escapes must use valid hexadecimal digits (0-9, A-F). '
      'Use \\UHHHHHHHH for 8-digit codes or \\u{...} for variable-length codes.';
}
