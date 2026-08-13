//! Bounded parser and canonical formatter for `strling.semantic@1.0.0`.
//!
//! The versioned contract under `spec/frontends/semantic/1.0` is authoritative.
//! This module owns syntax recognition, syntax-preserving formatting evidence,
//! and direct lowering into canonical Semantic IR. It deliberately owns no
//! target, emitter, binding, filesystem, environment, runtime, or package policy.

use std::collections::{BTreeMap, BTreeSet};
use std::error::Error;
use std::fmt;

use crate::diagnostic::{
    CompilerPhase, Diagnostic, DiagnosticCategory, DiagnosticCode, DiagnosticOccurrence, Severity,
    SeverityBasis,
};
use crate::normalization::{normalize, NormalizationErrors};
use crate::semantic::{
    AssertionPolarity, BuiltinClassName, CaseMatching, CharacterDomain, CharacterSetMember,
    LineTerminators, LookaroundDirection, Node, Normalization, PositionKind, RepetitionMaximum,
    RepetitionMode, SemanticProgram, UnicodeScalar,
};
use crate::source::{
    CaptureId, FrontendIdentity, NodeId, Provenance, SourceContent, SourceDocument, SourceId,
    SourceOrigin, SourceSpan,
};
use crate::validation::{Validate, ValidationErrors};

pub const FRONTEND_ID: &str = "strling.semantic";
pub const DIALECT_VERSION: &str = "1.0.0";
pub const SOURCE_EDITION: &str = "1.0";
pub const MEDIA_TYPE: &str = "text/x-strling-semantic";
pub const MAX_SOURCE_BYTES: usize = 1_048_576;
pub const MAX_NESTING_DEPTH: usize = 128;
pub const MAX_MATERIAL_NODES: usize = 65_535;
pub const MAX_CAPTURES: usize = 16_384;
pub const MAX_SET_MEMBERS: usize = 65_535;
pub const MAX_IDENTIFIER_BYTES: usize = 64;
pub const MAX_INTEGER: u64 = 4_294_967_295;

const RESERVED_WORDS: &[&str] = &[
    "any",
    "at",
    "before",
    "capture",
    "case",
    "character",
    "choice",
    "empty",
    "if",
    "not",
    "pattern",
    "repeat",
    "same",
    "semantic",
    "sequence",
    "text",
    "unless",
    "without",
];

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum SemanticFrontendErrorCode {
    InvalidHeader,
    UnsupportedVersion,
    MissingCaseDeclaration,
    DuplicateTopLevel,
    UnexpectedToken,
    MissingDelimiter,
    InvalidIdentifier,
    ReservedIdentifier,
    InvalidEscape,
    UnterminatedString,
    InvalidUnicodeScalar,
    InvalidInteger,
    ResourceLimit,
    EmptyText,
    InvalidSetScalar,
    InvalidRange,
    InvalidRepeatBounds,
    InsufficientChildren,
    EmptyCharacterSet,
    DuplicateCapture,
    UnresolvedCapture,
    ReferenceBeforeCapture,
    UnsupportedTargetAnnotation,
    UnsupportedModuleImport,
    UnsupportedPolicyDirective,
    UnsupportedRegexSyntax,
    UnsupportedNumericReference,
}

impl SemanticFrontendErrorCode {
    #[must_use]
    pub const fn id(self) -> &'static str {
        match self {
            Self::InvalidHeader => "STRL-DSL-1001",
            Self::UnsupportedVersion => "STRL-DSL-1002",
            Self::MissingCaseDeclaration => "STRL-DSL-1003",
            Self::DuplicateTopLevel => "STRL-DSL-1004",
            Self::UnexpectedToken => "STRL-DSL-1005",
            Self::MissingDelimiter => "STRL-DSL-1006",
            Self::InvalidIdentifier => "STRL-DSL-1007",
            Self::ReservedIdentifier => "STRL-DSL-1008",
            Self::InvalidEscape => "STRL-DSL-1009",
            Self::UnterminatedString => "STRL-DSL-1010",
            Self::InvalidUnicodeScalar => "STRL-DSL-1011",
            Self::InvalidInteger => "STRL-DSL-1012",
            Self::ResourceLimit => "STRL-DSL-1013",
            Self::EmptyText => "STRL-DSL-2001",
            Self::InvalidSetScalar => "STRL-DSL-2002",
            Self::InvalidRange => "STRL-DSL-2003",
            Self::InvalidRepeatBounds => "STRL-DSL-2004",
            Self::InsufficientChildren => "STRL-DSL-2005",
            Self::EmptyCharacterSet => "STRL-DSL-2006",
            Self::DuplicateCapture => "STRL-DSL-2007",
            Self::UnresolvedCapture => "STRL-DSL-2008",
            Self::ReferenceBeforeCapture => "STRL-DSL-2009",
            Self::UnsupportedTargetAnnotation => "STRL-DSL-3001",
            Self::UnsupportedModuleImport => "STRL-DSL-3002",
            Self::UnsupportedPolicyDirective => "STRL-DSL-3003",
            Self::UnsupportedRegexSyntax => "STRL-DSL-3004",
            Self::UnsupportedNumericReference => "STRL-DSL-3005",
        }
    }

    #[must_use]
    pub const fn message(self) -> &'static str {
        match self {
            Self::InvalidHeader => "source must begin with the exact Semantic STRling header",
            Self::UnsupportedVersion => "source selects an unsupported Semantic STRling edition",
            Self::MissingCaseDeclaration => {
                "source requires exactly one case declaration before pattern"
            }
            Self::DuplicateTopLevel => "source contains more than one top-level pattern",
            Self::UnexpectedToken => "token cannot begin the required production",
            Self::MissingDelimiter => "required source delimiter is missing",
            Self::InvalidIdentifier => "capture identifier is not lowercase ASCII snake form",
            Self::ReservedIdentifier => "capture identifier is reserved by Semantic STRling 1.0",
            Self::InvalidEscape => "string escape is outside the Semantic STRling 1.0 set",
            Self::UnterminatedString => "string reaches a line ending or end of input",
            Self::InvalidUnicodeScalar => "string escape does not encode a Unicode scalar",
            Self::InvalidInteger => "integer is malformed or exceeds the Semantic STRling limit",
            Self::ResourceLimit => "source exceeds a Semantic STRling frontend resource limit",
            Self::EmptyText => "semantic text value must not be empty",
            Self::InvalidSetScalar => "character-set scalar must contain exactly one scalar",
            Self::InvalidRange => "character range start must not exceed its end",
            Self::InvalidRepeatBounds => "finite repetition maximum is less than its minimum",
            Self::InsufficientChildren => "sequence and choice require at least two children",
            Self::EmptyCharacterSet => "character set requires at least one member",
            Self::DuplicateCapture => "capture name duplicates an earlier declaration",
            Self::UnresolvedCapture => "reference names no capture declaration",
            Self::ReferenceBeforeCapture => {
                "reference must follow the completed capture declaration it names"
            }
            Self::UnsupportedTargetAnnotation => "target selection is not Semantic STRling syntax",
            Self::UnsupportedModuleImport => "module and import syntax is unavailable",
            Self::UnsupportedPolicyDirective => "source policy directives are unavailable",
            Self::UnsupportedRegexSyntax => "raw regex syntax is unavailable",
            Self::UnsupportedNumericReference => "numeric capture identities are unavailable",
        }
    }

    #[must_use]
    pub const fn phase(self) -> CompilerPhase {
        match self {
            Self::EmptyText
            | Self::InvalidSetScalar
            | Self::InvalidRange
            | Self::InvalidRepeatBounds
            | Self::InsufficientChildren
            | Self::EmptyCharacterSet
            | Self::DuplicateCapture
            | Self::UnresolvedCapture
            | Self::ReferenceBeforeCapture => CompilerPhase::SemanticLowering,
            _ => CompilerPhase::FrontendParse,
        }
    }

    #[must_use]
    pub const fn category(self) -> DiagnosticCategory {
        match self {
            Self::ResourceLimit => DiagnosticCategory::ResourceLimit,
            Self::EmptyText
            | Self::InvalidSetScalar
            | Self::InvalidRange
            | Self::InvalidRepeatBounds
            | Self::InsufficientChildren
            | Self::EmptyCharacterSet
            | Self::DuplicateCapture
            | Self::UnresolvedCapture
            | Self::ReferenceBeforeCapture => DiagnosticCategory::SemanticValidity,
            _ => DiagnosticCategory::Syntax,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SemanticFrontendError {
    pub code: SemanticFrontendErrorCode,
    pub byte_offset: u64,
    pub diagnostic: Diagnostic,
    pub frontend: FrontendIdentity,
    pub source_provenance: Provenance,
}

impl fmt::Display for SemanticFrontendError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "{} at byte {}: {}",
            self.code.id(),
            self.byte_offset,
            self.code.message()
        )
    }
}

impl Error for SemanticFrontendError {}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum SemanticFrontendFailure {
    Diagnostic(Box<SemanticFrontendError>),
    InvalidSource(ValidationErrors),
    ReferencedSourceUnavailable,
    InvalidSemanticOutput(NormalizationErrors),
}

impl SemanticFrontendFailure {
    #[must_use]
    pub fn diagnostic(&self) -> Option<&SemanticFrontendError> {
        match self {
            Self::Diagnostic(error) => Some(error.as_ref()),
            Self::InvalidSource(_)
            | Self::ReferencedSourceUnavailable
            | Self::InvalidSemanticOutput(_) => None,
        }
    }
}

impl fmt::Display for SemanticFrontendFailure {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Diagnostic(error) => error.fmt(formatter),
            Self::InvalidSource(errors) => {
                write!(formatter, "source contract is invalid: {errors}")
            }
            Self::ReferencedSourceUnavailable => formatter
                .write_str("referenced source content must be resolved before frontend parsing"),
            Self::InvalidSemanticOutput(errors) => {
                write!(formatter, "frontend produced invalid Semantic IR: {errors}")
            }
        }
    }
}

impl Error for SemanticFrontendFailure {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Diagnostic(error) => Some(error.as_ref()),
            Self::InvalidSource(errors) => Some(errors),
            Self::InvalidSemanticOutput(errors) => Some(errors),
            Self::ReferencedSourceUnavailable => None,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct RawError {
    code: SemanticFrontendErrorCode,
    byte_offset: usize,
}

impl RawError {
    fn new(code: SemanticFrontendErrorCode, byte_offset: usize) -> Self {
        Self { code, byte_offset }
    }

    fn attach(self, document: &SourceDocument, text: &str) -> SemanticFrontendError {
        let diagnostic = Diagnostic {
            contract_version: document.contract_version,
            occurrence: DiagnosticOccurrence::new(0),
            code: DiagnosticCode::try_from(self.code.id())
                .expect("frozen Semantic STRling diagnostic identity is valid"),
            severity: Severity::Error,
            severity_basis: SeverityBasis::Normative,
            phase: self.code.phase(),
            category: self.code.category(),
            message: self.code.message().to_owned(),
            primary_location: Some(source_span_at(&document.source_id, text, self.byte_offset)),
            related_locations: None,
            advice: None,
            fixes: None,
        };
        diagnostic
            .validate()
            .expect("constructed Semantic STRling diagnostic is valid");
        SemanticFrontendError {
            code: self.code,
            byte_offset: self.byte_offset as u64,
            diagnostic,
            frontend: document.frontend.clone(),
            source_provenance: document.provenance.clone(),
        }
    }
}

fn source_span_at(source_id: &SourceId, text: &str, byte_offset: usize) -> SourceSpan {
    let mut start = byte_offset.min(text.len());
    while start > 0 && !text.is_char_boundary(start) {
        start -= 1;
    }
    let end = text[start..]
        .chars()
        .next()
        .map_or(start, |character| start + character.len_utf8());
    SourceSpan::new(source_id.clone(), start as u64, end as u64)
        .expect("parser diagnostic offsets form a valid span")
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct ByteSpan {
    start: usize,
    end: usize,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct SyntaxString {
    value: String,
    span: ByteSpan,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct SyntaxIdentifier {
    value: String,
    span: ByteSpan,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct SyntaxComment {
    start: usize,
    text: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct SyntaxDocument {
    header_start: usize,
    case_start: usize,
    pattern_start: usize,
    case_matching: CaseMatching,
    root: SyntaxNode,
    comments: Vec<SyntaxComment>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct SyntaxNode {
    span: ByteSpan,
    kind: SyntaxNodeKind,
}

#[derive(Clone, Debug, Eq, PartialEq)]
enum SyntaxNodeKind {
    Empty,
    Sequence(Vec<SyntaxNode>),
    Alternation(Vec<SyntaxNode>),
    Literal(SyntaxString),
    Wildcard(LineTerminators),
    CharacterSet {
        negated: bool,
        members: Vec<SyntaxSetMember>,
    },
    Repeat {
        min: u64,
        min_span: ByteSpan,
        max: RepetitionMaximum,
        mode: RepetitionMode,
        body: Box<SyntaxNode>,
    },
    Position(PositionKind),
    Capture {
        name: SyntaxIdentifier,
        body: Box<SyntaxNode>,
    },
    Backreference(SyntaxIdentifier),
    Lookaround {
        direction: LookaroundDirection,
        polarity: AssertionPolarity,
        body: Box<SyntaxNode>,
    },
    Atomic(Box<SyntaxNode>),
}

#[derive(Clone, Debug, Eq, PartialEq)]
enum SyntaxSetMember {
    Literal {
        source_start: usize,
        value: SyntaxString,
    },
    Range {
        source_start: usize,
        start: SyntaxString,
        end: SyntaxString,
    },
    Builtin {
        source_start: usize,
        name: BuiltinClassName,
        domain: CharacterDomain,
        negated: bool,
    },
    UnicodeProperty {
        source_start: usize,
        property: SyntaxString,
        value: Option<SyntaxString>,
        negated: bool,
    },
}

#[derive(Clone, Debug, Eq, PartialEq)]
enum TokenKind {
    Word(String),
    Number(String),
    String(String),
    LeftBrace,
    RightBrace,
    Semicolon,
    Symbol(char),
    Eof,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct Token {
    kind: TokenKind,
    start: usize,
    end: usize,
    separated: bool,
}

struct Lexer<'a> {
    text: &'a str,
    position: usize,
    comments: Vec<SyntaxComment>,
}

impl<'a> Lexer<'a> {
    fn new(text: &'a str) -> Self {
        Self {
            text,
            position: 0,
            comments: Vec::new(),
        }
    }

    fn next_token(&mut self) -> Result<Token, RawError> {
        let separated = self.skip_layout();
        let start = self.position;
        let Some(character) = self.peek_char() else {
            return Ok(Token {
                kind: TokenKind::Eof,
                start,
                end: start,
                separated,
            });
        };
        let kind = match character {
            '{' => {
                self.position += 1;
                TokenKind::LeftBrace
            }
            '}' => {
                self.position += 1;
                TokenKind::RightBrace
            }
            ';' => {
                self.position += 1;
                TokenKind::Semicolon
            }
            '"' => return self.lex_string(separated),
            value if value.is_ascii_digit() => {
                self.advance_while(|next| next.is_ascii_digit() || next == '.');
                TokenKind::Number(self.text[start..self.position].to_owned())
            }
            value if value.is_alphabetic() || value == '_' => {
                self.advance_while(|next| next.is_alphanumeric() || next == '_');
                TokenKind::Word(self.text[start..self.position].to_owned())
            }
            value => {
                self.position += value.len_utf8();
                TokenKind::Symbol(value)
            }
        };
        Ok(Token {
            kind,
            start,
            end: self.position,
            separated,
        })
    }

    fn skip_layout(&mut self) -> bool {
        let start = self.position;
        loop {
            self.advance_while(|character| matches!(character, ' ' | '\t' | '\r' | '\n'));
            if self.peek_char() != Some('#') {
                break;
            }
            let comment_start = self.position;
            self.position += 1;
            let text_start = self.position;
            self.advance_while(|character| !matches!(character, '\r' | '\n'));
            let text = self.text[text_start..self.position].to_owned();
            self.comments.push(SyntaxComment {
                start: comment_start,
                text,
            });
            if self.text[self.position..].starts_with("\r\n") {
                self.position += 2;
            } else if matches!(self.peek_char(), Some('\r' | '\n')) {
                self.position += 1;
            }
        }
        self.position != start
    }

    fn lex_string(&mut self, separated: bool) -> Result<Token, RawError> {
        let start = self.position;
        self.position += 1;
        let mut value = String::new();
        loop {
            let Some(character) = self.peek_char() else {
                return Err(RawError::new(
                    SemanticFrontendErrorCode::UnterminatedString,
                    start.saturating_add(1),
                ));
            };
            match character {
                '"' => {
                    self.position += 1;
                    return Ok(Token {
                        kind: TokenKind::String(value),
                        start,
                        end: self.position,
                        separated,
                    });
                }
                '\r' | '\n' => {
                    return Err(RawError::new(
                        SemanticFrontendErrorCode::UnterminatedString,
                        start.saturating_add(1),
                    ));
                }
                '\\' => {
                    let escape_start = self.position;
                    self.position += 1;
                    let Some(escape) = self.peek_char() else {
                        return Err(RawError::new(
                            SemanticFrontendErrorCode::UnterminatedString,
                            start.saturating_add(1),
                        ));
                    };
                    self.position += escape.len_utf8();
                    match escape {
                        '"' => value.push('"'),
                        '\\' => value.push('\\'),
                        'b' => value.push('\u{0008}'),
                        'f' => value.push('\u{000c}'),
                        'n' => value.push('\n'),
                        'r' => value.push('\r'),
                        't' => value.push('\t'),
                        '0' => value.push('\0'),
                        'u' => value.push(self.lex_unicode_escape(escape_start)?),
                        _ => {
                            return Err(RawError::new(
                                SemanticFrontendErrorCode::InvalidEscape,
                                escape_start,
                            ))
                        }
                    }
                }
                value_char if value_char <= '\u{001f}' => {
                    return Err(RawError::new(
                        SemanticFrontendErrorCode::InvalidUnicodeScalar,
                        self.position,
                    ));
                }
                value_char => {
                    value.push(value_char);
                    self.position += value_char.len_utf8();
                }
            }
        }
    }

    fn lex_unicode_escape(&mut self, escape_start: usize) -> Result<char, RawError> {
        if self.peek_char() != Some('{') {
            return Err(RawError::new(
                SemanticFrontendErrorCode::InvalidEscape,
                escape_start,
            ));
        }
        self.position += 1;
        let digits_start = self.position;
        self.advance_while(|character| character.is_ascii_hexdigit());
        let digits = &self.text[digits_start..self.position];
        if digits.is_empty() || digits.len() > 6 || self.peek_char() != Some('}') {
            return Err(RawError::new(
                SemanticFrontendErrorCode::InvalidEscape,
                escape_start,
            ));
        }
        self.position += 1;
        let scalar = u32::from_str_radix(digits, 16).map_err(|_| {
            RawError::new(
                SemanticFrontendErrorCode::InvalidUnicodeScalar,
                escape_start,
            )
        })?;
        char::from_u32(scalar).ok_or_else(|| {
            RawError::new(
                SemanticFrontendErrorCode::InvalidUnicodeScalar,
                escape_start,
            )
        })
    }

    fn peek_char(&self) -> Option<char> {
        self.text[self.position..].chars().next()
    }

    fn advance_while(&mut self, predicate: impl Fn(char) -> bool) {
        while let Some(character) = self.peek_char() {
            if !predicate(character) {
                break;
            }
            self.position += character.len_utf8();
        }
    }
}

struct Parser<'a> {
    lexer: Lexer<'a>,
    current: Token,
    material_nodes: usize,
    captures: usize,
}

impl<'a> Parser<'a> {
    fn new(text: &'a str) -> Result<Self, RawError> {
        let mut lexer = Lexer::new(text);
        let current = lexer.next_token()?;
        Ok(Self {
            lexer,
            current,
            material_nodes: 0,
            captures: 0,
        })
    }

    fn parse(mut self) -> Result<SyntaxDocument, RawError> {
        let header_start = self.parse_header()?;
        let (case_start, case_matching) = self.parse_case_declaration()?;
        if self.word_is("case") {
            return Err(RawError::new(
                SemanticFrontendErrorCode::MissingCaseDeclaration,
                self.current.start,
            ));
        }
        if !self.word_is("pattern") {
            return Err(RawError::new(
                unsupported_code(&self.current)
                    .unwrap_or(SemanticFrontendErrorCode::UnexpectedToken),
                self.current.start,
            ));
        }
        let pattern_start = self.bump()?.start;
        self.require_layout(SemanticFrontendErrorCode::UnexpectedToken)?;
        let root = self.parse_node(1)?;
        if !matches!(self.current.kind, TokenKind::Eof) {
            let code = if self.word_is("case") {
                SemanticFrontendErrorCode::MissingCaseDeclaration
            } else {
                SemanticFrontendErrorCode::DuplicateTopLevel
            };
            return Err(RawError::new(code, self.current.start));
        }
        validate_semantics(&root)?;
        Ok(SyntaxDocument {
            header_start,
            case_start,
            pattern_start,
            case_matching,
            root,
            comments: self.lexer.comments,
        })
    }

    fn parse_header(&mut self) -> Result<usize, RawError> {
        let header_start = self.current.start;
        if !self.word_is("semantic") {
            return Err(RawError::new(SemanticFrontendErrorCode::InvalidHeader, 0));
        }
        self.bump()?;
        if !self.current.separated || !self.word_is("strling") {
            return Err(RawError::new(SemanticFrontendErrorCode::InvalidHeader, 0));
        }
        self.bump()?;
        if !self.current.separated {
            return Err(RawError::new(SemanticFrontendErrorCode::InvalidHeader, 0));
        }
        match &self.current.kind {
            TokenKind::Number(version) if version == SOURCE_EDITION => {
                self.bump()?;
            }
            TokenKind::Number(_) => {
                return Err(RawError::new(
                    SemanticFrontendErrorCode::UnsupportedVersion,
                    self.current.start,
                ))
            }
            _ => return Err(RawError::new(SemanticFrontendErrorCode::InvalidHeader, 0)),
        }
        self.expect_semicolon()?;
        Ok(header_start)
    }

    fn parse_case_declaration(&mut self) -> Result<(usize, CaseMatching), RawError> {
        if !self.word_is("case") {
            return Err(RawError::new(
                SemanticFrontendErrorCode::MissingCaseDeclaration,
                self.current.start,
            ));
        }
        let start = self.bump()?.start;
        self.require_layout(SemanticFrontendErrorCode::MissingCaseDeclaration)?;
        let case_matching = if self.word_is("sensitive") {
            CaseMatching::Sensitive
        } else if self.word_is("insensitive") {
            CaseMatching::Insensitive
        } else {
            return Err(RawError::new(
                SemanticFrontendErrorCode::MissingCaseDeclaration,
                self.current.start,
            ));
        };
        self.bump()?;
        self.expect_semicolon()?;
        Ok((start, case_matching))
    }

    fn parse_node(&mut self, depth: usize) -> Result<SyntaxNode, RawError> {
        if depth > MAX_NESTING_DEPTH {
            return Err(RawError::new(
                SemanticFrontendErrorCode::ResourceLimit,
                self.current.start,
            ));
        }
        self.material_nodes += 1;
        if self.material_nodes > MAX_MATERIAL_NODES {
            return Err(RawError::new(
                SemanticFrontendErrorCode::ResourceLimit,
                self.current.start,
            ));
        }
        let start = self.current.start;
        match self.current_word() {
            Some("empty") => self.parse_empty(start),
            Some("sequence") => self.parse_composition(start, depth, true),
            Some("choice") => self.parse_composition(start, depth, false),
            Some("text") => self.parse_text(start),
            Some("any") => self.parse_wildcard(start),
            Some("character") => self.parse_character_set(start, depth),
            Some("repeat") => self.parse_repeat(start, depth),
            Some("at") | Some("not") | Some("before") => self.parse_position(start),
            Some("capture") => self.parse_capture(start, depth),
            Some("same") => self.parse_reference(start),
            Some("if") | Some("unless") => self.parse_lookaround(start, depth),
            Some("without") => self.parse_atomic(start, depth),
            _ => {
                let code = unsupported_code(&self.current)
                    .unwrap_or(SemanticFrontendErrorCode::UnexpectedToken);
                let offset = if code == SemanticFrontendErrorCode::UnexpectedToken {
                    start.saturating_add(1)
                } else {
                    start
                };
                Err(RawError::new(code, offset))
            }
        }
    }

    fn parse_empty(&mut self, start: usize) -> Result<SyntaxNode, RawError> {
        self.bump()?;
        let end = self.expect_semicolon()?.end;
        Ok(SyntaxNode {
            span: ByteSpan { start, end },
            kind: SyntaxNodeKind::Empty,
        })
    }

    fn parse_composition(
        &mut self,
        start: usize,
        depth: usize,
        sequence: bool,
    ) -> Result<SyntaxNode, RawError> {
        self.bump()?;
        self.expect_left_brace()?;
        let mut children = Vec::new();
        while !matches!(self.current.kind, TokenKind::RightBrace) {
            if matches!(self.current.kind, TokenKind::Eof) {
                return Err(RawError::new(
                    SemanticFrontendErrorCode::MissingDelimiter,
                    self.current.start,
                ));
            }
            if !children.is_empty() {
                self.require_layout(SemanticFrontendErrorCode::UnexpectedToken)?;
            }
            children.push(self.parse_node(depth + 1)?);
        }
        let end = self.bump()?.end;
        Ok(SyntaxNode {
            span: ByteSpan { start, end },
            kind: if sequence {
                SyntaxNodeKind::Sequence(children)
            } else {
                SyntaxNodeKind::Alternation(children)
            },
        })
    }

    fn parse_text(&mut self, start: usize) -> Result<SyntaxNode, RawError> {
        self.bump()?;
        self.require_layout(SemanticFrontendErrorCode::UnexpectedToken)?;
        let text = self.parse_string()?;
        let end = self.expect_semicolon()?.end;
        Ok(SyntaxNode {
            span: ByteSpan { start, end },
            kind: SyntaxNodeKind::Literal(text),
        })
    }

    fn parse_wildcard(&mut self, start: usize) -> Result<SyntaxNode, RawError> {
        self.bump()?;
        self.expect_word("character", true)?;
        let line_terminators = if self.word_is("including") {
            self.bump()?;
            LineTerminators::Include
        } else if self.word_is("excluding") {
            self.bump()?;
            LineTerminators::Exclude
        } else {
            return Err(RawError::new(
                SemanticFrontendErrorCode::UnexpectedToken,
                self.current.start,
            ));
        };
        self.expect_word("line", true)?;
        self.expect_word("terminators", true)?;
        let end = self.expect_semicolon()?.end;
        Ok(SyntaxNode {
            span: ByteSpan { start, end },
            kind: SyntaxNodeKind::Wildcard(line_terminators),
        })
    }

    fn parse_character_set(&mut self, start: usize, _depth: usize) -> Result<SyntaxNode, RawError> {
        self.bump()?;
        self.require_layout(SemanticFrontendErrorCode::UnexpectedToken)?;
        let negated = if self.word_is("from") {
            self.bump()?;
            false
        } else if self.word_is("except") {
            self.bump()?;
            true
        } else {
            return Err(RawError::new(
                SemanticFrontendErrorCode::UnexpectedToken,
                self.current.start,
            ));
        };
        self.expect_left_brace()?;
        let mut members = Vec::new();
        while !matches!(self.current.kind, TokenKind::RightBrace) {
            if matches!(self.current.kind, TokenKind::Eof) {
                return Err(RawError::new(
                    SemanticFrontendErrorCode::MissingDelimiter,
                    self.current.start,
                ));
            }
            if !members.is_empty() {
                self.require_layout(SemanticFrontendErrorCode::UnexpectedToken)?;
            }
            if members.len() >= MAX_SET_MEMBERS {
                return Err(RawError::new(
                    SemanticFrontendErrorCode::ResourceLimit,
                    self.current.start,
                ));
            }
            members.push(self.parse_set_member()?);
        }
        let end = self.bump()?.end;
        Ok(SyntaxNode {
            span: ByteSpan { start, end },
            kind: SyntaxNodeKind::CharacterSet { negated, members },
        })
    }

    fn parse_set_member(&mut self) -> Result<SyntaxSetMember, RawError> {
        let source_start = self.current.start;
        let negated = if self.word_is("not") {
            self.bump()?;
            self.require_layout(SemanticFrontendErrorCode::UnexpectedToken)?;
            true
        } else {
            false
        };
        if self.word_is("scalar") {
            if negated {
                return Err(RawError::new(
                    SemanticFrontendErrorCode::UnexpectedToken,
                    self.current.start,
                ));
            }
            self.bump()?;
            self.require_layout(SemanticFrontendErrorCode::UnexpectedToken)?;
            let value = self.parse_string()?;
            self.expect_semicolon()?;
            return Ok(SyntaxSetMember::Literal {
                source_start,
                value,
            });
        }
        if self.word_is("range") {
            if negated {
                return Err(RawError::new(
                    SemanticFrontendErrorCode::UnexpectedToken,
                    self.current.start,
                ));
            }
            self.bump()?;
            self.require_layout(SemanticFrontendErrorCode::UnexpectedToken)?;
            let start = self.parse_string()?;
            self.expect_word("through", true)?;
            let end = self.parse_string_required()?;
            self.expect_semicolon()?;
            return Ok(SyntaxSetMember::Range {
                source_start,
                start,
                end,
            });
        }
        if self.word_is("property") {
            self.bump()?;
            self.require_layout(SemanticFrontendErrorCode::UnexpectedToken)?;
            let property = self.parse_string()?;
            let value = if self.word_is("value") {
                self.bump()?;
                Some(self.parse_string_required()?)
            } else {
                None
            };
            self.expect_semicolon()?;
            return Ok(SyntaxSetMember::UnicodeProperty {
                source_start,
                property,
                value,
                negated,
            });
        }
        let domain = if self.word_is("ascii") {
            self.bump()?;
            CharacterDomain::Ascii
        } else if self.word_is("unicode") {
            self.bump()?;
            CharacterDomain::Unicode
        } else {
            return Err(RawError::new(
                SemanticFrontendErrorCode::UnexpectedToken,
                self.current.start,
            ));
        };
        self.require_layout(SemanticFrontendErrorCode::UnexpectedToken)?;
        let name = if self.word_is("digit") {
            BuiltinClassName::Digit
        } else if self.word_is("word") {
            BuiltinClassName::Word
        } else if self.word_is("whitespace") {
            BuiltinClassName::Whitespace
        } else {
            return Err(RawError::new(
                SemanticFrontendErrorCode::UnexpectedToken,
                self.current.start,
            ));
        };
        self.bump()?;
        self.expect_semicolon()?;
        Ok(SyntaxSetMember::Builtin {
            source_start,
            name,
            domain,
            negated,
        })
    }

    fn parse_repeat(&mut self, start: usize, depth: usize) -> Result<SyntaxNode, RawError> {
        self.bump()?;
        self.expect_word("from", true)?;
        let (min, min_span) = self.parse_integer_required()?;
        self.expect_word("to", true)?;
        self.require_layout(SemanticFrontendErrorCode::InvalidInteger)?;
        let max = if self.word_is("unbounded") {
            self.bump()?;
            RepetitionMaximum::Unbounded
        } else {
            let (maximum, _) = self.parse_integer()?;
            RepetitionMaximum::Bounded(maximum)
        };
        self.expect_word("using", true)?;
        self.require_layout(SemanticFrontendErrorCode::UnexpectedToken)?;
        let mode = if self.word_is("greedy") {
            RepetitionMode::Greedy
        } else if self.word_is("lazy") {
            RepetitionMode::Lazy
        } else if self.word_is("possessive") {
            RepetitionMode::Possessive
        } else {
            return Err(RawError::new(
                SemanticFrontendErrorCode::UnexpectedToken,
                self.current.start,
            ));
        };
        self.bump()?;
        self.expect_left_brace()?;
        let body = self.parse_node(depth + 1)?;
        let end = self.expect_right_brace()?.end;
        Ok(SyntaxNode {
            span: ByteSpan { start, end },
            kind: SyntaxNodeKind::Repeat {
                min,
                min_span,
                max,
                mode,
                body: Box::new(body),
            },
        })
    }

    fn parse_position(&mut self, start: usize) -> Result<SyntaxNode, RawError> {
        let position = if self.word_is("not") {
            self.bump()?;
            self.expect_word("at", true)?;
            self.expect_word("word", true)?;
            self.expect_word("boundary", true)?;
            PositionKind::NotWordBoundary
        } else if self.word_is("before") {
            self.bump()?;
            self.expect_word("final", true)?;
            self.expect_word("line", true)?;
            self.expect_word("terminator", true)?;
            PositionKind::EndBeforeFinalLineTerminator
        } else {
            self.bump()?;
            self.require_layout(SemanticFrontendErrorCode::UnexpectedToken)?;
            if self.word_is("input") {
                self.bump()?;
                self.require_layout(SemanticFrontendErrorCode::UnexpectedToken)?;
                if self.word_is("start") {
                    self.bump()?;
                    PositionKind::InputStart
                } else if self.word_is("end") {
                    self.bump()?;
                    PositionKind::InputEnd
                } else {
                    return Err(RawError::new(
                        SemanticFrontendErrorCode::UnexpectedToken,
                        self.current.start,
                    ));
                }
            } else if self.word_is("line") {
                self.bump()?;
                self.require_layout(SemanticFrontendErrorCode::UnexpectedToken)?;
                if self.word_is("start") {
                    self.bump()?;
                    PositionKind::LineStart
                } else if self.word_is("end") {
                    self.bump()?;
                    PositionKind::LineEnd
                } else {
                    return Err(RawError::new(
                        SemanticFrontendErrorCode::UnexpectedToken,
                        self.current.start,
                    ));
                }
            } else if self.word_is("word") {
                self.bump()?;
                self.expect_word("boundary", true)?;
                PositionKind::WordBoundary
            } else {
                return Err(RawError::new(
                    SemanticFrontendErrorCode::UnexpectedToken,
                    self.current.start,
                ));
            }
        };
        let end = self.expect_semicolon()?.end;
        Ok(SyntaxNode {
            span: ByteSpan { start, end },
            kind: SyntaxNodeKind::Position(position),
        })
    }

    fn parse_capture(&mut self, start: usize, depth: usize) -> Result<SyntaxNode, RawError> {
        self.bump()?;
        self.require_layout(SemanticFrontendErrorCode::InvalidIdentifier)?;
        let name = self.parse_identifier()?;
        self.captures += 1;
        if self.captures > MAX_CAPTURES {
            return Err(RawError::new(
                SemanticFrontendErrorCode::ResourceLimit,
                name.span.start,
            ));
        }
        self.expect_left_brace()?;
        let body = self.parse_node(depth + 1)?;
        let end = self.expect_right_brace()?.end;
        Ok(SyntaxNode {
            span: ByteSpan { start, end },
            kind: SyntaxNodeKind::Capture {
                name,
                body: Box::new(body),
            },
        })
    }

    fn parse_reference(&mut self, start: usize) -> Result<SyntaxNode, RawError> {
        self.bump()?;
        self.expect_word("text", true)?;
        self.expect_word("as", true)?;
        self.require_layout(SemanticFrontendErrorCode::InvalidIdentifier)?;
        let name = self.parse_identifier()?;
        let end = self.expect_semicolon()?.end;
        Ok(SyntaxNode {
            span: ByteSpan { start, end },
            kind: SyntaxNodeKind::Backreference(name),
        })
    }

    fn parse_lookaround(&mut self, start: usize, depth: usize) -> Result<SyntaxNode, RawError> {
        let polarity = if self.word_is("if") {
            AssertionPolarity::Positive
        } else {
            AssertionPolarity::Negative
        };
        self.bump()?;
        self.require_layout(SemanticFrontendErrorCode::UnexpectedToken)?;
        let direction = if self.word_is("followed") {
            self.bump()?;
            LookaroundDirection::Ahead
        } else if self.word_is("preceded") {
            self.bump()?;
            LookaroundDirection::Behind
        } else {
            return Err(RawError::new(
                SemanticFrontendErrorCode::UnexpectedToken,
                self.current.start,
            ));
        };
        self.expect_word("by", true)?;
        self.expect_left_brace()?;
        let body = self.parse_node(depth + 1)?;
        let end = self.expect_right_brace()?.end;
        Ok(SyntaxNode {
            span: ByteSpan { start, end },
            kind: SyntaxNodeKind::Lookaround {
                direction,
                polarity,
                body: Box::new(body),
            },
        })
    }

    fn parse_atomic(&mut self, start: usize, depth: usize) -> Result<SyntaxNode, RawError> {
        self.bump()?;
        self.expect_word("backtracking", true)?;
        self.expect_left_brace()?;
        let body = self.parse_node(depth + 1)?;
        let end = self.expect_right_brace()?.end;
        Ok(SyntaxNode {
            span: ByteSpan { start, end },
            kind: SyntaxNodeKind::Atomic(Box::new(body)),
        })
    }

    fn parse_identifier(&mut self) -> Result<SyntaxIdentifier, RawError> {
        let token = self.current.clone();
        let TokenKind::Word(value) = &token.kind else {
            let (code, offset) = if matches!(token.kind, TokenKind::Number(_)) {
                (
                    SemanticFrontendErrorCode::UnsupportedNumericReference,
                    token.start.saturating_sub(1),
                )
            } else {
                (SemanticFrontendErrorCode::InvalidIdentifier, token.start)
            };
            return Err(RawError::new(code, offset));
        };
        if value.len() > MAX_IDENTIFIER_BYTES || !valid_identifier(value) {
            return Err(RawError::new(
                SemanticFrontendErrorCode::InvalidIdentifier,
                token.start,
            ));
        }
        if RESERVED_WORDS.binary_search(&value.as_str()).is_ok() {
            return Err(RawError::new(
                SemanticFrontendErrorCode::ReservedIdentifier,
                token.start,
            ));
        }
        self.bump()?;
        Ok(SyntaxIdentifier {
            value: value.clone(),
            span: ByteSpan {
                start: token.start,
                end: token.end,
            },
        })
    }

    fn parse_string(&mut self) -> Result<SyntaxString, RawError> {
        let token = self.current.clone();
        let TokenKind::String(value) = &token.kind else {
            return Err(RawError::new(
                SemanticFrontendErrorCode::UnexpectedToken,
                token.start,
            ));
        };
        self.bump()?;
        Ok(SyntaxString {
            value: value.clone(),
            span: ByteSpan {
                start: token.start,
                end: token.end,
            },
        })
    }

    fn parse_string_required(&mut self) -> Result<SyntaxString, RawError> {
        self.require_layout(SemanticFrontendErrorCode::UnexpectedToken)?;
        self.parse_string()
    }

    fn parse_integer(&mut self) -> Result<(u64, ByteSpan), RawError> {
        let token = self.current.clone();
        let TokenKind::Number(value) = &token.kind else {
            return Err(RawError::new(
                SemanticFrontendErrorCode::InvalidInteger,
                token.start,
            ));
        };
        if value.len() > 1 && value.starts_with('0') {
            return Err(RawError::new(
                SemanticFrontendErrorCode::InvalidInteger,
                token.start + 1,
            ));
        }
        if value.is_empty() || !value.bytes().all(|byte| byte.is_ascii_digit()) {
            let offset = value
                .bytes()
                .position(|byte| !byte.is_ascii_digit())
                .map_or(token.start, |index| token.start + index);
            return Err(RawError::new(
                SemanticFrontendErrorCode::InvalidInteger,
                offset,
            ));
        }
        let integer = value
            .parse::<u64>()
            .map_err(|_| RawError::new(SemanticFrontendErrorCode::InvalidInteger, token.start))?;
        if integer > MAX_INTEGER {
            return Err(RawError::new(
                SemanticFrontendErrorCode::InvalidInteger,
                token.start,
            ));
        }
        self.bump()?;
        Ok((
            integer,
            ByteSpan {
                start: token.start,
                end: token.end,
            },
        ))
    }

    fn parse_integer_required(&mut self) -> Result<(u64, ByteSpan), RawError> {
        self.require_layout(SemanticFrontendErrorCode::InvalidInteger)?;
        self.parse_integer()
    }

    fn expect_word(&mut self, expected: &str, required_layout: bool) -> Result<Token, RawError> {
        if required_layout {
            self.require_layout(SemanticFrontendErrorCode::UnexpectedToken)?;
        }
        if !self.word_is(expected) {
            return Err(RawError::new(
                SemanticFrontendErrorCode::UnexpectedToken,
                self.current.start,
            ));
        }
        self.bump()
    }

    fn expect_left_brace(&mut self) -> Result<Token, RawError> {
        if !matches!(self.current.kind, TokenKind::LeftBrace) {
            return Err(RawError::new(
                SemanticFrontendErrorCode::MissingDelimiter,
                self.current.start,
            ));
        }
        self.bump()
    }

    fn expect_right_brace(&mut self) -> Result<Token, RawError> {
        if !matches!(self.current.kind, TokenKind::RightBrace) {
            return Err(RawError::new(
                SemanticFrontendErrorCode::MissingDelimiter,
                self.current.start,
            ));
        }
        self.bump()
    }

    fn expect_semicolon(&mut self) -> Result<Token, RawError> {
        if !matches!(self.current.kind, TokenKind::Semicolon) {
            return Err(RawError::new(
                SemanticFrontendErrorCode::MissingDelimiter,
                self.current.start,
            ));
        }
        self.bump()
    }

    fn require_layout(&self, code: SemanticFrontendErrorCode) -> Result<(), RawError> {
        if self.current.separated {
            Ok(())
        } else {
            Err(RawError::new(code, self.current.start))
        }
    }

    fn current_word(&self) -> Option<&str> {
        match &self.current.kind {
            TokenKind::Word(value) => Some(value),
            _ => None,
        }
    }

    fn word_is(&self, expected: &str) -> bool {
        self.current_word() == Some(expected)
    }

    fn bump(&mut self) -> Result<Token, RawError> {
        let next = self.lexer.next_token()?;
        Ok(std::mem::replace(&mut self.current, next))
    }
}

fn valid_identifier(value: &str) -> bool {
    let mut bytes = value.bytes();
    matches!(bytes.next(), Some(b'a'..=b'z'))
        && bytes.all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'_')
}

fn unsupported_code(token: &Token) -> Option<SemanticFrontendErrorCode> {
    match &token.kind {
        TokenKind::Word(value)
            if matches!(value.as_str(), "target" | "profile" | "engine" | "option") =>
        {
            Some(SemanticFrontendErrorCode::UnsupportedTargetAnnotation)
        }
        TokenKind::Word(value)
            if matches!(value.as_str(), "module" | "import" | "include" | "export") =>
        {
            Some(SemanticFrontendErrorCode::UnsupportedModuleImport)
        }
        TokenKind::Word(value)
            if matches!(
                value.as_str(),
                "portability"
                    | "portable"
                    | "require"
                    | "safety"
                    | "warning"
                    | "suppress"
                    | "suppression"
                    | "runtime"
            ) =>
        {
            Some(SemanticFrontendErrorCode::UnsupportedPolicyDirective)
        }
        TokenKind::Symbol(_) => Some(SemanticFrontendErrorCode::UnsupportedRegexSyntax),
        _ => None,
    }
}

fn validate_semantics(root: &SyntaxNode) -> Result<(), RawError> {
    fn collect_captures(node: &SyntaxNode, captures: &mut BTreeSet<String>) {
        match &node.kind {
            SyntaxNodeKind::Sequence(children) | SyntaxNodeKind::Alternation(children) => {
                for child in children {
                    collect_captures(child, captures);
                }
            }
            SyntaxNodeKind::Capture { name, body } => {
                captures.insert(name.value.clone());
                collect_captures(body, captures);
            }
            SyntaxNodeKind::Repeat { body, .. }
            | SyntaxNodeKind::Lookaround { body, .. }
            | SyntaxNodeKind::Atomic(body) => collect_captures(body, captures),
            SyntaxNodeKind::Empty
            | SyntaxNodeKind::Literal(_)
            | SyntaxNodeKind::Wildcard(_)
            | SyntaxNodeKind::CharacterSet { .. }
            | SyntaxNodeKind::Position(_)
            | SyntaxNodeKind::Backreference(_) => {}
        }
    }

    fn scalar(value: &SyntaxString) -> Result<char, RawError> {
        let mut characters = value.value.chars();
        match (characters.next(), characters.next()) {
            (Some(character), None) => Ok(character),
            _ => Err(RawError::new(
                SemanticFrontendErrorCode::InvalidSetScalar,
                value.span.start,
            )),
        }
    }

    fn visit(
        node: &SyntaxNode,
        all_captures: &BTreeSet<String>,
        completed: &mut BTreeSet<String>,
        active: &mut BTreeSet<String>,
        declared: &mut BTreeSet<String>,
    ) -> Result<(), RawError> {
        match &node.kind {
            SyntaxNodeKind::Empty | SyntaxNodeKind::Wildcard(_) | SyntaxNodeKind::Position(_) => {}
            SyntaxNodeKind::Literal(value) => {
                if value.value.is_empty() {
                    return Err(RawError::new(
                        SemanticFrontendErrorCode::EmptyText,
                        value.span.start,
                    ));
                }
            }
            SyntaxNodeKind::Sequence(children) | SyntaxNodeKind::Alternation(children) => {
                if children.len() < 2 {
                    let offset = children
                        .first()
                        .map_or(node.span.end.saturating_sub(1), |child| {
                            child.span.start.saturating_add(2)
                        });
                    return Err(RawError::new(
                        SemanticFrontendErrorCode::InsufficientChildren,
                        offset,
                    ));
                }
                for child in children {
                    visit(child, all_captures, completed, active, declared)?;
                }
            }
            SyntaxNodeKind::CharacterSet { members, .. } => {
                if members.is_empty() {
                    return Err(RawError::new(
                        SemanticFrontendErrorCode::EmptyCharacterSet,
                        node.span.end.saturating_sub(1),
                    ));
                }
                for member in members {
                    match member {
                        SyntaxSetMember::Literal { value, .. } => {
                            let _ = scalar(value).map_err(|_| {
                                RawError::new(
                                    SemanticFrontendErrorCode::InvalidSetScalar,
                                    node.span.end,
                                )
                            })?;
                        }
                        SyntaxSetMember::Range { start, end, .. } => {
                            let start_scalar = scalar(start)?;
                            let end_scalar = scalar(end)?;
                            if start_scalar > end_scalar {
                                return Err(RawError::new(
                                    SemanticFrontendErrorCode::InvalidRange,
                                    start.span.start.saturating_add(1),
                                ));
                            }
                        }
                        SyntaxSetMember::Builtin { .. } => {}
                        SyntaxSetMember::UnicodeProperty {
                            property, value, ..
                        } => {
                            if property.value.is_empty()
                                || value.as_ref().is_some_and(|item| item.value.is_empty())
                            {
                                return Err(RawError::new(
                                    SemanticFrontendErrorCode::EmptyText,
                                    property.span.start,
                                ));
                            }
                        }
                    }
                }
            }
            SyntaxNodeKind::Repeat {
                min,
                min_span,
                max,
                body,
                ..
            } => {
                if matches!(max, RepetitionMaximum::Bounded(maximum) if maximum < min) {
                    return Err(RawError::new(
                        SemanticFrontendErrorCode::InvalidRepeatBounds,
                        min_span.end,
                    ));
                }
                visit(body, all_captures, completed, active, declared)?;
            }
            SyntaxNodeKind::Capture { name, body } => {
                if !declared.insert(name.value.clone()) {
                    return Err(RawError::new(
                        SemanticFrontendErrorCode::DuplicateCapture,
                        node.span.start.saturating_sub(2),
                    ));
                }
                active.insert(name.value.clone());
                visit(body, all_captures, completed, active, declared)?;
                active.remove(&name.value);
                completed.insert(name.value.clone());
            }
            SyntaxNodeKind::Backreference(name) => {
                if completed.contains(&name.value) {
                    return Ok(());
                }
                let code = if active.contains(&name.value) || all_captures.contains(&name.value) {
                    SemanticFrontendErrorCode::ReferenceBeforeCapture
                } else {
                    SemanticFrontendErrorCode::UnresolvedCapture
                };
                let offset = if code == SemanticFrontendErrorCode::UnresolvedCapture {
                    node.span.start.saturating_add(1)
                } else {
                    node.span.start
                };
                return Err(RawError::new(code, offset));
            }
            SyntaxNodeKind::Lookaround { body, .. } | SyntaxNodeKind::Atomic(body) => {
                visit(body, all_captures, completed, active, declared)?;
            }
        }
        Ok(())
    }

    let mut all_captures = BTreeSet::new();
    collect_captures(root, &mut all_captures);
    visit(
        root,
        &all_captures,
        &mut BTreeSet::new(),
        &mut BTreeSet::new(),
        &mut BTreeSet::new(),
    )
}

struct Lowerer {
    source_id: SourceId,
    next_node: usize,
    next_capture: usize,
    completed_captures: BTreeMap<String, CaptureId>,
}

impl Lowerer {
    fn new(source_id: SourceId) -> Self {
        Self {
            source_id,
            next_node: 1,
            next_capture: 1,
            completed_captures: BTreeMap::new(),
        }
    }

    fn lower(&mut self, node: &SyntaxNode) -> Node {
        let node_id = NodeId::try_from(format!("node:semantic/n{}", self.next_node))
            .expect("governed material identity is valid");
        self.next_node += 1;
        let origin = Some(SourceOrigin {
            source_spans: Some(vec![SourceSpan::new(
                self.source_id.clone(),
                node.span.start as u64,
                node.span.end as u64,
            )
            .expect("parser material span is valid")]),
            derived_from_node_ids: None,
        });
        match &node.kind {
            SyntaxNodeKind::Empty => Node::Empty { node_id, origin },
            SyntaxNodeKind::Sequence(children) => Node::Sequence {
                node_id,
                origin,
                items: children.iter().map(|child| self.lower(child)).collect(),
            },
            SyntaxNodeKind::Alternation(children) => Node::Alternation {
                node_id,
                origin,
                branches: children.iter().map(|child| self.lower(child)).collect(),
            },
            SyntaxNodeKind::Literal(value) => Node::Literal {
                node_id,
                origin,
                text: value.value.clone(),
            },
            SyntaxNodeKind::Wildcard(line_terminators) => Node::Wildcard {
                node_id,
                origin,
                line_terminators: *line_terminators,
            },
            SyntaxNodeKind::CharacterSet { negated, members } => Node::CharacterSet {
                node_id,
                origin,
                negated: *negated,
                members: members.iter().map(lower_set_member).collect(),
            },
            SyntaxNodeKind::Repeat {
                min,
                max,
                mode,
                body,
                ..
            } => Node::Repeat {
                node_id,
                origin,
                body: Box::new(self.lower(body)),
                min: *min,
                max: *max,
                mode: *mode,
            },
            SyntaxNodeKind::Position(position) => Node::Position {
                node_id,
                origin,
                position: *position,
            },
            SyntaxNodeKind::Capture { name, body } => {
                let capture_id =
                    CaptureId::try_from(format!("capture:semantic/c{}", self.next_capture))
                        .expect("governed capture identity is valid");
                self.next_capture += 1;
                let body = Box::new(self.lower(body));
                self.completed_captures
                    .insert(name.value.clone(), capture_id.clone());
                Node::Capture {
                    node_id,
                    origin,
                    capture_id,
                    name: Some(name.value.clone()),
                    body,
                }
            }
            SyntaxNodeKind::Backreference(name) => Node::Backreference {
                node_id,
                origin,
                capture_id: self
                    .completed_captures
                    .get(&name.value)
                    .expect("validated reference resolves to completed capture")
                    .clone(),
            },
            SyntaxNodeKind::Lookaround {
                direction,
                polarity,
                body,
            } => Node::Lookaround {
                node_id,
                origin,
                direction: *direction,
                polarity: *polarity,
                body: Box::new(self.lower(body)),
            },
            SyntaxNodeKind::Atomic(body) => Node::Atomic {
                node_id,
                origin,
                body: Box::new(self.lower(body)),
            },
        }
    }
}

fn lower_set_member(member: &SyntaxSetMember) -> CharacterSetMember {
    fn scalar(value: &SyntaxString) -> UnicodeScalar {
        UnicodeScalar::from_char(
            value
                .value
                .chars()
                .next()
                .expect("validated set scalar is nonempty"),
        )
    }
    match member {
        SyntaxSetMember::Literal { value, .. } => CharacterSetMember::Literal {
            value: scalar(value),
        },
        SyntaxSetMember::Range { start, end, .. } => CharacterSetMember::Range {
            start: scalar(start),
            end: scalar(end),
        },
        SyntaxSetMember::Builtin {
            name,
            domain,
            negated,
            ..
        } => CharacterSetMember::Builtin {
            name: *name,
            domain: *domain,
            negated: *negated,
        },
        SyntaxSetMember::UnicodeProperty {
            property,
            value,
            negated,
            ..
        } => CharacterSetMember::UnicodeProperty {
            property: property.value.clone(),
            value: value.as_ref().map(|item| item.value.clone()),
            negated: *negated,
        },
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ParsedSemantic {
    pub program: SemanticProgram,
    syntax: SyntaxDocument,
}

/// Parse one resolved inline `strling.semantic@1.0.0` source document.
pub fn parse(document: &SourceDocument) -> Result<ParsedSemantic, SemanticFrontendFailure> {
    document
        .validate()
        .map_err(SemanticFrontendFailure::InvalidSource)?;
    let text = match &document.content {
        SourceContent::Inline {
            media_type, text, ..
        } => {
            if document.frontend.id.as_str() != FRONTEND_ID
                || document.frontend.dialect_version.as_str() != DIALECT_VERSION
                || media_type
                    .as_deref()
                    .is_some_and(|media_type| media_type != MEDIA_TYPE)
            {
                return Err(SemanticFrontendFailure::Diagnostic(Box::new(
                    RawError::new(SemanticFrontendErrorCode::InvalidHeader, 0)
                        .attach(document, text),
                )));
            }
            text
        }
        SourceContent::Reference { .. } => {
            return Err(SemanticFrontendFailure::ReferencedSourceUnavailable)
        }
    };
    if text.len() > MAX_SOURCE_BYTES {
        return Err(SemanticFrontendFailure::Diagnostic(Box::new(
            RawError::new(SemanticFrontendErrorCode::ResourceLimit, MAX_SOURCE_BYTES)
                .attach(document, text),
        )));
    }
    let syntax = Parser::new(text).and_then(Parser::parse).map_err(|error| {
        SemanticFrontendFailure::Diagnostic(Box::new(error.attach(document, text)))
    })?;
    let root = Lowerer::new(document.source_id.clone()).lower(&syntax.root);
    let candidate = SemanticProgram {
        contract_version: document.contract_version,
        specification_version: document.specification_version.clone(),
        normalization: Normalization::CanonicalV1,
        case_matching: syntax.case_matching,
        sources: Some(vec![document.clone()]),
        root,
    };
    let program = normalize(&candidate).map_err(SemanticFrontendFailure::InvalidSemanticOutput)?;
    Ok(ParsedSemantic { program, syntax })
}

/// Render one successful parse using the ratified canonical formatting rules.
#[must_use]
pub fn format(parsed: &ParsedSemantic) -> String {
    let mut output = String::new();
    output.push_str("semantic strling 1.0;\n");
    output.push_str(match parsed.syntax.case_matching {
        CaseMatching::Sensitive => "case sensitive;\n\n",
        CaseMatching::Insensitive => "case insensitive;\n\n",
    });
    let mut comments = CommentWriter::new(&parsed.syntax.comments);
    comments.write_before(parsed.syntax.root.span.start, 0, &mut output);
    output.push_str("pattern ");
    format_node(&parsed.syntax.root, 0, &mut comments, &mut output);
    output.push('\n');
    comments.write_before(usize::MAX, 0, &mut output);
    output
}

struct CommentWriter<'a> {
    comments: &'a [SyntaxComment],
    next: usize,
}

impl<'a> CommentWriter<'a> {
    fn new(comments: &'a [SyntaxComment]) -> Self {
        Self { comments, next: 0 }
    }

    fn write_before(&mut self, byte_limit: usize, indentation: usize, output: &mut String) {
        while self
            .comments
            .get(self.next)
            .is_some_and(|comment| comment.start < byte_limit)
        {
            let comment = &self.comments[self.next];
            indent(indentation, output);
            let text = comment.text.trim();
            output.push('#');
            if !text.is_empty() {
                output.push(' ');
                output.push_str(text);
            }
            output.push('\n');
            self.next += 1;
        }
    }
}

fn format_node(
    node: &SyntaxNode,
    indentation: usize,
    comments: &mut CommentWriter<'_>,
    output: &mut String,
) {
    match &node.kind {
        SyntaxNodeKind::Empty => output.push_str("empty;"),
        SyntaxNodeKind::Sequence(children) => {
            format_children(
                "sequence",
                children,
                node.span.end,
                indentation,
                comments,
                output,
            );
        }
        SyntaxNodeKind::Alternation(children) => {
            format_children(
                "choice",
                children,
                node.span.end,
                indentation,
                comments,
                output,
            );
        }
        SyntaxNodeKind::Literal(value) => {
            output.push_str("text ");
            format_string(&value.value, output);
            output.push(';');
        }
        SyntaxNodeKind::Wildcard(line_terminators) => output.push_str(match line_terminators {
            LineTerminators::Include => "any character including line terminators;",
            LineTerminators::Exclude => "any character excluding line terminators;",
        }),
        SyntaxNodeKind::CharacterSet { negated, members } => {
            output.push_str(if *negated {
                "character except {\n"
            } else {
                "character from {\n"
            });
            for member in members {
                comments.write_before(member.source_start(), indentation + 1, output);
                indent(indentation + 1, output);
                format_set_member(member, output);
                output.push('\n');
            }
            comments.write_before(node.span.end, indentation, output);
            indent(indentation, output);
            output.push('}');
        }
        SyntaxNodeKind::Repeat {
            min,
            max,
            mode,
            body,
            ..
        } => {
            output.push_str("repeat from ");
            output.push_str(&min.to_string());
            output.push_str(" to ");
            match max {
                RepetitionMaximum::Bounded(maximum) => output.push_str(&maximum.to_string()),
                RepetitionMaximum::Unbounded => output.push_str("unbounded"),
            }
            output.push_str(" using ");
            output.push_str(match mode {
                RepetitionMode::Greedy => "greedy",
                RepetitionMode::Lazy => "lazy",
                RepetitionMode::Possessive => "possessive",
            });
            output.push_str(" {\n");
            comments.write_before(body.span.start, indentation + 1, output);
            indent(indentation + 1, output);
            format_node(body, indentation + 1, comments, output);
            output.push('\n');
            comments.write_before(node.span.end, indentation, output);
            indent(indentation, output);
            output.push('}');
        }
        SyntaxNodeKind::Position(position) => output.push_str(match position {
            PositionKind::InputStart => "at input start;",
            PositionKind::InputEnd => "at input end;",
            PositionKind::LineStart => "at line start;",
            PositionKind::LineEnd => "at line end;",
            PositionKind::WordBoundary => "at word boundary;",
            PositionKind::NotWordBoundary => "not at word boundary;",
            PositionKind::EndBeforeFinalLineTerminator => "before final line terminator;",
        }),
        SyntaxNodeKind::Capture { name, body } => {
            output.push_str("capture ");
            output.push_str(&name.value);
            output.push_str(" {\n");
            comments.write_before(body.span.start, indentation + 1, output);
            indent(indentation + 1, output);
            format_node(body, indentation + 1, comments, output);
            output.push('\n');
            comments.write_before(node.span.end, indentation, output);
            indent(indentation, output);
            output.push('}');
        }
        SyntaxNodeKind::Backreference(name) => {
            output.push_str("same text as ");
            output.push_str(&name.value);
            output.push(';');
        }
        SyntaxNodeKind::Lookaround {
            direction,
            polarity,
            body,
        } => {
            output.push_str(match polarity {
                AssertionPolarity::Positive => "if ",
                AssertionPolarity::Negative => "unless ",
            });
            output.push_str(match direction {
                LookaroundDirection::Ahead => "followed by {\n",
                LookaroundDirection::Behind => "preceded by {\n",
            });
            comments.write_before(body.span.start, indentation + 1, output);
            indent(indentation + 1, output);
            format_node(body, indentation + 1, comments, output);
            output.push('\n');
            comments.write_before(node.span.end, indentation, output);
            indent(indentation, output);
            output.push('}');
        }
        SyntaxNodeKind::Atomic(body) => {
            output.push_str("without backtracking {\n");
            comments.write_before(body.span.start, indentation + 1, output);
            indent(indentation + 1, output);
            format_node(body, indentation + 1, comments, output);
            output.push('\n');
            comments.write_before(node.span.end, indentation, output);
            indent(indentation, output);
            output.push('}');
        }
    }
}

fn format_children(
    keyword: &str,
    children: &[SyntaxNode],
    end: usize,
    indentation: usize,
    comments: &mut CommentWriter<'_>,
    output: &mut String,
) {
    output.push_str(keyword);
    output.push_str(" {\n");
    for child in children {
        comments.write_before(child.span.start, indentation + 1, output);
        indent(indentation + 1, output);
        format_node(child, indentation + 1, comments, output);
        output.push('\n');
    }
    comments.write_before(end, indentation, output);
    indent(indentation, output);
    output.push('}');
}

impl SyntaxSetMember {
    fn source_start(&self) -> usize {
        match self {
            Self::Literal { source_start, .. }
            | Self::Range { source_start, .. }
            | Self::Builtin { source_start, .. }
            | Self::UnicodeProperty { source_start, .. } => *source_start,
        }
    }
}

fn format_set_member(member: &SyntaxSetMember, output: &mut String) {
    match member {
        SyntaxSetMember::Literal { value, .. } => {
            output.push_str("scalar ");
            format_string(&value.value, output);
        }
        SyntaxSetMember::Range { start, end, .. } => {
            output.push_str("range ");
            format_string(&start.value, output);
            output.push_str(" through ");
            format_string(&end.value, output);
        }
        SyntaxSetMember::Builtin {
            name,
            domain,
            negated,
            ..
        } => {
            if *negated {
                output.push_str("not ");
            }
            output.push_str(match domain {
                CharacterDomain::Ascii => "ascii ",
                CharacterDomain::Unicode => "unicode ",
            });
            output.push_str(match name {
                BuiltinClassName::Digit => "digit",
                BuiltinClassName::Word => "word",
                BuiltinClassName::Whitespace => "whitespace",
            });
        }
        SyntaxSetMember::UnicodeProperty {
            property,
            value,
            negated,
            ..
        } => {
            if *negated {
                output.push_str("not ");
            }
            output.push_str("property ");
            format_string(&property.value, output);
            if let Some(value) = value {
                output.push_str(" value ");
                format_string(&value.value, output);
            }
        }
    }
    output.push(';');
}

fn format_string(value: &str, output: &mut String) {
    output.push('"');
    for character in value.chars() {
        match character {
            '"' => output.push_str("\\\""),
            '\\' => output.push_str("\\\\"),
            '\u{0008}' => output.push_str("\\b"),
            '\u{000c}' => output.push_str("\\f"),
            '\n' => output.push_str("\\n"),
            '\r' => output.push_str("\\r"),
            '\t' => output.push_str("\\t"),
            '\0' => output.push_str("\\0"),
            value if value <= '\u{001f}' || value == '\u{007f}' => {
                use std::fmt::Write;
                let _ = write!(output, "\\u{{{:X}}}", value as u32);
            }
            value => output.push(value),
        }
    }
    output.push('"');
}

fn indent(level: usize, output: &mut String) {
    for _ in 0..level {
        output.push_str("    ");
    }
}
