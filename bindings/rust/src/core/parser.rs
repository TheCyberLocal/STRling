//! STRling Parser - Recursive Descent Parser for STRling DSL

use crate::core::errors::STRlingParseError;
use crate::core::hint_engine::get_hint;
use crate::core::nodes::*;
use std::collections::{HashMap, HashSet};

pub type ParseError = STRlingParseError;

#[derive(Debug, Clone)]
struct Cursor {
    text: String,
    i: usize,
    extended_mode: bool,
    in_class: usize,
}

#[allow(dead_code)]
impl Cursor {
    fn new(text: String, i: usize, extended_mode: bool, in_class: usize) -> Self {
        Self { text, i, extended_mode, in_class }
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
        self.text.chars().nth(self.i + n)
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
        while !self.eof() {
            if let Some(ch) = self.peek_char(0) {
                if " \t\r\n".contains(ch) {
                    self.i += 1;
                    continue;
                }
                if ch == '#' {
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

#[allow(dead_code)]
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

        parser.control_escapes.insert('n', '\n');
        parser.control_escapes.insert('r', '\r');
        parser.control_escapes.insert('t', '\t');
        parser.control_escapes.insert('f', '\u{000C}');
        parser.control_escapes.insert('v', '\u{000B}');

        parser
    }

    fn raise_error(&self, message: String, pos: usize) -> STRlingParseError {
        let hint = get_hint(&message, &self.src, pos);
        STRlingParseError::new(message, pos, self.src.clone(), hint)
    }

    fn raise_error_with_text(&self, message: String, pos: usize, text: &str) -> STRlingParseError {
        let hint = get_hint(&message, text, pos);
        STRlingParseError::new(message, pos, text.to_string(), hint)
    }

    fn parse_directives(&mut self) -> Result<(), STRlingParseError> {
        let text = self.original_text.clone();
        let mut flags = Flags::default();
        let lines: Vec<&str> = text.lines().collect();
        let mut pattern_lines: Vec<String> = Vec::new();
        let mut in_pattern = false;

        for line in &lines {
            let stripped = line.trim();

            if !in_pattern && (stripped.is_empty() || stripped.starts_with('#')) {
                continue;
            }

            if stripped.starts_with('%') {
                if in_pattern {
                    return Err(self.raise_error_with_text(
                        "Directive after pattern".to_string(), 0, &text));
                }
                if !stripped.starts_with("%flags") {
                    return Err(self.raise_error_with_text(
                        "Malformed directive".to_string(), 0, &text));
                }

                if let Some(idx) = line.find("%flags") {
                    let after = &line[idx + "%flags".len()..];
                    let allowed: HashSet<char> = " ,\t[]imsuxIMSUX".chars().collect();
                    let mut j = 0;
                    for (k, c) in after.chars().enumerate() {
                        if allowed.contains(&c) {
                            j = k + 1;
                        } else {
                            break;
                        }
                    }

                    let flags_token = &after[..j];
                    let remainder = &after[j..];
                    let valid_flags = "imsux";

                    let letters: String = flags_token
                        .chars()
                        .filter(|c| c.is_alphabetic())
                        .map(|c| c.to_ascii_lowercase())
                        .collect();

                    for ch in letters.chars() {
                        if !valid_flags.contains(ch) {
                            return Err(self.raise_error_with_text(
                                format!("Invalid flag '{}'", ch), 0, &text));
                        }
                    }

                    if !letters.is_empty() {
                        flags = Flags::from_letters(&letters);
                    } else if !remainder.trim().is_empty() {
                        let ch = remainder.trim().chars().next().unwrap();
                        return Err(self.raise_error_with_text(
                            format!("Invalid flag '{}'", ch), 0, &text));
                    }

                    if !remainder.trim().is_empty() {
                        pattern_lines.push(remainder.to_string());
                        in_pattern = true;
                    }
                }
                continue;
            }

            if stripped.contains("%flags") {
                return Err(self.raise_error_with_text(
                    "Directive after pattern".to_string(), 0, &text));
            }

            in_pattern = true;
            pattern_lines.push(line.to_string());
        }

        let src = pattern_lines.join("\n");
        self.flags = flags.clone();
        self.src = src.clone();
        self.cur = Cursor::new(src, 0, flags.extended, 0);
        Ok(())
    }

    pub fn parse(&mut self) -> Result<(Flags, Node), STRlingParseError> {
        self.parse_directives()?;
        let node = self.parse_alt()?;
        self.cur.skip_ws_and_comments();

        if !self.cur.eof() {
            if let Some(ch) = self.cur.peek_char(0) {
                if ch == ')' {
                    return Err(self.raise_error("Unmatched ')'".to_string(), self.cur.i));
                }
            }
            return Err(self.raise_error("Unexpected trailing input".to_string(), self.cur.i));
        }

        Ok((self.flags.clone(), node))
    }

    fn parse_alt(&mut self) -> Result<Node, STRlingParseError> {
        self.cur.skip_ws_and_comments();

        if let Some('|') = self.cur.peek_char(0) {
            return Err(self.raise_error("Alternation lacks left-hand side".to_string(), self.cur.i));
        }

        let mut branches = vec![self.parse_seq()?];
        self.cur.skip_ws_and_comments();

        while let Some('|') = self.cur.peek_char(0) {
            let pipe_pos = self.cur.i;
            self.cur.take();
            self.cur.skip_ws_and_comments();

            if self.cur.eof() {
                return Err(self.raise_error("Alternation lacks right-hand side".to_string(), pipe_pos));
            }

            if let Some('|') = self.cur.peek_char(0) {
                return Err(self.raise_error("Empty alternation".to_string(), pipe_pos));
            }

            if let Some(')') = self.cur.peek_char(0) {
                return Err(self.raise_error("Alternation lacks right-hand side".to_string(), pipe_pos));
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

    fn parse_seq(&mut self) -> Result<Node, STRlingParseError> {
        let mut parts = Vec::new();

        loop {
            self.cur.skip_ws_and_comments();
            if self.cur.eof() { break; }
            if let Some(ch) = self.cur.peek_char(0) {
                if ch == '|' || ch == ')' { break; }
            }

            let atom = self.parse_atom()?;
            self.cur.skip_ws_and_comments();

            if let Some(quant) = self.try_parse_quantifier(&atom)? {
                parts.push(Node::Quantifier(Quantifier {
                    target: QuantifierTarget { child: Box::new(atom) },
                    min: quant.0,
                    max: quant.1,
                    mode: quant.2.clone(),
                    greedy: quant.2 == "Greedy",
                    lazy: quant.2 == "Lazy",
                    possessive: quant.2 == "Possessive",
                }));
            } else {
                parts.push(atom);
            }
        }

        if parts.is_empty() {
            Ok(Node::Literal(Literal { value: String::new() }))
        } else if parts.len() == 1 {
            Ok(parts.into_iter().next().unwrap())
        } else {
            Ok(Node::Sequence(Sequence { parts }))
        }
    }

    fn try_parse_quantifier(&mut self, child: &Node) -> Result<Option<(i32, MaxBound, String)>, STRlingParseError> {
        if self.cur.eof() { return Ok(None); }

        let start_pos = self.cur.i;
        let ch = self.cur.peek_char(0);

        let (min, max) = match ch {
            Some('*') => { self.cur.take(); (0, MaxBound::Infinite("Inf".to_string())) }
            Some('+') => { self.cur.take(); (1, MaxBound::Infinite("Inf".to_string())) }
            Some('?') => { self.cur.take(); (0, MaxBound::Finite(1)) }
            Some('{') => {
                let save = self.cur.i;
                self.cur.take(); // consume {

                // Look ahead for invalid brace content
                let mut look_ahead = String::new();
                let mut j = self.cur.i;
                while j < self.cur.text.len() {
                    let c = self.cur.text.chars().nth(j).unwrap_or('\0');
                    if c == '}' { break; }
                    look_ahead.push(c);
                    j += 1;
                }

                let valid_re = regex::Regex::new(r"^\d+(,\d*)?$").unwrap();
                if j < self.cur.text.len() && !look_ahead.is_empty() && !valid_re.is_match(&look_ahead) {
                    return Err(self.raise_error("Brace quantifier: Invalid brace quantifier content".to_string(), save));
                }

                let mut num_str = String::new();
                while !self.cur.eof() {
                    if let Some(c) = self.cur.peek_char(0) {
                        if c.is_ascii_digit() { num_str.push(c); self.cur.take(); } else { break; }
                    } else { break; }
                }
                if num_str.is_empty() {
                    return Err(self.raise_error("Expected number in quantifier".to_string(), self.cur.i));
                }
                let min_val: i32 = num_str.parse().unwrap_or(0);

                let max_val;
                if self.cur.match_str(",") {
                    let mut max_str = String::new();
                    while !self.cur.eof() {
                        if let Some(c) = self.cur.peek_char(0) {
                            if c.is_ascii_digit() { max_str.push(c); self.cur.take(); } else { break; }
                        } else { break; }
                    }
                    if max_str.is_empty() {
                        max_val = MaxBound::Infinite("Inf".to_string());
                    } else {
                        max_val = MaxBound::Finite(max_str.parse().unwrap_or(0));
                    }
                } else {
                    max_val = MaxBound::Finite(min_val);
                }

                if !self.cur.match_str("}") {
                    return Err(self.raise_error("Incomplete quantifier".to_string(), self.cur.i));
                }

                if let MaxBound::Finite(mx) = &max_val {
                    if min_val > *mx {
                        return Err(self.raise_error("Invalid quantifier range".to_string(), save));
                    }
                }

                (min_val, max_val)
            }
            _ => return Ok(None),
        };

        // Cannot quantify anchor
        if let Node::Anchor(_) = child {
            return Err(self.raise_error("Cannot quantify anchor".to_string(), start_pos));
        }

        let mode = if let Some('?') = self.cur.peek_char(0) {
            self.cur.take(); "Lazy".to_string()
        } else if let Some('+') = self.cur.peek_char(0) {
            self.cur.take(); "Possessive".to_string()
        } else {
            "Greedy".to_string()
        };

        Ok(Some((min, max, mode)))
    }

    fn parse_atom(&mut self) -> Result<Node, STRlingParseError> {
        if self.cur.eof() {
            return Err(self.raise_error("Unexpected end of input".to_string(), self.cur.i));
        }

        let ch = self.cur.peek_char(0).unwrap();

        match ch {
            '.' => { self.cur.take(); Ok(Node::Dot(Dot {})) }
            '^' => { self.cur.take(); Ok(Node::Anchor(Anchor { at: "Start".to_string() })) }
            '$' => { self.cur.take(); Ok(Node::Anchor(Anchor { at: "End".to_string() })) }
            '(' => self.parse_group(),
            '[' => self.parse_char_class(),
            '\\' => self.parse_escape(),
            '*' | '+' | '?' => {
                Err(self.raise_error(format!("Invalid quantifier '{}'", ch), self.cur.i))
            }
            '{' => {
                // Check for invalid brace content
                let save = self.cur.i;
                let mut look_ahead = String::new();
                let mut j = self.cur.i + 1;
                while j < self.cur.text.len() {
                    let c = self.cur.text.chars().nth(j).unwrap_or('\0');
                    if c == '}' { break; }
                    look_ahead.push(c);
                    j += 1;
                }
                if j < self.cur.text.len() {
                    let valid_re = regex::Regex::new(r"^\d+(,\d*)?$").unwrap();
                    if !look_ahead.is_empty() && !valid_re.is_match(&look_ahead) {
                        return Err(self.raise_error("Brace quantifier: Invalid brace quantifier content".to_string(), save));
                    }
                }
                Err(self.raise_error(format!("Invalid quantifier '{}'", ch), self.cur.i))
            }
            _ => self.parse_literal(),
        }
    }

    fn parse_literal(&mut self) -> Result<Node, STRlingParseError> {
        if let Some(ch) = self.cur.take() {
            Ok(Node::Literal(Literal { value: ch.to_string() }))
        } else {
            Err(self.raise_error("Unexpected end of input".to_string(), self.cur.i))
        }
    }

    fn parse_escape(&mut self) -> Result<Node, STRlingParseError> {
        let start_pos = self.cur.i;
        self.cur.take(); // consume backslash

        if self.cur.eof() {
            return Err(self.raise_error("Incomplete escape sequence".to_string(), start_pos));
        }

        let ch = self.cur.take().unwrap();

        match ch {
            'b' => Ok(Node::Anchor(Anchor { at: "WordBoundary".to_string() })),
            'B' => Ok(Node::Anchor(Anchor { at: "NotWordBoundary".to_string() })),
            'A' => Ok(Node::Anchor(Anchor { at: "AbsoluteStart".to_string() })),
            'Z' => Ok(Node::Anchor(Anchor { at: "EndBeforeFinalNewline".to_string() })),
            // NOTE: lowercase \z is intentionally NOT an anchor

            'd' | 'D' | 'w' | 'W' | 's' | 'S' => {
                Ok(Node::CharacterClass(CharacterClass {
                    negated: false,
                    items: vec![ClassItem::Esc(ClassEscape {
                        escape_type: ch.to_string(),
                        property: None,
                    })],
                }))
            }

            'n' | 'r' | 't' | 'f' | 'v' => {
                let value = self.control_escapes.get(&ch).unwrap();
                Ok(Node::Literal(Literal { value: value.to_string() }))
            }

            '0' => Ok(Node::Literal(Literal { value: "\x00".to_string() })),

            '1'..='9' => {
                let mut num = (ch as u32 - '0' as u32) as usize;
                while !self.cur.eof() {
                    if let Some(c) = self.cur.peek_char(0) {
                        if c.is_ascii_digit() {
                            num = num * 10 + (c as u32 - '0' as u32) as usize;
                            self.cur.take();
                        } else { break; }
                    } else { break; }
                }
                if num > self.cap_count {
                    return Err(self.raise_error(
                        format!("Backreference to undefined group \\{}", num), start_pos));
                }
                Ok(Node::Backreference(Backreference {
                    by_index: Some(num as i32),
                    by_name: None,
                }))
            }

            'k' => {
                if self.cur.peek_char(0) != Some('<') {
                    return Err(self.raise_error("Expected '<' after \\k".to_string(), self.cur.i));
                }
                self.cur.take();
                let mut name = String::new();
                while !self.cur.eof() {
                    if let Some(c) = self.cur.peek_char(0) {
                        if c == '>' { break; }
                        name.push(c);
                        self.cur.take();
                    } else { break; }
                }
                if self.cur.eof() {
                    return Err(self.raise_error("Unterminated named backref".to_string(), self.cur.i));
                }
                self.cur.take(); // consume >
                if !self.cap_names.contains(&name) {
                    return Err(self.raise_error(
                        format!("Backreference to undefined group <{}>", name), start_pos));
                }
                Ok(Node::Backreference(Backreference {
                    by_index: None,
                    by_name: Some(name),
                }))
            }

            'x' => self.parse_hex_escape(start_pos),
            'u' | 'U' => self.parse_unicode_escape(ch, start_pos),

            'p' | 'P' => {
                if self.cur.peek_char(0) != Some('{') {
                    return Err(self.raise_error("Expected { after \\p/\\P".to_string(), start_pos));
                }
                self.cur.take();
                let mut prop = String::new();
                while !self.cur.eof() {
                    if let Some(c) = self.cur.peek_char(0) {
                        if c == '}' { break; }
                        prop.push(c);
                        self.cur.take();
                    } else { break; }
                }
                if self.cur.eof() {
                    return Err(self.raise_error("Unterminated \\p{...}".to_string(), start_pos));
                }
                self.cur.take(); // consume }
                Ok(Node::CharacterClass(CharacterClass {
                    negated: false,
                    items: vec![ClassItem::Esc(ClassEscape {
                        escape_type: ch.to_string(),
                        property: Some(prop),
                    })],
                }))
            }

            _ => {
                if ch.is_alphanumeric() {
                    return Err(self.raise_error(
                        format!("Unknown escape sequence \\{}", ch), start_pos));
                }
                Ok(Node::Literal(Literal { value: ch.to_string() }))
            }
        }
    }

    fn parse_hex_escape(&mut self, start_pos: usize) -> Result<Node, STRlingParseError> {
        if self.cur.peek_char(0) == Some('{') {
            self.cur.take();
            let mut hex = String::new();
            while !self.cur.eof() {
                if let Some(c) = self.cur.peek_char(0) {
                    if c.is_ascii_hexdigit() { hex.push(c); self.cur.take(); } else { break; }
                } else { break; }
            }
            if !self.cur.match_str("}") {
                return Err(self.raise_error("Unterminated \\x{...}".to_string(), start_pos));
            }
            let cp = u32::from_str_radix(&hex, 16).unwrap_or(0);
            return Ok(Node::Literal(Literal {
                value: char::from_u32(cp).unwrap_or('\0').to_string()
            }));
        }

        let mut hex = String::new();
        for _ in 0..2 {
            if let Some(c) = self.cur.take() { hex.push(c); }
        }
        if hex.len() != 2 || !hex.chars().all(|c| c.is_ascii_hexdigit()) {
            return Err(self.raise_error("Invalid \\xHH escape".to_string(), start_pos));
        }
        let cp = u32::from_str_radix(&hex, 16).unwrap_or(0);
        Ok(Node::Literal(Literal {
            value: char::from_u32(cp).unwrap_or('\0').to_string()
        }))
    }

    fn parse_unicode_escape(&mut self, tp: char, start_pos: usize) -> Result<Node, STRlingParseError> {
        if tp == 'u' && self.cur.peek_char(0) == Some('{') {
            self.cur.take();
            let mut hex = String::new();
            while !self.cur.eof() {
                if let Some(c) = self.cur.peek_char(0) {
                    if c.is_ascii_hexdigit() { hex.push(c); self.cur.take(); } else { break; }
                } else { break; }
            }
            if !self.cur.match_str("}") {
                return Err(self.raise_error("Unterminated \\u{...}".to_string(), start_pos));
            }
            let cp = u32::from_str_radix(&hex, 16).unwrap_or(0);
            return Ok(Node::Literal(Literal {
                value: char::from_u32(cp).unwrap_or('\0').to_string()
            }));
        }

        if tp == 'u' {
            let mut hex = String::new();
            for _ in 0..4 {
                if let Some(c) = self.cur.take() { hex.push(c); }
            }
            if hex.len() != 4 || !hex.chars().all(|c| c.is_ascii_hexdigit()) {
                return Err(self.raise_error("Invalid \\uHHHH escape".to_string(), start_pos));
            }
            let cp = u32::from_str_radix(&hex, 16).unwrap_or(0);
            return Ok(Node::Literal(Literal {
                value: char::from_u32(cp).unwrap_or('\0').to_string()
            }));
        }

        if tp == 'U' {
            let mut hex = String::new();
            for _ in 0..8 {
                if let Some(c) = self.cur.take() { hex.push(c); }
            }
            if hex.len() != 8 || !hex.chars().all(|c| c.is_ascii_hexdigit()) {
                return Err(self.raise_error("Invalid \\UHHHHHHHH escape".to_string(), start_pos));
            }
            let cp = u32::from_str_radix(&hex, 16).unwrap_or(0);
            return Ok(Node::Literal(Literal {
                value: char::from_u32(cp).unwrap_or('\0').to_string()
            }));
        }

        Err(self.raise_error("Invalid unicode escape".to_string(), start_pos))
    }

    fn parse_group(&mut self) -> Result<Node, STRlingParseError> {
        let start_pos = self.cur.i;
        self.cur.take(); // consume '('

        if let Some('?') = self.cur.peek_char(0) {
            self.cur.take();

            if let Some(ch) = self.cur.peek_char(0) {
                match ch {
                    ':' => {
                        self.cur.take();
                        let body = self.parse_alt()?;
                        self.expect_char(')', "Unterminated group")?;
                        return Ok(Node::Group(Group {
                            capturing: false, name: None, atomic: Some(false),
                            body: Box::new(body),
                        }));
                    }
                    '=' | '!' => {
                        let positive = ch == '=';
                        self.cur.take();
                        let body = self.parse_alt()?;
                        self.expect_char(')', "Unterminated lookahead")?;
                        if positive {
                            return Ok(Node::Lookahead(LookaroundBody { body: Box::new(body) }));
                        } else {
                            return Ok(Node::NegativeLookahead(LookaroundBody { body: Box::new(body) }));
                        }
                    }
                    '<' => {
                        self.cur.take();
                        if let Some(next_ch) = self.cur.peek_char(0) {
                            if next_ch == '=' || next_ch == '!' {
                                let positive = next_ch == '=';
                                self.cur.take();
                                let body = self.parse_alt()?;
                                self.expect_char(')', "Unterminated lookbehind")?;
                                if positive {
                                    return Ok(Node::Lookbehind(LookaroundBody { body: Box::new(body) }));
                                } else {
                                    return Ok(Node::NegativeLookbehind(LookaroundBody { body: Box::new(body) }));
                                }
                            } else {
                                // Named group
                                let name = self.parse_group_name()?;
                                self.expect_char('>', "Unterminated group name")?;

                                let name_re = regex::Regex::new(r"^[a-zA-Z_][a-zA-Z0-9_]*$").unwrap();
                                if !name_re.is_match(&name) {
                                    return Err(self.raise_error(
                                        format!("Invalid group name '{}'", name), start_pos));
                                }

                                if self.cap_names.contains(&name) {
                                    return Err(self.raise_error(
                                        format!("Duplicate group name '{}'", name), start_pos));
                                }

                                self.cap_names.insert(name.clone());
                                self.cap_count += 1;
                                let body = self.parse_alt()?;
                                self.expect_char(')', "Unterminated group")?;
                                return Ok(Node::Group(Group {
                                    capturing: true, name: Some(name), atomic: Some(false),
                                    body: Box::new(body),
                                }));
                            }
                        } else {
                            return Err(self.raise_error("Unterminated group name".to_string(), self.cur.i));
                        }
                    }
                    '>' => {
                        self.cur.take();
                        let body = self.parse_alt()?;
                        self.expect_char(')', "Unterminated atomic group")?;
                        return Ok(Node::Group(Group {
                            capturing: false, name: None, atomic: Some(true),
                            body: Box::new(body),
                        }));
                    }
                    _ => {
                        // Check for inline modifiers like (?i), (?im)
                        let save = self.cur.i;
                        let mut scan = String::new();
                        let mut j = save;
                        while j < self.cur.text.len() {
                            let c = self.cur.text.chars().nth(j).unwrap_or('\0');
                            if "imsux".contains(c) { scan.push(c); j += 1; }
                            else { break; }
                        }
                        if !scan.is_empty() && j < self.cur.text.len() && self.cur.text.chars().nth(j) == Some(')') {
                            return Err(self.raise_error(
                                format!("Inline modifiers like (?{}...) are not supported", scan), start_pos));
                        }
                        return Err(self.raise_error(
                            format!("Unknown group modifier: ?{}", ch), self.cur.i - 1));
                    }
                }
            }
        }

        // Regular capturing group
        self.cap_count += 1;
        let body = self.parse_alt()?;
        self.expect_char(')', "Unterminated group")?;
        Ok(Node::Group(Group {
            capturing: true, name: None, atomic: Some(false),
            body: Box::new(body),
        }))
    }

    fn parse_char_class(&mut self) -> Result<Node, STRlingParseError> {
        let start_pos = self.cur.i;
        self.cur.take(); // consume '['
        self.cur.in_class += 1;

        let negated = if let Some('^') = self.cur.peek_char(0) {
            self.cur.take(); true
        } else {
            false
        };

        // Empty char class check
        if let Some(']') = self.cur.peek_char(0) {
            self.cur.in_class -= 1;
            return Err(self.raise_error("Unterminated character class".to_string(), start_pos));
        }

        let mut items = Vec::new();

        loop {
            if self.cur.eof() {
                self.cur.in_class -= 1;
                return Err(self.raise_error("Unterminated character class".to_string(), start_pos));
            }

            if let Some(']') = self.cur.peek_char(0) {
                self.cur.take();
                break;
            }

            let item = self.parse_class_item()?;

            // Check for range: X-Y
            if self.cur.peek_char(0) == Some('-') && self.cur.peek_char(1) != Some(']') && !self.cur.eof() {
                if let ClassItem::Char(ref from_lit) = item {
                    let from_ch = from_lit.ch.chars().next().unwrap_or('\0');
                    self.cur.take(); // consume '-'

                    if self.cur.eof() || self.cur.peek_char(0) == Some(']') {
                        items.push(item);
                        items.push(ClassItem::Char(ClassLiteral { ch: "-".to_string() }));
                        continue;
                    }

                    let to_item = self.parse_class_item()?;
                    if let ClassItem::Char(ref to_lit) = to_item {
                        let to_ch = to_lit.ch.chars().next().unwrap_or('\0');
                        if to_ch < from_ch {
                            self.cur.in_class -= 1;
                            return Err(self.raise_error("Invalid character range".to_string(), start_pos));
                        }
                        items.push(ClassItem::Range(ClassRange {
                            from_ch: from_lit.ch.clone(),
                            to_ch: to_lit.ch.clone(),
                        }));
                        continue;
                    } else {
                        items.push(item);
                        items.push(ClassItem::Char(ClassLiteral { ch: "-".to_string() }));
                        items.push(to_item);
                        continue;
                    }
                }
            }

            items.push(item);
        }

        self.cur.in_class -= 1;

        Ok(Node::CharacterClass(CharacterClass { negated, items }))
    }

    fn parse_class_item(&mut self) -> Result<ClassItem, STRlingParseError> {
        if let Some('\\') = self.cur.peek_char(0) {
            let start_pos = self.cur.i;
            self.cur.take();

            if self.cur.eof() {
                return Err(self.raise_error("Incomplete escape sequence".to_string(), start_pos));
            }

            let ch = self.cur.take().unwrap();

            match ch {
                'd' | 'D' | 'w' | 'W' | 's' | 'S' => {
                    Ok(ClassItem::Esc(ClassEscape {
                        escape_type: ch.to_string(),
                        property: None,
                    }))
                }
                'b' => Ok(ClassItem::Char(ClassLiteral { ch: "\x08".to_string() })),
                '0' => Ok(ClassItem::Char(ClassLiteral { ch: "\x00".to_string() })),
                'n' => Ok(ClassItem::Char(ClassLiteral { ch: "\n".to_string() })),
                'r' => Ok(ClassItem::Char(ClassLiteral { ch: "\r".to_string() })),
                't' => Ok(ClassItem::Char(ClassLiteral { ch: "\t".to_string() })),
                'f' => Ok(ClassItem::Char(ClassLiteral { ch: "\u{000C}".to_string() })),
                'v' => Ok(ClassItem::Char(ClassLiteral { ch: "\u{000B}".to_string() })),
                'x' => {
                    if self.cur.peek_char(0) == Some('{') {
                        self.cur.take();
                        let mut hex = String::new();
                        while !self.cur.eof() {
                            if let Some(c) = self.cur.peek_char(0) {
                                if c.is_ascii_hexdigit() { hex.push(c); self.cur.take(); } else { break; }
                            } else { break; }
                        }
                        if !self.cur.match_str("}") {
                            return Err(self.raise_error("Unterminated \\x{...}".to_string(), start_pos));
                        }
                        let cp = u32::from_str_radix(&hex, 16).unwrap_or(0);
                        Ok(ClassItem::Char(ClassLiteral { ch: char::from_u32(cp).unwrap_or('\0').to_string() }))
                    } else {
                        let mut hex = String::new();
                        for _ in 0..2 {
                            if let Some(c) = self.cur.take() { hex.push(c); }
                        }
                        if hex.len() != 2 || !hex.chars().all(|c| c.is_ascii_hexdigit()) {
                            return Err(self.raise_error("Invalid \\xHH escape".to_string(), start_pos));
                        }
                        let cp = u32::from_str_radix(&hex, 16).unwrap_or(0);
                        Ok(ClassItem::Char(ClassLiteral { ch: char::from_u32(cp).unwrap_or('\0').to_string() }))
                    }
                }
                'u' => {
                    if self.cur.peek_char(0) == Some('{') {
                        self.cur.take();
                        let mut hex = String::new();
                        while !self.cur.eof() {
                            if let Some(c) = self.cur.peek_char(0) {
                                if c.is_ascii_hexdigit() { hex.push(c); self.cur.take(); } else { break; }
                            } else { break; }
                        }
                        if !self.cur.match_str("}") {
                            return Err(self.raise_error("Unterminated \\u{...}".to_string(), start_pos));
                        }
                        let cp = u32::from_str_radix(&hex, 16).unwrap_or(0);
                        Ok(ClassItem::Char(ClassLiteral { ch: char::from_u32(cp).unwrap_or('\0').to_string() }))
                    } else {
                        let mut hex = String::new();
                        for _ in 0..4 {
                            if let Some(c) = self.cur.take() { hex.push(c); }
                        }
                        if hex.len() != 4 || !hex.chars().all(|c| c.is_ascii_hexdigit()) {
                            return Err(self.raise_error("Invalid \\uHHHH escape".to_string(), start_pos));
                        }
                        let cp = u32::from_str_radix(&hex, 16).unwrap_or(0);
                        Ok(ClassItem::Char(ClassLiteral { ch: char::from_u32(cp).unwrap_or('\0').to_string() }))
                    }
                }
                'p' | 'P' => {
                    if self.cur.peek_char(0) != Some('{') {
                        return Err(self.raise_error("Expected { after \\p/\\P".to_string(), start_pos));
                    }
                    self.cur.take();
                    let mut prop = String::new();
                    while !self.cur.eof() {
                        if let Some(c) = self.cur.peek_char(0) {
                            if c == '}' { break; }
                            prop.push(c);
                            self.cur.take();
                        } else { break; }
                    }
                    if self.cur.eof() {
                        return Err(self.raise_error("Unterminated \\p{...}".to_string(), start_pos));
                    }
                    self.cur.take();
                    Ok(ClassItem::Esc(ClassEscape {
                        escape_type: ch.to_string(),
                        property: Some(prop),
                    }))
                }
                _ => {
                    if ch.is_alphanumeric() {
                        return Err(self.raise_error(
                            format!("Unknown escape sequence \\{}", ch), start_pos));
                    }
                    Ok(ClassItem::Char(ClassLiteral { ch: ch.to_string() }))
                }
            }
        } else {
            let ch = self.cur.take().unwrap();
            Ok(ClassItem::Char(ClassLiteral { ch: ch.to_string() }))
        }
    }

    fn parse_group_name(&mut self) -> Result<String, STRlingParseError> {
        let mut name = String::new();

        while let Some(ch) = self.cur.peek_char(0) {
            if ch == '>' { break; }
            name.push(ch);
            self.cur.take();
        }

        if self.cur.eof() {
            return Err(self.raise_error("Unterminated group name".to_string(), self.cur.i));
        }

        if name.is_empty() {
            return Err(self.raise_error("Invalid group name ''".to_string(), self.cur.i));
        }

        Ok(name)
    }

    fn expect_char(&mut self, expected: char, error_msg: &str) -> Result<(), STRlingParseError> {
        if let Some(ch) = self.cur.take() {
            if ch == expected { Ok(()) }
            else { Err(self.raise_error(error_msg.to_string(), self.cur.i - 1)) }
        } else {
            Err(self.raise_error(error_msg.to_string(), self.cur.i))
        }
    }
}

pub fn parse(text: &str) -> Result<(Flags, Node), STRlingParseError> {
    let mut parser = Parser::new(text.to_string());
    parser.parse()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_simple_literal() {
        let result = parse("hello");
        assert!(result.is_ok());
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
    }

    #[test]
    fn test_parse_alternation() {
        let result = parse("a|b");
        assert!(result.is_ok());
    }

    #[test]
    fn test_parse_quantifier() {
        let result = parse("a*");
        assert!(result.is_ok());
    }

    #[test]
    fn test_parse_group() {
        let result = parse("(abc)");
        assert!(result.is_ok());
    }

    #[test]
    fn test_unmatched_paren_error() {
        let result = parse("test)");
        assert!(result.is_err());
    }

    #[test]
    fn test_empty_alternation() {
        let result = parse("a||b");
        assert!(result.is_err());
    }
}
