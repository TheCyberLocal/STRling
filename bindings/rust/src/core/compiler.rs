//! STRling Compiler - AST to IR Transformation
//!
//! This module implements the compiler that transforms Abstract Syntax Tree (AST)
//! nodes from the parser into an optimized Intermediate Representation (IR). The
//! compilation process includes:
//!   - Lowering AST nodes to IR operations
//!   - Flattening nested sequences and alternations
//!   - Coalescing adjacent literal nodes for efficiency
//!   - Ensuring quantifier children are properly grouped
//!   - Analyzing and tracking regex features used
//!
//! The IR is designed to be easily consumed by target emitters (e.g., PCRE2)
//! while maintaining semantic accuracy and enabling optimizations.

use crate::core::ir::*;
use crate::core::nodes::*;
use std::collections::HashSet;

/// Compiler for transforming AST nodes into optimized IR.
///
/// The Compiler class handles the complete transformation pipeline from parsed
/// AST to normalized IR, including feature detection for metadata generation.
pub struct Compiler {
    features_used: HashSet<String>,
}

impl Compiler {
    /// Create a new compiler instance
    pub fn new() -> Self {
        Self {
            features_used: HashSet::new(),
        }
    }

    /// Compile an AST node and return IR with metadata
    ///
    /// This is the main entry point for compilation with full metadata tracking.
    /// It performs lowering, normalization, and feature analysis.
    pub fn compile_with_metadata(&mut self, root_node: &Node) -> CompileResult {
        let ir_root = self.lower(root_node);
        let ir_root = self.normalize(ir_root);
        
        self.analyze_features(&ir_root);
        
        CompileResult {
            ir: ir_root,
            metadata: Metadata {
                features_used: self.features_used.iter().cloned().collect(),
            },
        }
    }

    /// Compile an AST node to IR without metadata
    pub fn compile(&mut self, root: &Node) -> IROp {
        let ir = self.lower(root);
        self.normalize(ir)
    }

    /// Lower AST node to IR
    fn lower(&self, node: &Node) -> IROp {
        match node {
            Node::Literal(lit) => IROp::Lit(IRLit {
                value: lit.value.clone(),
            }),
            Node::Dot(_) => IROp::Dot(IRDot {}),
            Node::Anchor(anchor) => {
                let at = if anchor.at == "NonWordBoundary" {
                    "NotWordBoundary".to_string()
                } else {
                    anchor.at.clone()
                };
                IROp::Anchor(IRAnchor { at })
            },
            Node::Sequence(seq) => {
                let parts: Vec<IROp> = seq.parts.iter().map(|p| self.lower(p)).collect();
                IROp::Seq(IRSeq { parts })
            }
            Node::Alternation(alt) => {
                let branches: Vec<IROp> = alt.branches.iter().map(|b| self.lower(b)).collect();
                IROp::Alt(IRAlt { branches })
            }
            Node::Quantifier(quant) => {
                let max = match &quant.max {
                    MaxBound::Finite(n) => IRMaxBound::Finite(*n),
                    MaxBound::Infinite(s) => IRMaxBound::Infinite(s.clone()),
                    MaxBound::Null(_) => IRMaxBound::Infinite("Inf".to_string()),
                };
                
                let mode = if quant.possessive {
                    "Possessive".to_string()
                } else if quant.lazy {
                    "Lazy".to_string()
                } else {
                    "Greedy".to_string()
                };

                IROp::Quant(IRQuant {
                    child: Box::new(self.lower(&quant.target.child)),
                    min: quant.min,
                    max,
                    mode,
                })
            }
            Node::Group(group) => IROp::Group(IRGroup {
                capturing: group.capturing,
                name: group.name.clone(),
                atomic: group.atomic.unwrap_or(false),
                body: Box::new(self.lower(&group.body)),
            }),
            Node::Lookahead(look) => IROp::Look(IRLook {
                dir: "Ahead".to_string(),
                neg: false,
                body: Box::new(self.lower(&look.body)),
            }),
            Node::NegativeLookahead(look) => IROp::Look(IRLook {
                dir: "Ahead".to_string(),
                neg: true,
                body: Box::new(self.lower(&look.body)),
            }),
            Node::Lookbehind(look) => IROp::Look(IRLook {
                dir: "Behind".to_string(),
                neg: false,
                body: Box::new(self.lower(&look.body)),
            }),
            Node::NegativeLookbehind(look) => IROp::Look(IRLook {
                dir: "Behind".to_string(),
                neg: true,
                body: Box::new(self.lower(&look.body)),
            }),
            Node::Backreference(backref) => IROp::Backref(IRBackref {
                by_index: backref.by_index,
                by_name: backref.by_name.clone(),
            }),
            Node::CharacterClass(cc) => IROp::CharClass(IRCharClass {
                negated: cc.negated,
                items: cc.items.iter().map(|item| self.lower_class_item(item)).collect(),
            }),
        }
    }

    /// Lower a class item from AST to IR
    fn lower_class_item(&self, item: &ClassItem) -> IRClassItem {
        match item {
            ClassItem::Char(lit) => IRClassItem::Char(IRClassLiteral {
                ch: lit.ch.clone(),
            }),
            ClassItem::Range(range) => IRClassItem::Range(IRClassRange {
                from_ch: range.from_ch.clone(),
                to_ch: range.to_ch.clone(),
            }),
            ClassItem::Esc(esc) => IRClassItem::Esc(IRClassEscape {
                escape_type: esc.escape_type.clone(),
                property: esc.property.clone(),
            }),
            ClassItem::UnicodeProperty(up) => {
                // Map UnicodeProperty entries into an IR class escape of type 'p'/'P'
                let etype = if up.negated { "P".to_string() } else { "p".to_string() };
                IRClassItem::Esc(IRClassEscape {
                    escape_type: etype,
                    property: Some(up.value.clone()),
                })
            }
        }
    }

    /// Normalize IR (flatten, coalesce, etc.)
    fn normalize(&self, node: IROp) -> IROp {
        match node {
            IROp::Seq(seq) => {
                // Flatten nested sequences
                let mut new_parts = Vec::new();
                for part in seq.parts {
                    let normalized = self.normalize(part);
                    if let IROp::Seq(inner_seq) = normalized {
                        new_parts.extend(inner_seq.parts);
                    } else {
                        new_parts.push(normalized);
                    }
                }
                
                // Coalesce adjacent literals
                let mut coalesced = Vec::new();
                let mut pending_lit = String::new();
                
                for part in new_parts {
                    if let IROp::Lit(lit) = &part {
                        pending_lit.push_str(&lit.value);
                    } else {
                        if !pending_lit.is_empty() {
                            coalesced.push(IROp::Lit(IRLit {
                                value: pending_lit.clone(),
                            }));
                            pending_lit.clear();
                        }
                        coalesced.push(part);
                    }
                }
                
                if !pending_lit.is_empty() {
                    coalesced.push(IROp::Lit(IRLit {
                        value: pending_lit,
                    }));
                }
                
                if coalesced.len() == 1 {
                    coalesced.into_iter().next().unwrap()
                } else {
                    IROp::Seq(IRSeq { parts: coalesced })
                }
            }
            IROp::Alt(mut alt) => {
                // Normalize branches
                alt.branches = alt.branches.into_iter().map(|b| self.normalize(b)).collect();
                IROp::Alt(alt)
            }
            IROp::Quant(mut quant) => {
                quant.child = Box::new(self.normalize(*quant.child));
                IROp::Quant(quant)
            }
            IROp::Group(mut group) => {
                group.body = Box::new(self.normalize(*group.body));
                // Normalize atomic from Option<bool> if needed
                IROp::Group(group)
            }
            IROp::Look(mut look) => {
                look.body = Box::new(self.normalize(*look.body));
                IROp::Look(look)
            }
            other => other,
        }
    }

    /// Analyze IR tree for features used
    fn analyze_features(&mut self, node: &IROp) {
        match node {
            IROp::Group(group) => {
                if group.atomic {
                    self.features_used.insert("atomic_group".to_string());
                }
                if group.name.is_some() {
                    self.features_used.insert("named_group".to_string());
                }
                self.analyze_features(&group.body);
            }
            IROp::Quant(quant) => {
                if quant.mode == "Possessive" {
                    self.features_used.insert("possessive_quantifier".to_string());
                }
                self.analyze_features(&quant.child);
            }
            IROp::Look(look) => {
                if look.dir == "Behind" {
                    self.features_used.insert("lookbehind".to_string());
                } else if look.dir == "Ahead" {
                    self.features_used.insert("lookahead".to_string());
                }
                self.analyze_features(&look.body);
            }
            IROp::Backref(_) => {
                self.features_used.insert("backreference".to_string());
            }
            IROp::CharClass(cc) => {
                for item in &cc.items {
                    if let IRClassItem::Esc(esc) = item {
                        if esc.escape_type == "p" || esc.escape_type == "P" {
                            self.features_used.insert("unicode_property".to_string());
                        }
                    }
                }
            }
            IROp::Seq(seq) => {
                for part in &seq.parts {
                    self.analyze_features(part);
                }
            }
            IROp::Alt(alt) => {
                for branch in &alt.branches {
                    self.analyze_features(branch);
                }
            }
            _ => {}
        }
    }
}

impl Default for Compiler {
    fn default() -> Self {
        Self::new()
    }
}

/// Result of compilation with metadata
#[derive(Debug, Clone)]
pub struct CompileResult {
    pub ir: IROp,
    pub metadata: Metadata,
}

/// Metadata about the compiled pattern
#[derive(Debug, Clone)]
pub struct Metadata {
    pub features_used: Vec<String>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_compile_literal() {
        let mut compiler = Compiler::new();
        let node = Node::Literal(Literal {
            value: "test".to_string(),
        });
        let ir = compiler.compile(&node);
        match ir {
            IROp::Lit(lit) => assert_eq!(lit.value, "test"),
            _ => panic!("Expected IRLit"),
        }
    }

    #[test]
    fn test_compile_sequence() {
        let mut compiler = Compiler::new();
        let node = Node::Sequence(Sequence {
            parts: vec![
                Node::Literal(Literal {
                    value: "a".to_string(),
                }),
                Node::Literal(Literal {
                    value: "b".to_string(),
                }),
            ],
        });
        let ir = compiler.compile(&node);
        // Should coalesce into a single literal
        match ir {
            IROp::Lit(lit) => assert_eq!(lit.value, "ab"),
            _ => panic!("Expected coalesced literal"),
        }
    }
}
