package strling

type SourceOptions struct {
	SpecificationVersion   string
	FrontendID             string
	FrontendVersion        string
	SourceID               string
	MediaType              string
	RequestedOutputs       []string
	CompilerOptions        map[string]any
	TargetProfileReference map[string]any
}

func SourceCompileRequest(source string, options *SourceOptions) map[string]any {
	prepared := SourceOptions{}
	if options != nil {
		prepared = *options
	}
	if prepared.SpecificationVersion == "" {
		prepared.SpecificationVersion = defaultSpecification
	}
	if prepared.FrontendID == "" {
		prepared.FrontendID = defaultSemanticFrontend
	}
	if prepared.FrontendVersion == "" {
		prepared.FrontendVersion = prepared.SpecificationVersion
	}
	if prepared.SourceID == "" {
		prepared.SourceID = defaultSourceIdentity
	}
	if prepared.MediaType == "" {
		prepared.MediaType = defaultSourceMediaType
	}
	if len(prepared.RequestedOutputs) == 0 {
		prepared.RequestedOutputs = []string{"semantic", "analysis"}
	}
	if prepared.CompilerOptions == nil {
		prepared.CompilerOptions = map[string]any{
			"partial_semantics": "forbid",
			"diagnostic_policy": map[string]any{"minimum_severity": "hint"},
		}
	}
	request := map[string]any{
		"contract_version":      defaultContractVersion,
		"specification_version": prepared.SpecificationVersion,
		"input": map[string]any{
			"kind": "source",
			"document": map[string]any{
				"contract_version":      defaultContractVersion,
				"source_id":             prepared.SourceID,
				"specification_version": prepared.SpecificationVersion,
				"frontend": map[string]any{
					"id":              prepared.FrontendID,
					"dialect_version": prepared.FrontendVersion,
				},
				"content": map[string]any{
					"kind":       "inline",
					"encoding":   "utf-8",
					"media_type": prepared.MediaType,
					"text":       source,
				},
				"provenance": map[string]any{"kind": "authored"},
			},
		},
		"requested_outputs": prepared.RequestedOutputs,
		"compiler_options":  prepared.CompilerOptions,
	}
	if prepared.TargetProfileReference != nil {
		request["target_profile"] = prepared.TargetProfileReference
	}
	return request
}

type SimplyStep map[string]any

func StdlibHelper(stepID, helperID string, parameters map[string]any) SimplyStep {
	return SimplyStep{
		"step_id":   stepID,
		"operation": "stdlib_helper",
		"arguments": map[string]any{
			"helper_id":  helperID,
			"parameters": parameters,
		},
	}
}

func SimplyBuilderRequest(steps []SimplyStep, rootStepID string) map[string]any {
	return map[string]any{
		"protocol_version":      defaultSimplyProtocol,
		"contract_version":      defaultContractVersion,
		"specification_version": defaultSpecification,
		"identity_namespace":    defaultSimplyNamespace,
		"semantic_options": map[string]any{
			"case_matching":             "sensitive",
			"text_model":                "unicode_scalar_values",
			"builtin_character_domain":  "unicode",
			"wildcard_line_terminators": "exclude",
		},
		"steps":        steps,
		"root_step_id": rootStepID,
		"compile": map[string]any{
			"requested_outputs": []string{"semantic", "analysis"},
			"compiler_options": map[string]any{
				"partial_semantics": "forbid",
				"diagnostic_policy": map[string]any{"minimum_severity": "hint"},
			},
		},
	}
}
