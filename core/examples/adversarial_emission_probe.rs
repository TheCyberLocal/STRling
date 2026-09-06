//! Repository-only observation of serializer diagnostics before kernel delivery.

use std::error::Error;
use std::io::{self, Read};

use serde_json::{json, Value};
use strling_kernel::capability_evaluation::evaluate_capabilities;
use strling_kernel::portability_planning::plan_portability;
use strling_kernel::python_re_lowering::lower_python_re;
use strling_kernel::python_re_serialization::serialize_python_re;
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::TargetProfile;
use strling_kernel::target_lowering::lower_pcre2;
use strling_kernel::target_serialization::serialize_pcre2;

fn main() -> Result<(), Box<dyn Error>> {
    let mut input = String::new();
    io::stdin()
        .take(4 * 1024 * 1024)
        .read_to_string(&mut input)?;
    let request: Value = serde_json::from_str(&input)?;
    let program: SemanticProgram = serde_json::from_value(request["program"].clone())?;
    let profile: TargetProfile = serde_json::from_value(request["profile"].clone())?;
    let foundational = analyze(&program)?;
    let structural = analyze_structure(&program, &foundational)?;
    let evaluation = evaluate_capabilities(&program, &foundational, &structural, &profile)?;
    let plan = plan_portability(&program, &foundational, &structural, &profile, &evaluation)?;
    let observation = match profile.engine.id.as_str() {
        "pcre2" => match lower_pcre2(&program, &profile, &plan) {
            Ok(lowered) => match serialize_pcre2(&lowered) {
                Ok(artifact) => json!({"artifact": artifact}),
                Err(error) => {
                    json!({"diagnostics": error.diagnostics, "display": error.to_string()})
                }
            },
            Err(error) => {
                json!({"diagnostics": error.diagnostics, "display": error.to_string()})
            }
        },
        "python_re" => match lower_python_re(&program, &profile, &plan) {
            Ok(lowered) => match serialize_python_re(&lowered) {
                Ok(artifact) => json!({"artifact": artifact}),
                Err(error) => {
                    json!({"diagnostics": error.diagnostics, "display": error.to_string()})
                }
            },
            Err(error) => {
                json!({"diagnostics": error.diagnostics, "display": error.to_string()})
            }
        },
        _ => return Err("probe supports only PCRE2 and Python serializers".into()),
    };
    println!("{}", serde_json::to_string(&observation)?);
    Ok(())
}
