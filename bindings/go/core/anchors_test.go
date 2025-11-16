package core

import (
	"testing"
)

// Test Design — anchors_test.go
//
// ## Purpose
// This test suite validates the correct parsing of all anchor tokens (^, $, \b, \B, etc.).
// It ensures that each anchor is correctly mapped to a corresponding Anchor AST node
// with the proper type and that its parsing is unaffected by flags or surrounding
// constructs.
//
// ## Description
// Anchors are zero-width assertions that do not consume characters but instead
// match a specific **position** within the input string, such as the start of a
// line or a boundary between a word and a space. This suite tests the parser's
// ability to correctly identify all supported core and extension anchors and
// produce the corresponding `nodes.Anchor` AST object.
//
// ## Scope
// -   **In scope:**
// -   Parsing of core line anchors (`^`, `$`) and word boundary anchors
// (`\b`, `\B`).
// -   Parsing of non-core, engine-specific absolute anchors (`\A`, `\Z`, `\z`).
//
// -   The structure and `at` value of the resulting `nodes.Anchor` AST node.
//
// -   How anchors are parsed when placed at the start, middle, or end of a sequence.
//
// -   Ensuring the parser's output for `^` and `$` is consistent regardless
// of the multiline (`m`) flag's presence.
// -   **Out of scope:**
// -   The runtime *behavioral change* of `^` and `$` when the `m` flag is
// active (this is an emitter/engine concern).
// -   Quantification of anchors.
// -   The behavior of `\b` inside a character class, where it represents a
// backspace literal (covered in `char_classes_test.go`).

// TestCategoryA_PositiveCases covers all positive cases for valid anchor syntax.
// These tests verify that each anchor token is parsed into the correct Anchor node
// with the expected `at` value.
func TestCategoryA_PositiveCases(t *testing.T) {
	testCases := []struct {
		inputDsl       string
		expectedAtValue string
		id             string
	}{
		// A.1: Core Line Anchors
		{"^", "Start", "line_start"},
		{"$", "End", "line_end"},
		// A.2: Core Word Boundary Anchors
		{`\b`, "WordBoundary", "word_boundary"},
		{`\B`, "NotWordBoundary", "not_word_boundary"},
		// A.3: Absolute Anchors (Extension Features)
		{`\A`, "AbsoluteStart", "absolute_start_ext"},
		{`\Z`, "EndBeforeFinalNewline", "end_before_newline_ext"},
	}
	
	for _, tc := range testCases {
		t.Run(tc.id, func(t *testing.T) {
			// Tests that each individual anchor token is parsed into the correct
			// Anchor AST node.
			_, ast, err := Parse(tc.inputDsl)
			if err != nil {
				t.Fatalf("Parse error: %v", err)
			}
			
			anchor, ok := ast.(Anchor)
			if !ok {
				t.Fatalf("Expected Anchor, got %T", ast)
			}
			
			if anchor.At != tc.expectedAtValue {
				t.Errorf("Expected at=%s, got at=%s", tc.expectedAtValue, anchor.At)
			}
		})
	}
}

// TestCategoryB_NegativeCases is intentionally empty.
// Anchors are single, unambiguous tokens, and there are no anchor-specific parse errors.
// Invalid escape sequences are handled by the literal/escape parser and are tested in
// that suite.
func TestCategoryB_NegativeCases(t *testing.T) {
	// Intentionally empty
}

// TestCategoryC_EdgeCases covers edge cases related to the position and combination of anchors.
func TestCategoryC_EdgeCases(t *testing.T) {
	t.Run("should parse a pattern with only anchors", func(t *testing.T) {
		// Tests that a pattern containing multiple anchors is parsed into a
		// correct sequence of Anchor nodes.
		_, ast, err := Parse(`^\A\b$`)
		if err != nil {
			t.Fatalf("Parse error: %v", err)
		}
		
		seq, ok := ast.(Seq)
		if !ok {
			t.Fatalf("Expected Seq, got %T", ast)
		}
		
		if len(seq.Parts) != 4 {
			t.Fatalf("Expected 4 parts, got %d", len(seq.Parts))
		}
		
		// Check all parts are anchors
		expectedAtValues := []string{"Start", "AbsoluteStart", "WordBoundary", "End"}
		for i, part := range seq.Parts {
			anchor, ok := part.(Anchor)
			if !ok {
				t.Fatalf("Part %d: expected Anchor, got %T", i, part)
			}
			if anchor.At != expectedAtValues[i] {
				t.Errorf("Part %d: expected at=%s, got at=%s", i, expectedAtValues[i], anchor.At)
			}
		}
	})
	
	// Test anchors in different positions
	positionTests := []struct {
		inputDsl         string
		expectedPosition int
		expectedAtValue  string
		id               string
	}{
		{`^a`, 0, "Start", "at_start"},
		{`a\bb`, 1, "WordBoundary", "in_middle"},
		{`ab$`, 2, "End", "at_end"},
	}
	
	for _, tc := range positionTests {
		t.Run("should_parse_anchors_in_different_positions_"+tc.id, func(t *testing.T) {
			// Tests that anchors are correctly parsed as part of a sequence at
			// various positions.
			_, ast, err := Parse(tc.inputDsl)
			if err != nil {
				t.Fatalf("Parse error: %v", err)
			}
			
			seq, ok := ast.(Seq)
			if !ok {
				t.Fatalf("Expected Seq, got %T", ast)
			}
			
			if tc.expectedPosition >= len(seq.Parts) {
				t.Fatalf("Position %d out of range (len=%d)", tc.expectedPosition, len(seq.Parts))
			}
			
			anchorNode := seq.Parts[tc.expectedPosition]
			anchor, ok := anchorNode.(Anchor)
			if !ok {
				t.Fatalf("Expected Anchor at position %d, got %T", tc.expectedPosition, anchorNode)
			}
			
			if anchor.At != tc.expectedAtValue {
				t.Errorf("Expected at=%s, got at=%s", tc.expectedAtValue, anchor.At)
			}
		})
	}
}

// TestCategoryD_InteractionCases covers how anchors interact with other DSL features,
// such as flags and grouping constructs.
func TestCategoryD_InteractionCases(t *testing.T) {
	t.Run("should not change the parsed AST when multiline flag is present", func(t *testing.T) {
		// A critical test to ensure the parser's output for `^` and `$` is
		// identical regardless of the multiline flag. The flag's semantic
		// effect is a runtime concern for the regex engine.
		_, astNoM, err := Parse("^a$")
		if err != nil {
			t.Fatalf("Parse error: %v", err)
		}
		
		_, astWithM, err := Parse("%flags m\n^a$")
		if err != nil {
			t.Fatalf("Parse error: %v", err)
		}
		
		// Compare the AST structures
		seqNoM, ok := astNoM.(Seq)
		if !ok {
			t.Fatalf("Expected Seq, got %T", astNoM)
		}
		
		seqWithM, ok := astWithM.(Seq)
		if !ok {
			t.Fatalf("Expected Seq, got %T", astWithM)
		}
		
		if len(seqNoM.Parts) != len(seqWithM.Parts) {
			t.Fatalf("Different number of parts: %d vs %d", len(seqNoM.Parts), len(seqWithM.Parts))
		}
		
		// Check specific anchors
		anchor0, ok := seqNoM.Parts[0].(Anchor)
		if !ok || anchor0.At != "Start" {
			t.Errorf("Expected Start anchor at position 0")
		}
		
		anchor2, ok := seqNoM.Parts[2].(Anchor)
		if !ok || anchor2.At != "End" {
			t.Errorf("Expected End anchor at position 2")
		}
	})
	
	// Test anchors inside groups and lookarounds
	groupTests := []struct {
		inputDsl        string
		expectedAtValue string
		id              string
	}{
		{`(^a)`, "Start", "in_capturing_group"},
		{`(?:a\b)`, "WordBoundary", "in_noncapturing_group"},
		{`(?=a$)`, "End", "in_lookahead"},
		{`(?<=^a)`, "Start", "in_lookbehind"},
	}
	
	for _, tc := range groupTests {
		t.Run("should_parse_anchors_inside_groups_and_lookarounds_"+tc.id, func(t *testing.T) {
			// Tests that anchors are correctly parsed when nested inside other
			// syntactic constructs.
			_, ast, err := Parse(tc.inputDsl)
			if err != nil {
				t.Fatalf("Parse error: %v", err)
			}
			
			// The anchor is inside a container (Group or Look)
			var containerBody Node
			switch container := ast.(type) {
			case Group:
				containerBody = container.Body
			case Look:
				containerBody = container.Body
			default:
				t.Fatalf("Expected Group or Look, got %T", ast)
			}
			
			// Find the anchor in the body
			var anchorNode *Anchor
			switch body := containerBody.(type) {
			case Seq:
				// Find the anchor in the sequence
				for _, part := range body.Parts {
					if anchor, ok := part.(Anchor); ok {
						anchorNode = &anchor
						break
					}
				}
			case Anchor:
				// Direct anchor
				anchorNode = &body
			}
			
			if anchorNode == nil {
				t.Fatalf("No anchor found in container body")
			}
			
			if anchorNode.At != tc.expectedAtValue {
				t.Errorf("Expected at=%s, got at=%s", tc.expectedAtValue, anchorNode.At)
			}
		})
	}
}
