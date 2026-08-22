#![no_main]

use libfuzzer_sys::fuzz_target;
use strling_kernel::normalization::normalize;
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::validation::from_json;

fuzz_target!(|data: &[u8]| {
    let source = String::from_utf8_lossy(data);
    let decoded = from_json::<SemanticProgram>(&source);
    if let Ok(candidate) = decoded {
        let normalized = normalize(&candidate);
        assert_eq!(normalized, normalize(&candidate));
        if let Ok(program) = normalized {
            let semantic = analyze(&program);
            assert_eq!(semantic, analyze(&program));
            if let Ok(facts) = semantic {
                let structural = analyze_structure(&program, &facts);
                assert_eq!(structural, analyze_structure(&program, &facts));
            }
        }
    }
});
