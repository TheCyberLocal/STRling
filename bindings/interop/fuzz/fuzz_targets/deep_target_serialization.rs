#![no_main]

use libfuzzer_sys::fuzz_target;
use serde_json::json;
use strling_kernel::compile;
use strling_kernel::protocol::CompileRequest;
use strling_kernel::target::TargetProfile;
use strling_kernel::validation::from_json;

const PROFILES: &[&str] = &[
    include_str!("../../../../spec/targets/profiles/pcre2-10.42.json"),
    include_str!("../../../../spec/targets/profiles/pcre2-10.43.json"),
    include_str!("../../../../spec/targets/profiles/ecmascript-2024.json"),
    include_str!("../../../../spec/targets/profiles/python-re-3.11.json"),
    include_str!("../../../../spec/targets/profiles/python-re-3.11-bytes.json"),
];

fuzz_target!(|data: &[u8]| {
    let profile_index = data.first().copied().unwrap_or_default() as usize % PROFILES.len();
    let text = String::from_utf8_lossy(data.get(1..).unwrap_or_default());
    let profile: TargetProfile = from_json(PROFILES[profile_index]).expect("governed profile");
    let mut request: CompileRequest = serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "input": {
            "kind": "semantic",
            "program": {
                "contract_version": "1.0.0",
                "specification_version": "1.0-draft.1",
                "normalization": "canonical-v1",
                "case_matching": "sensitive",
                "root": {
                    "node_id": "node:deep-quality.literal",
                    "kind": "literal",
                    "text": text
                }
            }
        },
        "requested_outputs": ["semantic", "analysis", "portability", "target_artifact"],
        "compiler_options": {
            "partial_semantics": "forbid",
            "diagnostic_policy": { "minimum_severity": "hint" }
        }
    }))
    .expect("governed compile request");
    request.target_profile = Some(profile.reference().expect("profile reference"));

    let first = compile(&request, Some(&profile));
    let repeated = compile(&request, Some(&profile));
    assert_eq!(format!("{first:?}"), format!("{repeated:?}"));
});
