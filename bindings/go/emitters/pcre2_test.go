package emitters

import (
	"testing"
	
	"github.com/thecyberlocal/strling/bindings/go/core"
)

// TestBasicEmit tests basic PCRE2 emission.
func TestBasicEmit(t *testing.T) {
	// Parse a simple pattern
	_, ast, err := core.Parse("^hello$")
	if err != nil {
		t.Fatalf("Parse error: %v", err)
	}
	
	// Compile to IR
	compiler := core.NewCompiler()
	ir := compiler.Compile(ast)
	
	// Emit to PCRE2
	pattern := Emit(ir, nil)
	
	expected := `^hello$`
	if pattern != expected {
		t.Errorf("Expected %q, got %q", expected, pattern)
	}
}

// TestAnchorEmit tests anchor emission.
func TestAnchorEmit(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"^", "^"},
		{"$", `$`},
		{`\b`, `\b`},
		{`\B`, `\B`},
		{`\A`, `\A`},
		{`\Z`, `\Z`},
	}
	
	for _, tc := range tests {
		t.Run(tc.input, func(t *testing.T) {
			_, ast, err := core.Parse(tc.input)
			if err != nil {
				t.Fatalf("Parse error: %v", err)
			}
			
			compiler := core.NewCompiler()
			ir := compiler.Compile(ast)
			pattern := Emit(ir, nil)
			
			if pattern != tc.expected {
				t.Errorf("Expected %q, got %q", tc.expected, pattern)
			}
		})
	}
}
