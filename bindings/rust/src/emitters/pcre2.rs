//! PCRE2 Emitter - Generate PCRE2-compatible regex patterns
//!
//! This module implements code generation for the PCRE2 regex engine.
//! It transforms the intermediate representation (IR) into PCRE2 syntax.

use crate::core::ir::*;
use crate::core::nodes::Flags;

/// PCRE2 emitter that generates PCRE2-compatible regex patterns from IR
pub struct PCRE2Emitter {
    flags: Flags,
}

impl PCRE2Emitter {
    /// Create a new PCRE2 emitter with the given flags
    pub fn new(flags: Flags) -> Self {
        Self { flags }
    }

    /// Emit PCRE2 pattern from IR
    ///
    /// # Arguments
    ///
    /// * `ir` - The IR node to emit
    ///
    /// # Returns
    ///
    /// A string containing the PCRE2 pattern
    pub fn emit(&self, ir: &IROp) -> String {
        self.emit_node(ir)
    }

    /// Emit a single IR node
    fn emit_node(&self, node: &IROp) -> String {
        match node {
            IROp::Lit(lit) => self.emit_literal(&lit.value),
            IROp::Dot(_) => ".".to_string(),
            IROp::Anchor(anchor) => match anchor.at.as_str() {
                "Start" => "^".to_string(),
                "End" => "$".to_string(),
                "WordBoundary" => "\\b".to_string(),
                "NotWordBoundary" => "\\B".to_string(),
                "AbsoluteStart" => "\\A".to_string(),
                "EndBeforeFinalNewline" => "\\Z".to_string(),
                "AbsoluteEnd" => "\\z".to_string(),
                _ => panic!("Unknown anchor type: {}", anchor.at),
            },
            IROp::Seq(seq) => {
                seq.parts.iter().map(|p| self.emit_node(p)).collect::<Vec<_>>().join("")
            }
            IROp::Alt(alt) => {
                alt.branches.iter().map(|b| self.emit_node(b)).collect::<Vec<_>>().join("|")
            }
            IROp::Quant(quant) => {
                let child = self.emit_node(&quant.child);
                let quantifier = match (quant.min, quant.max.as_ref()) {
                    (0, None) => "*".to_string(),
                    (1, None) => "+".to_string(),
                    (0, Some(1)) => "?".to_string(),
                    (min, None) => format!("{{{},}}", min),
                    (min, Some(max)) if min == *max => format!("{{{}}}", min),
                    (min, Some(max)) => format!("{{{},{}}}", min, max),
                };
                
                let mode_suffix = match quant.mode.as_str() {
                    "Lazy" => "?",
                    "Possessive" => "+",
                    _ => "",  // Greedy has no suffix
                };
                
                format!("{}{}{}", child, quantifier, mode_suffix)
            }
            IROp::Group(group) => {
                let body = self.emit_node(&group.body);
                if group.atomic {
                    format!("(?>{})", body)
                } else if let Some(name) = &group.name {
                    format!("(?<{}>{})", name, body)
                } else if !group.capturing {
                    format!("(?:{})", body)
                } else {
                    format!("({})", body)
                }
            }
            IROp::Look(look) => {
                let body = self.emit_node(&look.body);
                match (look.dir.as_str(), look.positive) {
                    ("Ahead", true) => format!("(?={})", body),
                    ("Ahead", false) => format!("(?!{})", body),
                    ("Behind", true) => format!("(?<={})", body),
                    ("Behind", false) => format!("(?<!{})", body),
                    _ => panic!("Unknown lookaround type"),
                }
            }
            IROp::Backref(backref) => {
                if let Some(name) = &backref.name {
                    format!("\\k<{}>", name)
                } else if let Some(num) = backref.num {
                    format!("\\{}", num)
                } else {
                    panic!("Backref must have either name or num")
                }
            }
            IROp::CharClass(cc) => {
                let mut result = String::from("[");
                if cc.negated {
                    result.push('^');
                }
                for item in &cc.items {
                    result.push_str(&self.emit_class_item(item));
                }
                result.push(']');
                result
            }
        }
    }

    /// Emit a character class item
    fn emit_class_item(&self, item: &IRClassItem) -> String {
        match item {
            IRClassItem::Literal(lit) => self.escape_class_char(&lit.value),
            IRClassItem::Range(range) => {
                format!("{}-{}", 
                    self.escape_class_char(&range.from),
                    self.escape_class_char(&range.to))
            }
            IRClassItem::Escape(esc) => {
                match esc.escape_type.as_str() {
                    "Digit" => "\\d".to_string(),
                    "NotDigit" => "\\D".to_string(),
                    "Word" => "\\w".to_string(),
                    "NotWord" => "\\W".to_string(),
                    "Space" => "\\s".to_string(),
                    "NotSpace" => "\\S".to_string(),
                    _ => esc.value.clone(),
                }
            }
        }
    }

    /// Escape a literal string for PCRE2
    fn emit_literal(&self, s: &str) -> String {
        let mut result = String::new();
        for ch in s.chars() {
            result.push_str(&self.escape_char(ch));
        }
        result
    }

    /// Escape a single character for PCRE2 pattern context
    fn escape_char(&self, ch: char) -> String {
        match ch {
            '.' | '*' | '+' | '?' | '^' | '$' | '|' | '(' | ')' | '[' | ']' | '{' | '}' | '\\' => {
                format!("\\{}", ch)
            }
            '\n' => "\\n".to_string(),
            '\r' => "\\r".to_string(),
            '\t' => "\\t".to_string(),
            '\u{000C}' => "\\f".to_string(),
            '\u{000B}' => "\\v".to_string(),
            _ => ch.to_string(),
        }
    }

    /// Escape a character for use inside a character class
    fn escape_class_char(&self, s: &str) -> String {
        let mut result = String::new();
        for ch in s.chars() {
            match ch {
                ']' | '\\' | '^' | '-' => result.push_str(&format!("\\{}", ch)),
                '\n' => result.push_str("\\n"),
                '\r' => result.push_str("\\r"),
                '\t' => result.push_str("\\t"),
                _ => result.push(ch),
            }
        }
        result
    }

    /// Get the flags string for the pattern
    pub fn get_flags_string(&self) -> String {
        let mut flags = String::new();
        if self.flags.ignore_case {
            flags.push('i');
        }
        if self.flags.multiline {
            flags.push('m');
        }
        if self.flags.dot_all {
            flags.push('s');
        }
        if self.flags.unicode {
            flags.push('u');
        }
        if self.flags.extended {
            flags.push('x');
        }
        flags
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_emit_literal() {
        let emitter = PCRE2Emitter::new(Flags::default());
        let ir = IROp::Lit(IRLit {
            value: "test".to_string(),
        });
        assert_eq!(emitter.emit(&ir), "test");
    }

    #[test]
    fn test_emit_dot() {
        let emitter = PCRE2Emitter::new(Flags::default());
        let ir = IROp::Dot(IRDot {});
        assert_eq!(emitter.emit(&ir), ".");
    }

    #[test]
    fn test_emit_anchor() {
        let emitter = PCRE2Emitter::new(Flags::default());
        let ir = IROp::Anchor(IRAnchor {
            at: "Start".to_string(),
        });
        assert_eq!(emitter.emit(&ir), "^");
    }

    #[test]
    fn test_emit_quantifier() {
        let emitter = PCRE2Emitter::new(Flags::default());
        let ir = IROp::Quant(IRQuant {
            child: Box::new(IROp::Lit(IRLit {
                value: "a".to_string(),
            })),
            min: 0,
            max: None,
            mode: "Greedy".to_string(),
        });
        assert_eq!(emitter.emit(&ir), "a*");
    }

    #[test]
    fn test_emit_group() {
        let emitter = PCRE2Emitter::new(Flags::default());
        let ir = IROp::Group(IRGroup {
            capturing: true,
            name: None,
            atomic: false,
            body: Box::new(IROp::Lit(IRLit {
                value: "test".to_string(),
            })),
        });
        assert_eq!(emitter.emit(&ir), "(test)");
    }

    #[test]
    fn test_emit_alternation() {
        let emitter = PCRE2Emitter::new(Flags::default());
        let ir = IROp::Alt(IRAlt {
            branches: vec![
                IROp::Lit(IRLit {
                    value: "a".to_string(),
                }),
                IROp::Lit(IRLit {
                    value: "b".to_string(),
                }),
            ],
        });
        assert_eq!(emitter.emit(&ir), "a|b");
    }
}
