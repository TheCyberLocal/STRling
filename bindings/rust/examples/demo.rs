use strling::{compile, CompileRequest};

fn main() {
    let request: CompileRequest = serde_json::from_str(include_str!(
        "../../../spec/contracts/1.0/examples/compile-request/regex-compat-success.json"
    ))
    .expect("canonical request fixture");
    let result = compile(&request, None).expect("canonical boundary");
    println!("{:?}", result.outcome);
}
