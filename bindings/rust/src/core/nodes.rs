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

// NodeTrait removed in favor of Serde serialization

// ---- Concrete nodes matching Base Schema ----

/// Enum representing all possible AST node types.
///
/// This enum encompasses all AST node variants, allowing for type-safe
/// pattern matching and easy traversal of the AST.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum Node {
    Alternation(Alternation),
    Sequence(Sequence),
    Literal(Literal),
    Dot(Dot),
    Anchor(Anchor),
    CharacterClass(CharacterClass),
    Quantifier(Quantifier),
    Group(Group),
    Backreference(Backreference),
    Lookahead(LookaroundBody),
    NegativeLookahead(LookaroundBody),
    Lookbehind(LookaroundBody),
    NegativeLookbehind(LookaroundBody),
}

/// Alternation node (OR operation).
///
/// Represents a choice between multiple branches.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Alternation {
    #[serde(alias = "alternatives")]
    pub branches: Vec<Node>,
}

/// Sequence node.
///
/// Represents a sequence of patterns to be matched in order.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Sequence {
    pub parts: Vec<Node>,
}

/// Literal string node.
///
/// Represents a literal string to match.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Literal {
    pub value: String,
}

/// Dot (any character) node.
///
/// Represents the `.` metacharacter that matches any character.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Dot;

/// Anchor node.
///
/// Represents position anchors in the pattern.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Anchor {
    /// Anchor type: "Start"|"End"|"WordBoundary"|"NotWordBoundary"|Absolute* variants
    pub at: String,
}

// --- CharClass ---

/// Enum representing all possible character class item types.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum ClassItem {
    Range(ClassRange),
    #[serde(alias = "Literal")]
    Char(ClassLiteral),
    #[serde(alias = "Escape")]
    Esc(ClassEscape),
    /// Unicode property reference inside a class, e.g. \p{L}
    UnicodeProperty(ClassUnicodeProperty),
}

/// Character range in a character class.
///
/// Represents a range like `a-z` or `0-9`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ClassRange {
    #[serde(rename = "from")]
    pub from_ch: String,
    #[serde(rename = "to")]
    pub to_ch: String,
}

/// Literal character in a character class.
///
/// Represents a single character literal.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ClassLiteral {
    #[serde(rename = "char", alias = "value")]
    pub ch: String,
}

/// Character class escape sequence.
///
/// Represents shorthand character classes like `\d`, `\w`, `\s`, etc.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct ClassEscape {
    /// Escape type: d, D, w, W, s, S, p, P
    /// Accept both the historical `type` field and the newer `kind` field
    /// coming from the JSON specs.
    #[serde(rename = "kind", alias = "type")]
    pub escape_type: String,
    /// Unicode property name (for \p and \P)
    pub property: Option<String>,
}

// Custom deserializer: accepts `kind` or `type` and normalizes long names
// like "digit" -> "d", "not-digit" -> "D" etc., while accepting
// already-short values like "d", "D", "p".
impl<'de> Deserialize<'de> for ClassEscape {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        #[derive(Deserialize)]
        struct Raw {
            #[serde(rename = "kind", alias = "type")]
            kind: String,
            property: Option<String>,
        }

        let raw = Raw::deserialize(deserializer)?;

        fn normalize_kind(k: &str) -> String {
            match k {
                "digit" => "d".to_string(),
                "not-digit" => "D".to_string(),
                "word" => "w".to_string(),
                "not-word" => "W".to_string(),
                "space" => "s".to_string(),
                "not-space" => "S".to_string(),
                other => other.to_string(),
            }
        }

        Ok(ClassEscape {
            escape_type: normalize_kind(&raw.kind),
            property: raw.property,
        })
    }
}

/// Character class node.
///
/// Represents a character class like `[abc]` or `[^0-9]`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CharacterClass {
    pub negated: bool,
    #[serde(alias = "members")]
    pub items: Vec<ClassItem>,
}

/// Unicode property entry inside a character class. Matches the JSON shape
/// used by the test specs (name, value, negated).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ClassUnicodeProperty {
    pub name: Option<String>,
    pub value: String,
    pub negated: bool,
}

/// Quantifier node.
///
/// Represents repetition of a pattern with specified min/max bounds.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Quantifier {
    #[serde(flatten)]
    pub target: QuantifierTarget,
    pub min: i32,
    /// Maximum repetitions: either a number or "Inf" for unbounded
    pub max: MaxBound,
    /// Quantifier mode: "Greedy" | "Lazy" | "Possessive"
    #[serde(default = "default_greedy_mode")]
    pub mode: String,
    // Helper fields to match JSON spec which might use boolean flags
    #[serde(default)]
    pub greedy: bool,
    #[serde(default)]
    pub lazy: bool,
    #[serde(default)]
    pub possessive: bool,
}

fn default_greedy_mode() -> String {
    "Greedy".to_string()
}

// Helper struct to handle "child" vs "target" naming if needed, 
// but JSON spec uses "target" for Quantifier?
// Let's check the JSON spec for Quantifier.
// "type": "Quantifier", "target": { ... }, "min": 1, "max": null, "greedy": true ...
// The existing code had `child`. I should rename it to `target` or use alias.
// But wait, `target` in JSON is the node being quantified.
// I'll use a wrapper or just rename `child` to `target`.

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct QuantifierTarget {
    #[serde(rename = "target")]
    pub child: Box<Node>,
}

/// Maximum bound for quantifiers.
///
/// Can be either a finite number or infinite.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum MaxBound {
    Finite(i32),
    Infinite(String), // "Inf"
    Null(Option<()>), // Handle null in JSON
}

/// Group node.
///
/// Represents a capturing or non-capturing group.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Group {
    pub capturing: bool,
    #[serde(alias = "expression")]
    pub body: Box<Node>,
    pub name: Option<String>,
    /// Extension: atomic group flag
    pub atomic: Option<bool>,
}

/// Backreference node.
///
/// Represents a reference to a previously captured group.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Backreference {
    #[serde(rename = "byIndex", alias = "index")]
    pub by_index: Option<i32>,
    #[serde(rename = "byName", alias = "name")]
    pub by_name: Option<String>,
}

/// Lookaround body.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LookaroundBody {
    pub body: Box<Node>,
}
