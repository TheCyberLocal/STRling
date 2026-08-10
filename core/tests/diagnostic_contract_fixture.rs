use strling_kernel::diagnostic::{Diagnostic, Severity};
use strling_kernel::diagnostic_generation::SAFETY_UNBOUNDED_NULLABLE_REPETITION;
use strling_kernel::validation::Validate;

const SAFETY_WARNING: &str =
    include_str!("../../spec/contracts/1.0/examples/diagnostic/semantic-safety-warning.json");

#[test]
fn canonical_safety_diagnostic_fixture_matches_the_rust_contract() {
    let diagnostic: Diagnostic =
        serde_json::from_str(SAFETY_WARNING).expect("canonical safety fixture must deserialize");

    diagnostic.validate().expect("fixture must validate");
    assert_eq!(
        diagnostic.code.as_str(),
        SAFETY_UNBOUNDED_NULLABLE_REPETITION
    );
    assert_eq!(diagnostic.severity, Severity::Warning);
    assert!(diagnostic.fixes.is_none());
}
