use std::collections::{BTreeMap, BTreeSet};

use crate::semantic::{Node, SemanticProgram};
use crate::source::{CaptureId, NodeId};

use super::{SemanticAnalysisError, SemanticAnalysisErrorCode, SemanticAnalysisErrors};

/// One logical capture declaration, independent of target engine numbering.
#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct CaptureDefinition {
    pub capture_id: CaptureId,
    pub definition_node_id: NodeId,
    pub body_node_id: NodeId,
    pub name: Option<String>,
}

/// Resolution of one backreference to its certified logical capture.
#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct BackreferenceResolution {
    pub backreference_node_id: NodeId,
    pub capture_id: CaptureId,
    pub definition_node_id: NodeId,
}

#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub(super) struct NodeCaptureFacts {
    pub captures_defined: BTreeSet<CaptureId>,
    pub captures_referenced: BTreeSet<CaptureId>,
    pub backreferences_used: BTreeSet<NodeId>,
    pub capture: Option<CaptureDefinition>,
    pub backreference: Option<BackreferenceResolution>,
}

pub(super) struct CaptureAnalysis {
    pub node_facts: BTreeMap<NodeId, NodeCaptureFacts>,
    pub definitions: BTreeMap<CaptureId, CaptureDefinition>,
    pub backreferences: BTreeMap<NodeId, BackreferenceResolution>,
}

pub(super) fn analyze_captures(
    input: &SemanticProgram,
) -> Result<CaptureAnalysis, SemanticAnalysisErrors> {
    let definitions = collect_definitions(&input.root)?;
    let mut analysis = CaptureAnalysis {
        node_facts: BTreeMap::new(),
        definitions,
        backreferences: BTreeMap::new(),
    };
    visit(&input.root, "$.root", &mut analysis)?;
    Ok(analysis)
}

fn collect_definitions(
    root: &Node,
) -> Result<BTreeMap<CaptureId, CaptureDefinition>, SemanticAnalysisErrors> {
    let mut definitions = BTreeMap::new();
    let mut pending = vec![(root, "$.root".to_owned())];
    while let Some((node, path)) = pending.pop() {
        match node {
            Node::Capture {
                node_id,
                capture_id,
                name,
                body,
                ..
            } => {
                let definition = CaptureDefinition {
                    capture_id: capture_id.clone(),
                    definition_node_id: node_id.clone(),
                    body_node_id: body.node_id().clone(),
                    name: name.clone(),
                };
                if definitions.insert(capture_id.clone(), definition).is_some() {
                    return Err(SemanticAnalysisErrors::single(SemanticAnalysisError::new(
                        SemanticAnalysisErrorCode::InvalidIdentity,
                        format!("{path}.capture_id"),
                        "logical capture identity must be unique",
                    )));
                }
                pending.push((body, format!("{path}.body")));
            }
            Node::Sequence { items, .. } => {
                pending.extend(
                    items
                        .iter()
                        .enumerate()
                        .rev()
                        .map(|(index, child)| (child, format!("{path}.items[{index}]"))),
                );
            }
            Node::Alternation { branches, .. } => {
                pending.extend(
                    branches
                        .iter()
                        .enumerate()
                        .rev()
                        .map(|(index, child)| (child, format!("{path}.branches[{index}]"))),
                );
            }
            Node::Repeat { body, .. }
            | Node::Lookaround { body, .. }
            | Node::Atomic { body, .. } => pending.push((body, format!("{path}.body"))),
            Node::Empty { .. }
            | Node::Literal { .. }
            | Node::Wildcard { .. }
            | Node::CharacterSet { .. }
            | Node::Position { .. }
            | Node::Backreference { .. } => {}
        }
    }
    Ok(definitions)
}

fn visit(
    node: &Node,
    path: &str,
    analysis: &mut CaptureAnalysis,
) -> Result<NodeCaptureFacts, SemanticAnalysisErrors> {
    let mut facts = match node {
        Node::Sequence { items, .. } => {
            let mut combined = NodeCaptureFacts::default();
            for (index, child) in items.iter().enumerate() {
                combined.merge(visit(child, &format!("{path}.items[{index}]"), analysis)?);
            }
            combined
        }
        Node::Alternation { branches, .. } => {
            let mut combined = NodeCaptureFacts::default();
            for (index, child) in branches.iter().enumerate() {
                combined.merge(visit(
                    child,
                    &format!("{path}.branches[{index}]"),
                    analysis,
                )?);
            }
            combined
        }
        Node::Repeat { body, .. } | Node::Lookaround { body, .. } | Node::Atomic { body, .. } => {
            visit(body, &format!("{path}.body"), analysis)?
        }
        Node::Capture {
            capture_id, body, ..
        } => {
            let mut nested = visit(body, &format!("{path}.body"), analysis)?;
            let definition = analysis
                .definitions
                .get(capture_id)
                .cloned()
                .ok_or_else(|| invariant(path, "capture definition was not indexed"))?;
            nested.captures_defined.insert(capture_id.clone());
            nested.capture = Some(definition);
            nested
        }
        Node::Backreference {
            node_id,
            capture_id,
            ..
        } => {
            let definition = analysis.definitions.get(capture_id).ok_or_else(|| {
                SemanticAnalysisErrors::single(SemanticAnalysisError::new(
                    SemanticAnalysisErrorCode::InvalidReference,
                    format!("{path}.capture_id"),
                    "backreference must resolve to a logical capture identity",
                ))
            })?;
            let resolution = BackreferenceResolution {
                backreference_node_id: node_id.clone(),
                capture_id: capture_id.clone(),
                definition_node_id: definition.definition_node_id.clone(),
            };
            if analysis
                .backreferences
                .insert(node_id.clone(), resolution.clone())
                .is_some()
            {
                return Err(SemanticAnalysisErrors::single(SemanticAnalysisError::new(
                    SemanticAnalysisErrorCode::InvalidIdentity,
                    format!("{path}.node_id"),
                    "backreference node identity must be unique",
                )));
            }
            NodeCaptureFacts {
                captures_defined: BTreeSet::new(),
                captures_referenced: BTreeSet::from([capture_id.clone()]),
                backreferences_used: BTreeSet::from([node_id.clone()]),
                capture: None,
                backreference: Some(resolution),
            }
        }
        Node::Empty { .. }
        | Node::Literal { .. }
        | Node::Wildcard { .. }
        | Node::CharacterSet { .. }
        | Node::Position { .. } => NodeCaptureFacts::default(),
    };

    let own_capture = if matches!(node, Node::Capture { .. }) {
        facts.capture.take()
    } else {
        None
    };
    let own_backreference = if matches!(node, Node::Backreference { .. }) {
        facts.backreference.take()
    } else {
        None
    };
    facts.capture = None;
    facts.backreference = None;
    let stored = NodeCaptureFacts {
        captures_defined: facts.captures_defined.clone(),
        captures_referenced: facts.captures_referenced.clone(),
        backreferences_used: facts.backreferences_used.clone(),
        capture: own_capture,
        backreference: own_backreference,
    };
    if analysis
        .node_facts
        .insert(node.node_id().clone(), stored)
        .is_some()
    {
        return Err(SemanticAnalysisErrors::single(SemanticAnalysisError::new(
            SemanticAnalysisErrorCode::InvalidIdentity,
            format!("{path}.node_id"),
            "node identity must be unique during capture analysis",
        )));
    }
    Ok(facts)
}

impl NodeCaptureFacts {
    fn merge(&mut self, child: Self) {
        self.captures_defined.extend(child.captures_defined);
        self.captures_referenced.extend(child.captures_referenced);
        self.backreferences_used.extend(child.backreferences_used);
    }
}

fn invariant(path: &str, message: &str) -> SemanticAnalysisErrors {
    SemanticAnalysisErrors::single(SemanticAnalysisError::new(
        SemanticAnalysisErrorCode::AnalysisInvariant,
        path,
        message,
    ))
}
