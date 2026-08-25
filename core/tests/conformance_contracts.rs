use std::convert::TryFrom;
use std::fs;
use std::path::{Path, PathBuf};

use serde_json::Value;
use strling_kernel::conformance::{CasePath, ConformanceCase, ConformanceManifest};
use strling_kernel::target::{TargetProfile, TargetProfileSet};
use strling_kernel::validation::{from_json, to_json, ContractError, ValidationCode};

fn repository_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(Path::parent)
        .expect("internal core manifest has repository grandparent")
        .to_path_buf()
}

fn read(path: impl AsRef<Path>) -> String {
    fs::read_to_string(path).expect("authored repository fixture")
}

fn manifest() -> ConformanceManifest {
    from_json(&read(
        repository_root().join("spec/conformance/manifest.json"),
    ))
    .expect("manifest validates")
}

fn profiles() -> TargetProfileSet {
    let root = repository_root();
    let profiles: Vec<TargetProfile> = [
        "pcre2-10.42.json",
        "pcre2-10.43.json",
        "ecmascript-2024.json",
        "python-re-3.11.json",
        "python-re-3.11-bytes.json",
    ]
    .iter()
    .map(|name| {
        from_json(&read(root.join("spec/targets/profiles").join(name))).expect("authored profile")
    })
    .collect();
    TargetProfileSet::new(profiles).expect("profile set")
}

fn corpus(manifest: &ConformanceManifest) -> Vec<(CasePath, ConformanceCase)> {
    let root = repository_root();
    manifest
        .cases
        .iter()
        .map(|entry| {
            let path = entry.path.as_str();
            (
                CasePath::try_from(path).expect("case path"),
                from_json(&read(root.join(path))).expect("authored case"),
            )
        })
        .collect()
}

#[test]
fn every_specification_authored_case_validates_and_fingerprints() {
    let manifest = manifest();
    assert_eq!(manifest.cases.len(), 20, "anti-shrinkage case denominator");
    for (entry, (_, case)) in manifest.cases.iter().zip(corpus(&manifest)) {
        assert_eq!(
            case.fingerprint().expect("case fingerprint"),
            entry.sha256,
            "{}",
            entry.path.as_str()
        );
        case.validate_against_profiles(&profiles())
            .unwrap_or_else(|errors| panic!("{}: {:?}", entry.path.as_str(), errors.errors));
    }
}

#[test]
fn draft_manifest_certifies_every_and_only_shared_case() {
    let manifest = manifest();
    manifest
        .certify_cases(&corpus(&manifest), &profiles())
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
    let bad_manifest: ConformanceManifest =
        from_json(fixture).expect("fingerprint requires corpus context");
    let current = manifest();
    let errors = bad_manifest
        .certify_cases(&corpus(&current), &profiles())
        .expect_err("wrong fingerprint must fail");
    assert!(errors
        .errors
        .iter()
        .any(|error| error.code == ValidationCode::InvalidDigest));
}

#[test]
fn manifest_rejects_missing_and_unowned_case_documents() {
    let manifest = manifest();
    let mut missing = corpus(&manifest);
    missing.pop();
    assert!(manifest.certify_cases(&missing, &profiles()).is_err());

    let mut extra = corpus(&manifest);
    let case = extra[0].1.clone();
    extra.push((
        CasePath::try_from("spec/conformance/cases/unowned.json").expect("path"),
        case,
    ));
    assert!(manifest.certify_cases(&extra, &profiles()).is_err());
}

#[test]
fn conformance_round_trips_preserve_structural_content() {
    let manifest = manifest();
    for (entry, (_, case)) in manifest.cases.iter().zip(corpus(&manifest)) {
        let fixture = read(repository_root().join(entry.path.as_str()));
        let first = to_json(&case).expect("case serialization");
        assert_eq!(first, to_json(&case).expect("deterministic serialization"));
        assert_eq!(
            serde_json::from_str::<Value>(&fixture).expect("fixture"),
            serde_json::from_str::<Value>(&first).expect("serialized case")
        );
    }
    let fixture = read(repository_root().join("spec/conformance/manifest.json"));
    assert_eq!(
        serde_json::from_str::<Value>(&fixture).expect("fixture"),
        serde_json::from_str::<Value>(&to_json(&manifest).expect("manifest serialization"))
            .expect("serialized manifest")
    );
}

#[test]
fn optional_case_fields_reject_explicit_null() {
    let manifest = manifest();
    let entry = &manifest.cases[0];
    let mut invalid: Value =
        serde_json::from_str(&read(repository_root().join(entry.path.as_str())))
            .expect("case JSON");
    invalid["title"] = Value::Null;
    assert!(serde_json::from_value::<ConformanceCase>(invalid).is_err());
}
