//! Unit tests for STRling Rust binding
//!
//! This module contains all unit tests ported from the JavaScript test suite.

use strling_core::parse;
use strling_core::core::nodes::*;

// Helper function to unwrap parse result
fn parse_ok(input: &str) -> Node {
    let (_, ast) = parse(input).expect("Parse should succeed");
    ast
}

// ============================================================================
// ANCHORS TESTS
// ============================================================================

#[cfg(test)]
mod anchors {
    use super::*;

    // Category A: Positive Cases
    #[test]
    fn test_anchor_line_start() {
        let ast = parse_ok("^");
        match ast {
            Node::Anchor(anchor) => {
                assert_eq!(anchor.at, "Start");
            }
            _ => panic!("Expected Anchor node, got {:?}", ast),
        }
    }

    #[test]
    fn test_anchor_line_end() {
        let ast = parse_ok("$");
        match ast {
            Node::Anchor(anchor) => {
                assert_eq!(anchor.at, "End");
            }
            _ => panic!("Expected Anchor node, got {:?}", ast),
        }
    }

    #[test]
    fn test_anchor_word_boundary() {
        let ast = parse_ok(r"\b");
        match ast {
            Node::Anchor(anchor) => {
                assert_eq!(anchor.at, "WordBoundary");
            }
            _ => panic!("Expected Anchor node, got {:?}", ast),
        }
    }

    #[test]
    fn test_anchor_not_word_boundary() {
        let ast = parse_ok(r"\B");
        match ast {
            Node::Anchor(anchor) => {
                assert_eq!(anchor.at, "NotWordBoundary");
            }
            _ => panic!("Expected Anchor node, got {:?}", ast),
        }
    }

    #[test]
    fn test_anchor_absolute_start() {
        let ast = parse_ok(r"\A");
        match ast {
            Node::Anchor(anchor) => {
                assert_eq!(anchor.at, "AbsoluteStart");
            }
            _ => panic!("Expected Anchor node, got {:?}", ast),
        }
    }

    #[test]
    fn test_anchor_end_before_newline() {
        let ast = parse_ok(r"\Z");
        match ast {
            Node::Anchor(anchor) => {
                assert_eq!(anchor.at, "EndBeforeFinalNewline");
            }
            _ => panic!("Expected Anchor node, got {:?}", ast),
        }
    }

    // Category C: Edge Cases
    #[test]
    fn test_pattern_with_only_anchors() {
        let ast = parse_ok(r"^\A\b$");
        match ast {
            Node::Seq(seq) => {
                assert_eq!(seq.parts.len(), 4);
                
                // Check all parts are anchors
                for part in &seq.parts {
                    match part {
                        Node::Anchor(_) => {},
                        _ => panic!("Expected all parts to be Anchor nodes"),
                    }
                }
                
                // Check specific anchor types
                let at_values: Vec<String> = seq.parts.iter().map(|part| {
                    match part {
                        Node::Anchor(a) => a.at.clone(),
                        _ => panic!("Expected Anchor"),
                    }
                }).collect();
                
                assert_eq!(at_values, vec!["Start", "AbsoluteStart", "WordBoundary", "End"]);
            }
            _ => panic!("Expected Seq node, got {:?}", ast),
        }
    }

    #[test]
    fn test_anchor_at_start_of_sequence() {
        let ast = parse_ok("^a");
        match ast {
            Node::Seq(seq) => {
                assert_eq!(seq.parts.len(), 2);
                match &seq.parts[0] {
                    Node::Anchor(anchor) => {
                        assert_eq!(anchor.at, "Start");
                    }
                    _ => panic!("Expected first part to be Anchor"),
                }
            }
            _ => panic!("Expected Seq node"),
        }
    }

    #[test]
    fn test_anchor_in_middle_of_sequence() {
        let ast = parse_ok(r"a\bb");
        match ast {
            Node::Seq(seq) => {
                assert_eq!(seq.parts.len(), 3);
                match &seq.parts[1] {
                    Node::Anchor(anchor) => {
                        assert_eq!(anchor.at, "WordBoundary");
                    }
                    _ => panic!("Expected middle part to be Anchor"),
                }
            }
            _ => panic!("Expected Seq node"),
        }
    }

    #[test]
    fn test_anchor_at_end_of_sequence() {
        let ast = parse_ok("ab$");
        match ast {
            Node::Seq(seq) => {
                // Parser creates separate Lit nodes for 'a' and 'b', so we have 3 parts
                assert_eq!(seq.parts.len(), 3);
                // Check that the last part is the anchor
                match seq.parts.last() {
                    Some(Node::Anchor(anchor)) => {
                        assert_eq!(anchor.at, "End");
                    }
                    _ => panic!("Expected last part to be Anchor"),
                }
            }
            _ => panic!("Expected Seq node"),
        }
    }

    // Category D: Interaction Cases
    #[test]
    fn test_multiline_flag_does_not_change_ast() {
        let ast_no_m = parse_ok("^a$");
        let ast_with_m = parse_ok("%flags m\n^a$");
        
        // Both should parse to the same AST structure
        match (&ast_no_m, &ast_with_m) {
            (Node::Seq(seq1), Node::Seq(seq2)) => {
                assert_eq!(seq1.parts.len(), 3);
                assert_eq!(seq2.parts.len(), 3);
                
                // Check first anchor
                match (&seq1.parts[0], &seq2.parts[0]) {
                    (Node::Anchor(a1), Node::Anchor(a2)) => {
                        assert_eq!(a1.at, "Start");
                        assert_eq!(a2.at, "Start");
                    }
                    _ => panic!("Expected Anchor nodes"),
                }
                
                // Check last anchor
                match (&seq1.parts[2], &seq2.parts[2]) {
                    (Node::Anchor(a1), Node::Anchor(a2)) => {
                        assert_eq!(a1.at, "End");
                        assert_eq!(a2.at, "End");
                    }
                    _ => panic!("Expected Anchor nodes"),
                }
            }
            _ => panic!("Expected Seq nodes"),
        }
    }

    #[test]
    fn test_anchor_in_capturing_group() {
        let ast = parse_ok("(^a)");
        match ast {
            Node::Group(group) => {
                assert!(group.capturing);
                match &*group.body {
                    Node::Seq(seq) => {
                        match &seq.parts[0] {
                            Node::Anchor(anchor) => {
                                assert_eq!(anchor.at, "Start");
                            }
                            _ => panic!("Expected Anchor in group body"),
                        }
                    }
                    _ => panic!("Expected Seq in group body"),
                }
            }
            _ => panic!("Expected Group node"),
        }
    }

    #[test]
    fn test_anchor_in_noncapturing_group() {
        let ast = parse_ok(r"(?:a\b)");
        match ast {
            Node::Group(group) => {
                assert!(!group.capturing);
                match &*group.body {
                    Node::Seq(seq) => {
                        match &seq.parts[1] {
                            Node::Anchor(anchor) => {
                                assert_eq!(anchor.at, "WordBoundary");
                            }
                            _ => panic!("Expected Anchor in group body"),
                        }
                    }
                    _ => panic!("Expected Seq in group body"),
                }
            }
            _ => panic!("Expected Group node"),
        }
    }

    #[test]
    fn test_anchor_in_lookahead() {
        let ast = parse_ok("(?=a$)");
        match ast {
            Node::Look(look) => {
                assert_eq!(look.dir, "Ahead");
                assert!(!look.neg);
                match &*look.body {
                    Node::Seq(seq) => {
                        match &seq.parts[1] {
                            Node::Anchor(anchor) => {
                                assert_eq!(anchor.at, "End");
                            }
                            _ => panic!("Expected Anchor in lookahead body"),
                        }
                    }
                    _ => panic!("Expected Seq in lookahead body"),
                }
            }
            _ => panic!("Expected Look node"),
        }
    }

    #[test]
    fn test_anchor_in_lookbehind() {
        let ast = parse_ok("(?<=^a)");
        match ast {
            Node::Look(look) => {
                assert_eq!(look.dir, "Behind");
                assert!(!look.neg);
                match &*look.body {
                    Node::Seq(seq) => {
                        match &seq.parts[0] {
                            Node::Anchor(anchor) => {
                                assert_eq!(anchor.at, "Start");
                            }
                            _ => panic!("Expected Anchor in lookbehind body"),
                        }
                    }
                    _ => panic!("Expected Seq in lookbehind body"),
                }
            }
            _ => panic!("Expected Look node"),
        }
    }

    // Category E: Complex Sequences
    #[test]
    fn test_anchor_between_quantified_atoms() {
        let ast = parse_ok("a*^b+");
        match ast {
            Node::Seq(seq) => {
                assert_eq!(seq.parts.len(), 3);
                match &seq.parts[0] {
                    Node::Quant(_) => {},
                    _ => panic!("Expected Quant node"),
                }
                match &seq.parts[1] {
                    Node::Anchor(anchor) => {
                        assert_eq!(anchor.at, "Start");
                    }
                    _ => panic!("Expected Anchor node"),
                }
                match &seq.parts[2] {
                    Node::Quant(_) => {},
                    _ => panic!("Expected Quant node"),
                }
            }
            _ => panic!("Expected Seq node"),
        }
    }

    #[test]
    fn test_anchor_after_quantified_group() {
        let ast = parse_ok("(ab)*$");
        match ast {
            Node::Seq(seq) => {
                assert_eq!(seq.parts.len(), 2);
                match &seq.parts[0] {
                    Node::Quant(_) => {},
                    _ => panic!("Expected Quant node"),
                }
                match &seq.parts[1] {
                    Node::Anchor(anchor) => {
                        assert_eq!(anchor.at, "End");
                    }
                    _ => panic!("Expected Anchor node"),
                }
            }
            _ => panic!("Expected Seq node"),
        }
    }

    #[test]
    fn test_multiple_anchors_same_type() {
        let ast = parse_ok("^^^");
        match ast {
            Node::Seq(seq) => {
                assert_eq!(seq.parts.len(), 3);
                for part in &seq.parts {
                    match part {
                        Node::Anchor(anchor) => {
                            assert_eq!(anchor.at, "Start");
                        }
                        _ => panic!("Expected Anchor node"),
                    }
                }
            }
            _ => panic!("Expected Seq node"),
        }
    }
}

// ============================================================================
// LITERALS AND ESCAPES TESTS  
// ============================================================================

#[cfg(test)]
mod literals_and_escapes {
    use super::*;

    // Basic literals that should work
    #[test]
    fn test_plain_literal_letter() {
        let ast = parse_ok("a");
        match ast {
            Node::Lit(lit) => {
                assert_eq!(lit.value, "a");
            }
            _ => panic!("Expected Lit node"),
        }
    }

    #[test]
    fn test_plain_literal_underscore() {
        let ast = parse_ok("_");
        match ast {
            Node::Lit(lit) => {
                assert_eq!(lit.value, "_");
            }
            _ => panic!("Expected Lit node"),
        }
    }

    // Identity escapes
    #[test]
    fn test_identity_escape_dot() {
        let ast = parse_ok(r"\.");
        match ast {
            Node::Lit(lit) => {
                assert_eq!(lit.value, ".");
            }
            _ => panic!("Expected Lit node"),
        }
    }

    #[test]
    fn test_identity_escape_paren() {
        let ast = parse_ok(r"\(");
        match ast {
            Node::Lit(lit) => {
                assert_eq!(lit.value, "(");
            }
            _ => panic!("Expected Lit node"),
        }
    }

    #[test]
    fn test_identity_escape_star() {
        let ast = parse_ok(r"\*");
        match ast {
            Node::Lit(lit) => {
                assert_eq!(lit.value, "*");
            }
            _ => panic!("Expected Lit node"),
        }
    }

    // Control escapes
    #[test]
    fn test_control_escape_newline() {
        let ast = parse_ok(r"\n");
        match ast {
            Node::Lit(lit) => {
                assert_eq!(lit.value, "\n");
            }
            _ => panic!("Expected Lit node"),
        }
    }

    #[test]
    fn test_control_escape_tab() {
        let ast = parse_ok(r"\t");
        match ast {
            Node::Lit(lit) => {
                assert_eq!(lit.value, "\t");
            }
            _ => panic!("Expected Lit node"),
        }
    }

    #[test]
    fn test_control_escape_carriage_return() {
        let ast = parse_ok(r"\r");
        match ast {
            Node::Lit(lit) => {
                assert_eq!(lit.value, "\r");
            }
            _ => panic!("Expected Lit node"),
        }
    }

    #[test]
    fn test_control_escape_form_feed() {
        let ast = parse_ok(r"\f");
        match ast {
            Node::Lit(lit) => {
                assert_eq!(lit.value, "\u{000C}");
            }
            _ => panic!("Expected Lit node"),
        }
    }

    #[test]
    fn test_control_escape_vertical_tab() {
        let ast = parse_ok(r"\v");
        match ast {
            Node::Lit(lit) => {
                assert_eq!(lit.value, "\u{000B}");
            }
            _ => panic!("Expected Lit node"),
        }
    }

    // Error cases
    #[test]
    #[should_panic(expected = "Unmatched ')'")]
    fn test_stray_closing_paren() {
        parse_ok(")");
    }

    #[test]
    #[should_panic(expected = "Alternation lacks left-hand side")]
    fn test_stray_pipe() {
        parse_ok("|");
    }
}

// ============================================================================
// QUANTIFIER TESTS
// ============================================================================

#[cfg(test)]
mod quantifiers {
    use super::*;

    #[test]
    fn test_quantifier_star() {
        let ast = parse_ok("a*");
        match ast {
            Node::Quant(quant) => {
                assert_eq!(quant.min, 0);
                match quant.max {
                    MaxBound::Infinite(_) => {},
                    _ => panic!("Expected infinite max"),
                }
                assert_eq!(quant.mode, "Greedy");
            }
            _ => panic!("Expected Quant node"),
        }
    }

    #[test]
    fn test_quantifier_plus() {
        let ast = parse_ok("a+");
        match ast {
            Node::Quant(quant) => {
                assert_eq!(quant.min, 1);
                match quant.max {
                    MaxBound::Infinite(_) => {},
                    _ => panic!("Expected infinite max"),
                }
                assert_eq!(quant.mode, "Greedy");
            }
            _ => panic!("Expected Quant node"),
        }
    }

    #[test]
    fn test_quantifier_question() {
        let ast = parse_ok("a?");
        match ast {
            Node::Quant(quant) => {
                assert_eq!(quant.min, 0);
                match quant.max {
                    MaxBound::Finite(1) => {},
                    _ => panic!("Expected max = 1"),
                }
                assert_eq!(quant.mode, "Greedy");
            }
            _ => panic!("Expected Quant node"),
        }
    }

    #[test]
    fn test_quantifier_star_lazy() {
        let ast = parse_ok("a*?");
        match ast {
            Node::Quant(quant) => {
                assert_eq!(quant.min, 0);
                match quant.max {
                    MaxBound::Infinite(_) => {},
                    _ => panic!("Expected infinite max"),
                }
                assert_eq!(quant.mode, "Lazy");
            }
            _ => panic!("Expected Quant node"),
        }
    }

    #[test]
    fn test_quantifier_plus_possessive() {
        let ast = parse_ok("a++");
        match ast {
            Node::Quant(quant) => {
                assert_eq!(quant.min, 1);
                match quant.max {
                    MaxBound::Infinite(_) => {},
                    _ => panic!("Expected infinite max"),
                }
                assert_eq!(quant.mode, "Possessive");
            }
            _ => panic!("Expected Quant node"),
        }
    }

    #[test]
    fn test_quantifier_on_group() {
        let ast = parse_ok("(ab)+");
        match ast {
            Node::Quant(quant) => {
                match &*quant.child {
                    Node::Group(_) => {},
                    _ => panic!("Expected Group as child of Quant"),
                }
            }
            _ => panic!("Expected Quant node"),
        }
    }

    #[test]
    fn test_multiple_quantifiers_sequence() {
        let ast = parse_ok("a*b+c?");
        match ast {
            Node::Seq(seq) => {
                assert_eq!(seq.parts.len(), 3);
                for part in &seq.parts {
                    match part {
                        Node::Quant(_) => {},
                        _ => panic!("Expected all parts to be Quant nodes"),
                    }
                }
            }
            _ => panic!("Expected Seq node"),
        }
    }
}


// ============================================================================
// GROUP TESTS (Basic)
// ============================================================================

#[cfg(test)]
mod groups {
    use super::*;

    #[test]
    fn test_capturing_group() {
        let ast = parse_ok("(a)");
        match ast {
            Node::Group(group) => {
                assert!(group.capturing);
                assert_eq!(group.name, None);
                assert_eq!(group.atomic, Some(false));
            }
            _ => panic!("Expected Group node"),
        }
    }

    #[test]
    fn test_non_capturing_group() {
        let ast = parse_ok("(?:a)");
        match ast {
            Node::Group(group) => {
                assert!(!group.capturing);
                assert_eq!(group.name, None);
                assert_eq!(group.atomic, Some(false));
            }
            _ => panic!("Expected Group node"),
        }
    }

    #[test]
    fn test_named_capturing_group() {
        let ast = parse_ok("(?<name>a)");
        match ast {
            Node::Group(group) => {
                assert!(group.capturing);
                assert_eq!(group.name, Some("name".to_string()));
                assert_eq!(group.atomic, Some(false));
            }
            _ => panic!("Expected Group node"),
        }
    }

    #[test]
    fn test_atomic_group() {
        let ast = parse_ok("(?>a)");
        match ast {
            Node::Group(group) => {
                assert!(!group.capturing);
                assert_eq!(group.name, None);
                assert_eq!(group.atomic, Some(true));
            }
            _ => panic!("Expected Group node"),
        }
    }

    #[test]
    fn test_nested_groups() {
        let ast = parse_ok("((a))");
        match ast {
            Node::Group(outer) => {
                match &*outer.body {
                    Node::Group(_) => {
                        // Success - nested group found
                    }
                    _ => panic!("Expected nested Group in body"),
                }
            }
            _ => panic!("Expected Group node"),
        }
    }

    #[test]
    #[should_panic(expected = "Unterminated group")]
    fn test_unterminated_group() {
        parse_ok("(a");
    }
}

// ============================================================================
// LOOKAROUND TESTS
// ============================================================================

#[cfg(test)]
mod lookarounds {
    use super::*;

    #[test]
    fn test_positive_lookahead() {
        let ast = parse_ok("a(?=b)");
        match ast {
            Node::Seq(seq) => {
                assert_eq!(seq.parts.len(), 2);
                match &seq.parts[1] {
                    Node::Look(look) => {
                        assert_eq!(look.dir, "Ahead");
                        assert!(!look.neg);
                    }
                    _ => panic!("Expected Look node"),
                }
            }
            _ => panic!("Expected Seq node"),
        }
    }

    #[test]
    fn test_negative_lookahead() {
        let ast = parse_ok("a(?!b)");
        match ast {
            Node::Seq(seq) => {
                match &seq.parts[1] {
                    Node::Look(look) => {
                        assert_eq!(look.dir, "Ahead");
                        assert!(look.neg);
                    }
                    _ => panic!("Expected Look node"),
                }
            }
            _ => panic!("Expected Seq node"),
        }
    }

    #[test]
    fn test_positive_lookbehind() {
        let ast = parse_ok("(?<=a)b");
        match ast {
            Node::Seq(seq) => {
                match &seq.parts[0] {
                    Node::Look(look) => {
                        assert_eq!(look.dir, "Behind");
                        assert!(!look.neg);
                    }
                    _ => panic!("Expected Look node"),
                }
            }
            _ => panic!("Expected Seq node"),
        }
    }

    #[test]
    fn test_negative_lookbehind() {
        let ast = parse_ok("(?<!a)b");
        match ast {
            Node::Seq(seq) => {
                match &seq.parts[0] {
                    Node::Look(look) => {
                        assert_eq!(look.dir, "Behind");
                        assert!(look.neg);
                    }
                    _ => panic!("Expected Look node"),
                }
            }
            _ => panic!("Expected Seq node"),
        }
    }
}

// ============================================================================
// ALTERNATION TESTS
// ============================================================================

#[cfg(test)]
mod alternation {
    use super::*;

    #[test]
    fn test_simple_alternation() {
        let ast = parse_ok("a|b");
        match ast {
            Node::Alt(alt) => {
                assert_eq!(alt.branches.len(), 2);
            }
            _ => panic!("Expected Alt node"),
        }
    }

    #[test]
    fn test_multiple_alternation() {
        let ast = parse_ok("a|b|c|d");
        match ast {
            Node::Alt(alt) => {
                assert_eq!(alt.branches.len(), 4);
            }
            _ => panic!("Expected Alt node"),
        }
    }

    #[test]
    fn test_alternation_with_sequences() {
        let ast = parse_ok("ab|cd");
        match ast {
            Node::Alt(alt) => {
                assert_eq!(alt.branches.len(), 2);
                // Each branch should be a sequence
                for branch in &alt.branches {
                    match branch {
                        Node::Seq(_) => {},
                        _ => panic!("Expected Seq branches"),
                    }
                }
            }
            _ => panic!("Expected Alt node"),
        }
    }

    #[test]
    #[should_panic(expected = "Alternation lacks left-hand side")]
    fn test_alternation_no_lhs() {
        parse_ok("|a");
    }

    #[test]
    #[should_panic(expected = "Alternation lacks right-hand side")]
    fn test_alternation_no_rhs() {
        parse_ok("a|");
    }

    #[test]
    #[should_panic(expected = "Empty alternation branch")]
    fn test_empty_alternation_branch() {
        parse_ok("a||b");
    }
}

// ============================================================================
// FLAGS TESTS
// ============================================================================

#[cfg(test)]
mod flags {
    use super::*;

    #[test]
    fn test_ignore_case_flag() {
        let (flags, _) = parse("%flags i\na").unwrap();
        assert!(flags.ignore_case);
        assert!(!flags.multiline);
        assert!(!flags.dot_all);
    }

    #[test]
    fn test_multiline_flag() {
        let (flags, _) = parse("%flags m\na").unwrap();
        assert!(!flags.ignore_case);
        assert!(flags.multiline);
        assert!(!flags.dot_all);
    }

    #[test]
    fn test_multiple_flags() {
        let (flags, _) = parse("%flags i,m,s\na").unwrap();
        assert!(flags.ignore_case);
        assert!(flags.multiline);
        assert!(flags.dot_all);
    }

    #[test]
    fn test_flags_without_separators() {
        let (flags, _) = parse("%flags ims\na").unwrap();
        assert!(flags.ignore_case);
        assert!(flags.multiline);
        assert!(flags.dot_all);
    }
}

// ============================================================================
// DOT TESTS
// ============================================================================

#[cfg(test)]
mod dot {
    use super::*;

    #[test]
    fn test_dot() {
        let ast = parse_ok(".");
        match ast {
            Node::Dot(_) => {},
            _ => panic!("Expected Dot node"),
        }
    }

    #[test]
    fn test_dot_in_sequence() {
        let ast = parse_ok("a.b");
        match ast {
            Node::Seq(seq) => {
                assert_eq!(seq.parts.len(), 3);
                match &seq.parts[1] {
                    Node::Dot(_) => {},
                    _ => panic!("Expected Dot in middle"),
                }
            }
            _ => panic!("Expected Seq node"),
        }
    }

    #[test]
    fn test_multiple_dots() {
        let ast = parse_ok("...");
        match ast {
            Node::Seq(seq) => {
                assert_eq!(seq.parts.len(), 3);
                for part in &seq.parts {
                    match part {
                        Node::Dot(_) => {},
                        _ => panic!("Expected Dot nodes"),
                    }
                }
            }
            _ => panic!("Expected Seq node"),
        }
    }
}

// ============================================================================
// COMPILER TESTS
// ============================================================================

#[cfg(test)]
mod compiler {
    use super::*;
    use strling_core::core::compiler::Compiler;
    use strling_core::core::ir::*;

    #[test]
    fn test_compile_literal() {
        let node = Node::Lit(Lit {
            value: "a".to_string(),
        });
        let mut compiler = Compiler::new();
        let ir = compiler.compile(&node);
        
        match ir {
            IROp::Lit(lit) => {
                assert_eq!(lit.value, "a");
            }
            _ => panic!("Expected IRLit"),
        }
    }

    #[test]
    fn test_compile_sequence_coalescing() {
        // Sequence of literals should be coalesced
        let node = Node::Seq(Seq {
            parts: vec![
                Node::Lit(Lit { value: "a".to_string() }),
                Node::Lit(Lit { value: "b".to_string() }),
            ],
        });
        let mut compiler = Compiler::new();
        let ir = compiler.compile(&node);
        
        // Should be coalesced into single literal
        match ir {
            IROp::Lit(lit) => {
                assert_eq!(lit.value, "ab");
            }
            _ => panic!("Expected coalesced IRLit, got {:?}", ir),
        }
    }

    #[test]
    fn test_compile_alternation() {
        let node = Node::Alt(Alt {
            branches: vec![
                Node::Lit(Lit { value: "a".to_string() }),
                Node::Lit(Lit { value: "b".to_string() }),
            ],
        });
        let mut compiler = Compiler::new();
        let ir = compiler.compile(&node);
        
        match ir {
            IROp::Alt(alt) => {
                assert_eq!(alt.branches.len(), 2);
            }
            _ => panic!("Expected IRAlt"),
        }
    }

    #[test]
    fn test_compile_quantifier() {
        let node = Node::Quant(Quant {
            child: Box::new(Node::Lit(Lit { value: "a".to_string() })),
            min: 1,
            max: MaxBound::Infinite("Inf".to_string()),
            mode: "Greedy".to_string(),
        });
        let mut compiler = Compiler::new();
        let ir = compiler.compile(&node);
        
        match ir {
            IROp::Quant(quant) => {
                assert_eq!(quant.min, 1);
                match quant.max {
                    IRMaxBound::Infinite(_) => {},
                    _ => panic!("Expected infinite max"),
                }
            }
            _ => panic!("Expected IRQuant"),
        }
    }

    #[test]
    fn test_compile_with_metadata_named_group() {
        let node = Node::Group(Group {
            capturing: true,
            name: Some("test".to_string()),
            atomic: Some(false),
            body: Box::new(Node::Lit(Lit { value: "a".to_string() })),
        });
        let mut compiler = Compiler::new();
        let result = compiler.compile_with_metadata(&node);
        
        assert!(result.metadata.features_used.contains(&"named_group".to_string()));
    }

    #[test]
    fn test_compile_with_metadata_lookahead() {
        let node = Node::Look(Look {
            dir: "Ahead".to_string(),
            neg: false,
            body: Box::new(Node::Lit(Lit { value: "a".to_string() })),
        });
        let mut compiler = Compiler::new();
        let result = compiler.compile_with_metadata(&node);
        
        assert!(result.metadata.features_used.contains(&"lookahead".to_string()));
    }

    #[test]
    fn test_compile_with_metadata_lookbehind() {
        let node = Node::Look(Look {
            dir: "Behind".to_string(),
            neg: false,
            body: Box::new(Node::Lit(Lit { value: "a".to_string() })),
        });
        let mut compiler = Compiler::new();
        let result = compiler.compile_with_metadata(&node);
        
        assert!(result.metadata.features_used.contains(&"lookbehind".to_string()));
    }

    #[test]
    fn test_compile_with_metadata_atomic_group() {
        let node = Node::Group(Group {
            capturing: false,
            name: None,
            atomic: Some(true),
            body: Box::new(Node::Lit(Lit { value: "a".to_string() })),
        });
        let mut compiler = Compiler::new();
        let result = compiler.compile_with_metadata(&node);
        
        assert!(result.metadata.features_used.contains(&"atomic_group".to_string()));
    }

    #[test]
    fn test_compile_with_metadata_possessive_quantifier() {
        let node = Node::Quant(Quant {
            child: Box::new(Node::Lit(Lit { value: "a".to_string() })),
            min: 1,
            max: MaxBound::Infinite("Inf".to_string()),
            mode: "Possessive".to_string(),
        });
        let mut compiler = Compiler::new();
        let result = compiler.compile_with_metadata(&node);
        
        assert!(result.metadata.features_used.contains(&"possessive_quantifier".to_string()));
    }
}
