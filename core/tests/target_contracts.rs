use std::convert::TryFrom;

use serde_json::Value;
use strling_kernel::source::Sha256Digest;
use strling_kernel::target::{
    CapabilityAvailability, ConstraintOperator, ConstraintScalar, ConstraintValue,
    PortabilityStatus, TargetArtifact, TargetProfile, TargetProfileSet,
};
use strling_kernel::validation::{from_json, to_json, ContractError, Validate, ValidationCode};

const PROFILES: &[(&str, &str, &str)] = &[
    (
        "PCRE2 10.42",
        include_str!("../../spec/targets/profiles/pcre2-10.42.json"),
        "15e9032404dd934ca060e82fbe47f2af5f0b84a4daf1037c3d607a6ef1c4d051",
    ),
    (
        "PCRE2 10.43",
        include_str!("../../spec/targets/profiles/pcre2-10.43.json"),
        "6b8a974a57d91698fb427e1c5525109deb4e7e481fcf07b79a35de716ccff979",
    ),
    (
        "ECMAScript 2024",
        include_str!("../../spec/targets/profiles/ecmascript-2024.json"),
        "5b012d7b0536610d4496718e6954c8f9ec80c16dde26a18f70663d0275ec333e",
    ),
    (
        "Python re 3.11",
        include_str!("../../spec/targets/profiles/python-re-3.11.json"),
        "5808a05beb86acf1577ab4b10055c65c0ee81eb7a167e1f6762c421e7043b751",
    ),
    (
        "Python re 3.11 bytes",
        include_str!("../../spec/targets/profiles/python-re-3.11-bytes.json"),
        "0ecba94d8083bf26d97f518aca94c6f2b9e4bbff7f0d0eb960c1fb6317c5fcfa",
    ),
];

const ARTIFACT: &str =
    include_str!("../../spec/contracts/1.0/examples/target-artifact/pcre2-with-options.json");

fn load_profiles() -> Vec<TargetProfile> {
    PROFILES
        .iter()
        .map(|(description, fixture, _)| {
            from_json(fixture).unwrap_or_else(|error| panic!("{description}: {error}"))
        })
        .collect()
}

#[test]
fn authored_target_profiles_validate_and_fingerprint_exactly() {
    for (description, fixture, expected_fingerprint) in PROFILES {
        let profile: TargetProfile =
            from_json(fixture).unwrap_or_else(|error| panic!("{description}: {error}"));
        let reference = profile.reference().expect("profile fingerprint");
        assert_eq!(reference.sha256.as_str(), *expected_fingerprint);
    }
}

#[test]
fn engine_versions_select_distinct_capability_records() {
    let profiles = load_profiles();
    let earlier = &profiles[0];
    let modern = &profiles[1];
    assert_eq!(earlier.engine.id, modern.engine.id);
    assert_ne!(earlier.engine.version, modern.engine.version);
    let variable_lookbehind = "assertions.lookbehind.variable_length";
    let earlier_capability = earlier
        .capabilities
        .iter()
        .find(|item| item.capability_id.as_str() == variable_lookbehind)
        .expect("10.42 capability");
    let modern_capability = modern
        .capabilities
        .iter()
        .find(|item| item.capability_id.as_str() == variable_lookbehind)
        .expect("10.43 capability");
    assert_eq!(
        earlier_capability.availability,
        CapabilityAvailability::Unavailable
    );
    assert_eq!(
        modern_capability.availability,
        CapabilityAvailability::Constrained
    );
}

#[test]
fn constraints_preserve_typed_operators_values_and_units() {
    let profile: TargetProfile = from_json(PROFILES[1].1).expect("PCRE2 profile");
    let capability = profile
        .capabilities
        .iter()
        .find(|item| item.capability_id.as_str() == "assertions.lookbehind.variable_length")
        .expect("variable lookbehind");
    let maximum = &capability.constraints[0];
    assert_eq!(maximum.operator, ConstraintOperator::AtMost);
    assert_eq!(
        maximum.unit.as_ref().map(|value| value.as_str()),
        Some("characters")
    );
    assert!(matches!(
        maximum.value,
        ConstraintValue::Scalar(ConstraintScalar::Number(ref value))
            if value.as_u64() == Some(255)
    ));
    let matcher = &capability.constraints[1];
    assert_eq!(matcher.operator, ConstraintOperator::RequiresOption);
    assert!(matches!(
        matcher.value,
        ConstraintValue::Scalar(ConstraintScalar::String(ref value))
            if value == "pcre2.matcher_api"
    ));
}

#[test]
fn malformed_profile_fixtures_are_rejected_structurally() {
    for fixture in [
        include_str!("../../spec/contracts/1.0/invalid/target-profile/boolean-capability.json"),
        include_str!(
            "../../spec/contracts/1.0/invalid/target-profile/constrained-without-constraint.json"
        ),
        include_str!("../../spec/contracts/1.0/invalid/target-profile/duplicate-capability.json"),
        include_str!("../../spec/contracts/1.0/invalid/target-profile/malformed-version.json"),
    ] {
        assert!(from_json::<TargetProfile>(fixture).is_err());
    }
}

#[test]
fn immutable_profile_references_resolve_only_exact_fingerprints() {
    let profiles = load_profiles();
    let set = TargetProfileSet::new(profiles.clone()).expect("profile set validates");
    for profile in &profiles {
        let reference = profile.reference().expect("reference");
        assert_eq!(
            set.resolve(&reference).expect("reference resolves"),
            profile
        );
    }
    let mut altered = profiles[1].reference().expect("reference");
    altered.sha256 =
        Sha256Digest::try_from("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
            .expect("digest shape");
    let errors = set
        .resolve(&altered)
        .expect_err("altered fingerprint must fail");
    assert!(errors
        .errors
        .iter()
        .any(|error| error.code == ValidationCode::InvalidDigest));
}

#[test]
fn target_artifact_keeps_pattern_options_and_profile_separate() {
    let artifact: TargetArtifact = from_json(ARTIFACT).expect("artifact validates");
    let profile: TargetProfile = from_json(PROFILES[1].1).expect("profile validates");
    artifact
        .validate_against_profile(&profile)
        .expect("artifact resolves against profile");
    assert_eq!(artifact.pattern.text, "(?<word>\\p{L}+)");
    assert!(artifact.pattern.flags.is_empty());
    assert_eq!(artifact.engine_options.len(), 6);
    assert!(!artifact.pattern.text.contains("(*UTF)"));
}

#[test]
fn target_artifact_pattern_flags_are_optional_unique_and_sorted() {
    let artifact: TargetArtifact = from_json(ARTIFACT).expect("legacy artifact validates");
    let serialized = to_json(&artifact).expect("legacy artifact serializes");
    assert!(!serialized.contains("\"flags\""));

    let mut flagged = artifact.clone();
    flagged.pattern.flags = vec!["i".to_owned(), "u".to_owned()];
    flagged.validate().expect("canonical pattern flags");

    flagged.pattern.flags.swap(0, 1);
    let errors = flagged.validate().expect_err("out-of-order pattern flags");
    assert!(errors
        .errors
        .iter()
        .any(|error| error.code == ValidationCode::NonCanonicalOrder));

    flagged.pattern.flags = vec!["unicode".to_owned()];
    let errors = flagged.validate().expect_err("multi-letter pattern flag");
    assert!(errors
        .errors
        .iter()
        .any(|error| error.code == ValidationCode::InvalidIdentity));
}

#[test]
fn profile_dependent_artifact_mismatches_are_structured() {
    let mut artifact: TargetArtifact = from_json(ARTIFACT).expect("artifact validates");
    let profile: TargetProfile = from_json(PROFILES[1].1).expect("profile validates");
    artifact.engine_options.pop();
    let errors = artifact
        .validate_against_profile(&profile)
        .expect_err("required UTF option is missing");
    assert!(errors
        .errors
        .iter()
        .any(|error| error.code == ValidationCode::UnresolvedReference));

    let artifact: TargetArtifact = from_json(ARTIFACT).expect("artifact validates");
    let wrong_profile: TargetProfile = from_json(PROFILES[0].1).expect("profile validates");
    assert!(artifact.validate_against_profile(&wrong_profile).is_err());
}

#[test]
fn target_contract_round_trips_are_structurally_stable() {
    for (_, fixture, _) in PROFILES {
        let profile: TargetProfile = from_json(fixture).expect("profile");
        let first = to_json(&profile).expect("profile serializes");
        assert_eq!(first, to_json(&profile).expect("stable serialization"));
        assert_eq!(
            serde_json::from_str::<Value>(fixture).expect("fixture"),
            serde_json::from_str::<Value>(&first).expect("serialized profile")
        );
    }
    let artifact: TargetArtifact = from_json(ARTIFACT).expect("artifact");
    let serialized = to_json(&artifact).expect("artifact serializes");
    assert_eq!(
        serde_json::from_str::<Value>(ARTIFACT).expect("fixture"),
        serde_json::from_str::<Value>(&serialized).expect("serialized artifact")
    );
}

#[test]
fn target_unknown_fields_and_null_runtime_are_rejected() {
    let unknown = PROFILES[2]
        .1
        .replace(r#""engine":"#, r#""implementation_hint": true, "engine":"#);
    assert!(matches!(
        from_json::<TargetProfile>(&unknown),
        Err(ContractError::Deserialization(_))
    ));
    let explicit_null = PROFILES[2]
        .1
        .replace(r#""engine":"#, r#""runtime": null, "engine":"#);
    assert!(matches!(
        from_json::<TargetProfile>(&explicit_null),
        Err(ContractError::Deserialization(_))
    ));
}

#[test]
fn portability_vocabulary_has_no_degraded_state() {
    for (spelling, expected) in [
        ("native", PortabilityStatus::Native),
        ("equivalent_rewrite", PortabilityStatus::EquivalentRewrite),
        ("unsupported", PortabilityStatus::Unsupported),
    ] {
        assert_eq!(
            serde_json::from_str::<PortabilityStatus>(&format!("\"{spelling}\""))
                .expect("certified status"),
            expected
        );
    }
    assert!(serde_json::from_str::<PortabilityStatus>("\"degraded\"").is_err());
}
