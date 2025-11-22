sealed class Node {
  factory Node.fromJson(Map<String, dynamic> json) {
    final type = json['type'] as String;
    switch (type) {
      case 'Literal':
        return Literal.fromJson(json);
      case 'Sequence':
        return Sequence.fromJson(json);
      case 'Alternation':
        return Alternation.fromJson(json);
      case 'Group':
        return Group.fromJson(json);
      case 'Quantifier':
        return Quantifier.fromJson(json);
      case 'CharacterClass':
        return CharacterClass.fromJson(json);
      case 'Range':
        return Range.fromJson(json);
      case 'Anchor':
        return Anchor.fromJson(json);
      case 'Dot':
        return Dot.fromJson(json);
      case 'Backreference':
        return Backreference.fromJson(json);
      case 'Lookahead':
      case 'Lookbehind':
      case 'NegativeLookahead':
      case 'NegativeLookbehind':
        return Lookaround.fromJson(json);
      case 'Escape':
        return Escape.fromJson(json);
      case 'UnicodeProperty':
        return UnicodeProperty.fromJson(json);
      default:
        throw FormatException('Unknown node type: $type');
    }
  }

  Map<String, dynamic> toIR();
}

class Literal extends Node {
  final String value;

  Literal(this.value);

  factory Literal.fromJson(Map<String, dynamic> json) {
    return Literal(json['value'] as String);
  }

  @override
  Map<String, dynamic> toIR() {
    return {
      'ir': 'Lit',
      'value': value,
    };
  }
  
  Map<String, dynamic> toClassItem() {
      if (value.length != 1) {
          throw FormatException('Literal in character class must be single char, got $value');
      }
      return {
          'ir': 'Char',
          'char': value,
      };
  }
}

class Sequence extends Node {
  final List<Node> parts;

  Sequence(this.parts);

  factory Sequence.fromJson(Map<String, dynamic> json) {
    return Sequence(
      (json['parts'] as List).map((e) => Node.fromJson(e as Map<String, dynamic>)).toList(),
    );
  }

  @override
  Map<String, dynamic> toIR() {
    return {
      'ir': 'Seq',
      'parts': parts.map((e) => e.toIR()).toList(),
    };
  }
}

class Alternation extends Node {
  final List<Node> alternatives;

  Alternation(this.alternatives);

  factory Alternation.fromJson(Map<String, dynamic> json) {
    return Alternation(
      (json['alternatives'] as List).map((e) => Node.fromJson(e as Map<String, dynamic>)).toList(),
    );
  }

  @override
  Map<String, dynamic> toIR() {
    return {
      'ir': 'Alt',
      'branches': alternatives.map((e) => e.toIR()).toList(),
    };
  }
}

class Group extends Node {
  final bool capturing;
  final Node body;
  final String? name;
  final bool? atomic;

  Group({required this.capturing, required this.body, this.name, this.atomic});

  factory Group.fromJson(Map<String, dynamic> json) {
    return Group(
      capturing: json['capturing'] as bool,
      body: Node.fromJson(json['body'] as Map<String, dynamic>),
      name: json['name'] as String?,
      atomic: json['atomic'] as bool?,
    );
  }

  @override
  Map<String, dynamic> toIR() {
    final map = <String, dynamic>{
      'ir': 'Group',
      'capturing': capturing,
      'body': body.toIR(),
    };
    if (name != null) map['name'] = name;
    if (atomic != null && atomic!) map['atomic'] = atomic;
    return map;
  }
}

class Quantifier extends Node {
  final Node target;
  final int min;
  final dynamic max; // int or "Inf" (or null in input AST?)
  final bool greedy;
  final bool lazy;
  final bool possessive;

  Quantifier({
    required this.target,
    required this.min,
    this.max,
    required this.greedy,
    required this.lazy,
    required this.possessive,
  });

  factory Quantifier.fromJson(Map<String, dynamic> json) {
    return Quantifier(
      target: Node.fromJson(json['target'] as Map<String, dynamic>),
      min: json['min'] as int,
      max: json['max'],
      greedy: json['greedy'] as bool,
      lazy: json['lazy'] as bool,
      possessive: json['possessive'] as bool,
    );
  }

  @override
  Map<String, dynamic> toIR() {
    String mode = 'Greedy';
    if (lazy) mode = 'Lazy';
    else if (possessive) mode = 'Possessive';

    return {
      'ir': 'Quant',
      'child': target.toIR(),
      'min': min,
      'max': max ?? 'Inf',
      'mode': mode,
    };
  }
}

class CharacterClass extends Node {
  final bool negated;
  final List<Node> members;

  CharacterClass({required this.negated, required this.members});

  factory CharacterClass.fromJson(Map<String, dynamic> json) {
    return CharacterClass(
      negated: json['negated'] as bool,
      members: (json['members'] as List).map((e) => Node.fromJson(e as Map<String, dynamic>)).toList(),
    );
  }

  @override
  Map<String, dynamic> toIR() {
    return {
      'ir': 'CharClass',
      'negated': negated,
      'items': members.map((e) {
          if (e is Literal) return e.toClassItem();
          if (e is Range) return e.toClassItem();
          if (e is Escape) return e.toClassItem();
          if (e is UnicodeProperty) return e.toClassItem();
          throw FormatException('Unsupported node type in character class: ${e.runtimeType}');
      }).toList(),
    };
  }
}

class Range extends Node {
  final String from;
  final String to;

  Range({required this.from, required this.to});

  factory Range.fromJson(Map<String, dynamic> json) {
    return Range(
      from: json['from'] as String,
      to: json['to'] as String,
    );
  }

  @override
  Map<String, dynamic> toIR() {
    throw FormatException('Range cannot be used as a standalone IR node');
  }
  
  Map<String, dynamic> toClassItem() {
      return {
          'ir': 'Range',
          'from': from,
          'to': to,
      };
  }
}

class Anchor extends Node {
  final String at;

  Anchor(this.at);

  factory Anchor.fromJson(Map<String, dynamic> json) {
    return Anchor(json['at'] as String);
  }

  @override
  Map<String, dynamic> toIR() {
    var val = at;
    if (val == 'NonWordBoundary') val = 'NotWordBoundary';
    return {
      'ir': 'Anchor',
      'at': val,
    };
  }
}

class Dot extends Node {
  Dot();

  factory Dot.fromJson(Map<String, dynamic> json) {
    return Dot();
  }

  @override
  Map<String, dynamic> toIR() {
    return {'ir': 'Dot'};
  }
}

class Backreference extends Node {
  final int? index;
  final String? name;

  Backreference({this.index, this.name});

  factory Backreference.fromJson(Map<String, dynamic> json) {
    return Backreference(
      index: json['index'] as int?,
      name: json['name'] as String?,
    );
  }

  @override
  Map<String, dynamic> toIR() {
    return {
      'ir': 'Backref',
      'by_index': index,
      'by_name': name,
    };
  }
}

class Lookaround extends Node {
  final String dir;
  final bool neg;
  final Node body;

  Lookaround({required this.dir, required this.neg, required this.body});

  factory Lookaround.fromJson(Map<String, dynamic> json) {
    final type = json['type'] as String;
    String dir;
    bool neg;
    
    if (type == 'Lookahead') { dir = 'Ahead'; neg = false; }
    else if (type == 'Lookbehind') { dir = 'Behind'; neg = false; }
    else if (type == 'NegativeLookahead') { dir = 'Ahead'; neg = true; }
    else if (type == 'NegativeLookbehind') { dir = 'Behind'; neg = true; }
    else { throw FormatException('Invalid lookaround type: $type'); }

    return Lookaround(
      dir: dir,
      neg: neg,
      body: Node.fromJson(json['body'] as Map<String, dynamic>),
    );
  }

  @override
  Map<String, dynamic> toIR() {
    return {
      'ir': 'Look',
      'dir': dir,
      'neg': neg,
      'body': body.toIR(),
    };
  }
}

class Escape extends Node {
  final String kind;

  Escape(this.kind);

  factory Escape.fromJson(Map<String, dynamic> json) {
    return Escape(json['kind'] as String);
  }

  @override
  Map<String, dynamic> toIR() {
    throw FormatException('Escape cannot be used as a standalone IR node');
  }
  
  Map<String, dynamic> toClassItem() {
      String type;
      switch (kind) {
          case 'digit': type = 'd'; break;
          case 'not-digit': type = 'D'; break;
          case 'word': type = 'w'; break;
          case 'not-word': type = 'W'; break;
          case 'space': type = 's'; break;
          case 'not-space': type = 'S'; break;
          default: throw FormatException('Unknown escape kind: $kind');
      }
      return {
          'ir': 'Escape',
          'type': type,
      };
  }
}

class UnicodeProperty extends Node {
  final String value;
  final bool negated;

  UnicodeProperty({required this.value, required this.negated});

  factory UnicodeProperty.fromJson(Map<String, dynamic> json) {
    return UnicodeProperty(
      value: json['value'] as String,
      negated: json['negated'] as bool,
    );
  }

  @override
  Map<String, dynamic> toIR() {
    throw FormatException('UnicodeProperty cannot be used as a standalone IR node');
  }
  
  Map<String, dynamic> toClassItem() {
      return {
          'ir': 'Escape',
          'type': negated ? 'P' : 'p',
          'property': value,
      };
  }
}
