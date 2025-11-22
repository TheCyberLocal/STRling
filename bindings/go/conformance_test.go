package strling

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"testing"

	"github.com/thecyberlocal/strling/bindings/go/core"
)

type SpecFile struct {
	ID          string                 `json:"id"`
	InputAST    NodeWrapper            `json:"input_ast"`
	ExpectedIR  map[string]interface{} `json:"expected_ir"`
}

func TestConformance(t *testing.T) {
	// Locate spec directory relative to this test file
	// Assuming running from bindings/go
	specDir := "../../tests/spec"
	
	// Verify spec dir exists
	if _, err := os.Stat(specDir); os.IsNotExist(err) {
		t.Skipf("Spec directory not found at %s, skipping conformance tests", specDir)
	}

	err := filepath.Walk(specDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if info.IsDir() || filepath.Ext(path) != ".json" {
			return nil
		}

		t.Run(filepath.Base(path), func(t *testing.T) {
			data, err := os.ReadFile(path)
			if err != nil {
				t.Fatalf("failed to read file: %v", err)
			}

			var spec SpecFile
			if err := json.Unmarshal(data, &spec); err != nil {
				t.Fatalf("failed to unmarshal spec: %v", err)
			}

			if spec.InputAST.Node == nil {
				t.Skip("Skipping test without input_ast (likely an error test case)")
			}

			astNode, err := spec.InputAST.Node.ToCore()
			if err != nil {
				t.Fatalf("failed to convert AST to core: %v", err)
			}

			compiler := core.NewCompiler()
			result := compiler.CompileWithMetadata(astNode)

			// Convert IROp to map using ToDict for comparison
			// t.Logf("Type of result['ir']: %T", result["ir"])
			if irOp, ok := result["ir"].(core.IROp); ok {
				result["ir"] = irOp.ToDict()
			} else {
				// t.Logf("result['ir'] does not implement core.IROp")
			}

			// Normalize types for comparison (int vs float64)
			// The easiest way is to round-trip both through JSON
			irJSON, _ := json.Marshal(result["ir"])
			expectedJSON, _ := json.Marshal(spec.ExpectedIR)

			var irMap, expectedMap map[string]interface{}
			json.Unmarshal(irJSON, &irMap)
			json.Unmarshal(expectedJSON, &expectedMap)

			if !reflect.DeepEqual(irMap, expectedMap) {
				t.Errorf("IR mismatch for %s:\nGot:      %s\nExpected: %s", spec.ID, string(irJSON), string(expectedJSON))
			}
		})
		return nil
	})
	if err != nil {
		t.Fatalf("failed to walk spec dir: %v", err)
	}
}
