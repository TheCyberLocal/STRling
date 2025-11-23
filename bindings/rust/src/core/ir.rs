//! STRling Intermediate Representation (IR) Node Definitions
//!
//! This module defines the complete set of IR node classes that represent
//! language-agnostic regex constructs. The IR serves as an intermediate layer
//! between the parsed AST and the target-specific emitters (e.g., PCRE2).
//!
//! IR nodes are designed to be:
//!   - Simple and composable
//!   - Easy to serialize (via to_dict methods)
//!   - Independent of any specific regex flavor
//!   - Optimized for transformation and analysis
//!
//! Each IR node corresponds to a fundamental regex operation (alternation,
//! sequencing, character classes, quantification, etc.) and can be serialized
//! to a dictionary representation for further processing or debugging.

use serde::{Deserialize, Serialize};
use serde_json::Value;

/// Base trait for all IR operations.
///
/// All IR nodes extend this base trait and must implement the to_dict() method
/// for serialization to a dictionary representation.
pub trait IROpTrait {
    /// Serialize the IR node to a dictionary representation.
    ///
    /// # Returns
    ///
    /// The dictionary representation of this IR node.
    fn to_dict(&self) -> Value;
}

/// Enum representing all possible IR operation types.
///
/// This enum encompasses all IR node variants, allowing for type-safe
/// pattern matching and easy traversal of the IR tree.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "ir")]
pub enum IROp {
    Alt(IRAlt),
    Seq(IRSeq),
    Lit(IRLit),
    Dot(IRDot),
    Anchor(IRAnchor),
    CharClass(IRCharClass),
    Quant(IRQuant),
    Group(IRGroup),
    Backref(IRBackref),
    Look(IRLook),
}

impl IROpTrait for IROp {
    fn to_dict(&self) -> Value {
        match self {
            IROp::Alt(n) => n.to_dict(),
            IROp::Seq(n) => n.to_dict(),
            IROp::Lit(n) => n.to_dict(),
            IROp::Dot(n) => n.to_dict(),
            IROp::Anchor(n) => n.to_dict(),
            IROp::CharClass(n) => n.to_dict(),
            IROp::Quant(n) => n.to_dict(),
            IROp::Group(n) => n.to_dict(),
            IROp::Backref(n) => n.to_dict(),
            IROp::Look(n) => n.to_dict(),
        }
    }
}

/// Represents an alternation (OR) operation in the IR.
///
/// Matches any one of the provided branches. Equivalent to the | operator
/// in traditional regex syntax.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct IRAlt {
    pub branches: Vec<IROp>,
}

impl IROpTrait for IRAlt {
    fn to_dict(&self) -> Value {
        serde_json::json!({
            "ir": "Alt",
            "branches": self.branches.iter().map(|b| b.to_dict()).collect::<Vec<_>>()
        })
    }
}

/// Represents a sequence operation in the IR.
///
/// Matches patterns in sequence, one after another.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct IRSeq {
    pub parts: Vec<IROp>,
}

impl IROpTrait for IRSeq {
    fn to_dict(&self) -> Value {
        serde_json::json!({
            "ir": "Seq",
            "parts": self.parts.iter().map(|p| p.to_dict()).collect::<Vec<_>>()
        })
    }
}

/// Represents a literal string in the IR.
///
/// Matches the exact string value.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct IRLit {
    pub value: String,
}

impl IROpTrait for IRLit {
    fn to_dict(&self) -> Value {
        serde_json::json!({
            "ir": "Lit",
            "value": self.value
        })
    }
}

/// Represents the dot (any character) in the IR.
///
/// Matches any single character.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct IRDot;

impl IROpTrait for IRDot {
    fn to_dict(&self) -> Value {
        serde_json::json!({
            "ir": "Dot"
        })
    }
}

/// Represents an anchor in the IR.
///
/// Matches a specific position in the text (start, end, word boundary, etc.).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct IRAnchor {
    pub at: String,
}

impl IROpTrait for IRAnchor {
    fn to_dict(&self) -> Value {
        serde_json::json!({
            "ir": "Anchor",
            "at": self.at
        })
    }
}

/// Enum representing all possible character class item types in IR.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "ir")]
pub enum IRClassItem {
    Range(IRClassRange),
    Char(IRClassLiteral),
    Esc(IRClassEscape),
}

impl IRClassItem {
    pub fn to_dict(&self) -> Value {
        match self {
            IRClassItem::Range(r) => r.to_dict(),
            IRClassItem::Char(c) => c.to_dict(),
            IRClassItem::Esc(e) => e.to_dict(),
        }
    }
}

/// Represents a character range in a character class.
///
/// Matches characters within the specified range.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct IRClassRange {
    #[serde(rename = "from")]
    pub from_ch: String,
    #[serde(rename = "to")]
    pub to_ch: String,
}

impl IRClassRange {
    pub fn to_dict(&self) -> Value {
        serde_json::json!({
            "ir": "Range",
            "from": self.from_ch,
            "to": self.to_ch
        })
    }
}

/// Represents a literal character in a character class.
///
/// Matches the exact character.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct IRClassLiteral {
    #[serde(rename = "char")]
    pub ch: String,
}

impl IRClassLiteral {
    pub fn to_dict(&self) -> Value {
        serde_json::json!({
            "ir": "Char",
            "char": self.ch
        })
    }
}

/// Represents a character class escape in IR.
///
/// Matches shorthand character classes like \d, \w, \s, etc.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct IRClassEscape {
    #[serde(rename = "type")]
    pub escape_type: String,
    pub property: Option<String>,
}

impl IRClassEscape {
    pub fn to_dict(&self) -> Value {
        let mut obj = serde_json::json!({
            "ir": "Esc",
            "type": self.escape_type
        });
        if let Some(ref prop) = self.property {
            obj["property"] = Value::String(prop.clone());
        }
        obj
    }
}

/// Represents a character class in IR.
///
/// Matches any character from the specified set.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct IRCharClass {
    pub negated: bool,
    pub items: Vec<IRClassItem>,
}

impl IROpTrait for IRCharClass {
    fn to_dict(&self) -> Value {
        serde_json::json!({
            "ir": "CharClass",
            "negated": self.negated,
            "items": self.items.iter().map(|i| i.to_dict()).collect::<Vec<_>>()
        })
    }
}

/// Represents a quantifier in IR.
///
/// Specifies repetition of a pattern.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct IRQuant {
    pub child: Box<IROp>,
    pub min: i32,
    /// Maximum repetitions: either a number or "Inf" for unbounded
    pub max: IRMaxBound,
    /// Quantifier mode: Greedy|Lazy|Possessive
    pub mode: String,
}

/// Maximum bound for IR quantifiers.
///
/// Can be either a finite number or infinite.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum IRMaxBound {
    Finite(i32),
    Infinite(String), // "Inf"
}

impl IROpTrait for IRQuant {
    fn to_dict(&self) -> Value {
        let max_value = match &self.max {
            IRMaxBound::Finite(n) => Value::Number((*n).into()),
            IRMaxBound::Infinite(s) => Value::String(s.clone()),
        };

        serde_json::json!({
            "ir": "Quant",
            "child": self.child.to_dict(),
            "min": self.min,
            "max": max_value,
            "mode": self.mode
        })
    }
}

/// Represents a group in IR.
///
/// A capturing or non-capturing group.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct IRGroup {
    pub capturing: bool,
    pub body: Box<IROp>,
    pub name: Option<String>,
    #[serde(default)]
    pub atomic: bool,
}

impl IROpTrait for IRGroup {
    fn to_dict(&self) -> Value {
        let mut obj = serde_json::json!({
            "ir": "Group",
            "capturing": self.capturing,
            "body": self.body.to_dict()
        });

        if let Some(ref name) = self.name {
            obj["name"] = Value::String(name.clone());
        }
        if self.atomic {
            obj["atomic"] = Value::Bool(true);
        }

        obj
    }
}

/// Represents a backreference in IR.
///
/// References a previously captured group.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct IRBackref {
    #[serde(rename = "byIndex")]
    pub by_index: Option<i32>,
    #[serde(rename = "byName")]
    pub by_name: Option<String>,
}

impl IROpTrait for IRBackref {
    fn to_dict(&self) -> Value {
        let mut obj = serde_json::json!({
            "ir": "Backref"
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

/// Represents a lookahead/lookbehind assertion in IR.
///
/// Zero-width assertion.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct IRLook {
    pub dir: String,
    pub neg: bool,
    pub body: Box<IROp>,
}

impl IROpTrait for IRLook {
    fn to_dict(&self) -> Value {
        serde_json::json!({
            "ir": "Look",
            "dir": self.dir,
            "neg": self.neg,
            "body": self.body.to_dict()
        })
    }
}
