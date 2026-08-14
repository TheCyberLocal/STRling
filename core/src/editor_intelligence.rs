//! Non-normative editor evidence projected by the canonical frontends.
//!
//! This module is public only so the unpublished `strling-editor-core` binary
//! can reuse the library implementation. It is not a language, compiler,
//! binding, target, runtime, or packaging contract.

use serde::{Deserialize, Serialize};
use serde_json::json;

use crate::source::SourceDocument;
use crate::{regex_frontend, semantic_frontend};

pub const EDITOR_EVIDENCE_CONTRACT_VERSION: &str = "1.0.0";
pub const EDITOR_PROJECTION_VERSION: &str = "1.1.0";
pub const MAX_COMPLETION_ITEMS: usize = 256;
pub const MAX_TOKENS: usize = 16_384;
pub const MAX_SYMBOLS: usize = 4_096;
pub const MAX_CAPTURE_LOCATIONS: usize = 16_384;
pub const MAX_REWRITE_ACTIONS: usize = 256;

/// Return the frontend-owned editor classification catalog for drift tests.
#[must_use]
pub fn semantic_keyword_terminals() -> &'static [&'static str] {
    semantic_frontend::KEYWORD_TERMINALS
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum EditorFrontend {
    Regex,
    Semantic,
}

impl EditorFrontend {
    fn source_identity(self) -> (&'static str, &'static str, &'static str, &'static str) {
        match self {
            Self::Regex => (
                "strling.regex-compat",
                "1.0.0",
                "text/x-strling-regex-compat",
                "imported",
            ),
            Self::Semantic => (
                "strling.semantic",
                "1.0.0",
                "text/x-strling-semantic",
                "authored",
            ),
        }
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct EditorRequest {
    pub contract_version: String,
    pub source_id: String,
    pub frontend: EditorFrontend,
    pub source: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub cursor_byte: Option<usize>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum EditorParseStatus {
    Complete,
    Incomplete,
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum EditorTokenType {
    String,
    Number,
    Operator,
    Regexp,
    Keyword,
    Function,
    Variable,
    Comment,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
pub struct EditorSpan {
    pub start: usize,
    pub end: usize,
}

impl EditorSpan {
    #[must_use]
    pub const fn new(start: usize, end: usize) -> Self {
        Self { start, end }
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct EditorToken {
    pub span: EditorSpan,
    #[serde(rename = "type")]
    pub token_type: EditorTokenType,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct EditorSymbol {
    pub node_id: String,
    pub kind: String,
    pub name: String,
    pub span: EditorSpan,
    pub selection_span: EditorSpan,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub capture_id: Option<String>,
    pub children: Vec<Self>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct EditorCaptureLink {
    pub capture_id: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
    pub declaration: EditorSpan,
    pub references: Vec<EditorSpan>,
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum EditorCompletionTier {
    ParserExpectedTerminal,
    CanonicalCaptureIdentity,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct EditorCompletion {
    pub identity: String,
    pub label: String,
    pub tier: EditorCompletionTier,
    pub detail: String,
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum EditorRewriteProofCondition {
    OriginalNodeIsRepeat,
    DirectBodyRelationship,
    BoundsExactlyOne,
    ModeNonPossessive,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct EditorRewriteAction {
    pub source_id: String,
    pub diagnostic_code: String,
    pub strategy_id: String,
    pub strategy_fingerprint: String,
    pub semantic_program: String,
    pub removed_wrapper_node_id: String,
    pub replacement_node_id: String,
    pub wrapper_span: EditorSpan,
    pub replacement_span: EditorSpan,
    pub replacement_text: String,
    pub proof_conditions: Vec<EditorRewriteProofCondition>,
    pub explanation: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct FrontendEditorEvidence {
    pub parse_status: EditorParseStatus,
    pub tokens: Vec<EditorToken>,
    pub symbols: Vec<EditorSymbol>,
    pub captures: Vec<EditorCaptureLink>,
    pub completions: Vec<EditorCompletion>,
    pub replacement_span: Option<EditorSpan>,
    pub formatted_source: Option<String>,
    pub rewrite_actions: Vec<EditorRewriteAction>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct EditorEvidence {
    pub contract_version: &'static str,
    pub projection_version: &'static str,
    pub source_id: String,
    pub frontend: EditorFrontend,
    pub parse_status: EditorParseStatus,
    pub tokens: Vec<EditorToken>,
    pub symbols: Vec<EditorSymbol>,
    pub captures: Vec<EditorCaptureLink>,
    pub completions: Vec<EditorCompletion>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub replacement_span: Option<EditorSpan>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub formatted_source: Option<String>,
    pub rewrite_actions: Vec<EditorRewriteAction>,
    pub truncated: bool,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct EditorRequestError {
    message: String,
}

impl EditorRequestError {
    fn new(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
        }
    }
}

impl std::fmt::Display for EditorRequestError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        self.message.fmt(formatter)
    }
}

impl std::error::Error for EditorRequestError {}

pub fn project(request: &EditorRequest) -> Result<EditorEvidence, EditorRequestError> {
    if request.contract_version != EDITOR_EVIDENCE_CONTRACT_VERSION {
        return Err(EditorRequestError::new(
            "unsupported editor evidence contract version",
        ));
    }
    if let Some(cursor) = request.cursor_byte {
        if cursor > request.source.len() || !request.source.is_char_boundary(cursor) {
            return Err(EditorRequestError::new(
                "cursor_byte must be a UTF-8 scalar boundary within source",
            ));
        }
    }
    let document = source_document(request)?;
    let mut projected = match request.frontend {
        EditorFrontend::Regex => {
            regex_frontend::project_editor(&document, &request.source, request.cursor_byte)
        }
        EditorFrontend::Semantic => {
            semantic_frontend::project_editor(&document, &request.source, request.cursor_byte)
        }
    };
    projected.completions.sort_by(|left, right| {
        (left.tier, &left.identity, &left.label).cmp(&(right.tier, &right.identity, &right.label))
    });
    let mut truncated = false;
    truncated |= truncate(&mut projected.completions, MAX_COMPLETION_ITEMS);
    truncated |= truncate(&mut projected.tokens, MAX_TOKENS);
    truncated |= truncate(&mut projected.rewrite_actions, MAX_REWRITE_ACTIONS);
    let symbol_count = count_symbols(&projected.symbols);
    if symbol_count > MAX_SYMBOLS {
        projected.symbols.clear();
        truncated = true;
    }
    let location_count = projected
        .captures
        .iter()
        .map(|capture| capture.references.len() + 1)
        .sum::<usize>();
    if location_count > MAX_CAPTURE_LOCATIONS {
        projected.captures.clear();
        truncated = true;
    }
    Ok(EditorEvidence {
        contract_version: EDITOR_EVIDENCE_CONTRACT_VERSION,
        projection_version: EDITOR_PROJECTION_VERSION,
        source_id: request.source_id.clone(),
        frontend: request.frontend,
        parse_status: projected.parse_status,
        tokens: projected.tokens,
        symbols: projected.symbols,
        captures: projected.captures,
        completions: projected.completions,
        replacement_span: projected.replacement_span,
        formatted_source: projected.formatted_source,
        rewrite_actions: projected.rewrite_actions,
        truncated,
    })
}

fn source_document(request: &EditorRequest) -> Result<SourceDocument, EditorRequestError> {
    let (frontend_id, dialect_version, media_type, provenance) = request.frontend.source_identity();
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "source_id": request.source_id,
        "specification_version": "1.0-draft.1",
        "frontend": {
            "id": frontend_id,
            "dialect_version": dialect_version
        },
        "content": {
            "kind": "inline",
            "encoding": "utf-8",
            "media_type": media_type,
            "text": request.source
        },
        "provenance": { "kind": provenance }
    }))
    .map_err(|error| EditorRequestError::new(format!("invalid source identity: {error}")))
}

fn truncate<T>(values: &mut Vec<T>, limit: usize) -> bool {
    if values.len() <= limit {
        return false;
    }
    values.truncate(limit);
    true
}

fn count_symbols(symbols: &[EditorSymbol]) -> usize {
    symbols
        .iter()
        .map(|symbol| 1 + count_symbols(&symbol.children))
        .sum()
}
