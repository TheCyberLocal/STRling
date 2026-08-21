// Code generated from the canonical standard-library registry. DO NOT EDIT.
// These lexical helpers record Simply recipes; they do not validate semantics.
package strling

const StdlibSurfaceSourceSHA256 = "db3d1fc6ddd1b0ef83cb7bfb4a9bd84c8bcc547d5a6649a6747cc4b94fb4edff"
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
