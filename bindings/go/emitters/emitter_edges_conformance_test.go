package emitters

// Emitter Edges Conformance — Go bridge.
//
// Drives the global pathological-AST fixture
// `tests/conformance/inputs/emitter_edges/pathological.json` through
// the Go PCRE2 emitter and asserts each safety guard fires:
//   1. Variable-Length Lookbehind Rejection — *core.STRlingCompilationError
//   2. AST Depth Limit Exceeded             — *core.STRlingCompilationError
//   3. ReDoS Risk Warning (`(a+)+`)         — non-fatal core.STRlingWarning
//
// The local astToIR mirrors the TypeScript bridge so the test targets
// the emitter without coupling to the parser/compiler stages. Keep it
// minimal — supporting only node types currently appearing in
// `pathological.json` — so adapter omissions cannot mask emitter bugs by
// silently dropping nodes.

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/strling-lang/strling/bindings/go/core"
)

func fixturePath(t *testing.T) string {
	t.Helper()
	dir, err := os.Getwd()
	if err != nil {
		t.Fatalf("getwd: %v", err)
	}
	for i := 0; i < 12; i++ {
		if _, err := os.Stat(filepath.Join(dir, "toolchain.json")); err == nil {
			return filepath.Join(dir, "tests", "conformance", "inputs",
				"emitter_edges", "pathological.json")
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}
	t.Fatalf("could not locate workspace root (toolchain.json) from %s", dir)
	return ""
}

func astToIR(t *testing.T, node map[string]interface{}) core.IROp {
	t.Helper()
	typ, _ := node["type"].(string)
	switch typ {
	case "Literal":
		val, _ := node["value"].(string)
		return core.IRLit{Value: val}
	case "Group":
		body, _ := node["content"].(map[string]interface{})
		return core.IRGroup{Capturing: false, Body: astToIR(t, body), Name: nil, Atomic: nil}
	case "Quantifier":
		body, _ := node["content"].(map[string]interface{})
		minF, _ := node["min"].(float64)
		var maxV interface{}
		if rawMax, present := node["max"]; present && rawMax != nil {
			if f, ok := rawMax.(float64); ok {
				maxV = int(f)
			} else {
				maxV = "Inf"
			}
		} else {
			// null/missing in the user-facing AST means unbounded → IR sentinel "Inf".
			maxV = "Inf"
		}
		mode, ok := node["mode"].(string)
		if !ok {
			mode = "Greedy"
		}
		return core.IRQuant{Child: astToIR(t, body), Min: int(minF), Max: maxV, Mode: mode}
	case "Lookbehind":
		body, _ := node["content"].(map[string]interface{})
		return core.IRLook{Dir: "Behind", Neg: false, Body: astToIR(t, body)}
	case "NegativeLookbehind":
		body, _ := node["content"].(map[string]interface{})
		return core.IRLook{Dir: "Behind", Neg: true, Body: astToIR(t, body)}
	case "Lookahead":
		body, _ := node["content"].(map[string]interface{})
		return core.IRLook{Dir: "Ahead", Neg: false, Body: astToIR(t, body)}
	case "NegativeLookahead":
		body, _ := node["content"].(map[string]interface{})
		return core.IRLook{Dir: "Ahead", Neg: true, Body: astToIR(t, body)}
	}
	t.Fatalf("astToIR: unsupported pathological AST node type %q. Extend the adapter when new pathological vectors are added.", typ)
	return nil
}

func expectedSubstring(prefixed string) string {
	if strings.HasPrefix(prefixed, "STRlingCompilationError:") {
		return strings.TrimSpace(strings.TrimPrefix(prefixed, "STRlingCompilationError:"))
	}
	if strings.HasPrefix(prefixed, "STRlingWarning") {
		if idx := strings.Index(prefixed, "]"); idx >= 0 {
			return strings.TrimSpace(strings.TrimLeft(prefixed[idx+1:], ": "))
		}
	}
	return prefixed
}

func TestEmitterEdgesPathological(t *testing.T) {
	path := fixturePath(t)
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read fixture: %v", err)
	}
	var doc struct {
		Tests []map[string]interface{} `json:"tests"`
	}
	if err := json.Unmarshal(raw, &doc); err != nil {
		t.Fatalf("parse fixture: %v", err)
	}
	for _, tc := range doc.Tests {
		name, _ := tc["name"].(string)
		t.Run(name, func(t *testing.T) {
			astMap, _ := tc["ast"].(map[string]interface{})
			ir := astToIR(t, astMap)
			maxDepth := 0
			if d, ok := tc["depth_override_for_test"].(float64); ok {
				maxDepth = int(d)
			}

			if ee, ok := tc["expected_error"].(string); ok {
				needle := expectedSubstring(ee)
				_, err := emitWithRecover(ir, maxDepth)
				if err == nil {
					t.Fatalf("expected STRlingCompilationError, got nil")
				}
				var ce *core.STRlingCompilationError
				if !errors.As(err, &ce) {
					t.Fatalf("expected *core.STRlingCompilationError, got %T: %v", err, err)
				}
				if !strings.Contains(ce.Message, needle) {
					t.Fatalf("error message missing %q\n  got: %s", needle, ce.Message)
				}
				return
			}
			if ew, ok := tc["expected_warning"].(string); ok {
				needle := expectedSubstring(ew)
				res, err := EmitWithDiagnostics(ir, nil, maxDepth)
				if err != nil {
					t.Fatalf("unexpected error: %v", err)
				}
				if res.Pattern == "" {
					t.Fatalf("expected non-empty pattern when only a warning fires")
				}
				found := false
				for _, w := range res.Warnings {
					if w.Code == "REDOS_RISK" && strings.Contains(w.Message, needle) {
						found = true
						break
					}
				}
				if !found {
					t.Fatalf("missing REDOS_RISK warning containing %q\n  warnings: %+v", needle, res.Warnings)
				}
				return
			}
			t.Fatalf("test case %q declares neither expected_error nor expected_warning", name)
		})
	}
}

func emitWithRecover(ir core.IROp, maxDepth int) (*core.CompileResult, error) {
	return EmitWithDiagnostics(ir, nil, maxDepth)
}

func TestEmitterEdgesNonPathologicalEmitsNoWarnings(t *testing.T) {
	res, err := EmitWithDiagnostics(core.IRLit{Value: "abc"}, nil, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if res.Pattern != "abc" {
		t.Fatalf("expected pattern 'abc', got %q", res.Pattern)
	}
	if len(res.Warnings) != 0 {
		t.Fatalf("expected no warnings, got %+v", res.Warnings)
	}
}

func TestEmitterEdgesDepthCapDoesNotFireUnderLimit(t *testing.T) {
	deep := core.IRGroup{
		Body: core.IRGroup{Body: core.IRLit{Value: "ok"}},
	}
	res, err := EmitWithDiagnostics(deep, nil, 5)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(res.Pattern, "ok") {
		t.Fatalf("pattern missing literal: %q", res.Pattern)
	}
	if len(res.Warnings) != 0 {
		t.Fatalf("expected no warnings, got %+v", res.Warnings)
	}
}
