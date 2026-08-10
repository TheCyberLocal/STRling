use std::collections::{BTreeMap, BTreeSet};

use crate::semantic::{Node, RepetitionMaximum, SemanticProgram};
use crate::source::{CaptureId, NodeId};

use super::{SemanticAnalysisError, SemanticAnalysisErrorCode, SemanticAnalysisErrors};

/// Whether successful matching can consume zero Unicode scalar values.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum Nullability {
    Nullable,
    NonNullable,
    Unknown,
}

/// Maximum successful consumption in Unicode scalar values.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum MaximumConsumption {
    Finite(u64),
    Unbounded,
}

/// Foundational relationship between successful matches and consumption.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum Consumption {
    AlwaysZeroWidth,
    AlwaysConsuming,
    Variable,
    Indeterminate,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) struct ConsumptionFacts {
    pub nullability: Nullability,
    pub minimum: u64,
    pub maximum: MaximumConsumption,
    pub consumption: Consumption,
}

pub(super) fn analyze_consumption(
    input: &SemanticProgram,
) -> Result<BTreeMap<NodeId, ConsumptionFacts>, SemanticAnalysisErrors> {
    ConsumptionAnalyzer::new(&input.root).analyze(&input.root, "$.root")
}

struct ConsumptionAnalyzer<'a> {
    captures: BTreeMap<CaptureId, &'a Node>,
    facts: BTreeMap<NodeId, ConsumptionFacts>,
    visiting: BTreeSet<NodeId>,
}

impl<'a> ConsumptionAnalyzer<'a> {
    fn new(root: &'a Node) -> Self {
        let mut captures = BTreeMap::new();
        let mut pending = vec![root];
        while let Some(node) = pending.pop() {
            match node {
                Node::Capture {
                    capture_id, body, ..
                } => {
                    captures.insert(capture_id.clone(), body.as_ref());
                    pending.push(body);
                }
                Node::Sequence { items, .. } => pending.extend(items.iter().rev()),
                Node::Alternation { branches, .. } => pending.extend(branches.iter().rev()),
                Node::Repeat { body, .. }
                | Node::Lookaround { body, .. }
                | Node::Atomic { body, .. } => pending.push(body),
                Node::Empty { .. }
                | Node::Literal { .. }
                | Node::Wildcard { .. }
                | Node::CharacterSet { .. }
                | Node::Position { .. }
                | Node::Backreference { .. } => {}
            }
        }
        Self {
            captures,
            facts: BTreeMap::new(),
            visiting: BTreeSet::new(),
        }
    }

    fn analyze(
        mut self,
        root: &'a Node,
        path: &str,
    ) -> Result<BTreeMap<NodeId, ConsumptionFacts>, SemanticAnalysisErrors> {
        self.node(root, path)?;
        Ok(self.facts)
    }

    fn node(
        &mut self,
        node: &'a Node,
        path: &str,
    ) -> Result<ConsumptionFacts, SemanticAnalysisErrors> {
        if let Some(facts) = self.facts.get(node.node_id()) {
            return Ok(*facts);
        }
        if !self.visiting.insert(node.node_id().clone()) {
            return Ok(ConsumptionFacts::conservative_reference_cycle());
        }

        let facts = match node {
            Node::Empty { .. } | Node::Position { .. } => ConsumptionFacts::zero_width(),
            Node::Literal { text, .. } => {
                let length = u64::try_from(text.chars().count()).map_err(|_| {
                    overflow(path, "literal Unicode scalar count does not fit in u64")
                })?;
                ConsumptionFacts::fixed(length)
            }
            Node::Wildcard { .. } | Node::CharacterSet { .. } => ConsumptionFacts::fixed(1),
            Node::Sequence { items, .. } => {
                let mut children = Vec::with_capacity(items.len());
                for (index, child) in items.iter().enumerate() {
                    children.push(self.node(child, &format!("{path}.items[{index}]"))?);
                }
                sequence(&children, path)?
            }
            Node::Alternation { branches, .. } => {
                let mut children = Vec::with_capacity(branches.len());
                for (index, child) in branches.iter().enumerate() {
                    children.push(self.node(child, &format!("{path}.branches[{index}]"))?);
                }
                alternation(&children)
            }
            Node::Repeat { body, min, max, .. } => {
                let body = self.node(body, &format!("{path}.body"))?;
                repeat(body, *min, *max, path)?
            }
            Node::Capture { body, .. } | Node::Atomic { body, .. } => {
                self.node(body, &format!("{path}.body"))?
            }
            Node::Backreference { capture_id, .. } => {
                let Some(body) = self.captures.get(capture_id).copied() else {
                    return Err(SemanticAnalysisErrors::single(SemanticAnalysisError::new(
                        SemanticAnalysisErrorCode::InvalidReference,
                        format!("{path}.capture_id"),
                        "backreference must resolve to a logical capture identity",
                    )));
                };
                let referenced = self.node(body, path)?;
                backreference(referenced)
            }
            Node::Lookaround { body, .. } => {
                self.node(body, &format!("{path}.body"))?;
                ConsumptionFacts::zero_width()
            }
        };

        self.visiting.remove(node.node_id());
        self.facts.insert(node.node_id().clone(), facts);
        Ok(facts)
    }
}

impl ConsumptionFacts {
    fn new(nullability: Nullability, minimum: u64, maximum: MaximumConsumption) -> Self {
        Self {
            nullability,
            minimum,
            maximum,
            consumption: classify(nullability, minimum, maximum),
        }
    }

    fn zero_width() -> Self {
        Self::new(Nullability::Nullable, 0, MaximumConsumption::Finite(0))
    }

    fn fixed(length: u64) -> Self {
        Self::new(
            if length == 0 {
                Nullability::Nullable
            } else {
                Nullability::NonNullable
            },
            length,
            MaximumConsumption::Finite(length),
        )
    }

    fn conservative_reference_cycle() -> Self {
        Self::new(Nullability::Unknown, 0, MaximumConsumption::Unbounded)
    }
}

fn sequence(
    children: &[ConsumptionFacts],
    path: &str,
) -> Result<ConsumptionFacts, SemanticAnalysisErrors> {
    let nullability = if children
        .iter()
        .any(|child| child.nullability == Nullability::NonNullable)
    {
        Nullability::NonNullable
    } else if children
        .iter()
        .all(|child| child.nullability == Nullability::Nullable)
    {
        Nullability::Nullable
    } else {
        Nullability::Unknown
    };

    let minimum = children.iter().try_fold(0_u64, |total, child| {
        total
            .checked_add(child.minimum)
            .ok_or_else(|| overflow(path, "sequence minimum consumption overflowed u64"))
    })?;

    let maximum = if children
        .iter()
        .any(|child| child.maximum == MaximumConsumption::Unbounded)
    {
        MaximumConsumption::Unbounded
    } else {
        MaximumConsumption::Finite(children.iter().try_fold(0_u64, |total, child| {
            match child.maximum {
                MaximumConsumption::Finite(maximum) => total
                    .checked_add(maximum)
                    .ok_or_else(|| overflow(path, "sequence maximum consumption overflowed u64")),
                MaximumConsumption::Unbounded => unreachable!("unbounded maximum handled above"),
            }
        })?)
    };

    Ok(ConsumptionFacts::new(nullability, minimum, maximum))
}

fn alternation(children: &[ConsumptionFacts]) -> ConsumptionFacts {
    let nullability = if children
        .iter()
        .any(|child| child.nullability == Nullability::Nullable)
    {
        Nullability::Nullable
    } else if children
        .iter()
        .all(|child| child.nullability == Nullability::NonNullable)
    {
        Nullability::NonNullable
    } else {
        Nullability::Unknown
    };
    let minimum = children
        .iter()
        .map(|child| child.minimum)
        .min()
        .expect("canonical alternation has at least two branches");
    let maximum = if children
        .iter()
        .any(|child| child.maximum == MaximumConsumption::Unbounded)
    {
        MaximumConsumption::Unbounded
    } else {
        MaximumConsumption::Finite(
            children
                .iter()
                .filter_map(|child| match child.maximum {
                    MaximumConsumption::Finite(maximum) => Some(maximum),
                    MaximumConsumption::Unbounded => None,
                })
                .max()
                .expect("canonical alternation has finite branch maxima"),
        )
    };
    ConsumptionFacts::new(nullability, minimum, maximum)
}

fn repeat(
    body: ConsumptionFacts,
    minimum_repetitions: u64,
    maximum_repetitions: RepetitionMaximum,
    path: &str,
) -> Result<ConsumptionFacts, SemanticAnalysisErrors> {
    let nullability = if minimum_repetitions == 0 {
        Nullability::Nullable
    } else {
        body.nullability
    };
    let minimum = body
        .minimum
        .checked_mul(minimum_repetitions)
        .ok_or_else(|| overflow(path, "repetition minimum consumption overflowed u64"))?;
    let maximum =
        match (body.maximum, maximum_repetitions) {
            (_, RepetitionMaximum::Bounded(0))
            | (MaximumConsumption::Finite(0), RepetitionMaximum::Unbounded) => {
                MaximumConsumption::Finite(0)
            }
            (MaximumConsumption::Unbounded, _) | (_, RepetitionMaximum::Unbounded) => {
                MaximumConsumption::Unbounded
            }
            (MaximumConsumption::Finite(body_maximum), RepetitionMaximum::Bounded(repetitions)) => {
                MaximumConsumption::Finite(body_maximum.checked_mul(repetitions).ok_or_else(
                    || overflow(path, "repetition maximum consumption overflowed u64"),
                )?)
            }
        };
    Ok(ConsumptionFacts::new(nullability, minimum, maximum))
}

fn backreference(referenced: ConsumptionFacts) -> ConsumptionFacts {
    let nullability = if referenced.minimum > 0 {
        Nullability::NonNullable
    } else {
        Nullability::Unknown
    };
    ConsumptionFacts::new(nullability, referenced.minimum, referenced.maximum)
}

fn classify(nullability: Nullability, minimum: u64, maximum: MaximumConsumption) -> Consumption {
    if maximum == MaximumConsumption::Finite(0) {
        Consumption::AlwaysZeroWidth
    } else if minimum > 0 {
        Consumption::AlwaysConsuming
    } else if nullability == Nullability::Nullable {
        Consumption::Variable
    } else {
        Consumption::Indeterminate
    }
}

fn overflow(path: &str, message: &str) -> SemanticAnalysisErrors {
    SemanticAnalysisErrors::single(SemanticAnalysisError::new(
        SemanticAnalysisErrorCode::ArithmeticOverflow,
        path,
        message,
    ))
}
