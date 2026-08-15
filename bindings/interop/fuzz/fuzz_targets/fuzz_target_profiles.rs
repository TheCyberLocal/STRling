#![no_main]

mod common;

use libfuzzer_sys::fuzz_target;
use serde_json::{json, Value};
use strling_kernel::target::TargetProfile;
use strling_kernel::validation::Validate;

fuzz_target!(|data: &[u8]| {
    let (selector, rest) = data.split_first().unwrap_or((&0, &[]));
    let mut target_profile: Value = serde_json::from_str(include_str!(
        "../../../../spec/targets/profiles/pcre2-10.42.json"
    ))
    .expect("canonical target-profile fuzz seed");
    match selector % 6 {
        0 => {}
        1 => {
            target_profile["profile_id"] =
                Value::String(String::from_utf8_lossy(rest).into_owned());
        }
        2 => {
            target_profile["engine"]["version"]["value"] =
                Value::String(String::from_utf8_lossy(rest).into_owned());
        }
        3 => {
            if let Some(capabilities) = target_profile["capabilities"].as_array_mut() {
                capabilities.truncate(usize::from(rest.first().copied().unwrap_or(0)) % 8);
            }
        }
        4 => target_profile["options"] = common::arbitrary_value(rest),
        _ => target_profile = common::arbitrary_value(rest),
    }
    let request = common::request(
        "target_profile.inspect",
        json!({"target_profile": target_profile}),
    );
    let response = common::assert_closed_response(&request);
    match response["status"].as_str() {
        Some("error") => {
            assert!(matches!(
                response["error"]["code"].as_str(),
                Some("STRL-INTEROP-0007" | "STRL-INTEROP-0008")
            ));
        }
        Some("completed") => {
            assert_eq!(
                Some("target_profile.inspect"),
                response["operation"].as_str()
            );
            let profile: TargetProfile =
                serde_json::from_value(response["result"]["target_profile"].clone())
                    .expect("completed inspection must return a canonical target profile");
            profile
                .validate()
                .expect("completed inspection profile must validate");
            let expected = serde_json::to_value(
                profile
                    .reference()
                    .expect("validated target profile must have a reference"),
            )
            .expect("serialize canonical target profile reference");
            assert_eq!(expected, response["result"]["profile_reference"]);
        }
        _ => unreachable!("closed response helper validates status"),
    }
});
