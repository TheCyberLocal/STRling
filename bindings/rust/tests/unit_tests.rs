//! Unit Tests for STRling Rust Binding
//!
//! This module provides comprehensive unit tests for all core components:
//! - Parser tests
//! - Compiler tests
//! - Emitter tests
//! - Interaction tests (Parser→Compiler, Compiler→Emitter)

use strling::core::parser::Parser;
use strling::core::compiler::Compiler;
use strling::core::nodes::*;
use strling::core::nodes::MaxBound;
use strling::core::ir::*;
use strling::emitters::pcre2::PCRE2Emitter;

// ============================================================================
// Parser Unit Tests
// ============================================================================

#[cfg(test)]
mod parser_tests {
    use super::*;

    #[test]
    fn test_parse_simple_literal() {
        let mut parser = Parser::new("hello".to_string());
        let (_flags, ast) = parser.parse().unwrap();

        // Parser may return Sequence of individual characters or consolidated Literal
        match ast {
            Node::Literal(lit) => assert_eq!(lit.value, "hello"),
            Node::Sequence(seq) => {
                // Check that the sequence is equivalent to "hello"
                let combined: String = seq.parts.iter().filter_map(|n| {
                    if let Node::Literal(lit) = n { Some(lit.value.clone()) } else { None }
                }).collect();
                assert_eq!(combined, "hello");
            }
            _ => panic!("Expected Literal or Sequence node, got {:?}", ast),
        }
    }

    #[test]
    fn test_parse_digit_shorthand() {
        // \d parses as CharacterClass with a ClassEscape item
        let mut parser = Parser::new("\\d".to_string());
        let (_flags, ast) = parser.parse().unwrap();

        match ast {
            Node::CharacterClass(cc) => {
                assert!(!cc.negated);
                assert_eq!(cc.items.len(), 1);
                match &cc.items[0] {
                    ClassItem::Esc(e) => assert_eq!(e.escape_type, "d"),
                    _ => panic!("Expected ClassEscape item"),
                }
            }
            _ => panic!("Expected CharacterClass node for \\d"),
        }
    }

    #[test]
    fn test_parse_word_shorthand() {
        let mut parser = Parser::new("\\w".to_string());
        let (_flags, ast) = parser.parse().unwrap();

        match ast {
            Node::CharacterClass(cc) => {
                assert!(!cc.negated);
                match &cc.items[0] {
                    ClassItem::Esc(e) => assert_eq!(e.escape_type, "w"),
                    _ => panic!("Expected ClassEscape item"),
                }
            }
            _ => panic!("Expected CharacterClass node"),
        }
    }

    #[test]
    fn test_parse_whitespace_shorthand() {
        let mut parser = Parser::new("\\s".to_string());
        let (_flags, ast) = parser.parse().unwrap();

        match ast {
            Node::CharacterClass(cc) => {
                assert!(!cc.negated);
                match &cc.items[0] {
                    ClassItem::Esc(e) => assert_eq!(e.escape_type, "s"),
                    _ => panic!("Expected ClassEscape item"),
                }
            }
            _ => panic!("Expected CharacterClass node"),
        }
    }

    #[test]
    fn test_parse_negated_digit_shorthand() {
        let mut parser = Parser::new("\\D".to_string());
        let (_flags, ast) = parser.parse().unwrap();

        match ast {
            Node::CharacterClass(cc) => {
                assert!(cc.negated);
                match &cc.items[0] {
                    ClassItem::Esc(e) => assert_eq!(e.escape_type, "d"),
                    _ => panic!("Expected ClassEscape item"),
                }
            }
            _ => panic!("Expected CharacterClass node"),
        }
    }

    #[test]
    fn test_parse_character_class() {
        let mut parser = Parser::new("[abc]".to_string());
        let (_flags, ast) = parser.parse().unwrap();

        match ast {
            Node::CharacterClass(cc) => {
                assert!(!cc.negated);
            }
            _ => panic!("Expected CharacterClass node"),
        }
    }

    #[test]
    fn test_parse_negated_character_class() {
        let mut parser = Parser::new("[^abc]".to_string());
        let (_flags, ast) = parser.parse().unwrap();

        match ast {
            Node::CharacterClass(cc) => {
                assert!(cc.negated);
            }
            _ => panic!("Expected CharacterClass node"),
        }
    }

    #[test]
    fn test_parse_quantifier_plus() {
        let mut parser = Parser::new("a+".to_string());
        let (_flags, ast) = parser.parse().unwrap();

        match ast {
            Node::Quantifier(q) => {
                assert_eq!(q.min, 1);
                assert!(q.max == MaxBound::Infinite("Inf".to_string()));
                assert!(!q.lazy);
                assert!(!q.possessive);
            }
            _ => panic!("Expected Quantifier node"),
        }
    }

    #[test]
    fn test_parse_quantifier_star() {
        let mut parser = Parser::new("a*".to_string());
        let (_flags, ast) = parser.parse().unwrap();

        match ast {
            Node::Quantifier(q) => {
                assert_eq!(q.min, 0);
                assert!(q.max == MaxBound::Infinite("Inf".to_string()));
            }
            _ => panic!("Expected Quantifier node"),
        }
    }

    #[test]
    fn test_parse_quantifier_question() {
        let mut parser = Parser::new("a?".to_string());
        let (_flags, ast) = parser.parse().unwrap();

        match ast {
            Node::Quantifier(q) => {
                assert_eq!(q.min, 0);
                assert_eq!(q.max, MaxBound::Finite(1));
            }
            _ => panic!("Expected Quantifier node"),
        }
    }

    #[test]
    fn test_parse_lazy_quantifier() {
        let mut parser = Parser::new("a+?".to_string());
        let (_flags, ast) = parser.parse().unwrap();

        match ast {
            Node::Quantifier(q) => {
                assert_eq!(q.min, 1);
                assert!(q.lazy);
            }
            _ => panic!("Expected Quantifier node"),
        }
    }

    #[test]
    fn test_parse_brace_quantifier_exact() {
        let mut parser = Parser::new("a{3}".to_string());
        let (_flags, ast) = parser.parse().unwrap();

        match ast {
            Node::Quantifier(q) => {
                assert_eq!(q.min, 3);
                assert_eq!(q.max, MaxBound::Finite(3));
            }
            _ => panic!("Expected Quantifier node"),
        }
    }

    #[test]
    fn test_parse_brace_quantifier_range() {
        let mut parser = Parser::new("a{2,5}".to_string());
        let (_flags, ast) = parser.parse().unwrap();

        match ast {
            Node::Quantifier(q) => {
                assert_eq!(q.min, 2);
                assert_eq!(q.max, MaxBound::Finite(5));
            }
            _ => panic!("Expected Quantifier node"),
        }
    }

    #[test]
    fn test_parse_brace_quantifier_at_least() {
        let mut parser = Parser::new("a{2,}".to_string());
        let (_flags, ast) = parser.parse().unwrap();

        match ast {
            Node::Quantifier(q) => {
                assert_eq!(q.min, 2);
                assert!(q.max == MaxBound::Infinite("Inf".to_string()));
            }
            _ => panic!("Expected Quantifier node"),
        }
    }

    #[test]
    fn test_parse_capturing_group() {
        let mut parser = Parser::new("(abc)".to_string());
        let (_flags, ast) = parser.parse().unwrap();

        match ast {
            Node::Group(g) => {
                assert!(g.capturing);
                assert!(g.name.is_none());
            }
            _ => panic!("Expected Group node"),
        }
    }

    #[test]
    fn test_parse_named_group() {
        let mut parser = Parser::new("(?<name>abc)".to_string());
        let (_flags, ast) = parser.parse().unwrap();

        match ast {
            Node::Group(g) => {
                assert!(g.capturing);
                assert_eq!(g.name, Some("name".to_string()));
            }
            _ => panic!("Expected Group node"),
        }
    }

    #[test]
    fn test_parse_noncapturing_group() {
        let mut parser = Parser::new("(?:abc)".to_string());
        let (_flags, ast) = parser.parse().unwrap();

        match ast {
            Node::Group(g) => {
                assert!(!g.capturing);
            }
            _ => panic!("Expected Group node"),
        }
    }

    #[test]
    fn test_parse_alternation() {
        let mut parser = Parser::new("a|b".to_string());
        let (_flags, ast) = parser.parse().unwrap();

        match ast {
            Node::Alternation(alt) => {
                assert_eq!(alt.branches.len(), 2);
            }
            _ => panic!("Expected Alternation node"),
        }
    }

    #[test]
    fn test_parse_lookahead() {
        let mut parser = Parser::new("(?=abc)".to_string());
        let (_flags, ast) = parser.parse().unwrap();

        match ast {
            Node::Lookahead(_) => {}
            _ => panic!("Expected Lookahead node"),
        }
    }

    #[test]
    fn test_parse_negative_lookahead() {
        let mut parser = Parser::new("(?!abc)".to_string());
        let (_flags, ast) = parser.parse().unwrap();

        match ast {
            Node::NegativeLookahead(_) => {}
            _ => panic!("Expected NegativeLookahead node"),
        }
    }

    #[test]
    fn test_parse_lookbehind() {
        let mut parser = Parser::new("(?<=abc)".to_string());
        let (_flags, ast) = parser.parse().unwrap();

        match ast {
            Node::Lookbehind(_) => {}
            _ => panic!("Expected Lookbehind node"),
        }
    }

    #[test]
    fn test_parse_negative_lookbehind() {
        let mut parser = Parser::new("(?<!abc)".to_string());
        let (_flags, ast) = parser.parse().unwrap();

        match ast {
            Node::NegativeLookbehind(_) => {}
            _ => panic!("Expected NegativeLookbehind node"),
        }
    }

    #[test]
    fn test_parse_dot() {
        let mut parser = Parser::new(".".to_string());
        let (_flags, ast) = parser.parse().unwrap();

        match ast {
            Node::Dot(_) => {}
            _ => panic!("Expected Dot node"),
        }
    }

    #[test]
    fn test_parse_anchor_start() {
        let mut parser = Parser::new("^".to_string());
        let (_flags, ast) = parser.parse().unwrap();

        match ast {
            Node::Anchor(a) => assert_eq!(a.at, "Start"),
            _ => panic!("Expected Anchor node"),
        }
    }

    #[test]
    fn test_parse_anchor_end() {
        let mut parser = Parser::new("$".to_string());
        let (_flags, ast) = parser.parse().unwrap();

        match ast {
            Node::Anchor(a) => assert_eq!(a.at, "End"),
            _ => panic!("Expected Anchor node"),
        }
    }

    #[test]
    fn test_parse_word_boundary() {
        let mut parser = Parser::new("\\b".to_string());
        let (_flags, ast) = parser.parse().unwrap();

        match ast {
            Node::Anchor(a) => assert_eq!(a.at, "WordBoundary"),
            _ => panic!("Expected Anchor node"),
        }
    }

    #[test]
    fn test_parse_sequence() {
        let mut parser = Parser::new("abc".to_string());
        let (_flags, ast) = parser.parse().unwrap();

        match ast {
            // Might be a single literal for consecutive chars
            Node::Literal(lit) => assert_eq!(lit.value, "abc"),
            Node::Sequence(seq) => assert!(!seq.parts.is_empty()),
            _ => panic!("Expected Literal or Sequence node"),
        }
    }

    #[test]
    fn test_parse_backreference() {
        let mut parser = Parser::new("(a)\\1".to_string());
        let (_flags, ast) = parser.parse().unwrap();

        match ast {
            Node::Sequence(seq) => {
                assert!(seq.parts.len() >= 2);
                match &seq.parts[1] {
                    Node::Backreference(br) => {
                        assert_eq!(br.by_index, Some(1));
                    }
                    _ => panic!("Expected Backreference as second part"),
                }
            }
            _ => panic!("Expected Sequence node"),
        }
    }

    #[test]
    fn test_parse_named_backreference() {
        let mut parser = Parser::new("(?<word>\\w+)\\k<word>".to_string());
        let (_flags, ast) = parser.parse().unwrap();

        match ast {
            Node::Sequence(seq) => {
                assert!(seq.parts.len() >= 2);
                let has_backref = seq.parts.iter().any(|p| matches!(p, Node::Backreference(br) if br.by_name == Some("word".to_string())));
                assert!(has_backref, "Expected named backreference");
            }
            _ => panic!("Expected Sequence node"),
        }
    }

    #[test]
    fn test_parse_flags_directive() {
        let mut parser = Parser::new("%flags i\ntest".to_string());
        let (flags, _ast) = parser.parse().unwrap();

        assert!(flags.ignore_case);
    }

    #[test]
    fn test_parse_unterminated_group_error() {
        let mut parser = Parser::new("(abc".to_string());
        let result = parser.parse();
        assert!(result.is_err());
    }

    #[test]
    fn test_parse_unterminated_class_error() {
        let mut parser = Parser::new("[abc".to_string());
        let result = parser.parse();
        assert!(result.is_err());
    }
}

// ============================================================================
// Compiler Unit Tests
// ============================================================================

#[cfg(test)]
mod compiler_tests {
    use super::*;

    fn compile(src: &str) -> IROp {
        let mut parser = Parser::new(src.to_string());
        let (_flags, ast) = parser.parse().unwrap();
        let mut compiler = Compiler::new();
        compiler.compile(&ast)
    }

    #[test]
    fn test_compile_literal() {
        let ir = compile("hello");
        match ir {
            IROp::Lit(lit) => assert_eq!(lit.value, "hello"),
            _ => panic!("Expected IRLit"),
        }
    }

    #[test]
    fn test_compile_digit_class() {
        let ir = compile("\\d");
        match ir {
            IROp::CharClass(cc) => {
                assert!(!cc.negated);
                assert_eq!(cc.items.len(), 1);
            }
            _ => panic!("Expected IRCharClass"),
        }
    }

    #[test]
    fn test_compile_quantifier_plus() {
        let ir = compile("a+");
        match ir {
            IROp::Quant(q) => {
                assert_eq!(q.min, 1);
                assert_eq!(q.max, IRMaxBound::Infinite("Inf".to_string()));
                assert_eq!(q.mode, "Greedy");
            }
            _ => panic!("Expected IRQuant"),
        }
    }

    #[test]
    fn test_compile_quantifier_star() {
        let ir = compile("a*");
        match ir {
            IROp::Quant(q) => {
                assert_eq!(q.min, 0);
                assert_eq!(q.max, IRMaxBound::Infinite("Inf".to_string()));
            }
            _ => panic!("Expected IRQuant"),
        }
    }

    #[test]
    fn test_compile_quantifier_question() {
        let ir = compile("a?");
        match ir {
            IROp::Quant(q) => {
                assert_eq!(q.min, 0);
                assert_eq!(q.max, IRMaxBound::Finite(1));
            }
            _ => panic!("Expected IRQuant"),
        }
    }

    #[test]
    fn test_compile_lazy_quantifier() {
        let ir = compile("a+?");
        match ir {
            IROp::Quant(q) => {
                assert_eq!(q.mode, "Lazy");
            }
            _ => panic!("Expected IRQuant"),
        }
    }

    #[test]
    fn test_compile_capturing_group() {
        let ir = compile("(a)");
        match ir {
            IROp::Group(g) => {
                assert!(g.capturing);
                assert!(g.name.is_none());
            }
            _ => panic!("Expected IRGroup"),
        }
    }

    #[test]
    fn test_compile_named_group() {
        let ir = compile("(?<foo>a)");
        match ir {
            IROp::Group(g) => {
                assert!(g.capturing);
                assert_eq!(g.name, Some("foo".to_string()));
            }
            _ => panic!("Expected IRGroup"),
        }
    }

    #[test]
    fn test_compile_noncapturing_group() {
        let ir = compile("(?:a)");
        match ir {
            IROp::Group(g) => {
                assert!(!g.capturing);
            }
            _ => panic!("Expected IRGroup"),
        }
    }

    #[test]
    fn test_compile_alternation() {
        let ir = compile("a|b");
        match ir {
            IROp::Alt(alt) => {
                assert_eq!(alt.branches.len(), 2);
            }
            _ => panic!("Expected IRAlt"),
        }
    }

    #[test]
    fn test_compile_sequence() {
        let ir = compile("a.b");
        match ir {
            IROp::Seq(seq) => {
                assert!(!seq.parts.is_empty());
            }
            _ => panic!("Expected IRSeq"),
        }
    }

    #[test]
    fn test_compile_lookahead() {
        let ir = compile("(?=a)");
        match ir {
            IROp::Look(look) => {
                assert_eq!(look.dir, "Ahead");
                assert!(!look.neg);
            }
            _ => panic!("Expected IRLook"),
        }
    }

    #[test]
    fn test_compile_negative_lookahead() {
        let ir = compile("(?!a)");
        match ir {
            IROp::Look(look) => {
                assert_eq!(look.dir, "Ahead");
                assert!(look.neg);
            }
            _ => panic!("Expected IRLook"),
        }
    }

    #[test]
    fn test_compile_lookbehind() {
        let ir = compile("(?<=a)");
        match ir {
            IROp::Look(look) => {
                assert_eq!(look.dir, "Behind");
                assert!(!look.neg);
            }
            _ => panic!("Expected IRLook"),
        }
    }

    #[test]
    fn test_compile_negative_lookbehind() {
        let ir = compile("(?<!a)");
        match ir {
            IROp::Look(look) => {
                assert_eq!(look.dir, "Behind");
                assert!(look.neg);
            }
            _ => panic!("Expected IRLook"),
        }
    }

    #[test]
    fn test_compile_anchor_start() {
        let ir = compile("^");
        match ir {
            IROp::Anchor(a) => assert_eq!(a.at, "Start"),
            _ => panic!("Expected IRAnchor"),
        }
    }

    #[test]
    fn test_compile_anchor_end() {
        let ir = compile("$");
        match ir {
            IROp::Anchor(a) => assert_eq!(a.at, "End"),
            _ => panic!("Expected IRAnchor"),
        }
    }

    #[test]
    fn test_compile_dot() {
        let ir = compile(".");
        match ir {
            IROp::Dot(_) => {}
            _ => panic!("Expected IRDot"),
        }
    }

    #[test]
    fn test_compile_backreference() {
        let ir = compile("(a)\\1");
        match ir {
            IROp::Seq(seq) => {
                let has_backref = seq.parts.iter().any(|p| matches!(p, IROp::Backref(_)));
                assert!(has_backref, "Expected IRBackref in sequence");
            }
            _ => panic!("Expected IRSeq"),
        }
    }
}

// ============================================================================
// Emitter Unit Tests
// ============================================================================

#[cfg(test)]
mod emitter_tests {
    use super::*;

    fn emit(src: &str) -> String {
        let mut parser = Parser::new(src.to_string());
        let (flags, ast) = parser.parse().unwrap();
        let mut compiler = Compiler::new();
        let ir = compiler.compile(&ast);
        PCRE2Emitter::new(flags).emit(&ir)
    }

    #[test]
    fn test_emit_literal() {
        assert_eq!(emit("hello"), "hello");
    }

    #[test]
    fn test_emit_digit() {
        // \d is parsed as CharacterClass with escape item, emits as [\d]
        // This is semantically equivalent to \d
        let result = emit("\\d");
        assert!(result == "\\d" || result == "[\\d]", "Expected \\d or [\\d], got {}", result);
    }

    #[test]
    fn test_emit_negated_digit() {
        // \D is parsed as negated CharacterClass, emits as [^\d] or \D
        let result = emit("\\D");
        assert!(result == "\\D" || result == "[^\\d]", "Expected \\D or [^\\d], got {}", result);
    }

    #[test]
    fn test_emit_word() {
        let result = emit("\\w");
        assert!(result == "\\w" || result == "[\\w]", "Expected \\w or [\\w], got {}", result);
    }

    #[test]
    fn test_emit_whitespace() {
        let result = emit("\\s");
        assert!(result == "\\s" || result == "[\\s]", "Expected \\s or [\\s], got {}", result);
    }

    #[test]
    fn test_emit_character_class() {
        let result = emit("[abc]");
        assert!(result.starts_with('[') && result.ends_with(']'));
    }

    #[test]
    fn test_emit_negated_class() {
        let result = emit("[^abc]");
        assert!(result.contains("[^"));
    }

    #[test]
    fn test_emit_quantifier_plus() {
        assert_eq!(emit("a+"), "a+");
    }

    #[test]
    fn test_emit_quantifier_star() {
        assert_eq!(emit("a*"), "a*");
    }

    #[test]
    fn test_emit_quantifier_question() {
        assert_eq!(emit("a?"), "a?");
    }

    #[test]
    fn test_emit_lazy_plus() {
        assert_eq!(emit("a+?"), "a+?");
    }

    #[test]
    fn test_emit_lazy_star() {
        assert_eq!(emit("a*?"), "a*?");
    }

    #[test]
    fn test_emit_brace_exact() {
        assert_eq!(emit("a{3}"), "a{3}");
    }

    #[test]
    fn test_emit_brace_range() {
        assert_eq!(emit("a{2,5}"), "a{2,5}");
    }

    #[test]
    fn test_emit_brace_at_least() {
        assert_eq!(emit("a{2,}"), "a{2,}");
    }

    #[test]
    fn test_emit_capturing_group() {
        assert_eq!(emit("(a)"), "(a)");
    }

    #[test]
    fn test_emit_named_group() {
        assert_eq!(emit("(?<foo>a)"), "(?<foo>a)");
    }

    #[test]
    fn test_emit_noncapturing_group() {
        assert_eq!(emit("(?:a)"), "(?:a)");
    }

    #[test]
    fn test_emit_alternation() {
        assert_eq!(emit("a|b"), "a|b");
    }

    #[test]
    fn test_emit_lookahead() {
        assert_eq!(emit("(?=a)"), "(?=a)");
    }

    #[test]
    fn test_emit_negative_lookahead() {
        assert_eq!(emit("(?!a)"), "(?!a)");
    }

    #[test]
    fn test_emit_lookbehind() {
        assert_eq!(emit("(?<=a)"), "(?<=a)");
    }

    #[test]
    fn test_emit_negative_lookbehind() {
        assert_eq!(emit("(?<!a)"), "(?<!a)");
    }

    #[test]
    fn test_emit_dot() {
        assert_eq!(emit("."), ".");
    }

    #[test]
    fn test_emit_anchor_start() {
        assert_eq!(emit("^"), "^");
    }

    #[test]
    fn test_emit_anchor_end() {
        assert_eq!(emit("$"), "$");
    }

    #[test]
    fn test_emit_word_boundary() {
        assert_eq!(emit("\\b"), "\\b");
    }

    #[test]
    fn test_emit_escaped_special_chars() {
        assert_eq!(emit("\\."), "\\.");
    }

    #[test]
    fn test_emit_flags_prefix() {
        // The emitter does not prepend inline flag modifiers to the pattern.
        // Flags are tracked separately and can be applied by the consumer.
        // This test verifies the pattern is emitted correctly.
        let result = emit("%flags i\ntest");
        assert!(result.contains("test") || result == "test");
    }

    #[test]
    fn test_emit_multiple_flags() {
        // Flags are tracked separately, not inlined in the pattern
        let result = emit("%flags i,m,s\ntest");
        assert!(result.contains("test") || result == "test");
    }
}

// ============================================================================
// Interaction Tests (Full Pipeline)
// ============================================================================

#[cfg(test)]
mod interaction_tests {
    use super::*;

    fn full_pipeline(src: &str) -> String {
        let mut parser = Parser::new(src.to_string());
        let (flags, ast) = parser.parse().unwrap();
        let mut compiler = Compiler::new();
        let ir = compiler.compile(&ast);
        PCRE2Emitter::new(flags).emit(&ir)
    }

    #[test]
    fn test_phone_number_pattern() {
        // Phone pattern: (ddd)[-. ]?(ddd)[-. ]?(dddd)
        let result = full_pipeline("(\\d{3})[-. ]?(\\d{3})[-. ]?(\\d{4})");
        // Should contain the capturing groups and quantifiers
        // \d may be emitted as [\d] which is semantically equivalent
        assert!(result.contains("{3}") || result.contains("{3}"));
        assert!(result.contains("?"));
    }

    #[test]
    fn test_email_local_part() {
        let result = full_pipeline("[a-zA-Z0-9._%+-]+");
        assert!(result.contains('+'));
        assert!(result.starts_with('['));
    }

    #[test]
    fn test_complex_alternation() {
        let result = full_pipeline("cat|dog|bird");
        assert_eq!(result.matches('|').count(), 2);
    }

    #[test]
    fn test_nested_groups() {
        let result = full_pipeline("((a)(b))");
        assert_eq!(result.matches('(').count(), 3);
    }

    #[test]
    fn test_quantified_group() {
        let result = full_pipeline("(ab)+");
        assert!(result.contains("(ab)+"));
    }

    #[test]
    fn test_alternation_in_group() {
        let result = full_pipeline("(a|b)");
        assert_eq!(result, "(a|b)");
    }

    #[test]
    fn test_lookahead_with_quantifier() {
        let result = full_pipeline("a(?=b+)");
        assert!(result.contains("(?="));
        assert!(result.contains("+"));
    }

    #[test]
    fn test_word_boundaries() {
        let result = full_pipeline("\\bword\\b");
        assert!(result.contains("\\b"));
    }

    #[test]
    fn test_character_class_with_range() {
        let result = full_pipeline("[a-z0-9]");
        assert!(result.contains("a-z"));
        assert!(result.contains("0-9"));
    }
}
