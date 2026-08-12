use std::convert::TryFrom;

use serde_json::Value;
use strling_kernel::conformance::{CasePath, ConformanceCase, ConformanceManifest};
use strling_kernel::target::{TargetProfile, TargetProfileSet};
use strling_kernel::validation::{from_json, to_json, ContractError, ValidationCode};

const CASES: &[(&str, &str, &str)] = &[
    (
        "spec/conformance/cases/parser-diagnostic.json",
        include_str!("../../spec/conformance/cases/parser-diagnostic.json"),
        "94d6c18f9812868852883c39531f8e961614486f6ea06278f37b57632153d674",
    ),
    (
        "spec/conformance/cases/capture-match.json",
        include_str!("../../spec/conformance/cases/capture-match.json"),
        "480463d7e35098d237e626fe6336b222256d0b97bfda5c765017765ddad1efd3",
    ),
    (
        "spec/conformance/cases/semantic-literal.json",
        include_str!("../../spec/conformance/cases/semantic-literal.json"),
        "a3ca1a49b8c77ca761b3801938fe01525b7307c6229f9abf63cace1e0d3f7772",
    ),
    (
        "spec/conformance/cases/lookbehind-targets.json",
        include_str!("../../spec/conformance/cases/lookbehind-targets.json"),
        "f78166eae8b0c943f213c42627cf230b24fbb558ca8cab221cac69ae677a158e",
    ),
];

const MANIFEST: &str = include_str!("../../spec/conformance/manifest.json");

fn profiles() -> TargetProfileSet {
    let profiles: Vec<TargetProfile> = [
        include_str!("../../spec/targets/profiles/pcre2-10.42.json"),
        include_str!("../../spec/targets/profiles/pcre2-10.43.json"),
        include_str!("../../spec/targets/profiles/ecmascript-2024.json"),
        include_str!("../../spec/targets/profiles/python-re-3.11.json"),
    ]
    .iter()
    .map(|fixture| from_json(fixture).expect("authored profile"))
    .collect();
    TargetProfileSet::new(profiles).expect("profile set")
}

fn corpus() -> Vec<(CasePath, ConformanceCase)> {
    CASES
        .iter()
        .map(|(path, fixture, _)| {
            (
                CasePath::try_from(*path).expect("case path"),
                from_json(fixture).expect("authored case"),
            )
        })
        .collect()
}

#[test]
fn every_specification_authored_seed_case_validates_and_fingerprints() {
    for (path, fixture, expected) in CASES {
        let case: ConformanceCase =
            from_json(fixture).unwrap_or_else(|error| panic!("{path}: {error}"));
        assert_eq!(
            case.fingerprint().expect("case fingerprint").as_str(),
            *expected
        );
        case.validate_against_profiles(&profiles())
            .unwrap_or_else(|errors| panic!("{path}: {:?}", errors.errors));
    }
}

#[test]
fn draft_manifest_certifies_every_and_only_seed_case() {
    let manifest: ConformanceManifest = from_json(MANIFEST).expect("manifest validates");
    manifest
        .certify_cases(&corpus(), &profiles())
        .unwrap_or_else(|errors| panic!("manifest failed: {:?}", errors.errors));
}

#[test]
fn implementation_output_cannot_claim_specification_authorship() {
    let fixture = include_str!(
        "../../spec/contracts/1.0/invalid/conformance-case/implementation-authored.json"
    );
    assert!(matches!(
        from_json::<ConformanceCase>(fixture),
        Err(ContractError::Deserialization(_))
    ));
}

#[test]
fn invalid_case_combinations_are_rejected() {
    for fixture in [
        include_str!(
            "../../spec/contracts/1.0/invalid/conformance-case/duplicate-target.json"
        ),
        include_str!(
            "../../spec/contracts/1.0/invalid/conformance-case/error-with-matches.json"
        ),
        include_str!(
            "../../spec/contracts/1.0/invalid/conformance-case/mismatched-semantic-specification.json"
        ),
        include_str!(
            "../../spec/contracts/1.0/invalid/conformance-case/missing-case-id.json"
        ),
    ] {
        assert!(from_json::<ConformanceCase>(fixture).is_err());
    }
}

#[test]
fn unresolved_target_expectation_fails_profile_certification() {
    let fixture = include_str!(
        "../../spec/contracts/1.0/invalid/conformance-case/invalid-target-reference.json"
    );
    let case: ConformanceCase = from_json(fixture).expect("shape is otherwise valid");
    let errors = case
        .validate_against_profiles(&profiles())
        .expect_err("profile reference must not resolve");
    assert!(errors.errors.iter().any(|error| matches!(
        error.code,
        ValidationCode::UnresolvedReference | ValidationCode::InvalidDigest
    )));
}

#[test]
fn invalid_authority_states_and_case_fingerprints_fail() {
    for fixture in [
        include_str!(
            "../../spec/contracts/1.0/invalid/conformance-manifest/draft-with-delegation.json"
        ),
        include_str!(
            "../../spec/contracts/1.0/invalid/conformance-manifest/normative-without-delegation.json"
        ),
    ] {
        assert!(from_json::<ConformanceManifest>(fixture).is_err());
    }
    let fixture = include_str!(
        "../../spec/contracts/1.0/invalid/conformance-manifest/wrong-case-fingerprint.json"
    );
    let manifest: ConformanceManifest =
        from_json(fixture).expect("fingerprint requires corpus context");
    let errors = manifest
        .certify_cases(&corpus(), &profiles())
        .expect_err("wrong fingerprint must fail");
    assert!(errors
        .errors
        .iter()
        .any(|error| error.code == ValidationCode::InvalidDigest));
}

#[test]
fn manifest_rejects_missing_and_unowned_case_documents() {
    let manifest: ConformanceManifest = from_json(MANIFEST).expect("manifest");
    let mut missing = corpus();
    missing.pop();
    assert!(manifest.certify_cases(&missing, &profiles()).is_err());

    let mut extra = corpus();
    let case = extra[0].1.clone();
    extra.push((
        CasePath::try_from("spec/conformance/cases/unowned.json").expect("path"),
        case,
    ));
    assert!(manifest.certify_cases(&extra, &profiles()).is_err());
}

#[test]
fn conformance_round_trips_preserve_structural_content() {
    for (_, fixture, _) in CASES {
        let case: ConformanceCase = from_json(fixture).expect("case");
        let first = to_json(&case).expect("case serialization");
        assert_eq!(first, to_json(&case).expect("deterministic serialization"));
        assert_eq!(
            serde_json::from_str::<Value>(fixture).expect("fixture"),
            serde_json::from_str::<Value>(&first).expect("serialized case")
        );
    }
    let manifest: ConformanceManifest = from_json(MANIFEST).expect("manifest");
    assert_eq!(
        serde_json::from_str::<Value>(MANIFEST).expect("fixture"),
        serde_json::from_str::<Value>(&to_json(&manifest).expect("manifest serialization"))
            .expect("serialized manifest")
    );
}

#[test]
fn optional_case_fields_reject_explicit_null() {
    let invalid = CASES[3]
        .1
        .replace(r#""title":"#, r#""delegation": null, "title":"#);
    assert!(matches!(
        from_json::<ConformanceCase>(&invalid),
        Err(ContractError::Deserialization(_))
    ));
}
