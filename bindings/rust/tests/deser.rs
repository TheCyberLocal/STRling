use serde_json;
use strling::core::nodes::*;

#[test]
fn class_escape_kind_normalizes() {
    // Accept `kind` long form and normalize to short code `d`
    let j = r#"{"kind":"digit"}"#;
    let ce: ClassEscape = serde_json::from_str(j).expect("Failed to deserialize ClassEscape");
    assert_eq!(ce.escape_type, "d");
    assert_eq!(ce.property, None);
}

#[test]
fn unicode_property_deserializes_and_maps() {
    let j = r#"{"type":"UnicodeProperty","name":null,"value":"L","negated":false}"#;
    let item: ClassItem = serde_json::from_str(j).expect("Failed to deserialize ClassItem::UnicodeProperty");

    match item {
        ClassItem::UnicodeProperty(up) => {
            assert_eq!(up.value, "L");
            assert!(!up.negated);
            assert!(up.name.is_none());
        }
        _ => panic!("expected UnicodeProperty variant"),
    }
}

#[test]
fn quantifier_target_accepts_target_and_child() {
    // `target` key
    let j = r#"{"target":{"type":"Literal","value":"a"}}"#;
    let q: QuantifierTarget = serde_json::from_str(j).expect("Failed to deserialize QuantifierTarget with 'target'");

    match *q.child {
        Node::Literal(Literal { value }) => assert_eq!(value, "a"),
        _ => panic!("expected Literal child"),
    }

    // `child` key (historical)
    let j2 = r#"{"child":{"type":"Literal","value":"b"}}"#;
    let q2: QuantifierTarget = serde_json::from_str(j2).expect("Failed to deserialize QuantifierTarget with 'child'");

    match *q2.child {
        Node::Literal(Literal { value }) => assert_eq!(value, "b"),
        _ => panic!("expected Literal child"),
    }
}

#[test]
fn maxbound_handles_null_inf_and_number() {
    // null -> Null
    let m: MaxBound = serde_json::from_str("null").expect("Failed to deserialize null into MaxBound");
    match m {
        MaxBound::Null => (),
        other => panic!("expected MaxBound::Null, got: {:?}", other),
    }

    // Inf -> Infinite("Inf")
    let m2: MaxBound = serde_json::from_str("\"Inf\"").expect("Failed to deserialize \"Inf\" into MaxBound");
    match m2 {
        MaxBound::Infinite(s) => assert_eq!(s, "Inf"),
        other => panic!("expected MaxBound::Infinite, got: {:?}", other),
    }

    // number -> Finite
    let m3: MaxBound = serde_json::from_str("3").expect("Failed to deserialize number into MaxBound");
    match m3 {
        MaxBound::Finite(n) => assert_eq!(n, 3),
        other => panic!("expected MaxBound::Finite, got: {:?}", other),
    }
}
