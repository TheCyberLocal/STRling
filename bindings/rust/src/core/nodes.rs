//! STRling AST Node Definitions
//!
//! This module defines the complete set of Abstract Syntax Tree (AST) node classes
//! that represent the parsed structure of STRling patterns. The AST is the direct
//! output of the parser and represents the syntactic structure of the pattern before
//! optimization and lowering to IR.
//!
//! AST nodes are designed to:
//!   - Closely mirror the source pattern syntax
//!   - Be easily serializable to the Base TargetArtifact schema
//!   - Provide a clean separation between parsing and compilation
//!   - Support multiple target regex flavors through the compilation pipeline
//!
//! Each AST node type corresponds to a syntactic construct in the STRling DSL
//! (alternation, sequencing, character classes, anchors, etc.) and can be
//! serialized to a dictionary representation for debugging or storage.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;

// ---- Flags container ----

/// Container for regex flags/modifiers.
///
/// Flags control the behavior of pattern matching (case sensitivity, multiline
/// mode, etc.). This class encapsulates all standard regex flags.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
pub struct Flags {
    #[serde(rename = "ignoreCase")]
    pub ignore_case: bool,
    pub multiline: bool,
    #[serde(rename = "dotAll")]
    pub dot_all: bool,
    pub unicode: bool,
    pub extended: bool,
}

impl Flags {
    pub fn to_dict(&self) -> HashMap<String, bool> {
        let mut map = HashMap::new();
        map.insert("ignoreCase".to_string(), self.ignore_case);
        map.insert("multiline".to_string(), self.multiline);
        map.insert("dotAll".to_string(), self.dot_all);
        map.insert("unicode".to_string(), self.unicode);
        map.insert("extended".to_string(), self.extended);
        map
    }

    pub fn from_letters(letters: &str) -> Self {
        let mut f = Flags::default();
        for ch in letters.replace(",", "").replace(" ", "").chars() {
            match ch {
                'i' => f.ignore_case = true,
                'm' => f.multiline = true,
                's' => f.dot_all = true,
                'u' => f.unicode = true,
                'x' => f.extended = true,
                _ => {
                    // Unknown flags are ignored at parser stage; may be warned later
                }
            }
        }
        f
    }
}

// ---- Base node trait ----

/// Base trait for all AST nodes.
///
/// All AST nodes must implement this trait to provide serialization
/// to a dictionary/JSON representation.
pub trait NodeTrait {
    fn to_dict(&self) -> Value;
}

// ---- Concrete nodes matching Base Schema ----

/// Enum representing all possible AST node types.
///
/// This enum encompasses all AST node variants, allowing for type-safe
/// pattern matching and easy traversal of the AST.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind")]
pub enum Node {
    Alt(Alt),
    Seq(Seq),
    Lit(Lit),
    Dot(Dot),
    Anchor(Anchor),
    CharClass(CharClass),
    Quant(Quant),
    Group(Group),
    Backref(Backref),
    Look(Look),
}

impl NodeTrait for Node {
    fn to_dict(&self) -> Value {
        match self {
            Node::Alt(n) => n.to_dict(),
            Node::Seq(n) => n.to_dict(),
            Node::Lit(n) => n.to_dict(),
            Node::Dot(n) => n.to_dict(),
            Node::Anchor(n) => n.to_dict(),
            Node::CharClass(n) => n.to_dict(),
            Node::Quant(n) => n.to_dict(),
            Node::Group(n) => n.to_dict(),
            Node::Backref(n) => n.to_dict(),
            Node::Look(n) => n.to_dict(),
        }
    }
}

/// Alternation node (OR operation).
///
/// Represents a choice between multiple branches.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Alt {
    pub branches: Vec<Node>,
}

impl NodeTrait for Alt {
    fn to_dict(&self) -> Value {
        serde_json::json!({
            "kind": "Alt",
            "branches": self.branches.iter().map(|b| b.to_dict()).collect::<Vec<_>>()
        })
    }
}

/// Sequence node.
///
/// Represents a sequence of patterns to be matched in order.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Seq {
    pub parts: Vec<Node>,
}

impl NodeTrait for Seq {
    fn to_dict(&self) -> Value {
        serde_json::json!({
            "kind": "Seq",
            "parts": self.parts.iter().map(|p| p.to_dict()).collect::<Vec<_>>()
        })
    }
}

/// Literal string node.
///
/// Represents a literal string to match.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Lit {
    pub value: String,
}

impl NodeTrait for Lit {
    fn to_dict(&self) -> Value {
        serde_json::json!({
            "kind": "Lit",
            "value": self.value
        })
    }
}

/// Dot (any character) node.
///
/// Represents the `.` metacharacter that matches any character.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Dot;

impl NodeTrait for Dot {
    fn to_dict(&self) -> Value {
        serde_json::json!({
            "kind": "Dot"
        })
    }
}

/// Anchor node.
///
/// Represents position anchors in the pattern.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Anchor {
    /// Anchor type: "Start"|"End"|"WordBoundary"|"NotWordBoundary"|Absolute* variants
    pub at: String,
}

impl NodeTrait for Anchor {
    fn to_dict(&self) -> Value {
        serde_json::json!({
            "kind": "Anchor",
            "at": self.at
        })
    }
}

// --- CharClass ---

/// Enum representing all possible character class item types.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind")]
pub enum ClassItem {
    Range(ClassRange),
    Char(ClassLiteral),
    Esc(ClassEscape),
}

impl ClassItem {
    pub fn to_dict(&self) -> Value {
        match self {
            ClassItem::Range(r) => r.to_dict(),
            ClassItem::Char(c) => c.to_dict(),
            ClassItem::Esc(e) => e.to_dict(),
        }
    }
}

/// Character range in a character class.
///
/// Represents a range like `a-z` or `0-9`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ClassRange {
    pub from_ch: String,
    pub to_ch: String,
}

impl ClassRange {
    pub fn to_dict(&self) -> Value {
        serde_json::json!({
            "kind": "Range",
            "from": self.from_ch,
            "to": self.to_ch
        })
    }
}

/// Literal character in a character class.
///
/// Represents a single character literal.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ClassLiteral {
    pub ch: String,
}

impl ClassLiteral {
    pub fn to_dict(&self) -> Value {
        serde_json::json!({
            "kind": "Char",
            "char": self.ch
        })
    }
}

/// Character class escape sequence.
///
/// Represents shorthand character classes like `\d`, `\w`, `\s`, etc.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ClassEscape {
    /// Escape type: d, D, w, W, s, S, p, P
    #[serde(rename = "type")]
    pub escape_type: String,
    /// Unicode property name (for \p and \P)
    pub property: Option<String>,
}

impl ClassEscape {
    pub fn to_dict(&self) -> Value {
        let mut obj = serde_json::json!({
            "kind": "Esc",
            "type": self.escape_type
        });
        if let Some(ref prop) = self.property {
            if self.escape_type == "p" || self.escape_type == "P" {
                obj["property"] = Value::String(prop.clone());
            }
        }
        obj
    }
}

/// Character class node.
///
/// Represents a character class like `[abc]` or `[^0-9]`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CharClass {
    pub negated: bool,
    pub items: Vec<ClassItem>,
}

impl NodeTrait for CharClass {
    fn to_dict(&self) -> Value {
        serde_json::json!({
            "kind": "CharClass",
            "negated": self.negated,
            "items": self.items.iter().map(|i| i.to_dict()).collect::<Vec<_>>()
        })
    }
}

/// Quantifier node.
///
/// Represents repetition of a pattern with specified min/max bounds.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Quant {
    pub child: Box<Node>,
    pub min: i32,
    /// Maximum repetitions: either a number or "Inf" for unbounded
    pub max: MaxBound,
    /// Quantifier mode: "Greedy" | "Lazy" | "Possessive"
    pub mode: String,
}

/// Maximum bound for quantifiers.
///
/// Can be either a finite number or infinite.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum MaxBound {
    Finite(i32),
    Infinite(String), // "Inf"
}

impl NodeTrait for Quant {
    fn to_dict(&self) -> Value {
        let max_value = match &self.max {
            MaxBound::Finite(n) => Value::Number((*n).into()),
            MaxBound::Infinite(s) => Value::String(s.clone()),
        };

        serde_json::json!({
            "kind": "Quant",
            "child": self.child.to_dict(),
            "min": self.min,
            "max": max_value,
            "mode": self.mode
        })
    }
}

/// Group node.
///
/// Represents a capturing or non-capturing group.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Group {
    pub capturing: bool,
    pub body: Box<Node>,
    pub name: Option<String>,
    /// Extension: atomic group flag
    pub atomic: Option<bool>,
}

impl NodeTrait for Group {
    fn to_dict(&self) -> Value {
        let mut obj = serde_json::json!({
            "kind": "Group",
            "capturing": self.capturing,
            "body": self.body.to_dict()
        });

        if let Some(ref name) = self.name {
            obj["name"] = Value::String(name.clone());
        }
        if let Some(atomic) = self.atomic {
            obj["atomic"] = Value::Bool(atomic);
        }

        obj
    }
}

/// Backreference node.
///
/// Represents a reference to a previously captured group.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Backref {
    #[serde(rename = "byIndex")]
    pub by_index: Option<i32>,
    #[serde(rename = "byName")]
    pub by_name: Option<String>,
}

impl NodeTrait for Backref {
    fn to_dict(&self) -> Value {
        let mut obj = serde_json::json!({
            "kind": "Backref"
        });

        if let Some(idx) = self.by_index {
            obj["byIndex"] = Value::Number(idx.into());
        }
        if let Some(ref name) = self.by_name {
            obj["byName"] = Value::String(name.clone());
        }

        obj
    }
}

/// Lookahead/Lookbehind assertion node.
///
/// Represents zero-width assertions.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Look {
    /// Direction: "Ahead" | "Behind"
    pub dir: String,
    /// Negation flag
    pub neg: bool,
    pub body: Box<Node>,
}

impl NodeTrait for Look {
    fn to_dict(&self) -> Value {
        serde_json::json!({
            "kind": "Look",
            "dir": self.dir,
            "neg": self.neg,
            "body": self.body.to_dict()
        })
    }
}
