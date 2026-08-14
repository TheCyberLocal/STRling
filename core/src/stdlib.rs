//! Canonical builder definitions for the governed standard-library registry.
//!
//! The module stays crate-private until the surface-generation task exposes
//! helpers through Simply, the Semantic DSL, bindings, and documentation.

use std::convert::TryFrom;

use crate::semantic::{
    BuiltinClassName, CharacterDomain, RepetitionMaximum, RepetitionMode, SemanticProgram,
};
use crate::simply::{
    SimplyBuilder, SimplyCharacterSetMember, SimplyErrors, SimplyOptions, SimplyValue,
};
use crate::source::SpecificationVersion;

pub(crate) const REGISTRY_VERSION: &str = "1.0.0";
pub(crate) const HELPER_COUNT: usize = 5;
pub(crate) const VARIANT_COUNT: usize = 8;
pub(crate) const SEMANTIC_VALIDATOR_COUNT: usize = 0;

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct CanonicalStdlibPattern {
    pub helper_id: &'static str,
    pub variant_id: &'static str,
    pub program: SemanticProgram,
}

fn builder(namespace: &str) -> Result<SimplyBuilder, SimplyErrors> {
    let specification_version = SpecificationVersion::try_from("1.0-draft.1")
        .expect("the governed specification version is statically valid");
    SimplyBuilder::new(namespace, specification_version, SimplyOptions::default())
}

fn literal(
    builder: &mut SimplyBuilder,
    step_id: &str,
    text: &str,
) -> Result<SimplyValue, SimplyErrors> {
    builder.literal(step_id, text)
}

fn repeated_set(
    builder: &mut SimplyBuilder,
    step_prefix: &str,
    members: &[SimplyCharacterSetMember],
    min: u64,
    max: RepetitionMaximum,
) -> Result<SimplyValue, SimplyErrors> {
    let set = builder.character_set(&format!("{step_prefix}.set"), members, false)?;
    builder.repeat(
        &format!("{step_prefix}.repeat"),
        &set,
        min,
        max,
        RepetitionMode::Greedy,
    )
}

fn optional(
    builder: &mut SimplyBuilder,
    step_id: &str,
    value: &SimplyValue,
) -> Result<SimplyValue, SimplyErrors> {
    builder.repeat(
        step_id,
        value,
        0,
        RepetitionMaximum::Bounded(1),
        RepetitionMode::Greedy,
    )
}

fn sequence(
    builder: &mut SimplyBuilder,
    step_id: &str,
    values: &[SimplyValue],
) -> Result<SimplyValue, SimplyErrors> {
    builder.sequence(step_id, values)
}

fn alternation(
    builder: &mut SimplyBuilder,
    step_id: &str,
    values: &[SimplyValue],
) -> Result<SimplyValue, SimplyErrors> {
    builder.alternation(step_id, values)
}

fn target_digit() -> SimplyCharacterSetMember {
    SimplyCharacterSetMember::Builtin {
        name: BuiltinClassName::Digit,
        domain: Some(CharacterDomain::TargetNative),
        negated: false,
    }
}

fn range(start: char, end: char) -> SimplyCharacterSetMember {
    SimplyCharacterSetMember::Range { start, end }
}

fn scalar(value: char) -> SimplyCharacterSetMember {
    SimplyCharacterSetMember::Literal { value }
}

fn ascii_letters_and(extra: &[char], include_target_digit: bool) -> Vec<SimplyCharacterSetMember> {
    let mut members = vec![range('A', 'Z'), range('a', 'z')];
    if include_target_digit {
        members.push(target_digit());
    }
    members.extend(extra.iter().copied().map(scalar));
    members
}

fn ascii_hex() -> Vec<SimplyCharacterSetMember> {
    vec![range('0', '9'), range('A', 'F'), range('a', 'f')]
}

fn finish(
    helper_id: &'static str,
    variant_id: &'static str,
    builder: SimplyBuilder,
    root: &SimplyValue,
) -> Result<CanonicalStdlibPattern, SimplyErrors> {
    Ok(CanonicalStdlibPattern {
        helper_id,
        variant_id,
        program: builder.finish_program(root)?,
    })
}

pub(crate) fn date_time() -> Result<CanonicalStdlibPattern, SimplyErrors> {
    let mut builder = builder("stdlib.date-time.default")?;
    let year = repeated_set(
        &mut builder,
        "year",
        &[target_digit()],
        4,
        RepetitionMaximum::Bounded(4),
    )?;
    let date_separator_one = literal(&mut builder, "date-separator-one", "-")?;
    let month = repeated_set(
        &mut builder,
        "month",
        &[target_digit()],
        2,
        RepetitionMaximum::Bounded(2),
    )?;
    let date_separator_two = literal(&mut builder, "date-separator-two", "-")?;
    let day = repeated_set(
        &mut builder,
        "day",
        &[target_digit()],
        2,
        RepetitionMaximum::Bounded(2),
    )?;
    let time_separator = literal(&mut builder, "time-separator", "T")?;
    let hour = repeated_set(
        &mut builder,
        "hour",
        &[target_digit()],
        2,
        RepetitionMaximum::Bounded(2),
    )?;
    let clock_separator_one = literal(&mut builder, "clock-separator-one", ":")?;
    let minute = repeated_set(
        &mut builder,
        "minute",
        &[target_digit()],
        2,
        RepetitionMaximum::Bounded(2),
    )?;
    let clock_separator_two = literal(&mut builder, "clock-separator-two", ":")?;
    let second = repeated_set(
        &mut builder,
        "second",
        &[target_digit()],
        2,
        RepetitionMaximum::Bounded(2),
    )?;

    let decimal_point = literal(&mut builder, "fraction.point", ".")?;
    let fraction_digits = repeated_set(
        &mut builder,
        "fraction.digits",
        &[target_digit()],
        1,
        RepetitionMaximum::Unbounded,
    )?;
    let fraction_body = sequence(
        &mut builder,
        "fraction.body",
        &[decimal_point, fraction_digits],
    )?;
    let fraction = optional(&mut builder, "fraction.optional", &fraction_body)?;

    let utc = literal(&mut builder, "offset.utc", "Z")?;
    let sign = builder.character_set("offset.numeric.sign", &[scalar('+'), scalar('-')], false)?;
    let offset_hour = repeated_set(
        &mut builder,
        "offset.numeric.hour",
        &[target_digit()],
        2,
        RepetitionMaximum::Bounded(2),
    )?;
    let offset_separator = literal(&mut builder, "offset.numeric.separator", ":")?;
    let offset_minute = repeated_set(
        &mut builder,
        "offset.numeric.minute",
        &[target_digit()],
        2,
        RepetitionMaximum::Bounded(2),
    )?;
    let numeric_offset = sequence(
        &mut builder,
        "offset.numeric",
        &[sign, offset_hour, offset_separator, offset_minute],
    )?;
    let offset_choice = alternation(&mut builder, "offset.choice", &[utc, numeric_offset])?;
    let offset = optional(&mut builder, "offset.optional", &offset_choice)?;

    let root = sequence(
        &mut builder,
        "root",
        &[
            year,
            date_separator_one,
            month,
            date_separator_two,
            day,
            time_separator,
            hour,
            clock_separator_one,
            minute,
            clock_separator_two,
            second,
            fraction,
            offset,
        ],
    )?;
    finish("stdlib.date_time", "date_time.default", builder, &root)
}

pub(crate) fn email() -> Result<CanonicalStdlibPattern, SimplyErrors> {
    let mut builder = builder("stdlib.email.default")?;
    let local = repeated_set(
        &mut builder,
        "local",
        &ascii_letters_and(&['.', '_', '%', '+', '-'], true),
        1,
        RepetitionMaximum::Unbounded,
    )?;
    let at = literal(&mut builder, "at", "@")?;
    let domain = repeated_set(
        &mut builder,
        "domain",
        &ascii_letters_and(&['.', '-'], true),
        1,
        RepetitionMaximum::Unbounded,
    )?;
    let dot = literal(&mut builder, "suffix-dot", ".")?;
    let suffix = repeated_set(
        &mut builder,
        "suffix",
        &ascii_letters_and(&[], false),
        2,
        RepetitionMaximum::Unbounded,
    )?;
    let root = sequence(&mut builder, "root", &[local, at, domain, dot, suffix])?;
    finish("stdlib.email", "email.default", builder, &root)
}

fn build_ip_v4(
    namespace: &str,
    helper_id: &'static str,
    variant_id: &'static str,
) -> Result<CanonicalStdlibPattern, SimplyErrors> {
    let mut builder = builder(namespace)?;
    let mut values = Vec::with_capacity(7);
    for index in 0..4 {
        values.push(repeated_set(
            &mut builder,
            &format!("component-{index}"),
            &[target_digit()],
            1,
            RepetitionMaximum::Bounded(3),
        )?);
        if index != 3 {
            values.push(literal(&mut builder, &format!("separator-{index}"), ".")?);
        }
    }
    let root = sequence(&mut builder, "root", &values)?;
    finish(helper_id, variant_id, builder, &root)
}

fn build_ip_v6(
    namespace: &str,
    helper_id: &'static str,
    variant_id: &'static str,
) -> Result<CanonicalStdlibPattern, SimplyErrors> {
    let mut builder = builder(namespace)?;
    let mut values = Vec::with_capacity(15);
    for index in 0..8 {
        values.push(repeated_set(
            &mut builder,
            &format!("group-{index}"),
            &ascii_hex(),
            1,
            RepetitionMaximum::Bounded(4),
        )?);
        if index != 7 {
            values.push(literal(&mut builder, &format!("separator-{index}"), ":")?);
        }
    }
    let root = sequence(&mut builder, "root", &values)?;
    finish(helper_id, variant_id, builder, &root)
}

fn build_ip_either() -> Result<CanonicalStdlibPattern, SimplyErrors> {
    let mut builder = builder("stdlib.ip.either")?;
    let mut v4_values = Vec::with_capacity(7);
    for index in 0..4 {
        v4_values.push(repeated_set(
            &mut builder,
            &format!("v4.component-{index}"),
            &[target_digit()],
            1,
            RepetitionMaximum::Bounded(3),
        )?);
        if index != 3 {
            v4_values.push(literal(
                &mut builder,
                &format!("v4.separator-{index}"),
                ".",
            )?);
        }
    }
    let v4 = sequence(&mut builder, "v4", &v4_values)?;

    let mut v6_values = Vec::with_capacity(15);
    for index in 0..8 {
        v6_values.push(repeated_set(
            &mut builder,
            &format!("v6.group-{index}"),
            &ascii_hex(),
            1,
            RepetitionMaximum::Bounded(4),
        )?);
        if index != 7 {
            v6_values.push(literal(
                &mut builder,
                &format!("v6.separator-{index}"),
                ":",
            )?);
        }
    }
    let v6 = sequence(&mut builder, "v6", &v6_values)?;
    let root = alternation(&mut builder, "root", &[v4, v6])?;
    finish("stdlib.ip", "ip.either", builder, &root)
}

pub(crate) fn ip(version: Option<i64>) -> Result<CanonicalStdlibPattern, SimplyErrors> {
    match version {
        Some(4) => build_ip_v4("stdlib.ip.v4", "stdlib.ip", "ip.v4"),
        Some(6) => build_ip_v6("stdlib.ip.v6-full", "stdlib.ip", "ip.v6_full"),
        _ => build_ip_either(),
    }
}

pub(crate) fn url() -> Result<CanonicalStdlibPattern, SimplyErrors> {
    let mut builder = builder("stdlib.url.default")?;
    let http = literal(&mut builder, "scheme.http", "http")?;
    let secure_text = literal(&mut builder, "scheme.secure.text", "s")?;
    let secure = optional(&mut builder, "scheme.secure.optional", &secure_text)?;
    let scheme_separator = literal(&mut builder, "scheme.separator", "://")?;
    let host = repeated_set(
        &mut builder,
        "host",
        &ascii_letters_and(&['.', '-'], true),
        1,
        RepetitionMaximum::Unbounded,
    )?;

    let port_colon = literal(&mut builder, "port.colon", ":")?;
    let port_digits = repeated_set(
        &mut builder,
        "port.digits",
        &[target_digit()],
        1,
        RepetitionMaximum::Unbounded,
    )?;
    let port_body = sequence(&mut builder, "port.body", &[port_colon, port_digits])?;
    let port = optional(&mut builder, "port.optional", &port_body)?;

    let path_slash = literal(&mut builder, "path.slash", "/")?;
    let path_tail = repeated_set(
        &mut builder,
        "path.tail",
        &ascii_letters_and(
            &[
                '/', '_', '-', '.', '~', '%', '&', '=', ':', '@', '!', '$', '\'', '(', ')', '*',
                '+', ',', ';',
            ],
            true,
        ),
        0,
        RepetitionMaximum::Unbounded,
    )?;
    let path_body = sequence(&mut builder, "path.body", &[path_slash, path_tail])?;
    let path = optional(&mut builder, "path.optional", &path_body)?;

    let query_mark = literal(&mut builder, "query.mark", "?")?;
    let query_tail = repeated_set(
        &mut builder,
        "query.tail",
        &ascii_letters_and(
            &[
                '/', '_', '-', '.', '~', '%', '&', '=', ':', '@', '!', '$', '\'', '(', ')', '*',
                '+', ',', ';', '?',
            ],
            true,
        ),
        0,
        RepetitionMaximum::Unbounded,
    )?;
    let query_body = sequence(&mut builder, "query.body", &[query_mark, query_tail])?;
    let query = optional(&mut builder, "query.optional", &query_body)?;

    let fragment_mark = literal(&mut builder, "fragment.mark", "#")?;
    let fragment_tail = repeated_set(
        &mut builder,
        "fragment.tail",
        &ascii_letters_and(
            &[
                '/', '_', '-', '.', '~', '%', '&', '=', ':', '@', '!', '$', '\'', '(', ')', '*',
                '+', ',', ';', '?', '#',
            ],
            true,
        ),
        0,
        RepetitionMaximum::Unbounded,
    )?;
    let fragment_body = sequence(
        &mut builder,
        "fragment.body",
        &[fragment_mark, fragment_tail],
    )?;
    let fragment = optional(&mut builder, "fragment.optional", &fragment_body)?;

    let root = sequence(
        &mut builder,
        "root",
        &[
            http,
            secure,
            scheme_separator,
            host,
            port,
            path,
            query,
            fragment,
        ],
    )?;
    finish("stdlib.url", "url.default", builder, &root)
}

fn build_uuid_generic() -> Result<CanonicalStdlibPattern, SimplyErrors> {
    let mut builder = builder("stdlib.uuid.generic")?;
    let mut values = Vec::with_capacity(9);
    for (index, width) in [8, 4, 4, 4, 12].into_iter().enumerate() {
        values.push(repeated_set(
            &mut builder,
            &format!("group-{index}"),
            &ascii_hex(),
            width,
            RepetitionMaximum::Bounded(width),
        )?);
        if index != 4 {
            values.push(literal(&mut builder, &format!("separator-{index}"), "-")?);
        }
    }
    let root = sequence(&mut builder, "root", &values)?;
    finish("stdlib.uuid", "uuid.generic", builder, &root)
}

fn build_uuid_v4() -> Result<CanonicalStdlibPattern, SimplyErrors> {
    let mut builder = builder("stdlib.uuid.v4")?;
    let group_zero = repeated_set(
        &mut builder,
        "group-0",
        &ascii_hex(),
        8,
        RepetitionMaximum::Bounded(8),
    )?;
    let separator_zero = literal(&mut builder, "separator-0", "-")?;
    let group_one = repeated_set(
        &mut builder,
        "group-1",
        &ascii_hex(),
        4,
        RepetitionMaximum::Bounded(4),
    )?;
    let separator_one = literal(&mut builder, "separator-1", "-")?;
    let version = literal(&mut builder, "version", "4")?;
    let version_tail = repeated_set(
        &mut builder,
        "version-tail",
        &ascii_hex(),
        3,
        RepetitionMaximum::Bounded(3),
    )?;
    let separator_two = literal(&mut builder, "separator-2", "-")?;
    let variant = builder.character_set(
        "variant",
        &[
            scalar('8'),
            scalar('9'),
            scalar('A'),
            scalar('B'),
            scalar('a'),
            scalar('b'),
        ],
        false,
    )?;
    let variant_tail = repeated_set(
        &mut builder,
        "variant-tail",
        &ascii_hex(),
        3,
        RepetitionMaximum::Bounded(3),
    )?;
    let separator_three = literal(&mut builder, "separator-3", "-")?;
    let group_four = repeated_set(
        &mut builder,
        "group-4",
        &ascii_hex(),
        12,
        RepetitionMaximum::Bounded(12),
    )?;
    let root = sequence(
        &mut builder,
        "root",
        &[
            group_zero,
            separator_zero,
            group_one,
            separator_one,
            version,
            version_tail,
            separator_two,
            variant,
            variant_tail,
            separator_three,
            group_four,
        ],
    )?;
    finish("stdlib.uuid", "uuid.v4", builder, &root)
}

pub(crate) fn uuid(version: Option<i64>) -> Result<CanonicalStdlibPattern, SimplyErrors> {
    if version == Some(4) {
        build_uuid_v4()
    } else {
        build_uuid_generic()
    }
}

#[cfg(test)]
mod tests {
    use serde::Deserialize;
    use serde_json::{json, Value};

    use crate::semantic::{CharacterDomain, CharacterSetMember, Node};
    use crate::semantic_frontend::{format, parse, DIALECT_VERSION, FRONTEND_ID, MEDIA_TYPE};
    use crate::source::SourceDocument;
    use crate::validation::Validate;

    use super::{
        date_time, email, ip, url, uuid, HELPER_COUNT, REGISTRY_VERSION, SEMANTIC_VALIDATOR_COUNT,
        VARIANT_COUNT,
    };

    const CANONICAL_SEMANTICS: &str =
        include_str!("../../spec/stdlib/registry/1.0/canonical-semantics.json");

    #[derive(Debug, Deserialize)]
    struct SemanticContract {
        entries: Vec<SemanticEntry>,
        semantic_validator_count: usize,
    }

    #[derive(Debug, Deserialize)]
    struct SemanticEntry {
        builder_identity: String,
        guarantee_level: String,
        helper_id: String,
        semantic_dsl_lines: Vec<String>,
        variant_id: String,
    }

    fn semantic_projection(program: &crate::semantic::SemanticProgram) -> Value {
        fn clean(value: &mut Value) {
            match value {
                Value::Object(object) => {
                    object.remove("node_id");
                    object.remove("capture_id");
                    object.remove("origin");
                    object.remove("sources");
                    for value in object.values_mut() {
                        clean(value);
                    }
                }
                Value::Array(values) => {
                    for value in values {
                        clean(value);
                    }
                }
                _ => {}
            }
        }

        let mut value = serde_json::to_value(program).expect("serialize Semantic IR");
        clean(&mut value);
        value
    }

    fn semantic_document(entry: &SemanticEntry) -> SourceDocument {
        let source = format!("{}\n", entry.semantic_dsl_lines.join("\n"));
        serde_json::from_value(json!({
            "contract_version": "1.0.0",
            "source_id": format!("src:stdlib.{}", entry.variant_id),
            "specification_version": "1.0-draft.1",
            "frontend": {
                "id": FRONTEND_ID,
                "dialect_version": DIALECT_VERSION
            },
            "display_name": format!("{}.strling", entry.variant_id),
            "content": {
                "kind": "inline",
                "encoding": "utf-8",
                "media_type": MEDIA_TYPE,
                "text": source
            },
            "provenance": {
                "kind": "authored",
                "description": "P14-T03 canonical standard-library Semantic DSL"
            }
        }))
        .expect("valid canonical stdlib source")
    }

    fn build_variant(variant_id: &str) -> super::CanonicalStdlibPattern {
        match variant_id {
            "date_time.default" => date_time().expect("date-time"),
            "email.default" => email().expect("email"),
            "ip.v4" => ip(Some(4)).expect("IPv4"),
            "ip.v6_full" => ip(Some(6)).expect("IPv6"),
            "ip.either" => ip(None).expect("IP default"),
            "url.default" => url().expect("URL"),
            "uuid.generic" => uuid(None).expect("UUID generic"),
            "uuid.v4" => uuid(Some(4)).expect("UUID v4"),
            value => panic!("unexpected variant {value}"),
        }
    }

    fn target_native_count(node: &Node) -> usize {
        let own = match node {
            Node::CharacterSet { members, .. } => members
                .iter()
                .filter(|member| {
                    matches!(
                        member,
                        CharacterSetMember::Builtin {
                            domain: CharacterDomain::TargetNative,
                            ..
                        }
                    )
                })
                .count(),
            _ => 0,
        };
        own + match node {
            Node::Sequence { items, .. } => items.iter().map(target_native_count).sum(),
            Node::Alternation { branches, .. } => branches.iter().map(target_native_count).sum(),
            Node::Repeat { body, .. }
            | Node::Capture { body, .. }
            | Node::Lookaround { body, .. }
            | Node::Atomic { body, .. } => target_native_count(body),
            Node::Empty { .. }
            | Node::Literal { .. }
            | Node::Wildcard { .. }
            | Node::CharacterSet { .. }
            | Node::Position { .. }
            | Node::Backreference { .. } => 0,
        }
    }

    #[test]
    fn registry_denominator_and_zero_semantic_validators_are_explicit() {
        assert_eq!(REGISTRY_VERSION, "1.0.0");
        assert_eq!(HELPER_COUNT, 5);
        assert_eq!(VARIANT_COUNT, 8);
        assert_eq!(SEMANTIC_VALIDATOR_COUNT, 0);
    }

    #[test]
    fn all_variants_build_valid_deterministic_canonical_programs() {
        let variants = [
            date_time().expect("date-time"),
            email().expect("email"),
            ip(Some(4)).expect("IPv4"),
            ip(Some(6)).expect("IPv6"),
            ip(None).expect("IP default"),
            url().expect("URL"),
            uuid(None).expect("UUID generic"),
            uuid(Some(4)).expect("UUID v4"),
        ];
        assert_eq!(variants.len(), VARIANT_COUNT);
        for variant in variants {
            variant.program.validate().expect("valid canonical program");
            let again = match variant.variant_id {
                "date_time.default" => date_time().expect("date-time again"),
                "email.default" => email().expect("email again"),
                "ip.v4" => ip(Some(4)).expect("IPv4 again"),
                "ip.v6_full" => ip(Some(6)).expect("IPv6 again"),
                "ip.either" => ip(None).expect("IP default again"),
                "url.default" => url().expect("URL again"),
                "uuid.generic" => uuid(None).expect("UUID generic again"),
                "uuid.v4" => uuid(Some(4)).expect("UUID v4 again"),
                value => panic!("unexpected variant {value}"),
            };
            assert_eq!(variant, again);
        }
    }

    #[test]
    fn selector_fallbacks_preserve_every_other_integer_and_null() {
        for value in [i64::MIN, -1, 0, 1, 5, 7, i64::MAX] {
            assert_eq!(
                ip(Some(value)).expect("IP fallback").variant_id,
                "ip.either"
            );
            assert_eq!(
                uuid(Some(value)).expect("UUID fallback").variant_id,
                "uuid.generic"
            );
        }
        assert_eq!(ip(None).expect("IP null").variant_id, "ip.either");
        assert_eq!(uuid(None).expect("UUID null").variant_id, "uuid.generic");
    }

    #[test]
    fn only_registered_target_dependent_helpers_use_target_native_digits() {
        assert!(target_native_count(&date_time().expect("date-time").program.root) > 0);
        assert!(target_native_count(&email().expect("email").program.root) > 0);
        assert!(target_native_count(&ip(Some(4)).expect("IPv4").program.root) > 0);
        assert_eq!(
            target_native_count(&ip(Some(6)).expect("IPv6").program.root),
            0
        );
        assert!(target_native_count(&url().expect("URL").program.root) > 0);
        assert_eq!(
            target_native_count(&uuid(None).expect("UUID").program.root),
            0
        );
        assert_eq!(
            target_native_count(&uuid(Some(4)).expect("UUID v4").program.root),
            0
        );
    }

    #[test]
    fn registry_semantic_ir_simply_and_dsl_forms_are_equivalent() {
        let contract: SemanticContract =
            serde_json::from_str(CANONICAL_SEMANTICS).expect("canonical semantics contract");
        assert_eq!(contract.semantic_validator_count, SEMANTIC_VALIDATOR_COUNT);
        assert_eq!(contract.entries.len(), VARIANT_COUNT);

        for entry in contract.entries {
            assert_eq!(entry.guarantee_level, "lexical_shape");
            assert!(entry.builder_identity.starts_with("core::stdlib::"));
            let built = build_variant(&entry.variant_id);
            assert_eq!(built.helper_id, entry.helper_id);
            assert_eq!(built.variant_id, entry.variant_id);

            let document = semantic_document(&entry);
            let parsed = parse(&document).expect("parse canonical stdlib DSL");
            let formatted = format(&parsed);
            let formatted_document: SourceDocument = serde_json::from_value(json!({
                "contract_version": "1.0.0",
                "source_id": format!("src:stdlib.formatted.{}", entry.variant_id),
                "specification_version": "1.0-draft.1",
                "frontend": {
                    "id": FRONTEND_ID,
                    "dialect_version": DIALECT_VERSION
                },
                "display_name": format!("{}.formatted.strling", entry.variant_id),
                "content": {
                    "kind": "inline",
                    "encoding": "utf-8",
                    "media_type": MEDIA_TYPE,
                    "text": formatted
                },
                "provenance": {
                    "kind": "authored",
                    "description": "P14-T03 formatted standard-library Semantic DSL"
                }
            }))
            .expect("valid formatted source");
            let reparsed = parse(&formatted_document).expect("reparse canonical formatting");

            assert_eq!(
                semantic_projection(&built.program),
                semantic_projection(&parsed.program),
                "builder and DSL differ for {}",
                entry.variant_id
            );
            assert_eq!(
                semantic_projection(&parsed.program),
                semantic_projection(&reparsed.program),
                "parse/format/parse differs for {}",
                entry.variant_id
            );
        }
    }
}
