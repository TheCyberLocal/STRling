use std::convert::TryFrom;

use strling_kernel::capability_evaluation::{
    resolve_capability_semantic_facts, ResolvedSemanticFact,
};
use strling_kernel::target::{
    BackreferenceUnsetBehavior, CapabilityId, CaptureResetBehavior, CaseFoldingMode,
    CharacterSetUniverse, LineTerminator, LineTerminatorSequencePolicy, MatchingUnit,
    SemanticAlgorithm, SemanticAlgorithmDefinition, SemanticSet, SemanticSetDefinition,
    TargetLimitBound, TargetLimitPrediction, TargetLimitScope, TargetProfile, UnicodeVersion,
};
use strling_kernel::validation::{from_json, Validate};

const PROFILES: &[(&str, &str)] = &[
    (
        "ecmascript",
        include_str!("../../spec/targets/profiles/ecmascript-2024.json"),
    ),
    (
        "pcre2-10.42",
        include_str!("../../spec/targets/profiles/pcre2-10.42.json"),
    ),
    (
        "pcre2-10.43",
        include_str!("../../spec/targets/profiles/pcre2-10.43.json"),
    ),
    (
        "python-str",
        include_str!("../../spec/targets/profiles/python-re-3.11.json"),
    ),
    (
        "python-bytes",
        include_str!("../../spec/targets/profiles/python-re-3.11-bytes.json"),
    ),
];

fn profile(name: &str) -> TargetProfile {
    let fixture = PROFILES
        .iter()
        .find_map(|(candidate, fixture)| (*candidate == name).then_some(*fixture))
        .expect("profile fixture");
    from_json(fixture).expect("governed profile must load")
}

fn semantic_set<'a>(profile: &'a TargetProfile, id: &str) -> &'a SemanticSet {
    profile
        .semantic_sets
        .iter()
        .find(|fact| fact.set_id.as_str() == id)
        .expect("semantic set")
}

fn algorithm<'a>(profile: &'a TargetProfile, id: &str) -> &'a SemanticAlgorithm {
    profile
        .semantic_algorithms
        .iter()
        .find(|fact| fact.algorithm_id.as_str() == id)
        .expect("semantic algorithm")
}

fn fixed_unicode_version(fact: &SemanticSet) -> Option<&str> {
    match fact.unicode_version.as_ref() {
        Some(UnicodeVersion::Fixed { value }) => Some(value.as_str()),
        Some(UnicodeVersion::LatestUnicodeAtEdition { .. }) | None => None,
    }
}

fn word_categories(profile: &TargetProfile) -> Vec<String> {
    match &semantic_set(profile, "word_characters").definition {
        SemanticSetDefinition::CharacterSet {
            unicode_general_categories,
            ..
        } => unicode_general_categories
            .iter()
            .map(|category| category.as_str().to_owned())
            .collect(),
        SemanticSetDefinition::LineTerminatorSet { .. } => panic!("word set kind"),
    }
}

fn line_definition(profile: &TargetProfile) -> (Vec<LineTerminator>, LineTerminatorSequencePolicy) {
    match &semantic_set(profile, "line_terminators").definition {
        SemanticSetDefinition::LineTerminatorSet {
            members,
            sequence_policy,
        } => (members.clone(), *sequence_policy),
        SemanticSetDefinition::CharacterSet { .. } => panic!("line set kind"),
    }
}

fn wildcard_exclusions(profile: &TargetProfile) -> Vec<String> {
    match &semantic_set(profile, "wildcard_exclusions").definition {
        SemanticSetDefinition::CharacterSet { scalars, .. } => scalars.clone(),
        SemanticSetDefinition::LineTerminatorSet { .. } => panic!("wildcard set kind"),
    }
}

fn folding(profile: &TargetProfile) -> (CaseFoldingMode, Option<String>, Vec<Vec<String>>) {
    match &algorithm(profile, "case_folding").definition {
        SemanticAlgorithmDefinition::CaseFolding {
            mode,
            variant,
            additional_equivalence_classes,
        } => (
            *mode,
            variant.as_ref().map(|value| value.as_str().to_owned()),
            additional_equivalence_classes.clone(),
        ),
        _ => panic!("case folding kind"),
    }
}

#[test]
fn governed_profiles_load_validate_and_carry_evidence_for_every_fact() {
    for (name, _) in PROFILES {
        let profile = profile(name);
        profile.validate().expect("profile validation");
        assert!(profile
            .semantic_sets
            .iter()
            .all(|fact| !fact.evidence.is_empty()));
        assert!(profile
            .semantic_algorithms
            .iter()
            .all(|fact| !fact.evidence.is_empty()));
        assert!(profile
            .target_limits
            .iter()
            .all(|fact| !fact.evidence.is_empty()));
    }
}

#[test]
fn word_character_facts_distinguish_ascii_mn_pc_letters_numbers_and_bytes() {
    let ecmascript = profile("ecmascript");
    let pcre_1042 = profile("pcre2-10.42");
    let pcre_1043 = profile("pcre2-10.43");
    let python = profile("python-str");
    let bytes = profile("python-bytes");

    let SemanticSetDefinition::CharacterSet {
        universe,
        scalars,
        ranges,
        unicode_general_categories,
    } = &semantic_set(&ecmascript, "word_characters").definition
    else {
        panic!("ECMAScript word set must be a character set");
    };
    assert_eq!(*universe, CharacterSetUniverse::UnicodeScalar);
    assert_eq!(scalars, &["U+005F"]);
    assert_eq!(ranges.len(), 3);
    assert!(unicode_general_categories.is_empty());

    assert_eq!(word_categories(&pcre_1042), ["L", "N"]);
    assert_eq!(word_categories(&python), ["L", "N"]);
    assert_eq!(word_categories(&pcre_1043), ["L", "Mn", "N", "Pc"]);
    assert_eq!(
        fixed_unicode_version(semantic_set(&pcre_1042, "word_characters")),
        Some("14.0.0")
    );
    assert_eq!(
        fixed_unicode_version(semantic_set(&pcre_1043, "word_characters")),
        Some("15.0.0")
    );

    let SemanticSetDefinition::CharacterSet {
        universe, ranges, ..
    } = &semantic_set(&bytes, "word_characters").definition
    else {
        panic!("bytes word set must be a character set");
    };
    assert_eq!(*universe, CharacterSetUniverse::Byte);
    assert_eq!(ranges.len(), 3);
}

#[test]
fn line_and_wildcard_facts_are_independent_and_cover_separator_classes() {
    let ecmascript = profile("ecmascript");
    let pcre = profile("pcre2-10.43");
    let python = profile("python-str");

    assert_eq!(
        line_definition(&ecmascript),
        (
            vec![
                LineTerminator::Lf,
                LineTerminator::Cr,
                LineTerminator::Ls,
                LineTerminator::Ps,
            ],
            LineTerminatorSequencePolicy::IndependentCodePoints,
        )
    );
    assert_eq!(
        line_definition(&pcre),
        (
            vec![
                LineTerminator::Lf,
                LineTerminator::Vt,
                LineTerminator::Ff,
                LineTerminator::Cr,
                LineTerminator::Crlf,
                LineTerminator::Nel,
                LineTerminator::Ls,
                LineTerminator::Ps,
            ],
            LineTerminatorSequencePolicy::AtomicLongest,
        )
    );
    assert_eq!(
        line_definition(&python),
        (
            vec![LineTerminator::Lf],
            LineTerminatorSequencePolicy::IndependentCodePoints,
        )
    );

    assert_eq!(wildcard_exclusions(&python), ["U+000A"]);
    assert_eq!(
        wildcard_exclusions(&ecmascript),
        ["U+000A", "U+000D", "U+2028", "U+2029"]
    );
    assert_eq!(
        wildcard_exclusions(&pcre),
        ["U+000A", "U+000B", "U+000C", "U+000D", "U+0085", "U+2028", "U+2029"]
    );
}

#[test]
fn folding_backreference_capture_and_matching_algorithms_are_explicit() {
    let ecmascript = profile("ecmascript");
    let pcre = profile("pcre2-10.43");
    let python = profile("python-str");
    let bytes = profile("python-bytes");

    assert_eq!(folding(&ecmascript).0, CaseFoldingMode::SimpleUnicode);
    assert_eq!(folding(&pcre).0, CaseFoldingMode::SimpleUnicode);
    assert_eq!(folding(&bytes).0, CaseFoldingMode::Ascii);
    let python_folding = folding(&python);
    assert_eq!(python_folding.0, CaseFoldingMode::EngineSpecific);
    assert_eq!(
        python_folding.1,
        Some("cpython_sre_unicode_lower_with_casefix".to_owned())
    );
    for equivalence_class in [
        &["U+0049", "U+0069", "U+0130", "U+0131"][..],
        &["U+004B", "U+006B", "U+212A"][..],
        &["U+0053", "U+0073", "U+017F"][..],
        &["U+03A3", "U+03C2", "U+03C3"][..],
    ] {
        assert!(python_folding.2.iter().any(|actual| actual
            .iter()
            .map(String::as_str)
            .eq(equivalence_class.iter().copied())));
    }

    assert!(matches!(
        algorithm(&ecmascript, "backreference_unset").definition,
        SemanticAlgorithmDefinition::BackreferenceUnset {
            behavior: BackreferenceUnsetBehavior::Empty
        }
    ));
    assert!(matches!(
        algorithm(&pcre, "backreference_unset").definition,
        SemanticAlgorithmDefinition::BackreferenceUnset {
            behavior: BackreferenceUnsetBehavior::Fail
        }
    ));
    assert!(matches!(
        algorithm(&ecmascript, "capture_reset_on_iteration").definition,
        SemanticAlgorithmDefinition::CaptureResetOnIteration {
            behavior: CaptureResetBehavior::Reset
        }
    ));
    assert!(matches!(
        algorithm(&python, "capture_reset_on_iteration").definition,
        SemanticAlgorithmDefinition::CaptureResetOnIteration {
            behavior: CaptureResetBehavior::Retain
        }
    ));
    assert!(matches!(
        algorithm(&bytes, "matching_unit").definition,
        SemanticAlgorithmDefinition::MatchingUnit {
            unit: MatchingUnit::Byte
        }
    ));
}

#[test]
fn pcre_limits_separate_exact_syntax_from_unknown_compiled_size() {
    for name in ["pcre2-10.42", "pcre2-10.43"] {
        let profile = profile(name);
        let compiled = &profile.target_limits[0];
        assert_eq!(compiled.limit_id.as_str(), "compiled_pattern_size");
        assert_eq!(compiled.scope, TargetLimitScope::CompiledPattern);
        assert!(matches!(compiled.bound, TargetLimitBound::Unknown));
        assert_eq!(
            compiled.prediction,
            TargetLimitPrediction::ArtifactAndConfigurationDependent
        );

        let quantifier = &profile.target_limits[1];
        assert_eq!(quantifier.limit_id.as_str(), "quantifier_value");
        assert_eq!(quantifier.scope, TargetLimitScope::SyntacticQuantifier);
        assert!(matches!(
            quantifier.bound,
            TargetLimitBound::Numeric { value: 65_535, .. }
        ));
        assert_eq!(quantifier.prediction, TargetLimitPrediction::Exact);
    }
}

#[test]
fn capability_evaluation_resolves_semantic_facts_and_unknown_stays_unknown() {
    let target = profile("python-str");
    let word = CapabilityId::try_from("boundaries.word").expect("capability ID");
    let facts = resolve_capability_semantic_facts(&target, &word)
        .expect("valid profile")
        .expect("listed capability");
    assert!(
        matches!(facts.as_slice(), [ResolvedSemanticFact::SemanticSet(set)] if set.set_id.as_str() == "word_characters")
    );

    let wildcard = CapabilityId::try_from("character_classes.wildcard").expect("capability ID");
    let facts = resolve_capability_semantic_facts(&target, &wildcard)
        .expect("valid profile")
        .expect("listed capability");
    assert!(facts.iter().any(|fact| matches!(fact, ResolvedSemanticFact::SemanticAlgorithm(algorithm) if algorithm.algorithm_id.as_str() == "matching_unit")));
    assert!(facts.iter().any(|fact| matches!(fact, ResolvedSemanticFact::SemanticSet(set) if set.set_id.as_str() == "wildcard_exclusions")));

    let missing = CapabilityId::try_from("future.unlisted").expect("capability ID");
    assert!(resolve_capability_semantic_facts(&target, &missing)
        .expect("valid profile")
        .is_none());

    let mut invalid = target;
    invalid.semantic_sets.pop();
    assert!(resolve_capability_semantic_facts(&invalid, &word).is_err());
}
