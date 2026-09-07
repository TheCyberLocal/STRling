use serde_json::json;
use strling_kernel::compile;
use strling_kernel::diagnostic::{CompilerPhase, DiagnosticCategory, Severity, SeverityBasis};
use strling_kernel::protocol::{CompileOutcome, CompileRequest};
use strling_kernel::source::CoordinateSystem;
use strling_kernel::target::TargetProfile;
use strling_kernel::validation::{from_json, Validate};

const SOURCE: &str = "semantic strling 1.0;\ncase sensitive;\npattern repeat from 65536 to 65536 using greedy { text \"a\"; }\n";
const SAFE_SOURCE: &str = "semantic strling 1.0;\ncase sensitive;\npattern repeat from 4096 to 4096 using greedy { text \"a\"; }\n";
const SOURCE_ID: &str = "src:emission-diagnostic-delivery";
const PCRE2_1042: &str = include_str!("../../spec/targets/profiles/pcre2-10.42.json");
const PCRE2_1043: &str = include_str!("../../spec/targets/profiles/pcre2-10.43.json");

fn profile(source: &str) -> TargetProfile {
    from_json(source).expect("governed target profile")
}

fn request(source: &str, target: &TargetProfile) -> CompileRequest {
    let value = json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "input": {
            "kind": "source",
            "document": {
                "contract_version": "1.0.0",
                "source_id": SOURCE_ID,
                "specification_version": "1.0-draft.1",
                "frontend": {
                    "id": "strling.semantic",
                    "dialect_version": "1.0.0"
                },
                "content": {
                    "kind": "inline",
                    "encoding": "utf-8",
                    "media_type": "text/x-strling-semantic",
                    "text": source
                },
                "provenance": {"kind": "authored"}
            }
        },
        "requested_outputs": ["semantic", "analysis", "portability", "target_artifact"],
        "compiler_options": {
            "partial_semantics": "forbid",
            "diagnostic_policy": {"minimum_severity": "hint"}
        },
        "target_profile": target.reference().expect("profile reference")
    });
    from_json(&serde_json::to_string(&value).expect("request JSON"))
        .expect("canonical compile request")
}

#[test]
fn governed_pcre2_emission_failures_are_structured_for_every_current_revision() {
    for target in [profile(PCRE2_1042), profile(PCRE2_1043)] {
        let request = request(SOURCE, &target);
        let first = compile(&request, Some(&target)).expect("governed compilation failure");
        let second = compile(&request, Some(&target)).expect("deterministic failure");

        assert_eq!(first, second);
        assert_eq!(first.outcome, CompileOutcome::Failed);
        assert!(first.semantic_result.is_some());
        assert!(first.analysis.is_some());
        assert!(first.artifact.is_none());
        let portability = first.portability.as_ref().expect("portability evidence");
        assert_eq!(
            portability.target_profile,
            target.reference().expect("profile reference")
        );

        let diagnostic = first
            .diagnostics
            .iter()
            .find(|item| item.code.as_str() == "STRL-PCRE2_LOWERING-0014")
            .expect("compiled-size refusal diagnostic");
        assert_eq!(diagnostic.severity, Severity::Error);
        assert_eq!(diagnostic.severity_basis, SeverityBasis::TargetProfile);
        assert_eq!(diagnostic.phase, CompilerPhase::TargetLowering);
        assert_eq!(diagnostic.category, DiagnosticCategory::TargetCapability);
        assert!(diagnostic.message.contains(target.profile_id.as_str()));
        assert!(diagnostic.message.contains(target.profile_version.as_str()));
        let location = diagnostic
            .primary_location
            .as_ref()
            .expect("source-attributed diagnostic");
        assert_eq!(location.source_id.as_str(), SOURCE_ID);
        assert_eq!(location.coordinate_system, CoordinateSystem::Utf8Bytes);
        assert_eq!((location.start, location.end), (46, 99));
        first.validate().expect("failed result remains canonical");
    }
}

#[test]
fn successful_target_compile_has_no_fabricated_emission_diagnostics() {
    let target = profile(PCRE2_1043);
    let result =
        compile(&request(SAFE_SOURCE, &target), Some(&target)).expect("governed target compile");

    assert_eq!(result.outcome, CompileOutcome::Succeeded);
    let artifact = result.artifact.expect("publishable artifact");
    assert!(artifact.emission_diagnostics.is_empty());
    assert!(!result.diagnostics.iter().any(|diagnostic| {
        diagnostic.code.as_str().starts_with("STRL-PCRE2_LOWERING-")
            || diagnostic.code.as_str().starts_with("STRL-PCRE2_EMISSION-")
    }));
}
