//! Integration tests for STRling core data structures

use strling::core::nodes::{Flags, Literal, Node};
use strling::core::ir::{IRLit, IROp, IROpTrait};
use strling::core::errors::STRlingParseError;

#[test]
fn test_flags_from_letters() {
    let flags = Flags::from_letters("ims");
    assert!(flags.ignore_case);
    assert!(flags.multiline);
    assert!(flags.dot_all);
    assert!(!flags.unicode);
    assert!(!flags.extended);
}

#[test]
fn test_flags_to_dict() {
    let flags = Flags::from_letters("imu");
    let dict = flags.to_dict();
    assert_eq!(dict.get("ignoreCase"), Some(&true));
    assert_eq!(dict.get("multiline"), Some(&true));
    assert_eq!(dict.get("unicode"), Some(&true));
    assert_eq!(dict.get("dotAll"), Some(&false));
    assert_eq!(dict.get("extended"), Some(&false));
}

#[test]
fn test_ast_node_serialization() {
    let lit_node = Node::Literal(Literal {
        value: "test".to_string(),
    });
    let json = serde_json::to_value(&lit_node).unwrap();

    assert_eq!(json["type"], "Literal");
    assert_eq!(json["value"], "test");
}

#[test]
fn test_ir_node_serialization() {
    let ir_lit = IROp::Lit(IRLit {
        value: "test".to_string(),
    });
    let ir_json = ir_lit.to_dict();

    assert_eq!(ir_json["ir"], "Lit");
    assert_eq!(ir_json["value"], "test");
}

#[test]
fn test_error_creation() {
    let error = STRlingParseError::new(
        "Test error".to_string(),
        5,
        "hello world".to_string(),
        Some("This is a hint".to_string()),
    );

    assert_eq!(error.message, "Test error");
    assert_eq!(error.pos, 5);
    assert_eq!(error.text, "hello world");
    assert!(error.hint.is_some());
    assert_eq!(error.hint.unwrap(), "This is a hint");
}

#[test]
fn test_error_formatting() {
    let error = STRlingParseError::new(
        "Unexpected character".to_string(),
        6,
        "hello world".to_string(),
        Some("Did you mean to escape this?".to_string()),
    );

    let formatted = error.to_formatted_string();
    assert!(formatted.contains("Unexpected character"));
    assert!(formatted.contains("Hint:"));
    assert!(formatted.contains("Did you mean to escape this?"));
}

#[test]
fn test_lsp_diagnostic() {
    let error = STRlingParseError::new(
        "Test error".to_string(),
        0,
        "test".to_string(),
        None,
    );

    let diagnostic = error.to_lsp_diagnostic();
    assert_eq!(diagnostic["severity"], 1);
    assert_eq!(diagnostic["source"], "STRling");
    assert!(diagnostic["message"].is_string());
    assert!(diagnostic["range"].is_object());
}

#[test]
fn test_default_flags() {
    let flags = Flags::default();
    assert!(!flags.ignore_case);
    assert!(!flags.multiline);
    assert!(!flags.dot_all);
    assert!(!flags.unicode);
    assert!(!flags.extended);
}
