#![no_main]

use libfuzzer_sys::fuzz_target;
use serde_json::json;
use strling_kernel::semantic_frontend::{format, parse};
use strling_kernel::source::SourceDocument;

fn document(source: &str) -> SourceDocument {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "source_id": "src:deep-quality.semantic-dsl",
        "specification_version": "1.0-draft.1",
        "frontend": {
            "id": "strling.semantic",
            "dialect_version": "1.0.0"
        },
        "content": {
            "kind": "inline",
            "encoding": "utf-8",
            "media_type": "text/strling-semantic",
            "text": source
        },
        "provenance": {
            "kind": "authored",
            "description": "P18-T03 governed deep-quality fuzz input"
        }
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
        let canonical = format(&parsed);
        let reparsed = parse(&document(&canonical)).expect("canonical output must reparse");
        assert_eq!(format(&reparsed), canonical);
    }
});
