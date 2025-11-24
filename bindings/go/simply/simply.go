package simply

import (
	"github.com/thecyberlocal/strling/bindings/go/core"
	"github.com/thecyberlocal/strling/bindings/go/emitters"
)

// Pattern is a high-level wrapper around core.Node that provides a fluent API
// matching the TypeScript/Python "Gold Standard" implementation.
type Pattern struct {
	node core.Node
}

// ToRegex compiles the pattern to a PCRE2 regex string.
func (p Pattern) ToRegex() (string, error) {
	compiler := core.NewCompiler()
	ir := compiler.Compile(p.node)
	regex := emitters.Emit(ir, nil)
	return regex, nil
}

// Start matches the beginning of a line (^).
func Start() Pattern {
	return Pattern{node: core.Anchor{At: "Start"}}
}

// End matches the end of a line ($).
func End() Pattern {
	return Pattern{node: core.Anchor{At: "End"}}
}

// Lit creates a literal pattern that matches the exact string.
func Lit(s string) Pattern {
	return Pattern{node: core.Lit{Value: s}}
}

// Digit matches exactly n digits (\d{n}).
// If n is not provided or is 0, matches a single digit.
func Digit(n int) Pattern {
	digitClass := core.CharClass{
		Negated: false,
		Items:   []core.ClassItem{core.ClassEscape{Type: "d"}},
	}
	
	if n <= 0 {
		n = 1
	}
	
	if n == 1 {
		return Pattern{node: digitClass}
	}
	
	return Pattern{node: core.Quant{Child: digitClass, Min: n, Max: n, Mode: "Greedy"}}
}

// AnyOf creates a character class matching any of the provided characters.
// Similar to TypeScript's inChars function.
func AnyOf(chars string) Pattern {
	items := make([]core.ClassItem, 0, len(chars))
	for _, c := range chars {
		items = append(items, core.ClassLiteral{Ch: string(c)})
	}
	return Pattern{node: core.CharClass{Negated: false, Items: items}}
}

// Merge concatenates multiple patterns into a single sequence.
// Equivalent to TypeScript's s.merge(...patterns).
func Merge(patterns ...Pattern) Pattern {
	if len(patterns) == 0 {
		return Pattern{node: core.Seq{Parts: []core.Node{}}}
	}
	if len(patterns) == 1 {
		return patterns[0]
	}
	
	nodes := make([]core.Node, len(patterns))
	for i, p := range patterns {
		nodes[i] = p.node
	}
	return Pattern{node: core.Seq{Parts: nodes}}
}

// Capture creates a numbered capture group around the pattern.
// Equivalent to TypeScript's s.capture(...patterns).
func Capture(pattern Pattern) Pattern {
	return Pattern{node: core.Group{Capturing: true, Body: pattern.node}}
}

// May makes the pattern optional (matches 0 or 1 times, equivalent to ?).
// Equivalent to TypeScript's s.may(...patterns).
func May(pattern Pattern) Pattern {
	return Pattern{node: core.Quant{Child: pattern.node, Min: 0, Max: 1, Mode: "Greedy"}}
}
