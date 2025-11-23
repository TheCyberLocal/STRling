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
}
