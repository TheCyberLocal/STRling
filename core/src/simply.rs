//! Idiomatic Rust construction for the host-neutral Simply builder protocol.

use std::collections::{BTreeMap, BTreeSet};
use std::error::Error;
use std::fmt;
use std::sync::Arc;

use serde::{Deserialize, Serialize};

use crate::normalization::{normalize, NormalizationErrorCode, NormalizationErrors};
use crate::protocol::{
    CompileInput, CompileRequest, CompilerOptions, RequestedOutput, ResourceLimits,
};
use crate::semantic::{
    AssertionPolarity, BuiltinClassName, CaseMatching, CharacterDomain, CharacterSetMember,
    LineTerminators, LookaroundDirection, Node, Normalization, PositionKind, RepetitionMaximum,
    RepetitionMode, SemanticProgram, UnicodeScalar,
};
use crate::source::{
    CaptureId, ContractVersion, NodeId, SourceDocument, SourceId, SourceOrigin,
    SpecificationVersion,
};
use crate::target::TargetProfileReference;
use crate::validation::{Validate, ValidationErrors};

/// The protocol version implemented by this native construction surface.
pub const SIMPLY_PROTOCOL_VERSION: &str = "1.0.0";

/// Explicit target-neutral options shared by every value in one builder.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SimplyOptions {
    pub case_matching: CaseMatching,
    pub builtin_character_domain: CharacterDomain,
    pub wildcard_line_terminators: LineTerminators,
}

impl Default for SimplyOptions {
    fn default() -> Self {
        Self {
            case_matching: CaseMatching::Sensitive,
            builtin_character_domain: CharacterDomain::Unicode,
            wildcard_line_terminators: LineTerminators::Exclude,
        }
    }
}

/// Protocol-shaped character-set input with Unicode scalar values represented by `char`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum SimplyCharacterSetMember {
    Literal {
        value: char,
    },
    Range {
        start: char,
        end: char,
    },
    Builtin {
        name: BuiltinClassName,
        domain: Option<CharacterDomain>,
        negated: bool,
    },
    UnicodeProperty {
        property: String,
        value: Option<String>,
        negated: bool,
    },
}

/// Compile-only routing appended after semantic construction has completed.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SimplyCompileProjection {
    pub target_profile: Option<TargetProfileReference>,
    pub requested_outputs: Vec<RequestedOutput>,
    pub compiler_options: CompilerOptions,
}

/// Stable machine identities for native Simply construction failures.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
pub enum SimplyErrorCode {
    #[serde(rename = "STRL-SIMPLY-0001")]
    InvalidArgument,
    #[serde(rename = "STRL-SIMPLY-0002")]
    InvalidBounds,
    #[serde(rename = "STRL-SIMPLY-0003")]
    DuplicateIdentity,
    #[serde(rename = "STRL-SIMPLY-0004")]
    DuplicateCaptureName,
    #[serde(rename = "STRL-SIMPLY-0005")]
    UnresolvedValue,
    #[serde(rename = "STRL-SIMPLY-0006")]
    UnresolvedCapture,
    #[serde(rename = "STRL-SIMPLY-0007")]
    ReusedValue,
    #[serde(rename = "STRL-SIMPLY-0008")]
    IncompatibleImport,
    #[serde(rename = "STRL-SIMPLY-0009")]
    InvalidProvenance,
    #[serde(rename = "STRL-SIMPLY-0010")]
    UnsupportedConstruct,
    #[serde(rename = "STRL-SIMPLY-0011")]
    InvalidCompileRequest,
    #[serde(rename = "STRL-SIMPLY-0012")]
    ResourceLimit,
}

impl SimplyErrorCode {
    /// Return the protocol-stable serialized error identity.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::InvalidArgument => "STRL-SIMPLY-0001",
            Self::InvalidBounds => "STRL-SIMPLY-0002",
            Self::DuplicateIdentity => "STRL-SIMPLY-0003",
            Self::DuplicateCaptureName => "STRL-SIMPLY-0004",
            Self::UnresolvedValue => "STRL-SIMPLY-0005",
            Self::UnresolvedCapture => "STRL-SIMPLY-0006",
            Self::ReusedValue => "STRL-SIMPLY-0007",
            Self::IncompatibleImport => "STRL-SIMPLY-0008",
            Self::InvalidProvenance => "STRL-SIMPLY-0009",
            Self::UnsupportedConstruct => "STRL-SIMPLY-0010",
            Self::InvalidCompileRequest => "STRL-SIMPLY-0011",
            Self::ResourceLimit => "STRL-SIMPLY-0012",
        }
    }
}

/// One stable Simply failure with a builder-request-shaped data path.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SimplyError {
    pub code: SimplyErrorCode,
    pub path: String,
}

impl SimplyError {
    fn new(code: SimplyErrorCode, path: impl Into<String>) -> Self {
        Self {
            code,
            path: path.into(),
        }
    }
}

/// Ordered failures returned without a partially constructed public result.
#[derive(Clone, Debug, Default, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SimplyErrors {
    pub errors: Vec<SimplyError>,
}

impl SimplyErrors {
    fn single(code: SimplyErrorCode, path: impl Into<String>) -> Self {
        Self {
            errors: vec![SimplyError::new(code, path)],
        }
    }
}

impl fmt::Display for SimplyErrors {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "{} Simply construction error(s)",
            self.errors.len()
        )
    }
}

impl Error for SimplyErrors {}

#[derive(Debug)]
struct OwnerToken;

/// An immutable, cloneable handle to one builder-owned semantic value.
#[derive(Clone, Debug)]
pub struct SimplyValue {
    owner: Arc<OwnerToken>,
    step_id: String,
}

impl SimplyValue {
    /// Return the stable protocol step key represented by this handle.
    #[must_use]
    pub fn step_id(&self) -> &str {
        &self.step_id
    }
}

#[derive(Clone, Debug)]
struct StoredValue {
    index: usize,
    consumed: bool,
    node: Node,
}

#[derive(Clone, Debug)]
struct PendingReference {
    capture_id: CaptureId,
    path: String,
}

#[derive(Default)]
struct NodeMetadata {
    node_ids: BTreeSet<NodeId>,
    capture_ids: BTreeSet<CaptureId>,
    capture_names: BTreeSet<String>,
}

/// A deterministic, single-parent construction graph over canonical Semantic IR nodes.
pub struct SimplyBuilder {
    owner: Arc<OwnerToken>,
    identity_namespace: String,
    specification_version: SpecificationVersion,
    options: SimplyOptions,
    values: BTreeMap<String, StoredValue>,
    node_ids: BTreeSet<NodeId>,
    capture_ids: BTreeSet<CaptureId>,
    capture_names: BTreeSet<String>,
    sources: BTreeMap<SourceId, SourceDocument>,
    pending_references: Vec<PendingReference>,
}

impl fmt::Debug for SimplyBuilder {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter
            .debug_struct("SimplyBuilder")
            .field("identity_namespace", &self.identity_namespace)
            .field("specification_version", &self.specification_version)
            .field("options", &self.options)
            .field("value_count", &self.values.len())
            .finish_non_exhaustive()
    }
}

impl SimplyBuilder {
    /// Start one explicit protocol graph. The Unicode scalar text model is fixed by the API.
    pub fn new(
        identity_namespace: &str,
        specification_version: SpecificationVersion,
        options: SimplyOptions,
    ) -> Result<Self, SimplyErrors> {
        if !valid_key(identity_namespace) {
            return Err(SimplyErrors::single(
                SimplyErrorCode::InvalidArgument,
                "$.identity_namespace",
            ));
        }
        Ok(Self {
            owner: Arc::new(OwnerToken),
            identity_namespace: identity_namespace.to_owned(),
            specification_version,
            options,
            values: BTreeMap::new(),
            node_ids: BTreeSet::new(),
            capture_ids: BTreeSet::new(),
            capture_names: BTreeSet::new(),
            sources: BTreeMap::new(),
            pending_references: Vec::new(),
        })
    }

    /// Construct an empty semantic value.
    pub fn empty(&mut self, step_id: &str) -> Result<SimplyValue, SimplyErrors> {
        let index = self.validate_step(step_id)?;
        let node_id = self.generated_node_id(step_id, index)?;
        self.ensure_node_identity(&node_id, index)?;
        self.node_ids.insert(node_id.clone());
        Ok(self.insert_value(
            step_id,
            index,
            Node::Empty {
                node_id,
                origin: None,
            },
        ))
    }

    /// Construct literal text; an empty string is the canonical empty node form.
    pub fn literal(&mut self, step_id: &str, text: &str) -> Result<SimplyValue, SimplyErrors> {
        let index = self.validate_step(step_id)?;
        let node_id = self.generated_node_id(step_id, index)?;
        self.ensure_node_identity(&node_id, index)?;
        let node = if text.is_empty() {
            Node::Empty {
                node_id: node_id.clone(),
                origin: None,
            }
        } else {
            Node::Literal {
                node_id: node_id.clone(),
                origin: None,
                text: text.to_owned(),
            }
        };
        self.node_ids.insert(node_id);
        Ok(self.insert_value(step_id, index, node))
    }

    /// Construct a wildcard, using the builder default when no override is supplied.
    pub fn wildcard(
        &mut self,
        step_id: &str,
        line_terminators: Option<LineTerminators>,
    ) -> Result<SimplyValue, SimplyErrors> {
        let index = self.validate_step(step_id)?;
        let node_id = self.generated_node_id(step_id, index)?;
        self.ensure_node_identity(&node_id, index)?;
        self.node_ids.insert(node_id.clone());
        Ok(self.insert_value(
            step_id,
            index,
            Node::Wildcard {
                node_id,
                origin: None,
                line_terminators: line_terminators
                    .unwrap_or(self.options.wildcard_line_terminators),
            },
        ))
    }

    /// Construct a canonical character set from protocol-shaped members.
    pub fn character_set(
        &mut self,
        step_id: &str,
        members: &[SimplyCharacterSetMember],
        negated: bool,
    ) -> Result<SimplyValue, SimplyErrors> {
        let index = self.validate_step(step_id)?;
        if members.is_empty() {
            return Err(SimplyErrors::single(
                SimplyErrorCode::InvalidArgument,
                format!("$.steps[{index}].arguments.members"),
            ));
        }
        let mut canonical = Vec::with_capacity(members.len());
        for (member_index, member) in members.iter().enumerate() {
            let path = format!("$.steps[{index}].arguments.members[{member_index}]");
            canonical.push(self.character_set_member(member, &path)?);
        }
        let node_id = self.generated_node_id(step_id, index)?;
        self.ensure_node_identity(&node_id, index)?;
        self.node_ids.insert(node_id.clone());
        Ok(self.insert_value(
            step_id,
            index,
            Node::CharacterSet {
                node_id,
                origin: None,
                negated,
                members: canonical,
            },
        ))
    }

    /// Construct an ordered sequence with at least two single-parent values.
    pub fn sequence(
        &mut self,
        step_id: &str,
        values: &[SimplyValue],
    ) -> Result<SimplyValue, SimplyErrors> {
        self.many_value(step_id, values, true)
    }

    /// Construct an ordered alternation with at least two single-parent values.
    pub fn alternation(
        &mut self,
        step_id: &str,
        values: &[SimplyValue],
    ) -> Result<SimplyValue, SimplyErrors> {
        self.many_value(step_id, values, false)
    }

    /// Add a transparent grouping identity to derivation provenance.
    pub fn group(
        &mut self,
        step_id: &str,
        value: &SimplyValue,
    ) -> Result<SimplyValue, SimplyErrors> {
        let index = self.validate_step(step_id)?;
        let group_id = self.generated_node_id(step_id, index)?;
        self.ensure_node_identity(&group_id, index)?;
        let (child_key, mut node) = self.resolve_one(value, index, "value")?;
        add_derived_origin(&mut node, group_id.clone());

        self.consume(&[child_key]);
        self.node_ids.insert(group_id);
        Ok(self.insert_value(step_id, index, node))
    }

    /// Construct a logical capture with an explicit stable key and optional unique name.
    pub fn capture(
        &mut self,
        step_id: &str,
        capture_key: &str,
        name: Option<&str>,
        value: &SimplyValue,
    ) -> Result<SimplyValue, SimplyErrors> {
        let index = self.validate_step(step_id)?;
        self.validate_key(
            capture_key,
            format!("$.steps[{index}].arguments.capture_key"),
        )?;
        if name.is_some_and(str::is_empty) {
            return Err(SimplyErrors::single(
                SimplyErrorCode::InvalidArgument,
                format!("$.steps[{index}].arguments.name"),
            ));
        }
        let node_id = self.generated_node_id(step_id, index)?;
        self.ensure_node_identity(&node_id, index)?;
        let capture_id = self.generated_capture_id(capture_key, index)?;
        if self.capture_ids.contains(&capture_id) {
            return Err(SimplyErrors::single(
                SimplyErrorCode::DuplicateIdentity,
                format!("$.steps[{index}].arguments.capture_key"),
            ));
        }
        if let Some(name) = name {
            if self.capture_names.contains(name) {
                return Err(SimplyErrors::single(
                    SimplyErrorCode::DuplicateCaptureName,
                    format!("$.steps[{index}].arguments.name"),
                ));
            }
        }
        let (child_key, body) = self.resolve_one(value, index, "value")?;

        self.consume(&[child_key]);
        self.node_ids.insert(node_id.clone());
        self.capture_ids.insert(capture_id.clone());
        if let Some(name) = name {
            self.capture_names.insert(name.to_owned());
        }
        Ok(self.insert_value(
            step_id,
            index,
            Node::Capture {
                node_id,
                origin: None,
                capture_id,
                name: name.map(str::to_owned),
                body: Box::new(body),
            },
        ))
    }

    /// Construct a logical backreference; capture resolution is checked at finish.
    pub fn backreference(
        &mut self,
        step_id: &str,
        capture_key: &str,
    ) -> Result<SimplyValue, SimplyErrors> {
        let index = self.validate_step(step_id)?;
        let path = format!("$.steps[{index}].arguments.capture_key");
        self.validate_key(capture_key, path.clone())?;
        let node_id = self.generated_node_id(step_id, index)?;
        self.ensure_node_identity(&node_id, index)?;
        let capture_id = self.generated_capture_id(capture_key, index)?;

        self.node_ids.insert(node_id.clone());
        self.pending_references.push(PendingReference {
            capture_id: capture_id.clone(),
            path,
        });
        Ok(self.insert_value(
            step_id,
            index,
            Node::Backreference {
                node_id,
                origin: None,
                capture_id,
            },
        ))
    }

    /// Construct an explicit canonical position assertion.
    pub fn position(
        &mut self,
        step_id: &str,
        position: PositionKind,
    ) -> Result<SimplyValue, SimplyErrors> {
        let index = self.validate_step(step_id)?;
        let node_id = self.generated_node_id(step_id, index)?;
        self.ensure_node_identity(&node_id, index)?;
        self.node_ids.insert(node_id.clone());
        Ok(self.insert_value(
            step_id,
            index,
            Node::Position {
                node_id,
                origin: None,
                position,
            },
        ))
    }

    /// Construct an explicit direction/polarity lookaround assertion.
    pub fn lookaround(
        &mut self,
        step_id: &str,
        direction: LookaroundDirection,
        polarity: AssertionPolarity,
        value: &SimplyValue,
    ) -> Result<SimplyValue, SimplyErrors> {
        let index = self.validate_step(step_id)?;
        let node_id = self.generated_node_id(step_id, index)?;
        self.ensure_node_identity(&node_id, index)?;
        let (child_key, body) = self.resolve_one(value, index, "value")?;

        self.consume(&[child_key]);
        self.node_ids.insert(node_id.clone());
        Ok(self.insert_value(
            step_id,
            index,
            Node::Lookaround {
                node_id,
                origin: None,
                direction,
                polarity,
                body: Box::new(body),
            },
        ))
    }

    /// Construct a target-neutral atomic group.
    pub fn atomic(
        &mut self,
        step_id: &str,
        value: &SimplyValue,
    ) -> Result<SimplyValue, SimplyErrors> {
        let index = self.validate_step(step_id)?;
        let node_id = self.generated_node_id(step_id, index)?;
        self.ensure_node_identity(&node_id, index)?;
        let (child_key, body) = self.resolve_one(value, index, "value")?;

        self.consume(&[child_key]);
        self.node_ids.insert(node_id.clone());
        Ok(self.insert_value(
            step_id,
            index,
            Node::Atomic {
                node_id,
                origin: None,
                body: Box::new(body),
            },
        ))
    }

    /// Construct a repetition with explicit finite/unbounded maximum and mode.
    pub fn repeat(
        &mut self,
        step_id: &str,
        value: &SimplyValue,
        min: u64,
        max: RepetitionMaximum,
        mode: RepetitionMode,
    ) -> Result<SimplyValue, SimplyErrors> {
        let index = self.validate_step(step_id)?;
        if matches!(max, RepetitionMaximum::Bounded(maximum) if maximum < min) {
            return Err(SimplyErrors::single(
                SimplyErrorCode::InvalidBounds,
                format!("$.steps[{index}].arguments.max"),
            ));
        }
        let node_id = self.generated_node_id(step_id, index)?;
        self.ensure_node_identity(&node_id, index)?;
        let (child_key, body) = self.resolve_one(value, index, "value")?;

        self.consume(&[child_key]);
        self.node_ids.insert(node_id.clone());
        Ok(self.insert_value(
            step_id,
            index,
            Node::Repeat {
                node_id,
                origin: None,
                body: Box::new(body),
                min,
                max,
                mode,
            },
        ))
    }

    /// Import one already-canonical Semantic IR node and its complete source set.
    pub fn import_node(
        &mut self,
        step_id: &str,
        node: Node,
        sources: Vec<SourceDocument>,
    ) -> Result<SimplyValue, SimplyErrors> {
        let index = self.validate_step(step_id)?;
        let imported_sources = self.prepare_sources(sources, index)?;
        let candidate = SemanticProgram {
            contract_version: ContractVersion::V1_0_0,
            specification_version: self.specification_version.clone(),
            normalization: Normalization::CanonicalV1,
            case_matching: self.options.case_matching,
            sources: map_sources(&imported_sources),
            root: node.clone(),
        };
        let normalized = normalize(&candidate).map_err(map_normalization_errors)?;
        if normalized.root != node {
            return Err(SimplyErrors::single(
                SimplyErrorCode::IncompatibleImport,
                format!("$.steps[{index}].arguments.node"),
            ));
        }
        let metadata = metadata(&node);
        self.validate_import_metadata(&metadata, index, "node")?;
        let merged_sources = self.merge_sources(&imported_sources, index)?;

        self.sources = merged_sources;
        self.register_metadata(metadata);
        Ok(self.insert_value(step_id, index, node))
    }

    /// Import one already-canonical Semantic IR program while preserving its root and sources.
    pub fn import_program(
        &mut self,
        step_id: &str,
        program: SemanticProgram,
    ) -> Result<SimplyValue, SimplyErrors> {
        let index = self.validate_step(step_id)?;
        if program.contract_version != ContractVersion::V1_0_0
            || program.specification_version != self.specification_version
            || program.normalization != Normalization::CanonicalV1
        {
            return Err(SimplyErrors::single(
                SimplyErrorCode::IncompatibleImport,
                format!("$.steps[{index}].arguments.program"),
            ));
        }
        if program.case_matching != self.options.case_matching {
            return Err(SimplyErrors::single(
                SimplyErrorCode::IncompatibleImport,
                format!("$.steps[{index}].arguments.program.case_matching"),
            ));
        }
        let imported_sources =
            self.prepare_sources(program.sources.clone().unwrap_or_default(), index)?;
        let candidate = SemanticProgram {
            sources: map_sources(&imported_sources),
            ..program.clone()
        };
        let normalized = normalize(&candidate).map_err(map_normalization_errors)?;
        if normalized.root != program.root {
            return Err(SimplyErrors::single(
                SimplyErrorCode::IncompatibleImport,
                format!("$.steps[{index}].arguments.program.root"),
            ));
        }
        let metadata = metadata(&program.root);
        self.validate_import_metadata(&metadata, index, "program.root")?;
        let merged_sources = self.merge_sources(&imported_sources, index)?;

        self.sources = merged_sources;
        self.register_metadata(metadata);
        Ok(self.insert_value(step_id, index, program.root))
    }

    /// Consume the graph and normalize it into the sole canonical Semantic IR program.
    pub fn finish_program(self, root: &SimplyValue) -> Result<SemanticProgram, SimplyErrors> {
        self.finish_program_inner(root)
    }

    /// Consume the graph, normalize it, and append compile-only routing.
    pub fn finish_request(
        self,
        root: &SimplyValue,
        mut projection: SimplyCompileProjection,
    ) -> Result<CompileRequest, SimplyErrors> {
        if projection.requested_outputs.is_empty() {
            return Err(SimplyErrors::single(
                SimplyErrorCode::InvalidCompileRequest,
                "$.compile.requested_outputs",
            ));
        }
        let output_count = projection.requested_outputs.len();
        projection.requested_outputs.sort();
        projection.requested_outputs.dedup();
        if projection.requested_outputs.len() != output_count {
            return Err(SimplyErrors::single(
                SimplyErrorCode::InvalidCompileRequest,
                "$.compile.requested_outputs",
            ));
        }

        let program = self.finish_program_inner(root)?;
        enforce_semantic_node_limit(&program, &projection.compiler_options.resource_limits)?;
        let request = CompileRequest {
            contract_version: ContractVersion::V1_0_0,
            specification_version: program.specification_version.clone(),
            input: CompileInput::Semantic {
                program: Box::new(program),
            },
            target_profile: projection.target_profile,
            requested_outputs: projection.requested_outputs,
            compiler_options: projection.compiler_options,
        };
        request.validate().map_err(map_compile_request_errors)?;
        Ok(request)
    }

    fn finish_program_inner(self, root: &SimplyValue) -> Result<SemanticProgram, SimplyErrors> {
        if !Arc::ptr_eq(&self.owner, &root.owner) {
            return Err(SimplyErrors::single(
                SimplyErrorCode::UnresolvedValue,
                "$.root_step_id",
            ));
        }
        let Some(root_value) = self.values.get(&root.step_id) else {
            return Err(SimplyErrors::single(
                SimplyErrorCode::UnresolvedValue,
                "$.root_step_id",
            ));
        };
        if root_value.consumed {
            return Err(SimplyErrors::single(
                SimplyErrorCode::ReusedValue,
                "$.root_step_id",
            ));
        }
        for (step_id, value) in &self.values {
            if step_id != &root.step_id && !value.consumed {
                return Err(SimplyErrors::single(
                    SimplyErrorCode::UnresolvedValue,
                    format!("$.steps[{}]", value.index),
                ));
            }
        }
        for reference in &self.pending_references {
            if !self.capture_ids.contains(&reference.capture_id) {
                return Err(SimplyErrors::single(
                    SimplyErrorCode::UnresolvedCapture,
                    reference.path.clone(),
                ));
            }
        }

        let candidate = SemanticProgram {
            contract_version: ContractVersion::V1_0_0,
            specification_version: self.specification_version,
            normalization: Normalization::CanonicalV1,
            case_matching: self.options.case_matching,
            sources: map_sources(&self.sources),
            root: root_value.node.clone(),
        };
        normalize(&candidate).map_err(map_normalization_errors)
    }

    fn many_value(
        &mut self,
        step_id: &str,
        values: &[SimplyValue],
        sequence: bool,
    ) -> Result<SimplyValue, SimplyErrors> {
        let index = self.validate_step(step_id)?;
        if values.len() < 2 {
            return Err(SimplyErrors::single(
                SimplyErrorCode::InvalidArgument,
                format!("$.steps[{index}].arguments.values"),
            ));
        }
        let node_id = self.generated_node_id(step_id, index)?;
        self.ensure_node_identity(&node_id, index)?;
        let (child_keys, children) = self.resolve_many(values, index)?;
        let node = if sequence {
            Node::Sequence {
                node_id: node_id.clone(),
                origin: None,
                items: children,
            }
        } else {
            Node::Alternation {
                node_id: node_id.clone(),
                origin: None,
                branches: children,
            }
        };

        self.consume(&child_keys);
        self.node_ids.insert(node_id);
        Ok(self.insert_value(step_id, index, node))
    }

    fn character_set_member(
        &self,
        member: &SimplyCharacterSetMember,
        path: &str,
    ) -> Result<CharacterSetMember, SimplyErrors> {
        match member {
            SimplyCharacterSetMember::Literal { value } => Ok(CharacterSetMember::Literal {
                value: UnicodeScalar::from_char(*value),
            }),
            SimplyCharacterSetMember::Range { start, end } => {
                if start > end {
                    return Err(SimplyErrors::single(SimplyErrorCode::InvalidArgument, path));
                }
                Ok(CharacterSetMember::Range {
                    start: UnicodeScalar::from_char(*start),
                    end: UnicodeScalar::from_char(*end),
                })
            }
            SimplyCharacterSetMember::Builtin {
                name,
                domain,
                negated,
            } => Ok(CharacterSetMember::Builtin {
                name: *name,
                domain: domain.unwrap_or(self.options.builtin_character_domain),
                negated: *negated,
            }),
            SimplyCharacterSetMember::UnicodeProperty {
                property,
                value,
                negated,
            } => {
                if property.is_empty() {
                    return Err(SimplyErrors::single(
                        SimplyErrorCode::InvalidArgument,
                        format!("{path}.property"),
                    ));
                }
                if value.as_ref().is_some_and(String::is_empty) {
                    return Err(SimplyErrors::single(
                        SimplyErrorCode::InvalidArgument,
                        format!("{path}.value"),
                    ));
                }
                Ok(CharacterSetMember::UnicodeProperty {
                    property: property.clone(),
                    value: value.clone(),
                    negated: *negated,
                })
            }
        }
    }

    fn validate_step(&self, step_id: &str) -> Result<usize, SimplyErrors> {
        let index = self.values.len();
        self.validate_key(step_id, format!("$.steps[{index}].step_id"))?;
        if self.values.contains_key(step_id) {
            return Err(SimplyErrors::single(
                SimplyErrorCode::DuplicateIdentity,
                format!("$.steps[{index}].step_id"),
            ));
        }
        Ok(index)
    }

    fn validate_key(&self, key: &str, path: String) -> Result<(), SimplyErrors> {
        if valid_key(key) {
            Ok(())
        } else {
            Err(SimplyErrors::single(SimplyErrorCode::InvalidArgument, path))
        }
    }

    fn generated_node_id(&self, step_id: &str, index: usize) -> Result<NodeId, SimplyErrors> {
        NodeId::try_from(format!("node:simply/{}/{step_id}", self.identity_namespace)).map_err(
            |_| {
                SimplyErrors::single(
                    SimplyErrorCode::InvalidArgument,
                    format!("$.steps[{index}].step_id"),
                )
            },
        )
    }

    fn generated_capture_id(
        &self,
        capture_key: &str,
        index: usize,
    ) -> Result<CaptureId, SimplyErrors> {
        CaptureId::try_from(format!(
            "capture:simply/{}/{capture_key}",
            self.identity_namespace
        ))
        .map_err(|_| {
            SimplyErrors::single(
                SimplyErrorCode::InvalidArgument,
                format!("$.steps[{index}].arguments.capture_key"),
            )
        })
    }

    fn ensure_node_identity(&self, node_id: &NodeId, index: usize) -> Result<(), SimplyErrors> {
        if self.node_ids.contains(node_id) {
            Err(SimplyErrors::single(
                SimplyErrorCode::DuplicateIdentity,
                format!("$.steps[{index}].step_id"),
            ))
        } else {
            Ok(())
        }
    }

    fn resolve_one(
        &self,
        value: &SimplyValue,
        index: usize,
        argument: &str,
    ) -> Result<(String, Node), SimplyErrors> {
        if !Arc::ptr_eq(&self.owner, &value.owner) {
            return Err(SimplyErrors::single(
                SimplyErrorCode::UnresolvedValue,
                format!("$.steps[{index}].arguments.{argument}"),
            ));
        }
        let Some(stored) = self.values.get(&value.step_id) else {
            return Err(SimplyErrors::single(
                SimplyErrorCode::UnresolvedValue,
                format!("$.steps[{index}].arguments.{argument}"),
            ));
        };
        if stored.consumed {
            return Err(SimplyErrors::single(
                SimplyErrorCode::ReusedValue,
                format!("$.steps[{index}].arguments.{argument}"),
            ));
        }
        Ok((value.step_id.clone(), stored.node.clone()))
    }

    fn resolve_many(
        &self,
        values: &[SimplyValue],
        index: usize,
    ) -> Result<(Vec<String>, Vec<Node>), SimplyErrors> {
        let mut seen = BTreeSet::new();
        let mut keys = Vec::with_capacity(values.len());
        let mut nodes = Vec::with_capacity(values.len());
        for (value_index, value) in values.iter().enumerate() {
            let path = format!("$.steps[{index}].arguments.values[{value_index}]");
            if !Arc::ptr_eq(&self.owner, &value.owner) {
                return Err(SimplyErrors::single(SimplyErrorCode::UnresolvedValue, path));
            }
            let Some(stored) = self.values.get(&value.step_id) else {
                return Err(SimplyErrors::single(SimplyErrorCode::UnresolvedValue, path));
            };
            if stored.consumed || !seen.insert(value.step_id.as_str()) {
                return Err(SimplyErrors::single(SimplyErrorCode::ReusedValue, path));
            }
            keys.push(value.step_id.clone());
            nodes.push(stored.node.clone());
        }
        Ok((keys, nodes))
    }

    fn consume(&mut self, keys: &[String]) {
        for key in keys {
            if let Some(value) = self.values.get_mut(key) {
                value.consumed = true;
            }
        }
    }

    fn insert_value(&mut self, step_id: &str, index: usize, node: Node) -> SimplyValue {
        self.values.insert(
            step_id.to_owned(),
            StoredValue {
                index,
                consumed: false,
                node,
            },
        );
        SimplyValue {
            owner: self.owner.clone(),
            step_id: step_id.to_owned(),
        }
    }

    fn prepare_sources(
        &self,
        sources: Vec<SourceDocument>,
        index: usize,
    ) -> Result<BTreeMap<SourceId, SourceDocument>, SimplyErrors> {
        let mut prepared = BTreeMap::new();
        for source in sources {
            if source.contract_version != ContractVersion::V1_0_0
                || source.specification_version != self.specification_version
            {
                return Err(SimplyErrors::single(
                    SimplyErrorCode::IncompatibleImport,
                    format!("$.steps[{index}].arguments.sources"),
                ));
            }
            source.validate().map_err(|_| {
                SimplyErrors::single(
                    SimplyErrorCode::InvalidProvenance,
                    format!("$.steps[{index}].arguments.sources"),
                )
            })?;
            match prepared.get(&source.source_id) {
                Some(existing) if existing != &source => {
                    return Err(SimplyErrors::single(
                        SimplyErrorCode::IncompatibleImport,
                        format!("$.steps[{index}].arguments.sources"),
                    ));
                }
                Some(_) => {}
                None => {
                    prepared.insert(source.source_id.clone(), source);
                }
            }
        }
        Ok(prepared)
    }

    fn merge_sources(
        &self,
        imported: &BTreeMap<SourceId, SourceDocument>,
        index: usize,
    ) -> Result<BTreeMap<SourceId, SourceDocument>, SimplyErrors> {
        let mut merged = self.sources.clone();
        for (source_id, source) in imported {
            match merged.get(source_id) {
                Some(existing) if existing != source => {
                    return Err(SimplyErrors::single(
                        SimplyErrorCode::IncompatibleImport,
                        format!("$.steps[{index}].arguments.sources"),
                    ));
                }
                Some(_) => {}
                None => {
                    merged.insert(source_id.clone(), source.clone());
                }
            }
        }
        Ok(merged)
    }

    fn validate_import_metadata(
        &self,
        metadata: &NodeMetadata,
        index: usize,
        argument: &str,
    ) -> Result<(), SimplyErrors> {
        if metadata
            .node_ids
            .iter()
            .any(|node_id| self.node_ids.contains(node_id))
            || metadata
                .capture_ids
                .iter()
                .any(|capture_id| self.capture_ids.contains(capture_id))
        {
            return Err(SimplyErrors::single(
                SimplyErrorCode::DuplicateIdentity,
                format!("$.steps[{index}].arguments.{argument}"),
            ));
        }
        if metadata
            .capture_names
            .iter()
            .any(|name| self.capture_names.contains(name))
        {
            return Err(SimplyErrors::single(
                SimplyErrorCode::DuplicateCaptureName,
                format!("$.steps[{index}].arguments.{argument}"),
            ));
        }
        Ok(())
    }

    fn register_metadata(&mut self, metadata: NodeMetadata) {
        self.node_ids.extend(metadata.node_ids);
        self.capture_ids.extend(metadata.capture_ids);
        self.capture_names.extend(metadata.capture_names);
    }
}

fn valid_key(value: &str) -> bool {
    let mut characters = value.chars();
    let Some(first) = characters.next() else {
        return false;
    };
    if !first.is_ascii_lowercase() {
        return false;
    }
    let mut separator = false;
    for character in characters {
        if character.is_ascii_lowercase() || character.is_ascii_digit() {
            separator = false;
        } else if matches!(character, '.' | '_' | '/' | '-') && !separator {
            separator = true;
        } else {
            return false;
        }
    }
    !separator
}

fn add_derived_origin(node: &mut Node, node_id: NodeId) {
    let origin = node_origin_mut(node).get_or_insert(SourceOrigin {
        source_spans: None,
        derived_from_node_ids: None,
    });
    let derived = origin.derived_from_node_ids.get_or_insert_with(Vec::new);
    derived.push(node_id);
    derived.sort();
    derived.dedup();
}

fn node_origin_mut(node: &mut Node) -> &mut Option<SourceOrigin> {
    match node {
        Node::Empty { origin, .. }
        | Node::Sequence { origin, .. }
        | Node::Alternation { origin, .. }
        | Node::Literal { origin, .. }
        | Node::Wildcard { origin, .. }
        | Node::CharacterSet { origin, .. }
        | Node::Repeat { origin, .. }
        | Node::Position { origin, .. }
        | Node::Capture { origin, .. }
        | Node::Backreference { origin, .. }
        | Node::Lookaround { origin, .. }
        | Node::Atomic { origin, .. } => origin,
    }
}

fn metadata(node: &Node) -> NodeMetadata {
    fn visit(node: &Node, metadata: &mut NodeMetadata) {
        metadata.node_ids.insert(node.node_id().clone());
        match node {
            Node::Sequence { items, .. } => {
                for child in items {
                    visit(child, metadata);
                }
            }
            Node::Alternation { branches, .. } => {
                for child in branches {
                    visit(child, metadata);
                }
            }
            Node::Capture {
                capture_id,
                name,
                body,
                ..
            } => {
                metadata.capture_ids.insert(capture_id.clone());
                if let Some(name) = name {
                    metadata.capture_names.insert(name.clone());
                }
                visit(body, metadata);
            }
            Node::Repeat { body, .. }
            | Node::Lookaround { body, .. }
            | Node::Atomic { body, .. } => visit(body, metadata),
            Node::Empty { .. }
            | Node::Literal { .. }
            | Node::Wildcard { .. }
            | Node::CharacterSet { .. }
            | Node::Position { .. }
            | Node::Backreference { .. } => {}
        }
    }

    let mut result = NodeMetadata::default();
    visit(node, &mut result);
    result
}

fn map_sources(sources: &BTreeMap<SourceId, SourceDocument>) -> Option<Vec<SourceDocument>> {
    if sources.is_empty() {
        None
    } else {
        Some(sources.values().cloned().collect())
    }
}

fn map_normalization_errors(errors: NormalizationErrors) -> SimplyErrors {
    SimplyErrors {
        errors: errors
            .errors
            .into_iter()
            .map(|error| {
                let code = match error.code {
                    NormalizationErrorCode::InvalidIdentity => SimplyErrorCode::DuplicateIdentity,
                    NormalizationErrorCode::InvalidReference => SimplyErrorCode::UnresolvedCapture,
                    NormalizationErrorCode::InvalidRepetitionBounds => {
                        SimplyErrorCode::InvalidBounds
                    }
                    NormalizationErrorCode::InvalidProvenance => SimplyErrorCode::InvalidProvenance,
                    NormalizationErrorCode::UnsupportedContractState => {
                        SimplyErrorCode::IncompatibleImport
                    }
                    NormalizationErrorCode::InvalidSemanticStructure
                    | NormalizationErrorCode::InvalidCharacterSet
                    | NormalizationErrorCode::CanonicalizationInvariant => {
                        SimplyErrorCode::InvalidArgument
                    }
                };
                SimplyError::new(code, error.path)
            })
            .collect(),
    }
}

fn map_compile_request_errors(errors: ValidationErrors) -> SimplyErrors {
    SimplyErrors {
        errors: errors
            .errors
            .into_iter()
            .map(|error| {
                let suffix = error.path.strip_prefix('$').unwrap_or(&error.path);
                SimplyError::new(
                    SimplyErrorCode::InvalidCompileRequest,
                    format!("$.compile{suffix}"),
                )
            })
            .collect(),
    }
}

fn enforce_semantic_node_limit(
    program: &SemanticProgram,
    limits: &Option<ResourceLimits>,
) -> Result<(), SimplyErrors> {
    if let Some(maximum) = limits.as_ref().and_then(|limits| limits.max_semantic_nodes) {
        let node_count = u64::try_from(program.node_ids().len()).unwrap_or(u64::MAX);
        if node_count > maximum {
            return Err(SimplyErrors::single(
                SimplyErrorCode::ResourceLimit,
                "$.compile.compiler_options.resource_limits.max_semantic_nodes",
            ));
        }
    }
    Ok(())
}
