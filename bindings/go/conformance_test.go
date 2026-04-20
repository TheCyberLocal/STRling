package strling

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	"github.com/strling-lang/strling/bindings/go/core"
)

// SpecFile represents a conformance test specification.
// It supports both success cases (with input_ast and expected_ir)
// and error cases (with input_dsl and expected_error).
type SpecFile struct {
	ID            string                 `json:"id"`
	InputAST      NodeWrapper            `json:"input_ast"`
	ExpectedIR    map[string]interface{} `json:"expected_ir"`
	InputDSL      string                 `json:"input_dsl"`
	ExpectedError string                 `json:"expected_error"`
	ExpectedHint  string                 `json:"expected_hint"`
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

			// Parser error test cases: parse input_dsl and check error + hint
			if spec.InputAST.Node == nil {
				if spec.InputDSL == "" || spec.ExpectedError == "" {
					return // no input to test
				}
				_, _, parseErr := core.Parse(spec.InputDSL)
				if parseErr == nil {
					t.Fatalf("expected parse error but got success")
				}
				parseError, ok := parseErr.(*core.STRlingParseError)
				if !ok {
					t.Fatalf("expected STRlingParseError, got %T", parseErr)
				}
				if !strings.Contains(parseError.Message, spec.ExpectedError) {
					t.Errorf("error message mismatch\n  Expected substring: %s\n  Actual: %s",
						spec.ExpectedError, parseError.Message)
				}
				if spec.ExpectedHint != "" && parseError.Hint != spec.ExpectedHint {
					t.Errorf("hint mismatch\n  Expected: %s\n  Actual:   %s",
						spec.ExpectedHint, parseError.Hint)
				}
				return
			}

			astNode, err := spec.InputAST.Node.ToCore()
			if err != nil {
				t.Fatalf("failed to convert AST to core: %v", err)
			}

			compiler := core.NewCompiler()
			result := compiler.CompileWithMetadata(astNode)

			// Convert IROp to map using ToDict for comparison
			if irOp, ok := result["ir"].(core.IROp); ok {
				result["ir"] = irOp.ToDict()
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
