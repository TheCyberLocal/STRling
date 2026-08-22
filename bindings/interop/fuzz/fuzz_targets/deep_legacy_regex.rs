#![no_main]

use libfuzzer_sys::fuzz_target;
use serde_json::json;
use strling_kernel::normalization::normalize;
use strling_kernel::regex_frontend::parse;
use strling_kernel::source::SourceDocument;

fn document(source: &str) -> SourceDocument {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "source_id": "src:deep-quality.legacy-regex",
        "specification_version": "1.0-draft.1",
        "frontend": {
            "id": "strling.regex-compat",
            "dialect_version": "1.0.0"
        },
        "content": {
            "kind": "inline",
            "encoding": "utf-8",
            "media_type": "text/strling-regex",
            "text": source
        },
        "provenance": { "kind": "imported" }
    }))
    .expect("governed source document")
}

fuzz_target!(|data: &[u8]| {
    let source = String::from_utf8_lossy(data);
    let input = document(&source);
    let first = parse(&input);
    let repeated = parse(&input);
    assert_eq!(format!("{first:?}"), format!("{repeated:?}"));

    if let Ok(parsed) = first {
        let normalized = normalize(&parsed.program);
        assert_eq!(normalized, normalize(&parsed.program));
        if let Ok(program) = normalized {
            assert_eq!(normalize(&program), Ok(program));
        }
    }
});
