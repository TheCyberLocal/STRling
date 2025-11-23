//! Simple, fluent builder helpers for constructing AST `Node`s.
//!
//! This module provides a tiny set of convenience functions that mirror the
//! Python and TypeScript `simply` builders. They make writing tests and
//! examples much more concise by producing `Node` instances with helper
//! constructors (start, end, literal, digit, any_of, merge, capture, optional/may).

use crate::core::nodes::*;

/// Anchor at the start of the input.
pub fn start() -> Node {
    Node::Anchor(Anchor { at: "Start".into() })
}

/// Anchor at the end of the input.
pub fn end() -> Node {
    Node::Anchor(Anchor { at: "End".into() })
}

/// A literal string.
pub fn literal(s: &str) -> Node {
    Node::Literal(Literal { value: s.to_string() })
}

/// Helper to build a `\d` character class and repeat it exactly `count` times.
pub fn digit(count: u32) -> Node {
    let class = Node::CharacterClass(CharacterClass {
        negated: false,
        items: vec![ClassItem::Esc(ClassEscape { escape_type: "d".into(), property: None })],
    });

    Node::Quantifier(Quantifier {
        target: QuantifierTarget { child: Box::new(class) },
        min: count as i32,
        max: MaxBound::Finite(count as i32),
        mode: "Greedy".to_string(),
        greedy: true,
        lazy: false,
        possessive: false,
    })
}

/// Construct a character class from a list of one-character strings.
/// Non-empty strings will be used as literal class members.
pub fn any_of(chars: &[&str]) -> Node {
    let mut items: Vec<ClassItem> = Vec::new();

    for s in chars.iter() {
        // treat the provided string as a literal character (take full string)
        items.push(ClassItem::Char(ClassLiteral { ch: s.to_string() }));
    }

    Node::CharacterClass(CharacterClass { negated: false, items })
}

/// Create a sequence (merge) from a list of nodes.
pub fn merge(parts: Vec<Node>) -> Node {
    Node::Sequence(Sequence { parts })
}

/// Create a simple capturing group around a node.
pub fn capture(node: Node) -> Node {
    Node::Group(Group { capturing: true, body: Box::new(node), name: None, atomic: None })
}

/// Create a simple non-capturing (or optional) quantifier (0..1)
pub fn optional(node: Node) -> Node {
    Node::Quantifier(Quantifier {
        target: QuantifierTarget { child: Box::new(node) },
        min: 0,
        max: MaxBound::Finite(1),
        mode: "Greedy".to_string(),
        greedy: true,
        lazy: false,
        possessive: false,
    })
}

/// Alias for `optional` to match Python's API (`may`).
pub fn may(node: Node) -> Node {
    optional(node)
}

/// Dot (`.`) - any character except newline (represented as a Dot node)
pub fn dot() -> Node {
    Node::Dot(Dot {})
}

/// Word boundary anchor: `\b`
pub fn word_boundary() -> Node {
    Node::Anchor(Anchor { at: "WordBoundary".into() })
}

/// Not-word-boundary anchor: `\B`
pub fn not_word_boundary() -> Node {
    Node::Anchor(Anchor { at: "NotWordBoundary".into() })
}

/// Negated variant of `any_of` -> build `[^...]`
pub fn not_any_of(chars: &[&str]) -> Node {
    let mut items: Vec<ClassItem> = Vec::new();

    for s in chars.iter() {
        items.push(ClassItem::Char(ClassLiteral { ch: s.to_string() }));
    }

    Node::CharacterClass(CharacterClass { negated: true, items })
}

/// Create ranges from a list of (from, to) tuples.
pub fn ranges(pairs: &[(&str, &str)]) -> Node {
    let mut items: Vec<ClassItem> = Vec::new();

    for (from, to) in pairs.iter() {
        items.push(ClassItem::Range(ClassRange { from_ch: from.to_string(), to_ch: to.to_string() }));
    }

    Node::CharacterClass(CharacterClass { negated: false, items })
}

/// Unicode property helper: `\p{...}`
pub fn prop(property: &str) -> Node {
    Node::CharacterClass(CharacterClass { negated: false, items: vec![ClassItem::Esc(ClassEscape { escape_type: "p".into(), property: Some(property.to_string()) })] })
}

/// Build a character class containing a single class escape (e.g. `\d`, `\w`, `\s`).
pub fn class_escape(kind: &str) -> Node {
    Node::CharacterClass(CharacterClass { negated: false, items: vec![ClassItem::Esc(ClassEscape { escape_type: kind.to_string(), property: None })] })
}

/// Escape helpers. These produce Literals for simple escapes.
pub fn escape(kind: &str) -> Node {
    // common mapping for control escapes
    let value = match kind {
        "n" => "\n".to_string(),
        "r" => "\r".to_string(),
        "t" => "\t".to_string(),
        "f" => "\x0c".to_string(),
        "v" => "\x0b".to_string(),
        "0" => "\0".to_string(),
        other => format!("\\{}", other),
    };

    Node::Literal(Literal { value })
}

/// Hex escape `\xHH` or `\x{H...}` — returns a Literal containing the corresponding character if valid
pub fn hex(code: &str) -> Node {
    // try to parse hex; fall back to literal escape string
    if let Ok(v) = i32::from_str_radix(code.trim_matches(|c| c == '{' || c == '}').trim(), 16) {
        if let Some(ch) = std::char::from_u32(v as u32) {
            return Node::Literal(Literal { value: ch.to_string() });
        }
    }

    Node::Literal(Literal { value: format!("\\x{{{}}}", code) })
}

/// Unicode codepoint escape `\u{...}` -> produce a literal of that codepoint when possible
pub fn unicode(code: &str) -> Node {
    if let Ok(v) = i32::from_str_radix(code.trim_matches(|c| c == '{' || c == '}').trim(), 16) {
        if let Some(ch) = std::char::from_u32(v as u32) {
            return Node::Literal(Literal { value: ch.to_string() });
        }
    }

    Node::Literal(Literal { value: format!("\\u{{{}}}", code) })
}

/// Named capturing group: `(?<name>...)`
pub fn named_capture(name: &str, node: Node) -> Node {
    Node::Group(Group { capturing: true, body: Box::new(node), name: Some(name.to_string()), atomic: None })
}

/// Non-capturing group: `(?:...)`
pub fn non_capturing(node: Node) -> Node {
    Node::Group(Group { capturing: false, body: Box::new(node), name: None, atomic: None })
}

/// Atomic group: `(?>...)` — keep capturing flag true by default to match existing examples
pub fn atomic(node: Node) -> Node {
    Node::Group(Group { capturing: true, body: Box::new(node), name: None, atomic: Some(true) })
}

/// Positive lookahead `(?=...)`
pub fn look_ahead(node: Node) -> Node {
    Node::Lookahead(LookaroundBody { body: Box::new(node) })
}

/// Negative lookahead `(?!...)`
pub fn neg_look_ahead(node: Node) -> Node {
    Node::NegativeLookahead(LookaroundBody { body: Box::new(node) })
}

/// Positive lookbehind `(?<=...)`
pub fn look_behind(node: Node) -> Node {
    Node::Lookbehind(LookaroundBody { body: Box::new(node) })
}

/// Negative lookbehind `(?<!...)`
pub fn neg_look_behind(node: Node) -> Node {
    Node::NegativeLookbehind(LookaroundBody { body: Box::new(node) })
}

/// Backreference by index (\1)
pub fn backref_index(i: i32) -> Node {
    Node::Backreference(Backreference { by_index: Some(i), by_name: None })
}

/// Backreference by name (\k<name>)
pub fn backref_name(name: &str) -> Node {
    Node::Backreference(Backreference { by_index: None, by_name: Some(name.to_string()) })
}

/// Helper to construct Flags from a letters string (e.g. "imx")
pub fn flag(letters: &str) -> Flags {
    Flags::from_letters(letters)
}

/// Create an alternation node from branches
pub fn alternation(branches: Vec<Node>) -> Node {
    Node::Alternation(Alternation { branches })
}

/// Convenience: either(left, right) -> alternation with two branches
pub fn either(left: Node, right: Node) -> Node {
    alternation(vec![left, right])
}

/// Create a quantifier (min..max) — `max=None` => infinite
pub fn repeat(node: Node, min: i32, max: Option<i32>) -> Node {
    let maxbound = match max {
        Some(n) => MaxBound::Finite(n),
        None => MaxBound::Infinite("Inf".to_string()),
    };

    Node::Quantifier(Quantifier { target: QuantifierTarget { child: Box::new(node) }, min, max: maxbound, mode: "Greedy".to_string(), greedy: true, lazy: false, possessive: false })
}

/// Greedy repeat helper
pub fn repeat_greedy(node: Node, min: i32, max: Option<i32>) -> Node { repeat(node, min, max) }

/// Lazy repeat helper
pub fn repeat_lazy(node: Node, min: i32, max: Option<i32>) -> Node {
    let mut n = repeat(node, min, max);
    match &mut n {
        Node::Quantifier(ref mut q) => {
            q.mode = "Lazy".to_string();
            q.greedy = false;
            q.lazy = true;
            q.possessive = false;
        }
        _ => {}
    }
    n
}

/// Possessive repeat helper
pub fn repeat_possessive(node: Node, min: i32, max: Option<i32>) -> Node {
    let mut n = repeat(node, min, max);
    match &mut n {
        Node::Quantifier(ref mut q) => {
            q.mode = "Possessive".to_string();
            q.greedy = false;
            q.lazy = false;
            q.possessive = true;
        }
        _ => {}
    }
    n
}

// ---------------------------------------------------------------------------
// Unit tests for the simple API — keep tests local to the module.
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_digit_quantifier() {
        let n = digit(3);

        match n {
            Node::Quantifier(q) => {
                assert_eq!(q.min, 3);
                assert_eq!(q.max, MaxBound::Finite(3));

                // inspect child
                match *q.target.child {
                    Node::CharacterClass(ref cc) => {
                        assert!(!cc.negated);
                        assert_eq!(cc.items.len(), 1);
                        match cc.items[0] {
                            ClassItem::Esc(ref esc) => assert_eq!(esc.escape_type, "d"),
                            _ => panic!("expected escape class item for digit"),
                        }
                    }
                    _ => panic!("expected character class child"),
                }
            }
            _ => panic!("expected quantifier node"),
        }
    }

    #[test]
    fn test_capture_optional_merge() {
        let n = merge(vec![start(), capture(digit(3)), may(any_of(&["-", ".", " "])), end()]);

        match n {
            Node::Sequence(seq) => {
                assert_eq!(seq.parts.len(), 4);

                // first part is start anchor
                match seq.parts[0] {
                    Node::Anchor(ref a) => assert_eq!(a.at, "Start"),
                    _ => panic!("expected start anchor"),
                }

                // second part is group
                match seq.parts[1] {
                    Node::Group(ref g) => {
                        assert!(g.capturing);
                        match *g.body {
                            Node::Quantifier(ref q) => assert_eq!(q.min, 3),
                            _ => panic!("expected quantifier inside group"),
                        }
                    }
                    _ => panic!("expected capturing group"),
                }

                // third part is optional quantifier
                match seq.parts[2] {
                    Node::Quantifier(ref q) => {
                        assert_eq!(q.min, 0);
                        assert_eq!(q.max, MaxBound::Finite(1));
                    }
                    _ => panic!("expected optional quantifier"),
                }

                // fourth part is end anchor
                match seq.parts[3] {
                    Node::Anchor(ref a) => assert_eq!(a.at, "End"),
                    _ => panic!("expected end anchor"),
                }
            }
            _ => panic!("expected sequence node"),
        }
    }

    #[test]
    fn test_misc_helpers() {
        // dot
        match dot() {
            Node::Dot(_) => {}
            _ => panic!("expected Dot"),
        }

        // word boundaries
        match word_boundary() {
            Node::Anchor(a) => assert_eq!(a.at, "WordBoundary"),
            _ => panic!("expected Anchor"),
        }

        match not_word_boundary() {
            Node::Anchor(a) => assert_eq!(a.at, "NotWordBoundary"),
            _ => panic!("expected Anchor"),
        }

        // not_any_of
        match not_any_of(&["a","e"]) {
            Node::CharacterClass(cc) => {
                assert!(cc.negated);
                assert_eq!(cc.items.len(), 2);
            }
            _ => panic!("expected CharacterClass"),
        }

        // ranges and prop
        match ranges(&[("A","Z"),("a","z")]) {
            Node::CharacterClass(cc) => {
                assert!(!cc.negated);
                assert_eq!(cc.items.len(), 2);
            }
            _ => panic!("expected CharacterClass"),
        }

        match prop("Lu") {
            Node::CharacterClass(cc) => {
                assert!(!cc.negated);
                match &cc.items[0] {
                    ClassItem::Esc(e) => assert_eq!(e.escape_type, "p"),
                    _ => panic!("expected ClassEscape"),
                }
            }
            _ => panic!("expected CharacterClass"),
        }

        // class escape test
        match class_escape("d") {
            Node::CharacterClass(cc) => match &cc.items[0] {
                ClassItem::Esc(e) => assert_eq!(e.escape_type, "d"),
                _ => panic!("expected ClassEscape"),
            },
            _ => panic!("expected CharacterClass"),
        }

        // flags helper
        let f = flag("im");
        assert!(f.ignore_case && f.multiline);

        // escapes
        match escape("n") {
            Node::Literal(l) => assert_eq!(l.value, "\n"),
            _ => panic!("expected Literal for escape n"),
        }

        match hex("41") {
            Node::Literal(l) => assert_eq!(l.value, "A"),
            _ => panic!("expected Literal for hex 41"),
        }

        match unicode("1F600") {
            Node::Literal(l) => assert_eq!(l.value, "😀"),
            _ => panic!("expected Literal for unicode 1F600"),
        }

        // named group
        match named_capture("area", digit(3)) {
            Node::Group(g) => assert_eq!(g.name, Some("area".to_string())),
            _ => panic!("expected Group"),
        }

        // non-capturing / atomic
        match non_capturing(digit(1)) {
            Node::Group(g) => assert!(!g.capturing),
            _ => panic!("expected non-capturing Group"),
        }

        match atomic(digit(1)) {
            Node::Group(g) => assert_eq!(g.atomic, Some(true)),
            _ => panic!("expected atomic Group"),
        }

        // lookarounds
        match look_ahead(digit(1)) {
            Node::Lookahead(_) => {}
            _ => panic!("expected Lookahead"),
        }

        match neg_look_ahead(digit(1)) {
            Node::NegativeLookahead(_) => {}
            _ => panic!("expected NegativeLookahead"),
        }

        match look_behind(literal("a")) {
            Node::Lookbehind(_) => {}
            _ => panic!("expected Lookbehind"),
        }

        match neg_look_behind(literal("a")) {
            Node::NegativeLookbehind(_) => {}
            _ => panic!("expected NegativeLookbehind"),
        }

        // backrefs
        match backref_index(2) {
            Node::Backreference(b) => assert_eq!(b.by_index, Some(2)),
            _ => panic!("expected Backreference by index"),
        }

        match backref_name("x") {
            Node::Backreference(b) => assert_eq!(b.by_name, Some("x".to_string())),
            _ => panic!("expected Backreference by name"),
        }

        // alternation
        match either(literal("cat"), literal("dog")) {
            Node::Alternation(a) => assert_eq!(a.branches.len(), 2),
            _ => panic!("expected Alternation"),
        }

        // quantifier helpers
        match repeat_greedy(literal("x"), 1, None) {
            Node::Quantifier(q) => assert_eq!(q.mode, "Greedy"),
            _ => panic!("expected Quantifier"),
        }

        match repeat_lazy(literal("x"), 1, Some(5)) {
            Node::Quantifier(q) => assert_eq!(q.mode, "Lazy"),
            _ => panic!("expected Quantifier"),
        }

        match repeat_possessive(literal("x"), 1, None) {
            Node::Quantifier(q) => assert_eq!(q.mode, "Possessive"),
            _ => panic!("expected Quantifier"),
        }
    }
}
