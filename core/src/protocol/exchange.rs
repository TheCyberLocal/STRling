use std::collections::BTreeMap;

use super::{
    CompileInput, CompileOutcome, CompileRequest, CompileResult, PartialSemantics, RequestedOutput,
    SemanticResultStatus,
};
use crate::source::{FrontendId, SourceDocument, SourceId, SourceSpan};
use crate::validation::{Validate, ValidationCode, ValidationError, ValidationErrors};

pub fn validate_exchange(
    request: &CompileRequest,
    result: &CompileResult,
    supported_frontends: &[FrontendId],
) -> Result<(), ValidationErrors> {
    let mut errors = ValidationErrors::default();
    if let Err(found) = request.validate() {
        errors.extend(found);
    }
    if let Err(found) = result.validate() {
        errors.extend(found);
    }
    if request.specification_version != result.specification_version {
        errors.push(ValidationError::new(
            ValidationCode::SpecificationMismatch,
            "$",
            "request and result specification versions must match",
        ));
    }
    if result.outcome == CompileOutcome::Succeeded {
        for output in &request.requested_outputs {
            let present = match output {
                RequestedOutput::Semantic => result.semantic_result.is_some(),
                RequestedOutput::Analysis => result.analysis.is_some(),
                RequestedOutput::Portability => result.portability.is_some(),
                RequestedOutput::TargetArtifact => result.artifact.is_some(),
            };
            if !present {
                errors.push(ValidationError::new(
                    ValidationCode::UnresolvedReference,
                    "$",
                    format!("successful result omitted requested output {output:?}"),
                ));
            }
        }
    }
    if result
        .semantic_result
        .as_ref()
        .is_some_and(|semantic| semantic.status == SemanticResultStatus::Partial)
        && request.compiler_options.partial_semantics != PartialSemantics::AllowForDiagnostics
    {
        errors.push(ValidationError::new(
            ValidationCode::NonCanonicalStructure,
            "$.semantic_result.status",
            "request did not permit partial diagnostic semantics",
        ));
    }
    if let CompileInput::Source { document } = &request.input {
        if !supported_frontends.contains(&document.frontend.id)
            && (result.outcome != CompileOutcome::Failed
                || !result
                    .diagnostics
                    .iter()
                    .any(|diagnostic| diagnostic.code.as_str() == "STRL-PROTOCOL-0002"))
        {
            errors.push(ValidationError::new(
                ValidationCode::UnresolvedReference,
                "$.input.document.frontend.id",
                "unsupported frontend requires structured STRL-PROTOCOL-0002 failure",
            ));
        }
    }
    if let Some(portability) = &result.portability {
        if request.target_profile.as_ref() != Some(&portability.target_profile) {
            errors.push(ValidationError::new(
                ValidationCode::UnresolvedReference,
                "$.portability.target_profile",
                "portability profile must equal requested target profile",
            ));
        }
    }
    if let Some(artifact) = &result.artifact {
        if request.target_profile.as_ref() != Some(&artifact.target_profile) {
            errors.push(ValidationError::new(
                ValidationCode::UnresolvedReference,
                "$.artifact.target_profile",
                "artifact profile must equal requested target profile",
            ));
        }
    }

    validate_diagnostic_sources(request, result, &mut errors);
    errors.finish()
}

fn validate_diagnostic_sources(
    request: &CompileRequest,
    result: &CompileResult,
    errors: &mut ValidationErrors,
) {
    let mut sources: BTreeMap<SourceId, &SourceDocument> = BTreeMap::new();
    match &request.input {
        CompileInput::Source { document } => {
            sources.insert(document.source_id.clone(), document);
        }
        CompileInput::Semantic { program } => {
            add_program_sources(program.sources.as_deref(), &mut sources, errors);
        }
    }
    if let Some(semantic) = &result.semantic_result {
        add_program_sources(semantic.program.sources.as_deref(), &mut sources, errors);
    }
    for (index, diagnostic) in result.diagnostics.iter().enumerate() {
        if let Some(span) = &diagnostic.primary_location {
            validate_attributed_span(
                span,
                &sources,
                format!("$.diagnostics[{index}].primary_location"),
                errors,
            );
        }
        if let Some(related) = &diagnostic.related_locations {
            for (related_index, related) in related.iter().enumerate() {
                validate_attributed_span(
                    &related.location,
                    &sources,
                    format!("$.diagnostics[{index}].related_locations[{related_index}].location"),
                    errors,
                );
            }
        }
        if let Some(fixes) = &diagnostic.fixes {
            for (fix_index, fix) in fixes.iter().enumerate() {
                for (edit_index, edit) in fix.edits.iter().enumerate() {
                    validate_attributed_span(
                        &edit.span,
                        &sources,
                        format!(
                            "$.diagnostics[{index}].fixes[{fix_index}].edits[{edit_index}].span"
                        ),
                        errors,
                    );
                }
            }
        }
    }
}

fn add_program_sources<'a>(
    program_sources: Option<&'a [SourceDocument]>,
    sources: &mut BTreeMap<SourceId, &'a SourceDocument>,
    errors: &mut ValidationErrors,
) {
    if let Some(program_sources) = program_sources {
        for source in program_sources {
            if let Some(existing) = sources.insert(source.source_id.clone(), source) {
                if existing != source {
                    errors.push(ValidationError::new(
                        ValidationCode::DuplicateIdentity,
                        "$.sources",
                        "conflicting source declarations share one source identity",
                    ));
                }
            }
        }
    }
}

fn validate_attributed_span(
    span: &SourceSpan,
    sources: &BTreeMap<SourceId, &SourceDocument>,
    path: String,
    errors: &mut ValidationErrors,
) {
    let Some(source) = sources.get(&span.source_id) else {
        errors.push(ValidationError::new(
            ValidationCode::UnresolvedReference,
            path,
            "diagnostic attribution must reference a declared source",
        ));
        return;
    };
    if let Some(text) = source.content.inline_text() {
        if let Err(found) = span.validate_against_text(text) {
            errors.extend(found);
        }
    }
}
