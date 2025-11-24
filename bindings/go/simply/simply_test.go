package simply

import (
	"testing"
)

// TestUSPhone verifies that building the US phone pattern using the simply
// builder produces the same PCRE2 string as the documented pattern.
func TestUSPhone(t *testing.T) {
	// Build: ^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$
	phone := Merge(
		Start(),
		Capture(Digit(3)),
		May(AnyOf("-. ")),
		Capture(Digit(3)),
		May(AnyOf("-. ")),
		Capture(Digit(4)),
		End(),
	)

	pattern := phone.ToRegex()

	// The emitter may escape '-' inside a character class, which results in "[\-. ]"
	expected := `^(\d{3})[\-. ]?(\d{3})[\-. ]?(\d{4})$`
	if pattern != expected {
		t.Fatalf("pattern mismatch: got %q, expected %q", pattern, expected)
	}
}
