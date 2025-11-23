use serde_json;
use strling_core::core::nodes::*;

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
