package simply

import (
    "testing"

    "github.com/thecyberlocal/strling/bindings/go/core"
    "github.com/thecyberlocal/strling/bindings/go/emitters"
)

// TestUSPhone verifies that building the US phone pattern using the simply
// builder produces the same PCRE2 string as the documented pattern.
func TestUSPhone(t *testing.T) {
    // Build: ^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$
    phone := Seq(
        Start(),
        GroupCapture(Quant(Digit(), 3, 3)),
        Quant(CharClassFromLiterals("-", ".", " "), 0, 1),
        GroupCapture(Quant(Digit(), 3, 3)),
        Quant(CharClassFromLiterals("-", ".", " "), 0, 1),
        GroupCapture(Quant(Digit(), 4, 4)),
        End(),
    )

    compiler := core.NewCompiler()
    ir := compiler.Compile(phone)

    pattern := emitters.Emit(ir, nil)

    // The emitter may escape '-' inside a character class, which results in "[\-. ]"
    expected := `^(\d{3})[\-. ]?(\d{3})[\-. ]?(\d{4})$`
    if pattern != expected {
        t.Fatalf("pattern mismatch: got %q, expected %q", pattern, expected)
    }
}
