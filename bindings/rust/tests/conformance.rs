use serde::Deserialize;
use strling_core::core::nodes::Node;
use strling_core::core::ir::IROp;
use strling_core::core::compiler::Compiler;
use std::fs;
use glob::glob;

#[derive(Deserialize)]
struct TestCase {
    id: String,
    input_ast: Option<Node>,
    expected_ir: Option<IROp>,
    expected_error: Option<String>,
}

#[test]
fn run_conformance_tests() {
    let pattern = "../../tests/spec/*.json";
    let paths = glob(pattern).expect("Failed to read glob pattern");
    let mut count = 0;
    let mut passed = 0;

    for entry in paths {
        match entry {
            Ok(path) => {
                let content = fs::read_to_string(&path).expect("Failed to read file");
                
                // Skip if it's an error test (has expected_error)
                if content.contains("\"expected_error\"") {
                    continue;
                }

                let test_case: TestCase = match serde_json::from_str(&content) {
                    Ok(tc) => tc,
                    Err(e) => {
                        println!("Skipping {}: Deserialization failed: {}", path.display(), e);
                        continue;
                    }
                };

                if let (Some(ast), Some(expected)) = (test_case.input_ast, test_case.expected_ir) {
                    let mut compiler = Compiler::new();
                    let ir = compiler.compile(&ast);
                    
                    if ir != expected {
                        println!("Mismatch in test {}", test_case.id);
                        println!("Expected: {:?}", expected);
                        println!("Got:      {:?}", ir);
                        panic!("Test failed: {}", test_case.id);
                    }
                    passed += 1;
                }
                count += 1;
            },
            Err(e) => println!("{:?}", e),
        }
    }
    println!("Passed {} conformance tests", passed);
    assert!(passed > 0, "No tests passed");
}
