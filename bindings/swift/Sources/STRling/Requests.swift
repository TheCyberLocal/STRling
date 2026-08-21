import Foundation

public typealias SimplyStep = [String: Any]

public struct SourceOptions {
    public var specificationVersion = "1.0-draft.1"
    public var frontendID = "semantic_strling"
    public var frontendVersion: String?
    public var sourceID = "src:swift.adapter"
    public var mediaType = "text/strling"
    public var requestedOutputs = ["semantic", "analysis"]
    public var compilerOptions: [String: Any] = [
        "partial_semantics": "forbid",
        "diagnostic_policy": ["minimum_severity": "hint"],
    ]
    public var targetProfileReference: [String: Any]?

    public init() {}
}

public func sourceCompileRequest(
    _ source: String,
    options: SourceOptions = SourceOptions()
) -> [String: Any] {
    var request: [String: Any] = [
        "contract_version": "1.0.0",
        "specification_version": options.specificationVersion,
        "input": [
            "kind": "source",
            "document": [
                "contract_version": "1.0.0",
                "source_id": options.sourceID,
                "specification_version": options.specificationVersion,
                "frontend": [
                    "id": options.frontendID,
                    "dialect_version": options.frontendVersion ?? options.specificationVersion,
                ],
                "content": [
                    "kind": "inline",
                    "encoding": "utf-8",
                    "media_type": options.mediaType,
                    "text": source,
                ],
                "provenance": ["kind": "authored"],
            ],
        ],
        "requested_outputs": options.requestedOutputs,
        "compiler_options": options.compilerOptions,
    ]
    if let targetProfileReference = options.targetProfileReference {
        request["target_profile"] = targetProfileReference
    }
    return request
}

public func stdlibHelper(
    _ stepID: String,
    _ helperID: String,
    _ parameters: [String: Any]
) -> SimplyStep {
    [
        "step_id": stepID,
        "operation": "stdlib_helper",
        "arguments": [
            "helper_id": helperID,
            "parameters": parameters,
        ],
    ]
}

public func simplyBuilderRequest(_ steps: [SimplyStep], rootStepID: String) -> [String: Any] {
    [
        "protocol_version": "1.1.0",
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "identity_namespace": "swift.adapter",
        "semantic_options": [
            "case_matching": "sensitive",
            "text_model": "unicode_scalar_values",
            "builtin_character_domain": "unicode",
            "wildcard_line_terminators": "exclude",
        ],
        "steps": steps,
        "root_step_id": rootStepID,
        "compile": [
            "requested_outputs": ["semantic", "analysis"],
            "compiler_options": [
                "partial_semantics": "forbid",
                "diagnostic_policy": ["minimum_severity": "hint"],
            ],
        ],
    ]
}
