/// STRling Essential — RFC-grounded patterns for the most commonly
/// validated string formats (email, URL, UUID, IP, dateTime).
///
/// Each helper composes existing AST primitives so the compiled output
/// flows through the standard pipeline and no raw regex leaks into the
/// public API.

library essential;

import 'src/nodes.dart';
import 'src/emitters/pcre2.dart' show emitPcre2;

List<Node> _letters() => [Range(from: 'A', to: 'Z'), Range(from: 'a', to: 'z')];
List<Node> _digits()  => [Escape('digit')];
List<Node> _hexes()   => [Range(from: 'A', to: 'F'), Range(from: 'a', to: 'f'), Range(from: '0', to: '9')];
List<Node> _chars(String s) => s.split('').map((c) => Literal(c) as Node).toList();

Node _classOf(List<Node> items, int min, dynamic max) {
  final cc = CharacterClass(negated: false, members: items);
  return Quantifier(target: cc, min: min, max: max, greedy: true, lazy: false, possessive: false);
}

Node _digN(int min, dynamic max)  => _classOf(_digits(),  min, max);
Node _hexN(int min, dynamic max)  => _classOf(_hexes(),   min, max);
Node _lettN(int min, dynamic max) => _classOf(_letters(), min, max);

Node _opt(Node node) {
  final grouped = Group(capturing: false, body: node);
  return Quantifier(target: grouped, min: 0, max: 1, greedy: true, lazy: false, possessive: false);
}

Node _seq(List<Node> parts) => Sequence(parts);
Node _alt(List<Node> branches) => Alternation(branches);
Node _lit(String s) => Literal(s);

/// Public Essential 5 facade.
class Essential {
  /// Email address pattern (RFC 5322 addr-spec).
  static Node email() {
    final local  = _classOf([..._letters(), ..._digits(), ..._chars('._%+-')], 1, null);
    final domain = _classOf([..._letters(), ..._digits(), ..._chars('.-')],    1, null);
    final tld    = _lettN(2, null);
    return _seq([local, _lit('@'), domain, _lit('.'), tld]);
  }

  /// HTTP / HTTPS URL pattern (RFC 3986 generic syntax).
  static Node url() {
    final base     = [..._letters(), ..._digits(), ..._chars("/_-.~%&=:@!\$'()*+,;")];
    final withQ    = [...base,    ..._chars('?')];
    final withFrag = [...withQ,   ..._chars('#')];

    final scheme   = _seq([_lit('http'), _opt(_lit('s'))]);
    final host     = _classOf([..._letters(), ..._digits(), ..._chars('.-')], 1, null);
    final port     = _opt(_seq([_lit(':'), _digN(1, null)]));
    final path     = _opt(_seq([_lit('/'), _classOf(base,     0, null)]));
    final query    = _opt(_seq([_lit('?'), _classOf(withQ,    0, null)]));
    final fragment = _opt(_seq([_lit('#'), _classOf(withFrag, 0, null)]));
    return _seq([scheme, _lit('://'), host, port, path, query, fragment]);
  }

  /// UUID pattern (RFC 4122). Pass `version: 4` for v4-specific validation.
  static Node uuid({int version = 0}) {
    if (version == 4) {
      final variant = _classOf(_chars('89ABab'), 1, 1);
      return _seq([
        _hexN(8, 8), _lit('-'),
        _hexN(4, 4), _lit('-'),
        _lit('4'), _hexN(3, 3), _lit('-'),
        variant, _hexN(3, 3), _lit('-'),
        _hexN(12, 12),
      ]);
    }
    return _seq([
      _hexN(8, 8), _lit('-'),
      _hexN(4, 4), _lit('-'),
      _hexN(4, 4), _lit('-'),
      _hexN(4, 4), _lit('-'),
      _hexN(12, 12),
    ]);
  }

  static Node _ipv4() => _seq([
    _digN(1, 3), _lit('.'),
    _digN(1, 3), _lit('.'),
    _digN(1, 3), _lit('.'),
    _digN(1, 3),
  ]);

  static Node _ipv6() => _seq([
    _hexN(1, 4), _lit(':'),
    _hexN(1, 4), _lit(':'),
    _hexN(1, 4), _lit(':'),
    _hexN(1, 4), _lit(':'),
    _hexN(1, 4), _lit(':'),
    _hexN(1, 4), _lit(':'),
    _hexN(1, 4), _lit(':'),
    _hexN(1, 4),
  ]);

  /// IP address pattern. `version: 4` for IPv4 (RFC 791), `6` for IPv6
  /// (RFC 4291); default accepts either.
  static Node ip({int version = 0}) {
    if (version == 4) return _ipv4();
    if (version == 6) return _ipv6();
    return _alt([_ipv4(), _ipv6()]);
  }

  /// ISO 8601 / RFC 3339 datetime pattern.
  static Node dateTime() {
    final sign   = _classOf(_chars('+-'), 1, 1);
    final frac   = _seq([_lit('.'), _digN(1, null)]);
    final offset = _seq([sign, _digN(2, 2), _lit(':'), _digN(2, 2)]);
    return _seq([
      _digN(4, 4), _lit('-'), _digN(2, 2), _lit('-'), _digN(2, 2),
      _lit('T'),
      _digN(2, 2), _lit(':'), _digN(2, 2), _lit(':'), _digN(2, 2),
      _opt(frac),
      _opt(_alt([_lit('Z'), offset])),
    ]);
  }

  /// Compile a Node to a PCRE2 regex string.
  static String compile(Node node) => emitPcre2(node.toIR());
}
