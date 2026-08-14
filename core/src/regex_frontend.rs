//! Bounded parser for the `strling.regex-compat@1.0.0` import frontend.
//!
//! The versioned contract under `spec/frontends/legacy-regex/1.0` is the
//! authority for accepted source. This module owns syntax recognition and
//! direct lowering into canonical Semantic IR. It deliberately has no target,
//! emitter, binding, filesystem, environment, or legacy-runtime dependency.

use std::collections::{BTreeMap, BTreeSet};
use std::error::Error;
use std::fmt;

use crate::diagnostic::{
    CompilerPhase, Diagnostic, DiagnosticCategory, DiagnosticCode, DiagnosticOccurrence,
    RelatedLocation, RelatedLocationRole, Severity, SeverityBasis,
};
use crate::editor_intelligence::{
    EditorCaptureLink, EditorCompletion, EditorCompletionTier, EditorParseStatus, EditorSpan,
    EditorSymbol, EditorToken, EditorTokenType, FrontendEditorEvidence,
};
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

pub const FRONTEND_ID: &str = "strling.regex-compat";
pub const DIALECT_VERSION: &str = "1.0.0";
pub const MAX_SOURCE_BYTES: usize = 1_048_576;
pub const MAX_NESTING_DEPTH: usize = 128;
pub const MAX_CAPTURE_GROUPS: usize = 65_535;
pub const MAX_QUANTIFIER_BOUND: u64 = 4_294_967_295;

/// Every stable diagnostic identity frozen by the frontend 1.0 contract.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum RegexFrontendErrorCode {
    InvalidUtf8,
    MissingFrontendIdentity,
    ConflictingFrontendMetadata,
    SourceTooLarge,
    NestingTooDeep,
    TooManyCaptures,
    MalformedDirective,
    UnsupportedDirective,
    DirectiveAfterPattern,
    DuplicateFlagsDirective,
    InlinePatternAfterDirective,
    InvalidFlag,
    AlternationMissingLeft,
    AlternationMissingRight,
    AlternationEmptyMiddle,
    QuantifierMissingAtom,
    StackedQuantifier,
    UnterminatedBraceQuantifier,
    InvalidBraceQuantifier,
    ReversedQuantifierBounds,
    QuantifiedAssertion,
    QuantifierBoundExceeded,
    UnmatchedClosingParenthesis,
    UnterminatedGroup,
    InvalidCaptureName,
    DuplicateCaptureName,
    UnsupportedGroupPrefix,
    InlineModifier,
    EmptyCharacterClass,
    UnterminatedCharacterClass,
    ReversedCharacterRange,
    InvalidCharacterRangeEndpoint,
    PropertyBracesRequired,
    UnterminatedProperty,
    EmptyProperty,
    RawTargetSyntax,
    UnexpectedEscapeEnd,
    UnknownEscape,
    InvalidHexEscape,
    InvalidUnicodeEscape,
    InvalidUnicodeScalar,
    OctalEscape,
    ForwardBackreference,
    UndefinedBackreference,
    MalformedNamedBackreference,
}

impl RegexFrontendErrorCode {
    #[must_use]
    pub const fn id(self) -> &'static str {
        match self {
            Self::InvalidUtf8 => "STRL-FRONTEND-0001",
            Self::MissingFrontendIdentity => "STRL-FRONTEND-0002",
            Self::ConflictingFrontendMetadata => "STRL-FRONTEND-0003",
            Self::SourceTooLarge => "STRL-FRONTEND-0004",
            Self::NestingTooDeep => "STRL-FRONTEND-0005",
            Self::TooManyCaptures => "STRL-FRONTEND-0006",
            Self::MalformedDirective => "STRL-FRONTEND-1001",
            Self::UnsupportedDirective => "STRL-FRONTEND-1002",
            Self::DirectiveAfterPattern => "STRL-FRONTEND-1003",
            Self::DuplicateFlagsDirective => "STRL-FRONTEND-1004",
            Self::InlinePatternAfterDirective => "STRL-FRONTEND-1005",
            Self::InvalidFlag => "STRL-FRONTEND-1006",
            Self::AlternationMissingLeft => "STRL-FRONTEND-2001",
            Self::AlternationMissingRight => "STRL-FRONTEND-2002",
            Self::AlternationEmptyMiddle => "STRL-FRONTEND-2003",
            Self::QuantifierMissingAtom => "STRL-FRONTEND-2004",
            Self::StackedQuantifier => "STRL-FRONTEND-2005",
            Self::UnterminatedBraceQuantifier => "STRL-FRONTEND-2006",
            Self::InvalidBraceQuantifier => "STRL-FRONTEND-2007",
            Self::ReversedQuantifierBounds => "STRL-FRONTEND-2008",
            Self::QuantifiedAssertion => "STRL-FRONTEND-2009",
            Self::QuantifierBoundExceeded => "STRL-FRONTEND-2010",
            Self::UnmatchedClosingParenthesis => "STRL-FRONTEND-2011",
            Self::UnterminatedGroup => "STRL-FRONTEND-2012",
            Self::InvalidCaptureName => "STRL-FRONTEND-2013",
            Self::DuplicateCaptureName => "STRL-FRONTEND-2014",
            Self::UnsupportedGroupPrefix => "STRL-FRONTEND-2015",
            Self::InlineModifier => "STRL-FRONTEND-2016",
            Self::EmptyCharacterClass => "STRL-FRONTEND-2017",
            Self::UnterminatedCharacterClass => "STRL-FRONTEND-2018",
            Self::ReversedCharacterRange => "STRL-FRONTEND-2019",
            Self::InvalidCharacterRangeEndpoint => "STRL-FRONTEND-2020",
            Self::PropertyBracesRequired => "STRL-FRONTEND-2021",
            Self::UnterminatedProperty => "STRL-FRONTEND-2022",
            Self::EmptyProperty => "STRL-FRONTEND-2023",
            Self::RawTargetSyntax => "STRL-FRONTEND-2024",
            Self::UnexpectedEscapeEnd => "STRL-FRONTEND-3001",
            Self::UnknownEscape => "STRL-FRONTEND-3002",
            Self::InvalidHexEscape => "STRL-FRONTEND-3003",
            Self::InvalidUnicodeEscape => "STRL-FRONTEND-3004",
            Self::InvalidUnicodeScalar => "STRL-FRONTEND-3005",
            Self::OctalEscape => "STRL-FRONTEND-3006",
            Self::ForwardBackreference => "STRL-FRONTEND-4001",
            Self::UndefinedBackreference => "STRL-FRONTEND-4002",
            Self::MalformedNamedBackreference => "STRL-FRONTEND-4003",
        }
    }

    #[must_use]
    pub const fn message(self) -> &'static str {
        match self {
            Self::InvalidUtf8 => "source bytes are not valid UTF-8",
            Self::MissingFrontendIdentity => "source omits the required frontend identity",
            Self::ConflictingFrontendMetadata => "source frontend metadata is incompatible",
            Self::SourceTooLarge => "source exceeds the frontend byte limit",
            Self::NestingTooDeep => "syntactic nesting exceeds the frontend depth limit",
            Self::TooManyCaptures => "capture count exceeds the frontend limit",
            Self::MalformedDirective => "malformed frontend directive",
            Self::UnsupportedDirective => "unsupported frontend directive",
            Self::DirectiveAfterPattern => "directive appears after pattern content",
            Self::DuplicateFlagsDirective => "flags directive appears more than once",
            Self::InlinePatternAfterDirective => "pattern content appears on a directive line",
            Self::InvalidFlag => "flags directive contains an unsupported flag",
            Self::AlternationMissingLeft => "alternation has no left branch",
            Self::AlternationMissingRight => "alternation has no right branch",
            Self::AlternationEmptyMiddle => "alternation contains an empty middle branch",
            Self::QuantifierMissingAtom => "quantifier has no preceding atom",
            Self::StackedQuantifier => "term has more than one repetition operator",
            Self::UnterminatedBraceQuantifier => "braced quantifier is not closed",
            Self::InvalidBraceQuantifier => "braced quantifier is malformed",
            Self::ReversedQuantifierBounds => "quantifier minimum exceeds maximum",
            Self::QuantifiedAssertion => "zero-width assertion cannot be quantified",
            Self::QuantifierBoundExceeded => "quantifier bound exceeds the frontend limit",
            Self::UnmatchedClosingParenthesis => "closing parenthesis has no opener",
            Self::UnterminatedGroup => "group or lookaround is not closed",
            Self::InvalidCaptureName => "capture name is not an ASCII identifier",
            Self::DuplicateCaptureName => "capture name duplicates an earlier declaration",
            Self::UnsupportedGroupPrefix => "group prefix is outside the frontend dialect",
            Self::InlineModifier => "inline modifiers are outside the frontend dialect",
            Self::EmptyCharacterClass => "character class has no item",
            Self::UnterminatedCharacterClass => "character class is not closed",
            Self::ReversedCharacterRange => "character range start exceeds end",
            Self::InvalidCharacterRangeEndpoint => "character range endpoint is not a scalar",
            Self::PropertyBracesRequired => "Unicode property escape requires braces",
            Self::UnterminatedProperty => "Unicode property escape is not closed",
            Self::EmptyProperty => "Unicode property name or value is empty",
            Self::RawTargetSyntax => "target-specific raw syntax is outside the frontend dialect",
            Self::UnexpectedEscapeEnd => "backslash appears at end of source or class",
            Self::UnknownEscape => "escape spelling is outside the frontend dialect",
            Self::InvalidHexEscape => "hexadecimal escape is malformed",
            Self::InvalidUnicodeEscape => "Unicode escape is malformed",
            Self::InvalidUnicodeScalar => "escape does not encode a Unicode scalar",
            Self::OctalEscape => "octal escape is outside the frontend dialect",
            Self::ForwardBackreference => "backreference refers to a later capture",
            Self::UndefinedBackreference => "backreference does not resolve",
            Self::MalformedNamedBackreference => "named backreference is malformed",
        }
    }

    #[must_use]
    pub const fn category(self) -> DiagnosticCategory {
        match self {
            Self::InvalidUtf8 => DiagnosticCategory::MalformedRequest,
            Self::MissingFrontendIdentity | Self::ConflictingFrontendMetadata => {
                DiagnosticCategory::UnsupportedFrontend
            }
            Self::SourceTooLarge | Self::NestingTooDeep | Self::TooManyCaptures => {
                DiagnosticCategory::ResourceLimit
            }
            _ => DiagnosticCategory::Syntax,
        }
    }
}

/// One first-in-source-order canonical frontend diagnostic and its source evidence.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RegexFrontendError {
    pub code: RegexFrontendErrorCode,
    pub byte_offset: u64,
    pub diagnostic: Diagnostic,
    pub frontend: FrontendIdentity,
    pub source_provenance: Provenance,
}

impl fmt::Display for RegexFrontendError {
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

impl Error for RegexFrontendError {}

#[derive(Clone, Debug, Eq, PartialEq)]
struct RawRelatedLocation {
    role: RelatedLocationRole,
    message: &'static str,
    byte_offset: usize,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct RawFrontendError {
    code: RegexFrontendErrorCode,
    byte_offset: usize,
    related: Vec<RawRelatedLocation>,
}

impl RawFrontendError {
    fn with_related(
        mut self,
        role: RelatedLocationRole,
        message: &'static str,
        byte_offset: usize,
    ) -> Self {
        self.related.push(RawRelatedLocation {
            role,
            message,
            byte_offset,
        });
        self
    }

    fn attach(self, document: &SourceDocument, text: &str) -> RegexFrontendError {
        let primary_location = source_span_at(&document.source_id, text, self.byte_offset);
        let related_locations: Vec<_> = self
            .related
            .into_iter()
            .map(|related| RelatedLocation {
                role: related.role,
                message: related.message.to_owned(),
                location: source_span_at(&document.source_id, text, related.byte_offset),
            })
            .collect();
        let diagnostic = Diagnostic {
            contract_version: document.contract_version,
            occurrence: DiagnosticOccurrence::new(0),
            code: DiagnosticCode::try_from(self.code.id())
                .expect("frozen frontend diagnostic identity is valid"),
            severity: Severity::Error,
            severity_basis: SeverityBasis::Normative,
            phase: CompilerPhase::FrontendParse,
            category: self.code.category(),
            message: self.code.message().to_owned(),
            primary_location: Some(primary_location),
            related_locations: (!related_locations.is_empty()).then_some(related_locations),
            advice: None,
            fixes: None,
        };
        diagnostic
            .validate()
            .expect("constructed frontend diagnostic is valid");
        RegexFrontendError {
            code: self.code,
            byte_offset: self.byte_offset as u64,
            diagnostic,
            frontend: document.frontend.clone(),
            source_provenance: document.provenance.clone(),
        }
    }
}

/// Frontend diagnostics remain distinct from canonical contract failures.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum RegexFrontendFailure {
    Diagnostic(Box<RegexFrontendError>),
    InvalidSource(ValidationErrors),
    ReferencedSourceUnavailable,
    InvalidSemanticOutput(ValidationErrors),
}

impl RegexFrontendFailure {
    #[must_use]
    pub fn diagnostic(&self) -> Option<&RegexFrontendError> {
        match self {
            Self::Diagnostic(error) => Some(error.as_ref()),
            Self::InvalidSource(_)
            | Self::ReferencedSourceUnavailable
            | Self::InvalidSemanticOutput(_) => None,
        }
    }
}

impl fmt::Display for RegexFrontendFailure {
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

impl Error for RegexFrontendFailure {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Diagnostic(error) => Some(error.as_ref()),
            Self::InvalidSource(errors) | Self::InvalidSemanticOutput(errors) => Some(errors),
            Self::ReferencedSourceUnavailable => None,
        }
    }
}

/// Normalized frontend flags retained as syntax evidence after semantic lowering.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct RegexFrontendFlags {
    case_insensitive: bool,
    multiline: bool,
    dot_matches_line_terminators: bool,
    unicode_classes: bool,
    extended_layout: bool,
}

impl RegexFrontendFlags {
    #[must_use]
    pub const fn case_insensitive(self) -> bool {
        self.case_insensitive
    }

    #[must_use]
    pub const fn multiline(self) -> bool {
        self.multiline
    }

    #[must_use]
    pub const fn dot_matches_line_terminators(self) -> bool {
        self.dot_matches_line_terminators
    }

    #[must_use]
    pub const fn unicode_classes(self) -> bool {
        self.unicode_classes
    }

    #[must_use]
    pub const fn extended_layout(self) -> bool {
        self.extended_layout
    }

    #[must_use]
    pub fn active_letters(self) -> Vec<char> {
        let mut active = Vec::new();
        for (enabled, letter) in [
            (self.case_insensitive, 'i'),
            (self.multiline, 'm'),
            (self.dot_matches_line_terminators, 's'),
            (self.unicode_classes, 'u'),
            (self.extended_layout, 'x'),
        ] {
            if enabled {
                active.push(letter);
            }
        }
        active
    }

    fn enable(&mut self, letter: char) {
        match letter.to_ascii_lowercase() {
            'i' => self.case_insensitive = true,
            'm' => self.multiline = true,
            's' => self.dot_matches_line_terminators = true,
            'u' => self.unicode_classes = true,
            'x' => self.extended_layout = true,
            _ => {}
        }
    }
}

/// Successful syntax evidence and its canonical target-neutral lowering.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ParsedRegex {
    pub flags: RegexFrontendFlags,
    pub flags_directive: Option<SourceSpan>,
    pub program: SemanticProgram,
    body_start: usize,
    capture_declarations: Vec<RegexCaptureDeclaration>,
    references: Vec<RegexReference>,
}

/// Parse one resolved inline SourceDocument under the frozen frontend contract.
pub fn parse(document: &SourceDocument) -> Result<ParsedRegex, RegexFrontendFailure> {
    document
        .validate()
        .map_err(RegexFrontendFailure::InvalidSource)?;
    if document.frontend.id.as_str() != FRONTEND_ID
        || document.frontend.dialect_version.as_str() != DIALECT_VERSION
    {
        return Err(RegexFrontendFailure::Diagnostic(Box::new(
            diagnostic(RegexFrontendErrorCode::ConflictingFrontendMetadata, 0)
                .attach(document, document.content.inline_text().unwrap_or("")),
        )));
    }
    let text = match &document.content {
        SourceContent::Inline { text, .. } => text,
        SourceContent::Reference { .. } => {
            return Err(RegexFrontendFailure::ReferencedSourceUnavailable)
        }
    };
    if text.len() > MAX_SOURCE_BYTES {
        return Err(RegexFrontendFailure::Diagnostic(Box::new(
            diagnostic(RegexFrontendErrorCode::SourceTooLarge, MAX_SOURCE_BYTES)
                .attach(document, text),
        )));
    }

    let preamble = parse_preamble(text).map_err(|error| {
        RegexFrontendFailure::Diagnostic(Box::new(error.attach(document, text)))
    })?;
    let ParsedPreamble {
        flags,
        body_start,
        flags_range,
    } = preamble;
    let mut parser = Parser::new(text, body_start, flags);
    let syntax = parser.parse().map_err(|error| {
        RegexFrontendFailure::Diagnostic(Box::new(error.attach(document, text)))
    })?;
    let capture_declarations = parser.capture_declarations.clone();
    let references = parser.references.clone();
    let root = Lowerer::new(
        flags.dot_matches_line_terminators,
        document.source_id.clone(),
    )
    .lower(syntax);
    let program = SemanticProgram {
        contract_version: document.contract_version,
        specification_version: document.specification_version.clone(),
        normalization: Normalization::CanonicalV1,
        case_matching: if flags.case_insensitive {
            CaseMatching::Insensitive
        } else {
            CaseMatching::Sensitive
        },
        sources: Some(vec![document.clone()]),
        root,
    };
    program
        .validate()
        .map_err(RegexFrontendFailure::InvalidSemanticOutput)?;
    let flags_directive = flags_range.map(|(start, end)| {
        SourceSpan::new(document.source_id.clone(), start as u64, end as u64)
            .expect("parser directive offsets are valid")
    });
    Ok(ParsedRegex {
        flags,
        flags_directive,
        program,
        body_start,
        capture_declarations,
        references,
    })
}

pub(crate) fn project_editor(
    document: &SourceDocument,
    text: &str,
    cursor_byte: Option<usize>,
) -> FrontendEditorEvidence {
    let parsed = parse(document).ok();
    let parser_state = regex_parser_state(text);
    let captures = parsed.as_ref().map_or_else(Vec::new, regex_capture_links);
    let symbols = parsed.as_ref().map_or_else(Vec::new, |parsed| {
        vec![regex_symbol(&parsed.program.root, parsed)]
    });
    let tokens = parsed
        .as_ref()
        .map_or_else(Vec::new, |parsed| regex_editor_tokens(text, parsed));
    let (completions, replacement_span) = cursor_byte.map_or_else(
        || (Vec::new(), None),
        |cursor| regex_completions(text, cursor, parser_state.as_ref()),
    );
    FrontendEditorEvidence {
        parse_status: if parsed.is_some() {
            EditorParseStatus::Complete
        } else {
            EditorParseStatus::Incomplete
        },
        tokens,
        symbols,
        captures,
        completions,
        replacement_span,
        formatted_source: None,
        rewrite_actions: Vec::new(),
    }
}

fn regex_parser_state(text: &str) -> Option<Parser<'_>> {
    let preamble = parse_preamble(text).ok()?;
    let mut parser = Parser::new(text, preamble.body_start, preamble.flags);
    let _ = parser.parse();
    Some(parser)
}

fn regex_capture_id(index: usize) -> String {
    format!("capture:regex-compat/{index:05}")
}

fn regex_capture_links(parsed: &ParsedRegex) -> Vec<EditorCaptureLink> {
    let mut references: BTreeMap<usize, Vec<EditorSpan>> = BTreeMap::new();
    for reference in &parsed.references {
        references
            .entry(reference.index)
            .or_default()
            .push(EditorSpan::new(reference.span.0, reference.span.1));
    }
    parsed
        .capture_declarations
        .iter()
        .map(|declaration| EditorCaptureLink {
            capture_id: regex_capture_id(declaration.index),
            name: declaration.name.clone(),
            declaration: EditorSpan::new(declaration.span.0, declaration.span.1),
            references: references.remove(&declaration.index).unwrap_or_default(),
        })
        .collect()
}

fn regex_symbol(node: &Node, parsed: &ParsedRegex) -> EditorSymbol {
    let span = regex_origin_span(node);
    let (kind, name, capture_id, children) = match node {
        Node::Empty { .. } => ("empty", "empty".to_owned(), None, Vec::new()),
        Node::Sequence { items, .. } => (
            "sequence",
            "sequence".to_owned(),
            None,
            items
                .iter()
                .map(|child| regex_symbol(child, parsed))
                .collect(),
        ),
        Node::Alternation { branches, .. } => (
            "alternation",
            "alternation".to_owned(),
            None,
            branches
                .iter()
                .map(|child| regex_symbol(child, parsed))
                .collect(),
        ),
        Node::Literal { .. } => ("literal", "literal".to_owned(), None, Vec::new()),
        Node::Wildcard { .. } => ("wildcard", "wildcard".to_owned(), None, Vec::new()),
        Node::CharacterSet { .. } => (
            "character_set",
            "character set".to_owned(),
            None,
            Vec::new(),
        ),
        Node::Repeat { body, .. } => (
            "repeat",
            "repeat".to_owned(),
            None,
            vec![regex_symbol(body, parsed)],
        ),
        Node::Position { .. } => ("position", "position".to_owned(), None, Vec::new()),
        Node::Capture {
            capture_id,
            name,
            body,
            ..
        } => (
            "capture",
            name.clone()
                .unwrap_or_else(|| capture_id.as_str().to_owned()),
            Some(capture_id.as_str().to_owned()),
            vec![regex_symbol(body, parsed)],
        ),
        Node::Backreference { capture_id, .. } => (
            "backreference",
            capture_id.as_str().to_owned(),
            Some(capture_id.as_str().to_owned()),
            Vec::new(),
        ),
        Node::Lookaround { body, .. } => (
            "lookaround",
            "lookaround".to_owned(),
            None,
            vec![regex_symbol(body, parsed)],
        ),
        Node::Atomic { body, .. } => (
            "atomic",
            "atomic".to_owned(),
            None,
            vec![regex_symbol(body, parsed)],
        ),
    };
    let selection_span = match node {
        Node::Capture { capture_id, .. } => parsed
            .capture_declarations
            .iter()
            .find(|declaration| regex_capture_id(declaration.index) == capture_id.as_str())
            .map_or(span, |declaration| {
                EditorSpan::new(declaration.span.0, declaration.span.1)
            }),
        Node::Backreference { capture_id, .. } => parsed
            .references
            .iter()
            .find(|reference| {
                regex_capture_id(reference.index) == capture_id.as_str()
                    && span.start <= reference.span.0
                    && reference.span.1 <= span.end
            })
            .map_or(span, |reference| {
                EditorSpan::new(reference.span.0, reference.span.1)
            }),
        _ => span,
    };
    EditorSymbol {
        node_id: node.node_id().as_str().to_owned(),
        kind: kind.to_owned(),
        name,
        span,
        selection_span,
        capture_id,
        children,
    }
}

fn regex_origin_span(node: &Node) -> EditorSpan {
    node.origin()
        .and_then(|origin| origin.source_spans.as_ref())
        .and_then(|spans| spans.first())
        .map_or(EditorSpan::new(0, 0), |span| {
            EditorSpan::new(span.start as usize, span.end as usize)
        })
}

fn regex_completions(
    text: &str,
    cursor: usize,
    parser: Option<&Parser<'_>>,
) -> (Vec<EditorCompletion>, Option<EditorSpan>) {
    let (start, end) = regex_replacement_span(text, cursor);
    let prefix = &text[start..cursor];
    let before_line = &text[..cursor];
    let line_start = before_line.rfind(['\n', '\r']).map_or(0, |index| index + 1);
    let line_prefix = &text[line_start..cursor];
    let trimmed_line = line_prefix.trim_start_matches([' ', '\t']);
    let mut labels: Vec<(String, EditorCompletionTier, String)> = Vec::new();
    if trimmed_line.starts_with("%flags") {
        let flag_content = trimmed_line
            .strip_prefix("%flags")
            .expect("checked flags prefix");
        let used: BTreeSet<char> = flag_content
            .chars()
            .filter(|character| {
                matches!(character.to_ascii_lowercase(), 'i' | 'm' | 's' | 'u' | 'x')
            })
            .map(|character| character.to_ascii_lowercase())
            .collect();
        labels.extend(
            ['i', 'm', 's', 'u', 'x']
                .into_iter()
                .filter(|letter| !used.contains(letter) || prefix == letter.to_string())
                .map(|letter| {
                    (
                        letter.to_string(),
                        EditorCompletionTier::ParserExpectedTerminal,
                        "Regex-compatible %flags letter".to_owned(),
                    )
                }),
        );
    } else if text[..cursor].trim().is_empty() {
        labels.push((
            "%flags".to_owned(),
            EditorCompletionTier::ParserExpectedTerminal,
            "Regex-compatible preamble directive".to_owned(),
        ));
    } else if start >= 3 && &text[start - 3..start] == "\\k<" {
        if let Some(parser) = parser {
            labels.extend(
                parser
                    .capture_declarations
                    .iter()
                    .filter(|declaration| declaration.span.1 <= cursor)
                    .filter_map(|declaration| declaration.name.as_ref())
                    .map(|name| {
                        (
                            name.clone(),
                            EditorCompletionTier::CanonicalCaptureIdentity,
                            "Canonical named capture declared before this reference".to_owned(),
                        )
                    }),
            );
        }
    } else if start > 0 && text.as_bytes()[start - 1] == b'\\' {
        if let Some(parser) = parser {
            labels.extend(
                parser
                    .capture_declarations
                    .iter()
                    .filter(|declaration| declaration.span.1 <= cursor)
                    .map(|declaration| {
                        (
                            declaration.index.to_string(),
                            EditorCompletionTier::CanonicalCaptureIdentity,
                            "Canonical numeric capture declared before this reference".to_owned(),
                        )
                    }),
            );
        }
    }
    let completions = labels
        .into_iter()
        .filter(|(label, _, _)| label.starts_with(prefix))
        .map(|(label, tier, detail)| EditorCompletion {
            identity: match tier {
                EditorCompletionTier::ParserExpectedTerminal => {
                    format!("regex-terminal:{label}")
                }
                EditorCompletionTier::CanonicalCaptureIdentity => {
                    format!("regex-capture:{label}")
                }
            },
            label,
            tier,
            detail,
        })
        .collect();
    (completions, Some(EditorSpan::new(start, end)))
}

fn regex_replacement_span(text: &str, cursor: usize) -> (usize, usize) {
    let bytes = text.as_bytes();
    let is_word = |byte: u8| byte.is_ascii_alphanumeric() || byte == b'_';
    let mut start = cursor;
    while start > 0 && is_word(bytes[start - 1]) {
        start -= 1;
    }
    let mut end = cursor;
    while end < bytes.len() && is_word(bytes[end]) {
        end += 1;
    }
    (start, end)
}

fn regex_editor_tokens(text: &str, parsed: &ParsedRegex) -> Vec<EditorToken> {
    let declarations: BTreeMap<usize, &RegexCaptureDeclaration> = parsed
        .capture_declarations
        .iter()
        .map(|declaration| (declaration.span.0, declaration))
        .collect();
    let references: BTreeMap<usize, &RegexReference> = parsed
        .references
        .iter()
        .map(|reference| (reference.span.0, reference))
        .collect();
    let mut tokens = Vec::new();
    regex_preamble_tokens(text, parsed.body_start, &mut tokens);
    let mut position = parsed.body_start;
    while position < text.len() {
        let character = text[position..]
            .chars()
            .next()
            .expect("position is a character boundary");
        if character == '\r' || character == '\n' {
            position += character.len_utf8();
            continue;
        }
        if parsed.flags.extended_layout && matches!(character, ' ' | '\t') {
            position += 1;
            continue;
        }
        if parsed.flags.extended_layout && character == '#' {
            let end = text[position..]
                .find(['\r', '\n'])
                .map_or(text.len(), |offset| position + offset);
            push_regex_token(&mut tokens, position, end, EditorTokenType::Comment);
            position = end;
            continue;
        }
        if text[position..].starts_with("(?<")
            && !text[position..].starts_with("(?<=")
            && !text[position..].starts_with("(?<!")
        {
            push_regex_token(
                &mut tokens,
                position,
                position + 3,
                EditorTokenType::Operator,
            );
            if let Some(declaration) = declarations.get(&(position + 3)) {
                push_regex_token(
                    &mut tokens,
                    declaration.span.0,
                    declaration.span.1,
                    EditorTokenType::Function,
                );
                position = declaration.span.1;
                continue;
            }
        }
        if text[position..].starts_with("\\k<") {
            push_regex_token(
                &mut tokens,
                position,
                position + 3,
                EditorTokenType::Operator,
            );
            if let Some(reference) = references.get(&(position + 3)) {
                push_regex_token(
                    &mut tokens,
                    reference.span.0,
                    reference.span.1,
                    EditorTokenType::Variable,
                );
                position = reference.span.1;
                continue;
            }
        }
        if character == '[' {
            push_regex_token(
                &mut tokens,
                position,
                position + 1,
                EditorTokenType::Operator,
            );
            let content_start = position + 1;
            let mut end = content_start;
            let mut escaped = false;
            while end < text.len() {
                let next = text[end..].chars().next().expect("class scalar");
                if next == ']' && !escaped {
                    break;
                }
                escaped = next == '\\' && !escaped;
                if next != '\\' {
                    escaped = false;
                }
                end += next.len_utf8();
            }
            push_regex_token(&mut tokens, content_start, end, EditorTokenType::Regexp);
            if end < text.len() {
                push_regex_token(&mut tokens, end, end + 1, EditorTokenType::Operator);
                position = end + 1;
            } else {
                position = end;
            }
            continue;
        }
        if character == '{' {
            push_regex_token(
                &mut tokens,
                position,
                position + 1,
                EditorTokenType::Operator,
            );
            position += 1;
            while position < text.len() && text.as_bytes()[position] != b'}' {
                let start = position;
                if text.as_bytes()[position].is_ascii_digit() {
                    while position < text.len() && text.as_bytes()[position].is_ascii_digit() {
                        position += 1;
                    }
                    push_regex_token(&mut tokens, start, position, EditorTokenType::Number);
                } else {
                    position += 1;
                    push_regex_token(&mut tokens, start, position, EditorTokenType::Operator);
                }
            }
            if position < text.len() {
                push_regex_token(
                    &mut tokens,
                    position,
                    position + 1,
                    EditorTokenType::Operator,
                );
                position += 1;
            }
            continue;
        }
        if character == '\\' {
            if let Some(reference) = references.get(&(position + 1)) {
                push_regex_token(
                    &mut tokens,
                    position,
                    reference.span.1,
                    EditorTokenType::Variable,
                );
                position = reference.span.1;
                continue;
            }
            let end = text[position + 1..]
                .chars()
                .next()
                .map_or(position + 1, |next| position + 1 + next.len_utf8());
            let token_type = if text
                .get(position..end)
                .is_some_and(|value| matches!(value, "\\b" | "\\B" | "\\A" | "\\Z"))
            {
                EditorTokenType::Keyword
            } else {
                EditorTokenType::Regexp
            };
            push_regex_token(&mut tokens, position, end, token_type);
            position = end;
            continue;
        }
        if matches!(character, '(' | ')' | '|' | '*' | '+' | '?' | '>' | ',') {
            let end = position + character.len_utf8();
            push_regex_token(&mut tokens, position, end, EditorTokenType::Operator);
            position = end;
            continue;
        }
        if matches!(character, '^' | '$') {
            let end = position + 1;
            push_regex_token(&mut tokens, position, end, EditorTokenType::Keyword);
            position = end;
            continue;
        }
        if character == '.' {
            push_regex_token(&mut tokens, position, position + 1, EditorTokenType::Regexp);
            position += 1;
            continue;
        }
        let start = position;
        while position < text.len() {
            let next = text[position..].chars().next().expect("literal scalar");
            if matches!(
                next,
                '\r' | '\n'
                    | '['
                    | '{'
                    | '('
                    | ')'
                    | '|'
                    | '*'
                    | '+'
                    | '?'
                    | '\\'
                    | '^'
                    | '$'
                    | '.'
                    | '>'
                    | ','
            ) || (parsed.flags.extended_layout && matches!(next, ' ' | '\t' | '#'))
            {
                break;
            }
            position += next.len_utf8();
        }
        push_regex_token(&mut tokens, start, position, EditorTokenType::Regexp);
    }
    tokens.sort_by_key(|token| (token.span.start, token.span.end));
    tokens
}

fn regex_preamble_tokens(text: &str, body_start: usize, tokens: &mut Vec<EditorToken>) {
    for line in physical_lines(&text[..body_start]) {
        let (trimmed, indentation) = trim_horizontal_start(line.content);
        let start = line.start + indentation;
        if trimmed.starts_with('#') {
            push_regex_token(
                tokens,
                start,
                line.start + line.content.len(),
                EditorTokenType::Comment,
            );
            continue;
        }
        if !trimmed.starts_with("%flags") {
            continue;
        }
        push_regex_token(tokens, start, start + 6, EditorTokenType::Keyword);
        let mut position = start + 6;
        let end = line.start + line.content.len();
        while position < end {
            let byte = text.as_bytes()[position];
            if matches!(
                byte,
                b'i' | b'I' | b'm' | b'M' | b's' | b'S' | b'u' | b'U' | b'x' | b'X'
            ) {
                push_regex_token(tokens, position, position + 1, EditorTokenType::Keyword);
            } else if byte == b',' {
                push_regex_token(tokens, position, position + 1, EditorTokenType::Operator);
            }
            position += 1;
        }
    }
}

fn push_regex_token(
    tokens: &mut Vec<EditorToken>,
    start: usize,
    end: usize,
    token_type: EditorTokenType,
) {
    if start < end {
        tokens.push(EditorToken {
            span: EditorSpan::new(start, end),
            token_type,
        });
    }
}

fn diagnostic(code: RegexFrontendErrorCode, byte_offset: usize) -> RawFrontendError {
    RawFrontendError {
        code,
        byte_offset,
        related: Vec::new(),
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

#[derive(Clone, Copy)]
struct PhysicalLine<'a> {
    start: usize,
    content: &'a str,
    has_ending: bool,
}

fn physical_lines(text: &str) -> Vec<PhysicalLine<'_>> {
    let mut lines = Vec::new();
    let mut start = 0;
    while start < text.len() {
        if let Some(relative_end) = text[start..].find('\n') {
            let line_end = start + relative_end;
            let content_end = if line_end > start && text.as_bytes()[line_end - 1] == b'\r' {
                line_end - 1
            } else {
                line_end
            };
            lines.push(PhysicalLine {
                start,
                content: &text[start..content_end],
                has_ending: true,
            });
            start = line_end + 1;
        } else {
            lines.push(PhysicalLine {
                start,
                content: &text[start..],
                has_ending: false,
            });
            start = text.len();
        }
    }
    lines
}

fn trim_horizontal_start(value: &str) -> (&str, usize) {
    let removed = value
        .as_bytes()
        .iter()
        .take_while(|byte| matches!(byte, b' ' | b'\t'))
        .count();
    (&value[removed..], removed)
}

struct ParsedPreamble {
    flags: RegexFrontendFlags,
    body_start: usize,
    flags_range: Option<(usize, usize)>,
}

fn parse_preamble(text: &str) -> Result<ParsedPreamble, RawFrontendError> {
    let lines = physical_lines(text);
    let mut flags = RegexFrontendFlags::default();
    let mut saw_flags = false;
    let mut flags_range: Option<(usize, usize)> = None;
    let mut body_start = text.len();
    let mut body_line_index = lines.len();

    for (index, line) in lines.iter().enumerate() {
        let (trimmed, indentation) = trim_horizontal_start(line.content);
        if !saw_flags && line.has_ending && (trimmed.is_empty() || trimmed.starts_with('#')) {
            continue;
        }
        if trimmed.starts_with('%') {
            if saw_flags {
                return Err(diagnostic(
                    RegexFrontendErrorCode::DuplicateFlagsDirective,
                    line.start + indentation,
                )
                .with_related(
                    RelatedLocationRole::Definition,
                    "The first flags directive is here.",
                    flags_range.expect("prior flags directive").0,
                ));
            }
            flags = parse_flags_directive(*line, indentation)?;
            saw_flags = true;
            flags_range = Some((line.start + indentation, line.start + line.content.len()));
            continue;
        }
        body_start = line.start;
        body_line_index = index;
        break;
    }

    for line in lines.iter().skip(body_line_index + 1) {
        let (trimmed, indentation) = trim_horizontal_start(line.content);
        if trimmed.starts_with('%') {
            return Err(diagnostic(
                RegexFrontendErrorCode::DirectiveAfterPattern,
                line.start + indentation,
            ));
        }
    }
    Ok(ParsedPreamble {
        flags,
        body_start,
        flags_range,
    })
}

fn parse_flags_directive(
    line: PhysicalLine<'_>,
    indentation: usize,
) -> Result<RegexFrontendFlags, RawFrontendError> {
    let offset = line.start + indentation;
    let content = &line.content[indentation..];
    if !content.starts_with("%flags") {
        return Err(diagnostic(
            RegexFrontendErrorCode::UnsupportedDirective,
            offset,
        ));
    }
    let after = &content[6..];
    if !after.is_empty() && !matches!(after.as_bytes().first(), Some(b' ' | b'\t')) {
        return Err(diagnostic(
            RegexFrontendErrorCode::MalformedDirective,
            offset,
        ));
    }

    let mut flags = RegexFrontendFlags::default();
    let mut cursor = 0;
    while cursor < after.len() && matches!(after.as_bytes()[cursor], b' ' | b'\t') {
        cursor += 1;
    }
    let mut bracketed = false;
    let mut closed = false;
    if after[cursor..].starts_with('[') {
        bracketed = true;
        cursor += 1;
    }
    let mut saw_valid = false;
    while cursor < after.len() {
        let character = after[cursor..].chars().next().expect("character boundary");
        let character_offset = line.start + indentation + 6 + cursor;
        if matches!(character, ' ' | '\t' | ',') {
            cursor += character.len_utf8();
            continue;
        }
        if character == ']' {
            if !bracketed || closed {
                return Err(diagnostic(
                    RegexFrontendErrorCode::MalformedDirective,
                    offset,
                ));
            }
            closed = true;
            cursor += 1;
            if !after[cursor..]
                .chars()
                .all(|remaining| matches!(remaining, ' ' | '\t'))
            {
                let extra = after[cursor..]
                    .char_indices()
                    .find(|(_, remaining)| !matches!(remaining, ' ' | '\t'))
                    .map_or(cursor, |(relative, _)| cursor + relative);
                return Err(diagnostic(
                    RegexFrontendErrorCode::InlinePatternAfterDirective,
                    line.start + indentation + 6 + extra,
                ));
            }
            break;
        }
        if matches!(character.to_ascii_lowercase(), 'i' | 'm' | 's' | 'u' | 'x') {
            if closed {
                return Err(diagnostic(
                    RegexFrontendErrorCode::InlinePatternAfterDirective,
                    character_offset,
                ));
            }
            flags.enable(character);
            saw_valid = true;
            cursor += character.len_utf8();
            continue;
        }
        let code = if saw_valid {
            RegexFrontendErrorCode::InlinePatternAfterDirective
        } else {
            RegexFrontendErrorCode::InvalidFlag
        };
        return Err(diagnostic(code, character_offset));
    }
    if bracketed && !closed {
        return Err(diagnostic(
            RegexFrontendErrorCode::MalformedDirective,
            offset,
        ));
    }
    if !line.has_ending {
        return Err(diagnostic(
            RegexFrontendErrorCode::MalformedDirective,
            offset,
        ));
    }
    Ok(flags)
}

#[derive(Clone, Debug)]
struct SyntaxNode {
    start: usize,
    end: usize,
    spans: Vec<(usize, usize)>,
    kind: SyntaxKind,
}

#[derive(Clone, Debug)]
enum SyntaxKind {
    Empty,
    Sequence(Vec<SyntaxNode>),
    Alternation(Vec<SyntaxNode>),
    Literal(String),
    Wildcard,
    CharacterSet {
        negated: bool,
        members: Vec<CharacterSetMember>,
    },
    Repeat {
        body: Box<SyntaxNode>,
        min: u64,
        max: RepetitionMaximum,
        mode: RepetitionMode,
    },
    Position(PositionKind),
    Capture {
        capture_index: usize,
        name: Option<String>,
        body: Box<SyntaxNode>,
    },
    Backreference(usize),
    Lookaround {
        direction: LookaroundDirection,
        polarity: AssertionPolarity,
        body: Box<SyntaxNode>,
    },
    Atomic(Box<SyntaxNode>),
}

impl SyntaxNode {
    fn new(start: usize, end: usize, kind: SyntaxKind) -> Self {
        Self {
            start,
            end,
            spans: vec![(start, end)],
            kind,
        }
    }

    fn is_assertion(&self) -> bool {
        matches!(
            self.kind,
            SyntaxKind::Position(_) | SyntaxKind::Lookaround { .. }
        )
    }

    fn cover(start: usize, end: usize, kind: SyntaxKind) -> Self {
        Self::new(start.min(end), end.max(start), kind)
    }
}

#[derive(Clone, Debug)]
enum PendingTarget {
    Numeric(usize),
    Named(String),
}

#[derive(Clone, Debug)]
struct PendingReference {
    offset: usize,
    target: PendingTarget,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct RegexCaptureDeclaration {
    index: usize,
    name: Option<String>,
    span: (usize, usize),
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct RegexReference {
    index: usize,
    span: (usize, usize),
}

struct Parser<'a> {
    text: &'a str,
    position: usize,
    flags: RegexFrontendFlags,
    depth: usize,
    capture_count: usize,
    capture_names: BTreeMap<String, (usize, usize)>,
    pending_references: Vec<PendingReference>,
    capture_declarations: Vec<RegexCaptureDeclaration>,
    references: Vec<RegexReference>,
}

impl<'a> Parser<'a> {
    fn new(text: &'a str, position: usize, flags: RegexFrontendFlags) -> Self {
        Self {
            text,
            position,
            flags,
            depth: 0,
            capture_count: 0,
            capture_names: BTreeMap::new(),
            pending_references: Vec::new(),
            capture_declarations: Vec::new(),
            references: Vec::new(),
        }
    }

    fn parse(&mut self) -> Result<SyntaxNode, RawFrontendError> {
        let syntax = self.parse_alternation()?;
        self.skip_layout();
        if self.peek() == Some(')') {
            return Err(diagnostic(
                RegexFrontendErrorCode::UnmatchedClosingParenthesis,
                self.position,
            ));
        }
        if !self.eof() {
            return Err(diagnostic(
                RegexFrontendErrorCode::RawTargetSyntax,
                self.position,
            ));
        }
        if let Some(reference) = self.pending_references.first() {
            let forward = match &reference.target {
                PendingTarget::Numeric(index) => *index <= self.capture_count,
                PendingTarget::Named(name) => self.capture_names.contains_key(name),
            };
            return Err(diagnostic(
                if forward {
                    RegexFrontendErrorCode::ForwardBackreference
                } else {
                    RegexFrontendErrorCode::UndefinedBackreference
                },
                reference.offset,
            ));
        }
        Ok(syntax)
    }

    fn eof(&self) -> bool {
        self.position >= self.text.len()
    }

    fn peek(&self) -> Option<char> {
        self.text[self.position..].chars().next()
    }

    fn peek_after(&self, character: char) -> Option<char> {
        self.text[self.position + character.len_utf8()..]
            .chars()
            .next()
    }

    fn starts_with(&self, value: &str) -> bool {
        self.text[self.position..].starts_with(value)
    }

    fn take(&mut self) -> Option<char> {
        let character = self.peek()?;
        self.position += character.len_utf8();
        Some(character)
    }

    fn skip_layout(&mut self) {
        if !self.flags.extended_layout {
            return;
        }
        loop {
            while matches!(self.peek(), Some(' ' | '\t' | '\r' | '\n')) {
                self.take();
            }
            if self.peek() != Some('#') {
                break;
            }
            while !matches!(self.peek(), None | Some('\r' | '\n')) {
                self.take();
            }
        }
    }

    fn parse_alternation(&mut self) -> Result<SyntaxNode, RawFrontendError> {
        self.skip_layout();
        let start = self.position;
        if self.peek() == Some('|') {
            return Err(diagnostic(
                RegexFrontendErrorCode::AlternationMissingLeft,
                self.position,
            ));
        }
        let mut branches = vec![self.parse_sequence()?];
        self.skip_layout();
        while self.peek() == Some('|') {
            let pipe_offset = self.position;
            self.take();
            self.skip_layout();
            if self.eof() || self.peek() == Some(')') {
                return Err(diagnostic(
                    RegexFrontendErrorCode::AlternationMissingRight,
                    pipe_offset,
                ));
            }
            if self.peek() == Some('|') {
                return Err(diagnostic(
                    RegexFrontendErrorCode::AlternationEmptyMiddle,
                    self.position,
                ));
            }
            branches.push(self.parse_sequence()?);
            self.skip_layout();
        }
        if branches.len() == 1 {
            Ok(branches.pop().expect("one branch"))
        } else {
            let end = branches.last().map_or(start, |branch| branch.end);
            Ok(SyntaxNode::cover(
                start,
                end,
                SyntaxKind::Alternation(branches),
            ))
        }
    }

    fn parse_sequence(&mut self) -> Result<SyntaxNode, RawFrontendError> {
        let start = self.position;
        let mut items = Vec::new();
        loop {
            self.skip_layout();
            let Some(character) = self.peek() else {
                break;
            };
            if matches!(character, '|' | ')') {
                break;
            }
            if matches!(character, '*' | '+' | '?' | '{') {
                return Err(diagnostic(
                    RegexFrontendErrorCode::QuantifierMissingAtom,
                    self.position,
                ));
            }
            let atom = self.parse_atom()?;
            let term = self.parse_quantifier(atom)?;
            push_sequence_item(&mut items, term);
        }
        match items.len() {
            0 => Ok(SyntaxNode::new(start, start, SyntaxKind::Empty)),
            1 => Ok(items.pop().expect("one item")),
            _ => {
                let end = items.last().map_or(start, |item| item.end);
                Ok(SyntaxNode::cover(start, end, SyntaxKind::Sequence(items)))
            }
        }
    }

    fn parse_atom(&mut self) -> Result<SyntaxNode, RawFrontendError> {
        let offset = self.position;
        let Some(character) = self.take() else {
            return Ok(SyntaxNode::new(offset, offset, SyntaxKind::Empty));
        };
        match character {
            '(' => self.parse_group(offset),
            '[' => self.parse_character_class(offset),
            '.' => Ok(SyntaxNode::new(offset, self.position, SyntaxKind::Wildcard)),
            '^' => Ok(SyntaxNode::new(
                offset,
                self.position,
                SyntaxKind::Position(if self.flags.multiline {
                    PositionKind::LineStart
                } else {
                    PositionKind::InputStart
                }),
            )),
            '$' => Ok(SyntaxNode::new(
                offset,
                self.position,
                SyntaxKind::Position(if self.flags.multiline {
                    PositionKind::LineEnd
                } else {
                    PositionKind::EndBeforeFinalLineTerminator
                }),
            )),
            '\\' => self
                .parse_escape(offset, false)
                .map(|value| SyntaxNode::new(offset, self.position, value.outside())),
            ']' | '}' => Err(diagnostic(RegexFrontendErrorCode::RawTargetSyntax, offset)),
            _ => Ok(SyntaxNode::new(
                offset,
                self.position,
                SyntaxKind::Literal(character.to_string()),
            )),
        }
    }

    fn parse_quantifier(&mut self, atom: SyntaxNode) -> Result<SyntaxNode, RawFrontendError> {
        self.skip_layout();
        let Some(character) = self.peek() else {
            return Ok(atom);
        };
        if !matches!(character, '*' | '+' | '?' | '{') {
            return Ok(atom);
        }
        let quantifier_offset = self.position;
        if atom.is_assertion() {
            return Err(diagnostic(
                RegexFrontendErrorCode::QuantifiedAssertion,
                quantifier_offset,
            ));
        }
        let (min, max) = match character {
            '*' => {
                self.take();
                (0, RepetitionMaximum::Unbounded)
            }
            '+' => {
                self.take();
                (1, RepetitionMaximum::Unbounded)
            }
            '?' => {
                self.take();
                (0, RepetitionMaximum::Bounded(1))
            }
            '{' => self.parse_braced_quantifier()?,
            _ => unreachable!(),
        };
        let mode = match self.peek() {
            Some('?') => {
                self.take();
                RepetitionMode::Lazy
            }
            Some('+') => {
                self.take();
                RepetitionMode::Possessive
            }
            _ => RepetitionMode::Greedy,
        };
        if matches!(self.peek(), Some('*' | '+' | '?' | '{')) {
            return Err(diagnostic(
                RegexFrontendErrorCode::StackedQuantifier,
                self.position,
            ));
        }
        let start = atom.start;
        Ok(SyntaxNode::cover(
            start,
            self.position,
            SyntaxKind::Repeat {
                body: Box::new(atom),
                min,
                max,
                mode,
            },
        ))
    }

    fn parse_braced_quantifier(&mut self) -> Result<(u64, RepetitionMaximum), RawFrontendError> {
        let brace_offset = self.position;
        self.take();
        let minimum_offset = self.position;
        let minimum = self.parse_bound(brace_offset, minimum_offset)?;
        match self.peek() {
            Some('}') => {
                self.take();
                Ok((minimum, RepetitionMaximum::Bounded(minimum)))
            }
            Some(',') => {
                self.take();
                if self.peek() == Some('}') {
                    self.take();
                    return Ok((minimum, RepetitionMaximum::Unbounded));
                }
                if self.eof() {
                    return Err(diagnostic(
                        RegexFrontendErrorCode::UnterminatedBraceQuantifier,
                        self.position,
                    ));
                }
                let maximum_offset = self.position;
                let maximum = self.parse_bound(brace_offset, maximum_offset)?;
                if self.peek() != Some('}') {
                    if self.eof() {
                        return Err(diagnostic(
                            RegexFrontendErrorCode::UnterminatedBraceQuantifier,
                            self.position,
                        ));
                    }
                    return Err(diagnostic(
                        RegexFrontendErrorCode::InvalidBraceQuantifier,
                        brace_offset,
                    ));
                }
                self.take();
                if minimum > maximum {
                    return Err(diagnostic(
                        RegexFrontendErrorCode::ReversedQuantifierBounds,
                        self.position,
                    ));
                }
                Ok((minimum, RepetitionMaximum::Bounded(maximum)))
            }
            None => Err(diagnostic(
                RegexFrontendErrorCode::UnterminatedBraceQuantifier,
                self.position,
            )),
            _ => Err(diagnostic(
                RegexFrontendErrorCode::InvalidBraceQuantifier,
                brace_offset,
            )),
        }
    }

    fn parse_bound(
        &mut self,
        brace_offset: usize,
        bound_offset: usize,
    ) -> Result<u64, RawFrontendError> {
        let start = self.position;
        while matches!(self.peek(), Some('0'..='9')) {
            self.take();
        }
        if self.position == start {
            return Err(diagnostic(
                RegexFrontendErrorCode::InvalidBraceQuantifier,
                brace_offset,
            ));
        }
        let digits = &self.text[start..self.position];
        let value = digits.parse::<u64>().map_err(|_| {
            diagnostic(
                RegexFrontendErrorCode::QuantifierBoundExceeded,
                bound_offset,
            )
        })?;
        if value > MAX_QUANTIFIER_BOUND {
            return Err(diagnostic(
                RegexFrontendErrorCode::QuantifierBoundExceeded,
                bound_offset,
            ));
        }
        Ok(value)
    }

    fn parse_group(&mut self, opener_offset: usize) -> Result<SyntaxNode, RawFrontendError> {
        if self.peek() == Some('*') {
            return Err(diagnostic(
                RegexFrontendErrorCode::RawTargetSyntax,
                self.position,
            ));
        }
        self.depth += 1;
        if self.depth > MAX_NESTING_DEPTH {
            return Err(diagnostic(
                RegexFrontendErrorCode::NestingTooDeep,
                opener_offset,
            ));
        }

        let mut capture: Option<(usize, Option<String>)> = None;
        let mut lookaround: Option<(LookaroundDirection, AssertionPolarity)> = None;
        let mut atomic = false;
        if self.peek() == Some('?') {
            let question_offset = self.position;
            self.take();
            if self.starts_with(":") {
                self.take();
            } else if self.starts_with(">") {
                self.take();
                atomic = true;
            } else if self.starts_with("=") {
                self.take();
                lookaround = Some((LookaroundDirection::Ahead, AssertionPolarity::Positive));
            } else if self.starts_with("!") {
                self.take();
                lookaround = Some((LookaroundDirection::Ahead, AssertionPolarity::Negative));
            } else if self.starts_with("<=") {
                self.position += 2;
                lookaround = Some((LookaroundDirection::Behind, AssertionPolarity::Positive));
            } else if self.starts_with("<!") {
                self.position += 2;
                lookaround = Some((LookaroundDirection::Behind, AssertionPolarity::Negative));
            } else if self.starts_with("<") {
                self.take();
                let name_start = self.position;
                let name = self.parse_identifier(RegexFrontendErrorCode::InvalidCaptureName)?;
                let name_end = self.position;
                if self.peek() != Some('>') {
                    return Err(diagnostic(
                        RegexFrontendErrorCode::InvalidCaptureName,
                        self.position,
                    ));
                }
                self.take();
                if let Some((_, first_offset)) = self.capture_names.get(&name) {
                    return Err(diagnostic(
                        RegexFrontendErrorCode::DuplicateCaptureName,
                        question_offset,
                    )
                    .with_related(
                        RelatedLocationRole::Definition,
                        "The first capture with this name is here.",
                        *first_offset,
                    ));
                }
                let index = self.new_capture(opener_offset)?;
                self.capture_names
                    .insert(name.clone(), (index, opener_offset));
                self.capture_declarations.push(RegexCaptureDeclaration {
                    index,
                    name: Some(name.clone()),
                    span: (name_start, name_end),
                });
                capture = Some((index, Some(name)));
            } else if matches!(
                self.peek(),
                Some('i' | 'I' | 'm' | 'M' | 's' | 'S' | 'u' | 'U' | 'x' | 'X')
            ) {
                return Err(diagnostic(
                    RegexFrontendErrorCode::InlineModifier,
                    question_offset,
                ));
            } else {
                return Err(diagnostic(
                    RegexFrontendErrorCode::UnsupportedGroupPrefix,
                    question_offset,
                ));
            }
        } else {
            let index = self.new_capture(opener_offset)?;
            self.capture_declarations.push(RegexCaptureDeclaration {
                index,
                name: None,
                span: (opener_offset, opener_offset + 1),
            });
            capture = Some((index, None));
        }

        let body = self.parse_alternation()?;
        self.skip_layout();
        if self.peek() != Some(')') {
            return Err(diagnostic(
                RegexFrontendErrorCode::UnterminatedGroup,
                self.position,
            ));
        }
        self.take();
        let end = self.position;
        self.depth -= 1;
        if let Some((direction, polarity)) = lookaround {
            Ok(SyntaxNode::cover(
                opener_offset,
                end,
                SyntaxKind::Lookaround {
                    direction,
                    polarity,
                    body: Box::new(body),
                },
            ))
        } else if atomic {
            Ok(SyntaxNode::cover(
                opener_offset,
                end,
                SyntaxKind::Atomic(Box::new(body)),
            ))
        } else if let Some((capture_index, name)) = capture {
            Ok(SyntaxNode::cover(
                opener_offset,
                end,
                SyntaxKind::Capture {
                    capture_index,
                    name,
                    body: Box::new(body),
                },
            ))
        } else {
            Ok(SyntaxNode::cover(opener_offset, end, body.kind))
        }
    }

    fn new_capture(&mut self, offset: usize) -> Result<usize, RawFrontendError> {
        if self.capture_count >= MAX_CAPTURE_GROUPS {
            return Err(diagnostic(RegexFrontendErrorCode::TooManyCaptures, offset));
        }
        self.capture_count += 1;
        Ok(self.capture_count)
    }

    fn parse_identifier(
        &mut self,
        error_code: RegexFrontendErrorCode,
    ) -> Result<String, RawFrontendError> {
        let start = self.position;
        let Some(first) = self.peek() else {
            return Err(diagnostic(error_code, self.position));
        };
        if !(first.is_ascii_alphabetic() || first == '_') {
            return Err(diagnostic(error_code, self.position));
        }
        self.take();
        while matches!(self.peek(), Some(character) if character.is_ascii_alphanumeric() || character == '_')
        {
            self.take();
        }
        Ok(self.text[start..self.position].to_owned())
    }

    fn parse_character_class(
        &mut self,
        opener_offset: usize,
    ) -> Result<SyntaxNode, RawFrontendError> {
        let mut negated = false;
        if self.peek() == Some('^') {
            self.take();
            negated = true;
        }
        let mut members = Vec::new();
        let mut item_count = 0;
        loop {
            if self.eof() {
                return Err(diagnostic(
                    RegexFrontendErrorCode::UnterminatedCharacterClass,
                    self.position,
                ));
            }
            if self.peek() == Some(']') {
                if item_count == 0 {
                    let later_close = self.text[self.position + 1..].contains(']');
                    if !later_close {
                        return Err(diagnostic(
                            RegexFrontendErrorCode::EmptyCharacterClass,
                            self.position,
                        ));
                    }
                } else {
                    self.take();
                    break;
                }
            }
            if self.starts_with("[:") {
                return Err(diagnostic(
                    RegexFrontendErrorCode::RawTargetSyntax,
                    self.position,
                ));
            }
            let left = self.parse_class_atom()?;
            let left_scalar = left.scalar;
            members.push(left.member);
            item_count += 1;

            if self.peek() == Some('-') && self.peek_after('-') != Some(']') {
                let hyphen_offset = self.position;
                self.take();
                if left_scalar.is_none() || self.eof() || self.peek() == Some(']') {
                    return Err(diagnostic(
                        RegexFrontendErrorCode::InvalidCharacterRangeEndpoint,
                        hyphen_offset,
                    ));
                }
                let right_offset = self.position;
                let right = self.parse_class_atom()?;
                let Some(right_scalar) = right.scalar else {
                    return Err(diagnostic(
                        RegexFrontendErrorCode::InvalidCharacterRangeEndpoint,
                        hyphen_offset,
                    ));
                };
                let left_scalar = left_scalar.expect("checked scalar endpoint");
                if left_scalar > right_scalar {
                    return Err(diagnostic(
                        RegexFrontendErrorCode::ReversedCharacterRange,
                        right_offset,
                    ));
                }
                members.pop();
                members.push(CharacterSetMember::Range {
                    start: UnicodeScalar::from_char(left_scalar),
                    end: UnicodeScalar::from_char(right_scalar),
                });
            }
        }
        members.sort_by_key(CharacterSetMember::canonical_key);
        members.dedup();
        Ok(SyntaxNode::cover(
            opener_offset,
            self.position,
            SyntaxKind::CharacterSet { negated, members },
        ))
    }

    fn parse_class_atom(&mut self) -> Result<ClassAtom, RawFrontendError> {
        let offset = self.position;
        let Some(character) = self.take() else {
            return Err(diagnostic(
                RegexFrontendErrorCode::UnterminatedCharacterClass,
                self.position,
            ));
        };
        if character == '\\' {
            return self
                .parse_escape(offset, true)
                .and_then(EscapeValue::class_atom);
        }
        Ok(ClassAtom::scalar(character))
    }

    fn parse_escape(
        &mut self,
        backslash_offset: usize,
        in_class: bool,
    ) -> Result<EscapeValue, RawFrontendError> {
        let Some(character) = self.take() else {
            return Err(diagnostic(
                RegexFrontendErrorCode::UnexpectedEscapeEnd,
                backslash_offset,
            ));
        };
        match character {
            'n' => Ok(EscapeValue::Scalar('\n')),
            'r' => Ok(EscapeValue::Scalar('\r')),
            't' => Ok(EscapeValue::Scalar('\t')),
            'f' => Ok(EscapeValue::Scalar('\u{000C}')),
            'v' => Ok(EscapeValue::Scalar('\u{000B}')),
            '0' => {
                if matches!(self.peek(), Some('0'..='9')) {
                    Err(diagnostic(
                        RegexFrontendErrorCode::OctalEscape,
                        backslash_offset,
                    ))
                } else {
                    Ok(EscapeValue::Scalar('\0'))
                }
            }
            'x' => self.parse_code_point_escape(
                backslash_offset,
                2,
                true,
                RegexFrontendErrorCode::InvalidHexEscape,
            ),
            'u' => self.parse_code_point_escape(
                backslash_offset,
                4,
                true,
                RegexFrontendErrorCode::InvalidUnicodeEscape,
            ),
            'U' => self.parse_code_point_escape(
                backslash_offset,
                8,
                false,
                RegexFrontendErrorCode::InvalidUnicodeEscape,
            ),
            'd' | 'D' | 'w' | 'W' | 's' | 'S' => Ok(EscapeValue::Member(shorthand_member(
                character,
                self.flags.unicode_classes,
            ))),
            'p' | 'P' => self.parse_property(backslash_offset, character == 'P'),
            'b' if !in_class => Ok(EscapeValue::Position(PositionKind::WordBoundary)),
            'B' if !in_class => Ok(EscapeValue::Position(PositionKind::NotWordBoundary)),
            'A' if !in_class => Ok(EscapeValue::Position(PositionKind::InputStart)),
            'Z' if !in_class => Ok(EscapeValue::Position(PositionKind::InputEnd)),
            'k' if !in_class => self.parse_named_backreference(backslash_offset),
            '1'..='9' if !in_class => {
                let start = self.position - 1;
                while matches!(self.peek(), Some('0'..='9')) {
                    self.take();
                }
                let digits = &self.text[start..self.position];
                if digits.len() >= 3 && digits.chars().all(|digit| matches!(digit, '0'..='7')) {
                    return Err(diagnostic(
                        RegexFrontendErrorCode::OctalEscape,
                        backslash_offset,
                    ));
                }
                let index = digits.parse::<usize>().unwrap_or(usize::MAX);
                if index <= self.capture_count {
                    self.references.push(RegexReference {
                        index,
                        span: (start, self.position),
                    });
                    Ok(EscapeValue::Backreference(index))
                } else {
                    self.pending_references.push(PendingReference {
                        offset: backslash_offset,
                        target: PendingTarget::Numeric(index),
                    });
                    Ok(EscapeValue::Backreference(1))
                }
            }
            '1'..='9' => Err(diagnostic(
                RegexFrontendErrorCode::OctalEscape,
                backslash_offset,
            )),
            'Q' => Err(diagnostic(
                RegexFrontendErrorCode::RawTargetSyntax,
                backslash_offset,
            )),
            punctuation if is_identity_escape(punctuation) => Ok(EscapeValue::Scalar(punctuation)),
            _ => Err(diagnostic(
                RegexFrontendErrorCode::UnknownEscape,
                backslash_offset,
            )),
        }
    }

    fn parse_code_point_escape(
        &mut self,
        backslash_offset: usize,
        fixed_digits: usize,
        allow_braces: bool,
        invalid_code: RegexFrontendErrorCode,
    ) -> Result<EscapeValue, RawFrontendError> {
        let digits = if allow_braces && self.peek() == Some('{') {
            self.take();
            let start = self.position;
            while matches!(self.peek(), Some(character) if character.is_ascii_hexdigit()) {
                self.take();
            }
            if self.position == start || self.peek() != Some('}') {
                return Err(diagnostic(invalid_code, backslash_offset));
            }
            let digits = &self.text[start..self.position];
            self.take();
            digits
        } else {
            let start = self.position;
            for _ in 0..fixed_digits {
                if !matches!(self.peek(), Some(character) if character.is_ascii_hexdigit()) {
                    return Err(diagnostic(invalid_code, backslash_offset));
                }
                self.take();
            }
            &self.text[start..self.position]
        };
        let value = u32::from_str_radix(digits, 16).map_err(|_| {
            diagnostic(
                RegexFrontendErrorCode::InvalidUnicodeScalar,
                backslash_offset,
            )
        })?;
        let scalar = char::from_u32(value).ok_or_else(|| {
            diagnostic(
                RegexFrontendErrorCode::InvalidUnicodeScalar,
                backslash_offset,
            )
        })?;
        Ok(EscapeValue::Scalar(scalar))
    }

    fn parse_property(
        &mut self,
        backslash_offset: usize,
        negated: bool,
    ) -> Result<EscapeValue, RawFrontendError> {
        if self.peek() != Some('{') {
            return Err(diagnostic(
                RegexFrontendErrorCode::PropertyBracesRequired,
                backslash_offset,
            ));
        }
        self.take();
        let content_start = self.position;
        while !matches!(self.peek(), None | Some('}')) {
            self.take();
        }
        if self.eof() {
            return Err(diagnostic(
                RegexFrontendErrorCode::UnterminatedProperty,
                backslash_offset,
            ));
        }
        let content = &self.text[content_start..self.position];
        self.take();
        let mut pieces = content.split('=');
        let property = pieces.next().unwrap_or_default();
        let value = pieces.next();
        if pieces.next().is_some()
            || !valid_identifier(property)
            || value.is_some_and(|item| !valid_identifier(item))
        {
            let offset = if content.is_empty() {
                content_start
            } else {
                backslash_offset
            };
            return Err(diagnostic(RegexFrontendErrorCode::EmptyProperty, offset));
        }
        Ok(EscapeValue::Member(CharacterSetMember::UnicodeProperty {
            property: property.to_owned(),
            value: value.map(str::to_owned),
            negated,
        }))
    }

    fn parse_named_backreference(
        &mut self,
        backslash_offset: usize,
    ) -> Result<EscapeValue, RawFrontendError> {
        if self.peek() != Some('<') {
            return Err(diagnostic(
                RegexFrontendErrorCode::MalformedNamedBackreference,
                backslash_offset,
            ));
        }
        self.take();
        let name_start = self.position;
        let name = match self.parse_identifier(RegexFrontendErrorCode::MalformedNamedBackreference)
        {
            Ok(name) => name,
            Err(_) => {
                return Err(diagnostic(
                    RegexFrontendErrorCode::MalformedNamedBackreference,
                    backslash_offset,
                ))
            }
        };
        let name_end = self.position;
        if self.peek() != Some('>') {
            return Err(diagnostic(
                RegexFrontendErrorCode::MalformedNamedBackreference,
                backslash_offset,
            ));
        }
        self.take();
        if let Some((index, _)) = self.capture_names.get(&name) {
            self.references.push(RegexReference {
                index: *index,
                span: (name_start, name_end),
            });
            Ok(EscapeValue::Backreference(*index))
        } else {
            self.pending_references.push(PendingReference {
                offset: backslash_offset,
                target: PendingTarget::Named(name),
            });
            Ok(EscapeValue::Backreference(1))
        }
    }
}

fn push_sequence_item(items: &mut Vec<SyntaxNode>, item: SyntaxNode) {
    let SyntaxNode {
        start,
        end,
        spans,
        kind,
    } = item;
    match kind {
        SyntaxKind::Literal(text) => {
            if let Some(SyntaxNode {
                end: previous_end,
                spans: previous_spans,
                kind: SyntaxKind::Literal(previous),
                ..
            }) = items.last_mut()
            {
                previous.push_str(&text);
                *previous_end = end.max(*previous_end);
                for span in spans {
                    if let Some(previous_span) = previous_spans.last_mut() {
                        if previous_span.1 == span.0 {
                            previous_span.1 = span.1;
                            continue;
                        }
                    }
                    previous_spans.push(span);
                }
            } else {
                items.push(SyntaxNode {
                    start,
                    end,
                    spans,
                    kind: SyntaxKind::Literal(text),
                });
            }
        }
        kind => items.push(SyntaxNode {
            start,
            end,
            spans,
            kind,
        }),
    }
}

fn valid_identifier(value: &str) -> bool {
    let mut characters = value.chars();
    matches!(characters.next(), Some(first) if first.is_ascii_alphabetic() || first == '_')
        && characters.all(|character| character.is_ascii_alphanumeric() || character == '_')
}

fn is_identity_escape(character: char) -> bool {
    matches!(
        character,
        '.' | '\\'
            | '|'
            | '('
            | ')'
            | '['
            | ']'
            | '{'
            | '}'
            | '^'
            | '$'
            | '*'
            | '+'
            | '?'
            | '/'
            | '-'
            | ':'
            | ','
            | ' '
            | '#'
    )
}

fn shorthand_member(character: char, unicode: bool) -> CharacterSetMember {
    let lower = character.to_ascii_lowercase();
    CharacterSetMember::Builtin {
        name: match lower {
            'd' => BuiltinClassName::Digit,
            'w' => BuiltinClassName::Word,
            's' => BuiltinClassName::Whitespace,
            _ => unreachable!(),
        },
        domain: if unicode {
            CharacterDomain::Unicode
        } else {
            CharacterDomain::Ascii
        },
        negated: character.is_ascii_uppercase(),
    }
}

struct ClassAtom {
    member: CharacterSetMember,
    scalar: Option<char>,
}

impl ClassAtom {
    fn scalar(value: char) -> Self {
        Self {
            member: CharacterSetMember::Literal {
                value: UnicodeScalar::from_char(value),
            },
            scalar: Some(value),
        }
    }
}

enum EscapeValue {
    Scalar(char),
    Member(CharacterSetMember),
    Position(PositionKind),
    Backreference(usize),
}

impl EscapeValue {
    fn outside(self) -> SyntaxKind {
        match self {
            Self::Scalar(value) => SyntaxKind::Literal(value.to_string()),
            Self::Member(member) => SyntaxKind::CharacterSet {
                negated: false,
                members: vec![member],
            },
            Self::Position(position) => SyntaxKind::Position(position),
            Self::Backreference(index) => SyntaxKind::Backreference(index),
        }
    }

    fn class_atom(self) -> Result<ClassAtom, RawFrontendError> {
        match self {
            Self::Scalar(value) => Ok(ClassAtom::scalar(value)),
            Self::Member(member) => Ok(ClassAtom {
                member,
                scalar: None,
            }),
            Self::Position(_) | Self::Backreference(_) => {
                Err(diagnostic(RegexFrontendErrorCode::UnknownEscape, 0))
            }
        }
    }
}

struct Lowerer {
    next_node: u64,
    dot_matches_line_terminators: bool,
    source_id: SourceId,
}

impl Lowerer {
    fn new(dot_matches_line_terminators: bool, source_id: SourceId) -> Self {
        Self {
            next_node: 0,
            dot_matches_line_terminators,
            source_id,
        }
    }

    fn lower(&mut self, syntax: SyntaxNode) -> Node {
        let node_id = self.node_id();
        let SyntaxNode { spans, kind, .. } = syntax;
        let origin = Some(SourceOrigin {
            source_spans: Some(
                spans
                    .into_iter()
                    .map(|(start, end)| {
                        SourceSpan::new(self.source_id.clone(), start as u64, end as u64)
                            .expect("parser syntax offsets form a valid source span")
                    })
                    .collect(),
            ),
            derived_from_node_ids: None,
        });
        match kind {
            SyntaxKind::Empty => Node::Empty { node_id, origin },
            SyntaxKind::Sequence(items) => Node::Sequence {
                node_id,
                origin,
                items: items.into_iter().map(|item| self.lower(item)).collect(),
            },
            SyntaxKind::Alternation(branches) => Node::Alternation {
                node_id,
                origin,
                branches: branches
                    .into_iter()
                    .map(|branch| self.lower(branch))
                    .collect(),
            },
            SyntaxKind::Literal(text) => Node::Literal {
                node_id,
                origin,
                text,
            },
            SyntaxKind::Wildcard => Node::Wildcard {
                node_id,
                origin,
                line_terminators: if self.dot_matches_line_terminators {
                    LineTerminators::Include
                } else {
                    LineTerminators::Exclude
                },
            },
            SyntaxKind::CharacterSet { negated, members } => Node::CharacterSet {
                node_id,
                origin,
                negated,
                members,
            },
            SyntaxKind::Repeat {
                body,
                min,
                max,
                mode,
            } => Node::Repeat {
                node_id,
                origin,
                body: Box::new(self.lower(*body)),
                min,
                max,
                mode,
            },
            SyntaxKind::Position(position) => Node::Position {
                node_id,
                origin,
                position,
            },
            SyntaxKind::Capture {
                capture_index,
                name,
                body,
            } => Node::Capture {
                node_id,
                origin,
                capture_id: capture_id(capture_index),
                name,
                body: Box::new(self.lower(*body)),
            },
            SyntaxKind::Backreference(index) => Node::Backreference {
                node_id,
                origin,
                capture_id: capture_id(index),
            },
            SyntaxKind::Lookaround {
                direction,
                polarity,
                body,
            } => Node::Lookaround {
                node_id,
                origin,
                direction,
                polarity,
                body: Box::new(self.lower(*body)),
            },
            SyntaxKind::Atomic(body) => Node::Atomic {
                node_id,
                origin,
                body: Box::new(self.lower(*body)),
            },
        }
    }

    fn node_id(&mut self) -> NodeId {
        self.next_node += 1;
        NodeId::try_from(format!("node:regex-compat/{:08}", self.next_node))
            .expect("generated node identity is valid")
    }
}

fn capture_id(index: usize) -> CaptureId {
    CaptureId::try_from(format!("capture:regex-compat/{index:05}"))
        .expect("generated capture identity is valid")
}
