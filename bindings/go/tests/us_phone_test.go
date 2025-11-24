package tests

import (
	"regexp"
	"testing"

	"github.com/thecyberlocal/strling/bindings/go/core"
	"github.com/thecyberlocal/strling/bindings/go/emitters"
	"github.com/thecyberlocal/strling/bindings/go/simply"
)

// TestUSPhoneNumberPattern verifies that building the US phone pattern using the simply
// fluent API produces the same PCRE2 regex as the TypeScript reference implementation.
//
// Expected output: ^(\d{3})[\-. ]?(\d{3})[\-. ]?(\d{4})$
//
// This test validates:
//  1. The simply builder creates the correct AST structure
//  2. The compiler produces the correct IR
//  3. The emitter generates the expected regex string
//  4. The pattern matches TypeScript reference output
func TestUSPhoneNumberPattern(t *testing.T) {
	// Build: ^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$
	// Using the fluent simply API - no raw AST types, no pointers, no NodeWrapper
	phone := simply.Seq(
		simply.Start(),
		simply.GroupCapture(simply.Quant(simply.Digit(), 3, 3)),
		simply.Quant(simply.CharClassFromLiterals("-", ".", " "), 0, 1),
		simply.GroupCapture(simply.Quant(simply.Digit(), 3, 3)),
		simply.Quant(simply.CharClassFromLiterals("-", ".", " "), 0, 1),
		simply.GroupCapture(simply.Quant(simply.Digit(), 4, 4)),
		simply.End(),
	)

	// Compile to IR
	compiler := core.NewCompiler()
	ir := compiler.Compile(phone)

	// Emit to PCRE2 regex
	pattern := emitters.Emit(ir, nil)

	// The emitter escapes '-' inside character classes, resulting in "[\-. ]"
	// This matches the TypeScript reference output
	expected := `^(\d{3})[\-. ]?(\d{3})[\-. ]?(\d{4})$`

	if pattern != expected {
		t.Errorf("US phone pattern mismatch:\n  got:      %q\n  expected: %q", pattern, expected)
	}
}

// TestUSPhoneNumberMatching verifies that the generated regex correctly matches
// valid US phone numbers in various formats and rejects invalid ones.
func TestUSPhoneNumberMatching(t *testing.T) {
	phone := simply.Seq(
		simply.Start(),
		simply.GroupCapture(simply.Quant(simply.Digit(), 3, 3)),
		simply.Quant(simply.CharClassFromLiterals("-", ".", " "), 0, 1),
		simply.GroupCapture(simply.Quant(simply.Digit(), 3, 3)),
		simply.Quant(simply.CharClassFromLiterals("-", ".", " "), 0, 1),
		simply.GroupCapture(simply.Quant(simply.Digit(), 4, 4)),
		simply.End(),
	)

	compiler := core.NewCompiler()
	ir := compiler.Compile(phone)
	pattern := emitters.Emit(ir, nil)

	// Compile to Go regexp for validation
	re := regexp.MustCompile(pattern)

	// Test cases: valid phone numbers should match
	validNumbers := []string{
		"555-123-4567",
		"555.123.4567",
		"555 123 4567",
		"5551234567",
		"555-1234567",
		"555.1234567",
	}

	for _, number := range validNumbers {
		if !re.MatchString(number) {
			t.Errorf("Expected pattern to match %q, but it did not", number)
		}
	}

	// Invalid phone numbers should not match
	invalidNumbers := []string{
		"555-12-4567",   // Middle section too short
		"55-123-4567",   // Area code too short
		"555-123-456",   // Last section too short
		"555-123-45678", // Last section too long
		"abc-123-4567",  // Non-digits in area code
	}

	for _, number := range invalidNumbers {
		if re.MatchString(number) {
			t.Errorf("Expected pattern NOT to match %q, but it did", number)
		}
	}
}
