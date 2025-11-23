//! STRling Parser - Recursive Descent Parser for STRling DSL
//!
//! This module implements a hand-rolled recursive-descent parser that transforms
//! STRling pattern syntax into Abstract Syntax Tree (AST) nodes. The parser handles:
//!   - Alternation and sequencing
//!   - Character classes and ranges
//!   - Quantifiers (greedy, lazy, possessive)
//!   - Groups (capturing, non-capturing, named, atomic)
//!   - Lookarounds (lookahead and lookbehind, positive and negative)
//!   - Anchors and special escapes
//!   - Extended/free-spacing mode with comments
//!
//! The parser produces AST nodes (defined in nodes.rs) that can be compiled
//! to IR and ultimately emitted as target-specific regex patterns. It includes
//! comprehensive error handling with position tracking for helpful diagnostics.

use crate::core::errors::STRlingParseError;
use crate::core::nodes::*;
use std::collections::{HashMap, HashSet};

/// Alias for backward compatibility
pub type ParseError = STRlingParseError;

/// Cursor for tracking position in the input text
#[derive(Debug, Clone)]
struct Cursor {
    text: String,
    i: usize,
    extended_mode: bool,
    in_class: usize,  // nesting count for char classes
}

impl Cursor {
    fn new(text: String, i: usize, extended_mode: bool, in_class: usize) -> Self {
        Self {
            text,
            i,
            extended_mode,
            in_class,
        }
    }

    fn eof(&self) -> bool {
        self.i >= self.text.len()
    }

    fn peek(&self, n: usize) -> String {
        let j = self.i + n;
        if j >= self.text.len() {
            String::new()
        } else {
            self.text.chars().nth(j).map(|c| c.to_string()).unwrap_or_default()
        }
    }

    fn peek_char(&self, n: usize) -> Option<char> {
        let j = self.i + n;
        self.text.chars().nth(j)
    }

    fn take(&mut self) -> Option<char> {
        if self.eof() {
            None
        } else {
            let ch = self.text.chars().nth(self.i);
            self.i += 1;
            ch
        }
    }

    fn match_str(&mut self, s: &str) -> bool {
        if self.text[self.i..].starts_with(s) {
            self.i += s.len();
            true
        } else {
            false
        }
    }

    fn skip_ws_and_comments(&mut self) {
        if !self.extended_mode || self.in_class > 0 {
            return;
        }
        // In free-spacing mode, ignore spaces/tabs/newlines and #-to-EOL comments
        while !self.eof() {
            if let Some(ch) = self.peek_char(0) {
                if " \t\r\n".contains(ch) {
                    self.i += 1;
                    continue;
                }
                if ch == '#' {
                    // skip comment to end of line
                    while !self.eof() && !"\r\n".contains(self.peek_char(0).unwrap_or('\0')) {
                        self.i += 1;
                    }
                    continue;
                }
            }
            break;
        }
    }
}

/// Parser for STRling DSL
pub struct Parser {
    original_text: String,
    flags: Flags,
    src: String,
    cur: Cursor,
    cap_count: usize,
    cap_names: HashSet<String>,
    control_escapes: HashMap<char, char>,
}

impl Parser {
    /// Create a new parser for the given input text
    pub fn new(text: String) -> Self {
        let mut parser = Parser {
            original_text: text.clone(),
            flags: Flags::default(),
            src: String::new(),
            cur: Cursor::new(String::new(), 0, false, 0),
            cap_count: 0,
            cap_names: HashSet::new(),
            control_escapes: HashMap::new(),
        };
        
        // Initialize control escapes
        parser.control_escapes.insert('n', '\n');
        parser.control_escapes.insert('r', '\r');
        parser.control_escapes.insert('t', '\t');
        parser.control_escapes.insert('f', '\u{000C}');
        parser.control_escapes.insert('v', '\u{000B}');
        
        // Parse directives
        let (flags, src) = parser.parse_directives(&text);
        parser.flags = flags.clone();
        parser.src = src.clone();
        parser.cur = Cursor::new(src, 0, flags.extended, 0);
        
        parser
    }

    fn raise_error(&self, message: String, pos: usize) -> STRlingParseError {
        // TODO: Integrate hint engine
        let hint = None;  // get_hint(message, self.src, pos)
        STRlingParseError::new(message, pos, self.src.clone(), hint)
    }

    /// Parse directives from the input text
    fn parse_directives(&self, text: &str) -> (Flags, String) {
        let mut flags = Flags::default();
        let lines: Vec<&str> = text.lines().collect();
        let mut pattern_lines: Vec<&str> = Vec::new();
        let mut in_pattern = false;
        
        for line in lines {
            let stripped = line.trim();
            
            // Skip leading blank lines or comments
            if !in_pattern && (stripped.is_empty() || stripped.starts_with('#')) {
                continue;
            }
            
            // Process %flags directive
            if !in_pattern && stripped.starts_with("%flags") {
                if let Some(idx) = line.find("%flags") {
                    let after = &line[idx + "%flags".len()..];
                    
                    // Extract flags portion
                    let allowed: HashSet<char> = " ,\t[]imsuxIMSUX".chars().collect();
                    let mut j = 0;
                    while j < after.len() && allowed.contains(&after.chars().nth(j).unwrap()) {
                        j += 1;
                    }
                    
                    let flags_token = &after[..j];
                    let remainder = &after[j..];
                    
                    // Parse flags
                    let letters: String = flags_token
                        .chars()
                        .filter(|c| "imsux".contains(*c) || "IMSUX".contains(*c))
                        .map(|c| c.to_ascii_lowercase())
                        .collect();
                    
                    flags = Flags::from_letters(&letters);
                    
                    if !remainder.trim().is_empty() {
                        in_pattern = true;
                        pattern_lines.push(remainder);
                    }
                }
                continue;
            }
            
            // Skip other directives
            if !in_pattern && stripped.starts_with('%') {
                continue;
            }
            
            // This is pattern content
            in_pattern = true;
            pattern_lines.push(line);
        }
        
        let pattern = pattern_lines.join("\n");
        (flags, pattern)
    }

    /// Parse the entire pattern
    pub fn parse(&mut self) -> Result<Node, STRlingParseError> {
        let node = self.parse_alt()?;
        self.cur.skip_ws_and_comments();
        
        if !self.cur.eof() {
            if let Some(ch) = self.cur.peek_char(0) {
                if ch == ')' {
                    return Err(STRlingParseError::new(
                        "Unmatched ')'".to_string(),
                        self.cur.i,
                        self.src.clone(),
                        Some("This ')' character does not have a matching opening '('. Did you mean to escape it with '\\)'?".to_string()),
                    ));
                }
                if ch == '|' {
                    return Err(self.raise_error(
                        "Alternation lacks right-hand side".to_string(),
                        self.cur.i,
                    ));
                }
            }
            return Err(self.raise_error(
                "Unexpected trailing input".to_string(),
                self.cur.i,
            ));
        }
        
        Ok(node)
    }

    /// Parse alternation: seq ('|' seq)* | seq
    fn parse_alt(&mut self) -> Result<Node, STRlingParseError> {
        self.cur.skip_ws_and_comments();
        
        // Check if the pattern starts with a pipe (no left-hand side)
        if let Some('|') = self.cur.peek_char(0) {
            return Err(self.raise_error(
                "Alternation lacks left-hand side".to_string(),
                self.cur.i,
            ));
        }
        
        let mut branches = vec![self.parse_seq()?];
        self.cur.skip_ws_and_comments();
        
        while let Some('|') = self.cur.peek_char(0) {
            let pipe_pos = self.cur.i;
            self.cur.take();
            self.cur.skip_ws_and_comments();
            
            // Check if the pipe is followed by end-of-input
            if self.cur.eof() {
                return Err(self.raise_error(
                    "Alternation lacks right-hand side".to_string(),
                    pipe_pos,
                ));
            }
            
            // Check if the pipe is followed by another pipe (empty branch)
            if let Some('|') = self.cur.peek_char(0) {
                return Err(self.raise_error(
                    "Empty alternation branch".to_string(),
                    pipe_pos,
                ));
            }
            
            branches.push(self.parse_seq()?);
            self.cur.skip_ws_and_comments();
        }
        
        if branches.len() == 1 {
            Ok(branches.into_iter().next().unwrap())
        } else {
            Ok(Node::Alternation(Alternation { branches }))
        }
    }

    /// Parse sequence: term*
    fn parse_seq(&mut self) -> Result<Node, STRlingParseError> {
        let mut parts = Vec::new();
        
        loop {
            self.cur.skip_ws_and_comments();
            
            if self.cur.eof() {
                break;
            }
            
            // Check for sequence terminators
            if let Some(ch) = self.cur.peek_char(0) {
                if ch == '|' || ch == ')' {
                    break;
                }
            }
            
            // Parse one term (atom potentially followed by quantifier)
            let atom = self.parse_atom()?;
            
            // Check for quantifier after the atom
            self.cur.skip_ws_and_comments();
            if let Some(quant) = self.try_parse_quantifier()? {
                // Wrap the atom in a quantifier
                let mode = quant.2;
                parts.push(Node::Quantifier(Quantifier {
                    target: QuantifierTarget { child: Box::new(atom) },
                    min: quant.0,
                    max: quant.1,
                    mode: mode.clone(),
                    greedy: mode == "Greedy",
                    lazy: mode == "Lazy",
                    possessive: mode == "Possessive",
                }));
            } else {
                parts.push(atom);
            }
        }
        
        if parts.is_empty() {
            // Empty sequence - return empty literal
            Ok(Node::Literal(Literal {
                value: String::new(),
            }))
        } else if parts.len() == 1 {
            Ok(parts.into_iter().next().unwrap())
        } else {
            Ok(Node::Sequence(Sequence { parts }))
        }
    }

    /// Try to parse a quantifier if present
    /// Returns Option<(min, max, mode)>
    fn try_parse_quantifier(&mut self) -> Result<Option<(i32, MaxBound, String)>, STRlingParseError> {
        if self.cur.eof() {
            return Ok(None);
        }
        
        let _start_pos = self.cur.i;
        let ch = self.cur.peek_char(0);
        
        let (min, max) = match ch {
            Some('*') => {
                self.cur.take();
                (0, MaxBound::Infinite("Inf".to_string()))
            }
            Some('+') => {
                self.cur.take();
                (1, MaxBound::Infinite("Inf".to_string()))
            }
            Some('?') => {
                self.cur.take();
                (0, MaxBound::Finite(1))
            }
            Some('{') => {
                // Parse {m,n} or {n}
                self.cur.take();
                // TODO: Implement brace quantifier parsing
                return Ok(None);
            }
            _ => return Ok(None),
        };
        
        // Check for mode suffix (greedy, lazy, possessive)
        let mode = if let Some('?') = self.cur.peek_char(0) {
            self.cur.take();
            "Lazy".to_string()
        } else if let Some('+') = self.cur.peek_char(0) {
            self.cur.take();
            "Possessive".to_string()
        } else {
            "Greedy".to_string()
        };
        
        Ok(Some((min, max, mode)))
    }

    /// Parse a single atom (character, class, group, etc.)
    fn parse_atom(&mut self) -> Result<Node, STRlingParseError> {
        if self.cur.eof() {
            return Err(self.raise_error(
                "Unexpected end of input".to_string(),
                self.cur.i,
            ));
        }
        
        let ch = self.cur.peek_char(0).unwrap();
        
        match ch {
            '.' => {
                self.cur.take();
                Ok(Node::Dot(Dot {}))
            }
            '^' => {
                self.cur.take();
                Ok(Node::Anchor(Anchor {
                    at: "Start".to_string(),
                }))
            }
            '$' => {
                self.cur.take();
                Ok(Node::Anchor(Anchor {
                    at: "End".to_string(),
                }))
            }
            '(' => self.parse_group(),
            '[' => self.parse_char_class(),
            '\\' => self.parse_escape(),
            _ => self.parse_literal(),
        }
    }

    /// Parse a literal character
    fn parse_literal(&mut self) -> Result<Node, STRlingParseError> {
        if let Some(ch) = self.cur.take() {
            Ok(Node::Literal(Literal {
                value: ch.to_string(),
            }))
        } else {
            Err(self.raise_error(
                "Unexpected end of input".to_string(),
                self.cur.i,
            ))
        }
    }

    /// Parse an escape sequence
    fn parse_escape(&mut self) -> Result<Node, STRlingParseError> {
        let start_pos = self.cur.i;
        self.cur.take();  // consume '\'
        
        if self.cur.eof() {
            return Err(self.raise_error(
                "Incomplete escape sequence".to_string(),
                start_pos,
            ));
        }
        
        let ch = self.cur.take().unwrap();
        
        match ch {
            // Anchors
            'b' => Ok(Node::Anchor(Anchor {
                at: "WordBoundary".to_string(),
            })),
            'B' => Ok(Node::Anchor(Anchor {
                at: "NotWordBoundary".to_string(),
            })),
            'A' => Ok(Node::Anchor(Anchor {
                at: "AbsoluteStart".to_string(),
            })),
            'Z' => Ok(Node::Anchor(Anchor {
                at: "EndBeforeFinalNewline".to_string(),
            })),
            'z' => Ok(Node::Anchor(Anchor {
                at: "AbsoluteEnd".to_string(),
            })),
            
            // Character class escapes
            'd' | 'D' | 'w' | 'W' | 's' | 'S' => {
                Ok(Node::CharacterClass(CharacterClass {
                    negated: ch.is_uppercase(),
                    items: vec![ClassItem::Esc(ClassEscape {
                        escape_type: ch.to_ascii_lowercase().to_string(),
                        property: None,
                    })],
                }))
            }
            
            // Control escapes
            'n' | 'r' | 't' | 'f' | 'v' => {
                let value = self.control_escapes.get(&ch).unwrap();
                Ok(Node::Literal(Literal {
                    value: value.to_string(),
                }))
            }
            
            // Identity escapes (escape the next character literally)
            _ => Ok(Node::Literal(Literal {
                value: ch.to_string(),
            })),
        }
    }

    /// Parse a group: (...)
    fn parse_group(&mut self) -> Result<Node, STRlingParseError> {
        let start_pos = self.cur.i;
        self.cur.take();  // consume '('
        
        // Check for group modifiers
        if let Some('?') = self.cur.peek_char(0) {
            self.cur.take();
            
            // Check what comes after '?'
            if let Some(ch) = self.cur.peek_char(0) {
                match ch {
                    ':' => {
                        // Non-capturing group: (?:...)
                        self.cur.take();
                        let body = self.parse_alt()?;
                        self.expect_char(')', "Unterminated group")?;
                        return Ok(Node::Group(Group {
                            capturing: false,
                            name: None,
                            atomic: Some(false),
                            body: Box::new(body),
                        }));
                    }
                    '=' | '!' => {
                        // Lookahead: (?=...) or (?!...)
                        let positive = ch == '=';
                        self.cur.take();
                        let body = self.parse_alt()?;
                        self.expect_char(')', "Unterminated lookahead")?;
                        if positive {
                            return Ok(Node::Lookahead(LookaroundBody {
                                body: Box::new(body),
                            }));
                        } else {
                            return Ok(Node::NegativeLookahead(LookaroundBody {
                                body: Box::new(body),
                            }));
                        }
                    }
                    '<' => {
                        // Could be lookbehind or named group
                        self.cur.take();
                        if let Some(next_ch) = self.cur.peek_char(0) {
                            if next_ch == '=' || next_ch == '!' {
                                // Lookbehind: (?<=...) or (?<!...)
                                let positive = next_ch == '=';
                                self.cur.take();
                                let body = self.parse_alt()?;
                                self.expect_char(')', "Unterminated lookbehind")?;
                                if positive {
                                    return Ok(Node::Lookbehind(LookaroundBody {
                                        body: Box::new(body),
                                    }));
                                } else {
                                    return Ok(Node::NegativeLookbehind(LookaroundBody {
                                        body: Box::new(body),
                                    }));
                                }
                            } else {
                                // Named group: (?<name>...)
                                let name = self.parse_group_name()?;
                                self.expect_char('>', "Unterminated group name")?;
                                let body = self.parse_alt()?;
                                self.expect_char(')', "Unterminated group")?;
                                self.cap_names.insert(name.clone());
                                self.cap_count += 1;
                                return Ok(Node::Group(Group {
                                    capturing: true,
                                    name: Some(name),
                                    atomic: Some(false),
                                    body: Box::new(body),
                                }));
                            }
                        }
                    }
                    '>' => {
                        // Atomic group: (?>...)
                        self.cur.take();
                        let body = self.parse_alt()?;
                        self.expect_char(')', "Unterminated atomic group")?;
                        return Ok(Node::Group(Group {
                            capturing: false,
                            name: None,
                            atomic: Some(true),
                            body: Box::new(body),
                        }));
                    }
                    _ => {
                        return Err(self.raise_error(
                            format!("Unknown group modifier: ?{}", ch),
                            self.cur.i - 1,
                        ));
                    }
                }
            }
        }
        
        // Regular capturing group
        self.cap_count += 1;
        let body = self.parse_alt()?;
        self.expect_char(')', "Unterminated group")?;
        Ok(Node::Group(Group {
            capturing: true,
            name: None,
            atomic: Some(false),
            body: Box::new(body),
        }))
    }

    /// Parse a character class: [...]
    fn parse_char_class(&mut self) -> Result<Node, STRlingParseError> {
        let start_pos = self.cur.i;
        self.cur.take();  // consume '['
        self.cur.in_class += 1;
        
        // Check for negation
        let negated = if let Some('^') = self.cur.peek_char(0) {
            self.cur.take();
            true
        } else {
            false
        };
        
        let mut items = Vec::new();
        
        // Parse class items
        loop {
            if self.cur.eof() {
                return Err(self.raise_error(
                    "Unterminated character class".to_string(),
                    start_pos,
                ));
            }
            
            if let Some(']') = self.cur.peek_char(0) {
                self.cur.take();
                break;
            }
            
            // Parse one class item
            // TODO: Implement full class item parsing (ranges, escapes, etc.)
            let ch = self.cur.take().unwrap();
            items.push(ClassItem::Char(ClassLiteral {
                ch: ch.to_string(),
            }));
        }
        
        self.cur.in_class -= 1;
        
        if items.is_empty() {
            return Err(self.raise_error(
                "Empty character class".to_string(),
                start_pos,
            ));
        }
        
        Ok(Node::CharacterClass(CharacterClass { negated, items }))
    }

    /// Parse a group name for named groups
    fn parse_group_name(&mut self) -> Result<String, STRlingParseError> {
        let mut name = String::new();
        
        while let Some(ch) = self.cur.peek_char(0) {
            if ch == '>' {
                break;
            }
            if ch.is_alphanumeric() || ch == '_' {
                name.push(ch);
                self.cur.take();
            } else {
                return Err(self.raise_error(
                    format!("Invalid character in group name: {}", ch),
                    self.cur.i,
                ));
            }
        }
        
        if name.is_empty() {
            return Err(self.raise_error(
                "Empty group name".to_string(),
                self.cur.i,
            ));
        }
        
        Ok(name)
    }

    /// Expect a specific character at the current position
    fn expect_char(&mut self, expected: char, error_msg: &str) -> Result<(), STRlingParseError> {
        if let Some(ch) = self.cur.take() {
            if ch == expected {
                Ok(())
            } else {
                Err(self.raise_error(
                    error_msg.to_string(),
                    self.cur.i - 1,
                ))
            }
        } else {
            Err(self.raise_error(
                error_msg.to_string(),
                self.cur.i,
            ))
        }
    }
}

/// Parse a STRling pattern into an AST
///
/// # Arguments
///
/// * `text` - The STRling pattern text to parse
///
/// # Returns
///
/// A tuple of (Flags, Node) where Flags contains the parsed flags and Node is the root AST node
///
/// # Errors
///
/// Returns STRlingParseError if the pattern is invalid
pub fn parse(text: &str) -> Result<(Flags, Node), STRlingParseError> {
    let mut parser = Parser::new(text.to_string());
    let node = parser.parse()?;
    Ok((parser.flags, node))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_simple_literal() {
        let result = parse("hello");
        assert!(result.is_ok());
        let (flags, node) = result.unwrap();
        // Should be a sequence of literals
        match node {
            Node::Sequence(seq) => {
                assert_eq!(seq.parts.len(), 5);
            }
            _ => panic!("Expected Seq node"),
        }
    }

    #[test]
    fn test_parse_anchor() {
        let result = parse("^test$");
        assert!(result.is_ok());
    }

    #[test]
    fn test_parse_dot() {
        let result = parse(".");
        assert!(result.is_ok());
        let (_, node) = result.unwrap();
        match node {
            Node::Dot(_) => {},
            _ => panic!("Expected Dot node"),
        }
    }

    #[test]
    fn test_parse_alternation() {
        let result = parse("a|b");
        assert!(result.is_ok());
        let (_, node) = result.unwrap();
        match node {
            Node::Alternation(alt) => {
                assert_eq!(alt.branches.len(), 2);
            }
            _ => panic!("Expected Alt node"),
        }
    }

    #[test]
    fn test_parse_quantifier() {
        let result = parse("a*");
        assert!(result.is_ok());
        let (_, node) = result.unwrap();
        match node {
            Node::Quantifier(quant) => {
                assert_eq!(quant.min, 0);
                match quant.max {
                    MaxBound::Infinite(_) => {},
                    _ => panic!("Expected infinite max"),
                }
            }
            _ => panic!("Expected Quant node"),
        }
    }

    #[test]
    fn test_parse_group() {
        let result = parse("(abc)");
        assert!(result.is_ok());
        let (_, node) = result.unwrap();
        match node {
            Node::Group(group) => {
                assert!(group.capturing);
                assert_eq!(group.name, None);
            }
            _ => panic!("Expected Group node"),
        }
    }

    #[test]
    fn test_unmatched_paren_error() {
        let result = parse("test)");
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(err.message.contains("Unmatched"));
    }

    #[test]
    fn test_empty_alternation() {
        let result = parse("a||b");
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(err.message.contains("Empty alternation"));
    }
}
