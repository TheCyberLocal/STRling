package simply

import (
	"github.com/thecyberlocal/strling/bindings/go/core"
	"github.com/thecyberlocal/strling/bindings/go/emitters"
)

// Pattern is a wrapper around the core AST node to provide a fluent/functional API.
// It hides the complexity of the AST from the user.
type Pattern struct {
	node core.Node
}

// ToRegex compiles the pattern to a regex string.
// It uses the core compiler and emitter to generate the final string.
func (p Pattern) ToRegex() string {
	compiler := core.NewCompiler()
	ir := compiler.Compile(p.node)
	return emitters.Emit(ir, nil)
}

// Start matches the start of the string/line (^).
func Start() Pattern {
	return Pattern{node: core.Anchor{At: "Start"}}
}

// End matches the end of the string/line ($).
func End() Pattern {
	return Pattern{node: core.Anchor{At: "End"}}
}

// Digit matches exactly n digits.
// If n <= 0, it defaults to 1.
func Digit(n int) Pattern {
	if n <= 0 {
		n = 1
	}
	// Create a digit class item (\d)
	digit := core.ClassEscape{Type: "d"}
	classNode := core.CharClass{
		Negated: false,
		Items:   []core.ClassItem{digit},
	}
	
	if n == 1 {
		return Pattern{node: classNode}
	}
	
	return Pattern{node: core.Quant{
		Child: classNode,
		Min:   n,
		Max:   n,
		Mode:  "Greedy",
	}}
}

// AnyOf matches any single character from the provided string.
// Example: AnyOf("abc") matches [abc].
func AnyOf(chars string) Pattern {
	items := make([]core.ClassItem, 0, len(chars))
	for _, c := range chars {
		items = append(items, core.ClassLiteral{Ch: string(c)})
	}
	return Pattern{node: core.CharClass{
		Negated: false,
		Items:   items,
	}}
}

// Merge combines multiple patterns into a sequence.
func Merge(parts ...Pattern) Pattern {
	if len(parts) == 0 {
		return Pattern{node: core.Seq{Parts: []core.Node{}}}
	}
	if len(parts) == 1 {
		return parts[0]
	}
	nodes := make([]core.Node, len(parts))
	for i, p := range parts {
		nodes[i] = p.node
	}
	return Pattern{node: core.Seq{Parts: nodes}}
}

// Capture wraps a pattern in a capturing group.
func Capture(inner Pattern) Pattern {
	return Pattern{node: core.Group{
		Capturing: true,
		Body:      inner.node,
	}}
}

// May makes a pattern optional (matches 0 or 1 times).
func May(inner Pattern) Pattern {
	return Pattern{node: core.Quant{
		Child: inner.node,
		Min:   0,
		Max:   1,
		Mode:  "Greedy",
	}}
}
