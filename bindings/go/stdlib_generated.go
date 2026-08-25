// Code generated from the canonical standard-library registry. DO NOT EDIT.
// These lexical helpers record Simply recipes; they do not validate semantics.
package strling

const StdlibSurfaceSourceSHA256 = "94f28b16873abd0b57b324b76e236cbe17706f5310758e066a88a776e4930a3d"
const StdlibRegistryVersion = "1.0.0"

var StdlibHelperIDs = []string{"stdlib.date_time", "stdlib.email", "stdlib.ip", "stdlib.url", "stdlib.uuid"}

func DateTime(stepID string) SimplyStep {
	return StdlibHelper(stepID, "stdlib.date_time", map[string]any{})
}

func Email(stepID string) SimplyStep {
	return StdlibHelper(stepID, "stdlib.email", map[string]any{})
}

func IP(stepID string, version *int) SimplyStep {
	return StdlibHelper(stepID, "stdlib.ip", map[string]any{"version": version})
}

func URL(stepID string) SimplyStep {
	return StdlibHelper(stepID, "stdlib.url", map[string]any{})
}

func UUID(stepID string, version *int) SimplyStep {
	return StdlibHelper(stepID, "stdlib.uuid", map[string]any{"version": version})
}
