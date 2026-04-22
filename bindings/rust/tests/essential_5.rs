//! Standard library Essential 5 conformance tests.
//!
//! Validates the canonical patterns exposed by `strling::essential` against
//! the cross-binding fixture spec at `spec/stdlib/essential_5.json`.

use std::fs;
use std::path::PathBuf;
use serde_json::Value;
use regex::Regex;

use strling::core::compiler::Compiler;
use strling::core::nodes::{Flags, Node};
use strling::emitters::pcre2::PCRE2Emitter;
use strling::essential::*;

fn load_spec() -> Value {
    let mut dir = std::env::current_dir().expect("cwd");
    loop {
        let candidate = dir.join("spec").join("stdlib").join("essential_5.json");
        if candidate.is_file() {
            let text = fs::read_to_string(&candidate).expect("read spec");
            return serde_json::from_str(&text).expect("parse spec");
        }
        if !dir.pop() {
            panic!("essential_5.json not found");
        }
    }
}

fn values(spec: &Value, pattern: &str, field: &str) -> Vec<String> {
    spec["patterns"][pattern]["fixtures"][field]
        .as_array().expect("array")
        .iter()
        .map(|v| v.as_str().expect("string").to_string())
        .collect()
}

fn compile_full(node: Node) -> Regex {
    let mut compiler = Compiler::new();
    let ir = compiler.compile(&node);
    let regex_str = PCRE2Emitter::new(Flags::default()).emit(&ir);
    Regex::new(&format!("^(?:{})$", regex_str)).expect("compile regex")
}

fn assert_all_match(re: &Regex, vals: &[String], label: &str) {
    for v in vals {
        assert!(re.is_match(v), "{} expected match: {}", label, v);
    }
}

fn assert_none_match(re: &Regex, vals: &[String], label: &str) {
    for v in vals {
        assert!(!re.is_match(v), "{} expected NO match: {}", label, v);
    }
}

fn _setup() -> PathBuf { PathBuf::new() }

#[test]
fn email_valid() {
    let spec = load_spec();
    let re = compile_full(email());
    assert_all_match(&re, &values(&spec, "email", "valid"), "email");
}

#[test]
fn email_invalid() {
    let spec = load_spec();
    let re = compile_full(email());
    assert_none_match(&re, &values(&spec, "email", "invalid"), "email");
}

#[test]
fn url_valid() {
    let spec = load_spec();
    let re = compile_full(url());
    assert_all_match(&re, &values(&spec, "url", "valid"), "url");
}

#[test]
fn url_invalid() {
    let spec = load_spec();
    let re = compile_full(url());
    assert_none_match(&re, &values(&spec, "url", "invalid"), "url");
}

#[test]
fn uuid_default_valid() {
    let spec = load_spec();
    let re = compile_full(uuid(0));
    assert_all_match(&re, &values(&spec, "uuid", "valid_default"), "uuid");
}

#[test]
fn uuid_default_invalid() {
    let spec = load_spec();
    let re = compile_full(uuid(0));
    assert_none_match(&re, &values(&spec, "uuid", "invalid_default"), "uuid");
}

#[test]
fn uuid_v4_valid() {
    let spec = load_spec();
    let re = compile_full(uuid(4));
    assert_all_match(&re, &values(&spec, "uuid", "valid_v4"), "uuid4");
}

#[test]
fn uuid_v4_invalid() {
    let spec = load_spec();
    let re = compile_full(uuid(4));
    assert_none_match(&re, &values(&spec, "uuid", "invalid_v4"), "uuid4");
}

#[test]
fn ipv4_valid() {
    let spec = load_spec();
    let re = compile_full(ip(4));
    assert_all_match(&re, &values(&spec, "ip", "valid_v4"), "ipv4");
}

#[test]
fn ipv4_invalid() {
    let spec = load_spec();
    let re = compile_full(ip(4));
    assert_none_match(&re, &values(&spec, "ip", "invalid_v4"), "ipv4");
}

#[test]
fn ipv6_valid() {
    let spec = load_spec();
    let re = compile_full(ip(6));
    assert_all_match(&re, &values(&spec, "ip", "valid_v6"), "ipv6");
}

#[test]
fn ipv6_invalid() {
    let spec = load_spec();
    let re = compile_full(ip(6));
    assert_none_match(&re, &values(&spec, "ip", "invalid_v6"), "ipv6");
}

#[test]
fn ip_default_both() {
    let spec = load_spec();
    let re = compile_full(ip(0));
    assert_all_match(&re, &values(&spec, "ip", "valid_v4"), "ip");
    assert_all_match(&re, &values(&spec, "ip", "valid_v6"), "ip");
}

#[test]
fn date_time_valid() {
    let spec = load_spec();
    let re = compile_full(date_time());
    assert_all_match(&re, &values(&spec, "dateTime", "valid"), "dateTime");
}

#[test]
fn date_time_invalid() {
    let spec = load_spec();
    let re = compile_full(date_time());
    assert_none_match(&re, &values(&spec, "dateTime", "invalid"), "dateTime");
}
