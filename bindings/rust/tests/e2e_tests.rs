//! E2E Tests for STRling Rust Binding
//!
//! Black Box: Input DSL → Match Regex against String
//! These tests validate the full pipeline from DSL input through
//! to actual regex matching against target strings.

use regex::Regex;
use strling::core::parser::Parser;
use strling::core::compiler::Compiler;
use strling::emitters::pcre2::PCRE2Emitter;

/// Helper function to compile DSL to regex and check if it matches
fn matches(dsl: &str, subject: &str) -> bool {
    let mut parser = Parser::new(dsl.to_string());
    let (flags, ast) = match parser.parse() {
        Ok(result) => result,
        Err(_) => return false,
    };

    let mut compiler = Compiler::new();
    let ir = compiler.compile(&ast);

    let emitter = PCRE2Emitter::new(flags.clone());
    let pattern = emitter.emit(&ir);

    // Build regex with flags
    let pattern = if flags.ignore_case {
        format!("(?i){}", pattern)
    } else {
        pattern
    };

    match Regex::new(&pattern) {
        Ok(re) => re.is_match(subject),
        Err(_) => false,
    }
}

/// Helper for full string match
fn full_matches(dsl: &str, subject: &str) -> bool {
    let anchored = format!("^{}$", dsl);
    matches(&anchored, subject)
}

// ============================================================================
// Phone Number Tests
// ============================================================================

#[test]
fn test_e2e_phone_number_basic() {
    let dsl = r"\d{3}-\d{3}-\d{4}";

    assert!(matches(dsl, "555-123-4567"), "Should match valid phone");
    assert!(matches(dsl, "123-456-7890"), "Should match valid phone");
    assert!(!matches(dsl, "12-345-6789"), "Should not match invalid phone");
    assert!(!matches(dsl, "not a phone"), "Should not match text");
}

#[test]
fn test_e2e_phone_number_with_groups() {
    let dsl = r"(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})";

    assert!(matches(dsl, "555-123-4567"), "Should match dashed phone");
    assert!(matches(dsl, "555.123.4567"), "Should match dotted phone");
    assert!(matches(dsl, "555 123 4567"), "Should match spaced phone");
    assert!(matches(dsl, "5551234567"), "Should match no-separator phone");
}

// ============================================================================
// Email Tests
// ============================================================================

#[test]
fn test_e2e_email_simple() {
    let dsl = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}";

    assert!(matches(dsl, "test@example.com"), "Should match simple email");
    assert!(matches(dsl, "user.name@domain.org"), "Should match email with dot");
    assert!(matches(dsl, "user+tag@domain.co.uk"), "Should match email with plus");
    assert!(!matches(dsl, "invalid-email"), "Should not match invalid email");
}

// ============================================================================
// IPv4 Tests
// ============================================================================

#[test]
fn test_e2e_ipv4_address() {
    let dsl = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}";

    assert!(matches(dsl, "192.168.1.1"), "Should match private IP");
    assert!(matches(dsl, "10.0.0.255"), "Should match 10.x range");
    assert!(matches(dsl, "255.255.255.0"), "Should match subnet mask");
    assert!(!matches(dsl, "192.168.1"), "Should not match incomplete IP");
}

// ============================================================================
// Hex Color Tests
// ============================================================================

#[test]
fn test_e2e_hex_color() {
    let dsl = r"#[0-9a-fA-F]{6}";

    assert!(matches(dsl, "#FFFFFF"), "Should match white");
    assert!(matches(dsl, "#000000"), "Should match black");
    assert!(matches(dsl, "#ff5733"), "Should match lowercase hex");
    assert!(!matches(dsl, "#GGG"), "Should not match invalid hex");
}

// ============================================================================
// Date Tests
// ============================================================================

#[test]
fn test_e2e_date_format() {
    let dsl = r"\d{4}-\d{2}-\d{2}";

    assert!(matches(dsl, "2024-01-15"), "Should match ISO date");
    assert!(matches(dsl, "1999-12-31"), "Should match Y2K date");
    assert!(!matches(dsl, "24-01-15"), "Should not match short year");
}

// ============================================================================
// Lookahead/Lookbehind Tests
// ============================================================================

#[test]
fn test_e2e_lookahead_positive() {
    let dsl = r"foo(?=bar)";

    assert!(matches(dsl, "foobar"), "Should match foo followed by bar");
    assert!(!matches(dsl, "foobaz"), "Should not match foo followed by baz");
    assert!(!matches(dsl, "foo"), "Should not match just foo");
}

#[test]
fn test_e2e_lookahead_negative() {
    let dsl = r"foo(?!bar)";

    assert!(matches(dsl, "foobaz"), "Should match foo NOT followed by bar");
    assert!(!matches(dsl, "foobar"), "Should not match foo followed by bar");
}

#[test]
fn test_e2e_lookbehind_positive() {
    let dsl = r"(?<=foo)bar";

    assert!(matches(dsl, "foobar"), "Should match bar preceded by foo");
    assert!(!matches(dsl, "bazbar"), "Should not match bar preceded by baz");
}

#[test]
fn test_e2e_lookbehind_negative() {
    let dsl = r"(?<!foo)bar";

    assert!(matches(dsl, "bazbar"), "Should match bar NOT preceded by foo");
    assert!(!matches(dsl, "foobar"), "Should not match bar preceded by foo");
}

// ============================================================================
// Word Boundary Tests
// ============================================================================

#[test]
fn test_e2e_word_boundary() {
    let dsl = r"\bcat\b";

    assert!(matches(dsl, "the cat sat"), "Should match standalone cat");
    assert!(matches(dsl, "cat"), "Should match just cat");
    assert!(!matches(dsl, "category"), "Should not match category");
    assert!(!matches(dsl, "concatenate"), "Should not match concatenate");
}

// ============================================================================
// Alternation Tests
// ============================================================================

#[test]
fn test_e2e_alternation() {
    let dsl = r"cat|dog|bird";

    assert!(matches(dsl, "I have a cat"), "Should match cat");
    assert!(matches(dsl, "I have a dog"), "Should match dog");
    assert!(matches(dsl, "I have a bird"), "Should match bird");
    assert!(!matches(dsl, "I have a fish"), "Should not match fish");
}

// ============================================================================
// Quantifier Tests
// ============================================================================

#[test]
fn test_e2e_quantifier_greedy_vs_lazy() {
    let greedy = r"<.*>";
    let lazy = r"<.*?>";

    assert!(matches(greedy, "<div><span></span></div>"), "Greedy should match");
    assert!(matches(lazy, "<div></div>"), "Lazy should match");
}

#[test]
fn test_e2e_quantifier_exact() {
    let dsl = r"a{3}";

    assert!(full_matches(dsl, "aaa"), "Should match exactly 3 a's");
    assert!(!full_matches(dsl, "aa"), "Should not match 2 a's");
}

#[test]
fn test_e2e_quantifier_range() {
    let dsl = r"a{2,4}";

    assert!(!full_matches(dsl, "a"), "Should not match 1 a");
    assert!(full_matches(dsl, "aa"), "Should match 2 a's");
    assert!(full_matches(dsl, "aaa"), "Should match 3 a's");
    assert!(full_matches(dsl, "aaaa"), "Should match 4 a's");
    assert!(!full_matches(dsl, "aaaaa"), "Should not match 5 a's");
}

// ============================================================================
// Capture Group Tests
// ============================================================================

#[test]
fn test_e2e_capture_groups() {
    let dsl = r"(\w+)\s+(\w+)";

    assert!(matches(dsl, "hello world"), "Should match two words");
    assert!(matches(dsl, "one two three"), "Should match in three words");
}

#[test]
fn test_e2e_named_capture_group() {
    let dsl = r"(?<word>\w+)";

    assert!(matches(dsl, "hello"), "Should match with named group");
}

// ============================================================================
// Complex Pattern Tests
// ============================================================================

#[test]
fn test_e2e_complex_url() {
    let dsl = r"https?://[a-zA-Z0-9.-]+(/[a-zA-Z0-9./_-]*)?";

    assert!(matches(dsl, "http://example.com"), "Should match http URL");
    assert!(matches(dsl, "https://example.com/path"), "Should match https URL with path");
    assert!(!matches(dsl, "ftp://example.com"), "Should not match ftp URL");
}

#[test]
fn test_e2e_username_validation() {
    let dsl = r"^[a-zA-Z][a-zA-Z0-9_]{2,15}$";

    assert!(matches(dsl, "user123"), "Should match valid username");
    assert!(matches(dsl, "John_Doe"), "Should match username with underscore");
    assert!(!matches(dsl, "123user"), "Should not match username starting with number");
    assert!(!matches(dsl, "ab"), "Should not match too short username");
}

#[test]
fn test_e2e_time_format() {
    let dsl = r"([01]?[0-9]|2[0-3]):[0-5][0-9]";

    assert!(matches(dsl, "12:30"), "Should match noon");
    assert!(matches(dsl, "23:59"), "Should match late night");
    assert!(matches(dsl, "0:00"), "Should match midnight");
    assert!(!matches(dsl, "25:00"), "Should not match invalid hour");
}

// ============================================================================
// Escape Sequence Tests
// ============================================================================

#[test]
fn test_e2e_special_char_matching() {
    let dsl = r"\.\*\+\?\[\]";

    assert!(matches(dsl, ".*+?[]"), "Should match escaped special chars");
}

#[test]
fn test_e2e_whitespace_matching() {
    let dsl = r"\s+";

    assert!(matches(dsl, "hello world"), "Should match space");
    assert!(matches(dsl, "line1\nline2"), "Should match newline");
    assert!(matches(dsl, "tab\there"), "Should match tab");
}

// ============================================================================
// Character Class Tests
// ============================================================================

#[test]
fn test_e2e_character_class_range() {
    let dsl = r"[a-z]+";

    assert!(full_matches(dsl, "hello"), "Should match lowercase");
    assert!(!full_matches(dsl, "HELLO"), "Should not match uppercase");
}

#[test]
fn test_e2e_negated_character_class() {
    let dsl = r"[^0-9]+";

    assert!(full_matches(dsl, "hello"), "Should match non-digits");
    assert!(!full_matches(dsl, "hello123"), "Should not match string with digits");
}

// ============================================================================
// Anchor Tests
// ============================================================================

#[test]
fn test_e2e_start_anchor() {
    let dsl = r"^hello";

    assert!(matches(dsl, "hello world"), "Should match at start");
    assert!(!matches(dsl, "say hello"), "Should not match in middle");
}

#[test]
fn test_e2e_end_anchor() {
    let dsl = r"world$";

    assert!(matches(dsl, "hello world"), "Should match at end");
    assert!(!matches(dsl, "world hello"), "Should not match at start");
}
