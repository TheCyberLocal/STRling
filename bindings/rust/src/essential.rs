//! Standard-library compatibility lexical-shape patterns for common string
//! formats. They do not establish semantic validity or standards conformance.
//!
//! Each helper composes existing AST node constructors so the compiled output
//! flows through the standard pipeline and no raw regex leaks into the public
//! API.

use crate::core::nodes::*;

fn letter_items() -> Vec<ClassItem> {
    vec![
        ClassItem::Range(ClassRange { from_ch: "A".into(), to_ch: "Z".into() }),
        ClassItem::Range(ClassRange { from_ch: "a".into(), to_ch: "z".into() }),
    ]
}

fn digit_items() -> Vec<ClassItem> {
    vec![ClassItem::Esc(ClassEscape { escape_type: "d".into(), property: None })]
}

fn hex_items() -> Vec<ClassItem> {
    vec![
        ClassItem::Range(ClassRange { from_ch: "A".into(), to_ch: "F".into() }),
        ClassItem::Range(ClassRange { from_ch: "a".into(), to_ch: "f".into() }),
        ClassItem::Range(ClassRange { from_ch: "0".into(), to_ch: "9".into() }),
    ]
}

fn chars_items(s: &str) -> Vec<ClassItem> {
    s.chars()
        .map(|c| ClassItem::Char(ClassLiteral { ch: c.to_string() }))
        .collect()
}

fn class_of(items: Vec<ClassItem>, min: i32, max: Option<i32>) -> Node {
    let class = Node::CharacterClass(CharacterClass { negated: false, items });
    if min == 1 && max == Some(1) {
        class
    } else {
        let max_bound = match max {
            Some(n) => MaxBound::Finite(n),
            None => MaxBound::Infinite("Inf".to_string()),
        };
        Node::Quantifier(Quantifier {
            target: QuantifierTarget { child: Box::new(class) },
            min,
            max: max_bound,
            mode: "Greedy".to_string(),
            greedy: true,
            lazy: false,
            possessive: false,
        })
    }
}

fn dig_n(min: i32, max: Option<i32>) -> Node { class_of(digit_items(), min, max) }
fn hex_n(min: i32, max: Option<i32>) -> Node { class_of(hex_items(), min, max) }
fn letters_n(min: i32, max: Option<i32>) -> Node { class_of(letter_items(), min, max) }

fn lit(s: &str) -> Node {
    Node::Literal(Literal { value: s.to_string() })
}

fn seq(parts: Vec<Node>) -> Node {
    Node::Sequence(Sequence { parts })
}

fn opt(node: Node) -> Node {
    let wrapped = Node::Group(Group {
        capturing: false,
        body: Box::new(node),
        name: None,
        atomic: None,
    });
    Node::Quantifier(Quantifier {
        target: QuantifierTarget { child: Box::new(wrapped) },
        min: 0,
        max: MaxBound::Finite(1),
        mode: "Greedy".to_string(),
        greedy: true,
        lazy: false,
        possessive: false,
    })
}

fn alt(branches: Vec<Node>) -> Node {
    Node::Alternation(Alternation { branches })
}

fn concat(a: Vec<ClassItem>, b: Vec<ClassItem>) -> Vec<ClassItem> {
    let mut out = a;
    out.extend(b);
    out
}

/// Matches the legacy email-like lexical shape; RFC 5322 conformance is not claimed.
pub fn email() -> Node {
    let local = class_of(
        concat(concat(letter_items(), digit_items()), chars_items("._%+-")),
        1, None);
    let domain = class_of(
        concat(concat(letter_items(), digit_items()), chars_items(".-")),
        1, None);
    let tld = letters_n(2, None);
    seq(vec![local, lit("@"), domain, lit("."), tld])
}

/// Matches the legacy HTTP(S) URL-like lexical shape; RFC 3986 conformance is not claimed.
pub fn url() -> Node {
    let base = concat(concat(letter_items(), digit_items()), chars_items("/_-.~%&=:@!$'()*+,;"));
    let with_q = concat(base.clone(), chars_items("?"));
    let with_frag = concat(with_q.clone(), chars_items("#"));

    let scheme = seq(vec![lit("http"), opt(lit("s"))]);
    let host = class_of(concat(concat(letter_items(), digit_items()), chars_items(".-")), 1, None);
    let port = opt(seq(vec![lit(":"), dig_n(1, None)]));
    let path = opt(seq(vec![lit("/"), class_of(base, 0, None)]));
    let query = opt(seq(vec![lit("?"), class_of(with_q, 0, None)]));
    let fragment = opt(seq(vec![lit("#"), class_of(with_frag, 0, None)]));
    seq(vec![scheme, lit("://"), host, port, path, query, fragment])
}

/// Matches the RFC 9562 UUID text shape. Pass `4` to constrain the version and
/// variant nibbles, or `0` to leave fields uninterpreted.
pub fn uuid(version: i32) -> Node {
    let dash = || lit("-");
    if version == 4 {
        let variant = class_of(chars_items("89ABab"), 1, Some(1));
        return seq(vec![
            hex_n(8, Some(8)), dash(),
            hex_n(4, Some(4)), dash(),
            lit("4"), hex_n(3, Some(3)), dash(),
            variant, hex_n(3, Some(3)), dash(),
            hex_n(12, Some(12)),
        ]);
    }
    seq(vec![
        hex_n(8, Some(8)), dash(),
        hex_n(4, Some(4)), dash(),
        hex_n(4, Some(4)), dash(),
        hex_n(4, Some(4)), dash(),
        hex_n(12, Some(12)),
    ])
}

/// Matches an IPv4-like or full-form IPv6 lexical shape; address validity is not claimed.
/// Pass `4` or `6` for family-specific matching, or `0` for either family.
pub fn ip(version: i32) -> Node {
    let ipv4 = || seq(vec![
        dig_n(1, Some(3)), lit("."),
        dig_n(1, Some(3)), lit("."),
        dig_n(1, Some(3)), lit("."),
        dig_n(1, Some(3)),
    ]);
    let ipv6 = || seq(vec![
        hex_n(1, Some(4)), lit(":"),
        hex_n(1, Some(4)), lit(":"),
        hex_n(1, Some(4)), lit(":"),
        hex_n(1, Some(4)), lit(":"),
        hex_n(1, Some(4)), lit(":"),
        hex_n(1, Some(4)), lit(":"),
        hex_n(1, Some(4)), lit(":"),
        hex_n(1, Some(4)),
    ]);
    match version {
        4 => ipv4(),
        6 => ipv6(),
        _ => alt(vec![ipv4(), ipv6()]),
    }
}

/// Matches a timestamp-like lexical shape; RFC 3339 / ISO 8601 validity is not claimed.
pub fn date_time() -> Node {
    let sign = class_of(chars_items("+-"), 1, Some(1));
    let frac = seq(vec![lit("."), dig_n(1, None)]);
    let offset = seq(vec![sign, dig_n(2, Some(2)), lit(":"), dig_n(2, Some(2))]);
    seq(vec![
        dig_n(4, Some(4)), lit("-"), dig_n(2, Some(2)), lit("-"), dig_n(2, Some(2)),
        lit("T"),
        dig_n(2, Some(2)), lit(":"), dig_n(2, Some(2)), lit(":"), dig_n(2, Some(2)),
        opt(frac),
        opt(alt(vec![lit("Z"), offset])),
    ])
}
