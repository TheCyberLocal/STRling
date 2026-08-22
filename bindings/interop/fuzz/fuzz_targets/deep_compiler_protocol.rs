#![no_main]

use libfuzzer_sys::fuzz_target;
use strling_kernel::compile;
use strling_kernel::protocol::CompileRequest;
use strling_kernel::validation::from_json;

fuzz_target!(|data: &[u8]| {
    let source = String::from_utf8_lossy(data);
    let first = from_json::<CompileRequest>(&source);
    let repeated = from_json::<CompileRequest>(&source);
    assert_eq!(format!("{first:?}"), format!("{repeated:?}"));

    if let Ok(request) = first {
        let result = compile(&request, None);
        assert_eq!(
            format!("{result:?}"),
            format!("{:?}", compile(&request, None))
        );
    }
});
