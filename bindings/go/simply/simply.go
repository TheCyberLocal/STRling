package simply

import "github.com/thecyberlocal/strling/bindings/go/core"

// A small, focused fluent builder for common STRling constructs.
// The goal is to let users construct patterns without touching internal AST wrappers.

// Start anchor
func Start() core.Node {
    return core.Anchor{At: "Start"}
}

// End anchor
func End() core.Node {
    return core.Anchor{At: "End"}
}

// Lit creates a literal node.
func Lit(s string) core.Node {
    return core.Lit{Value: s}
}

// Digit returns a character class matching a single digit (\d).
func Digit() core.Node {
    return core.CharClass{Negated: false, Items: []core.ClassItem{core.ClassEscape{Type: "d"}}}
}

// CharClassFromLiterals creates a small character class out of literal characters.
func CharClassFromLiterals(chars ...string) core.Node {
    items := make([]core.ClassItem, 0, len(chars))
    for _, c := range chars {
        if len(c) == 1 {
            items = append(items, core.ClassLiteral{Ch: c})
        } else {
            // For strings longer than 1, treat as sequence of literals (not ideal for class)
            // but we'll fallback to adding the first char.
            items = append(items, core.ClassLiteral{Ch: string(c[0])})
        }
    }
    return core.CharClass{Negated: false, Items: items}
}

// Seq builds a sequence node from provided children.
func Seq(parts ...core.Node) core.Node {
    return core.Seq{Parts: parts}
}

// GroupCapture wraps a node into a capturing group.
func GroupCapture(body core.Node) core.Node {
    return core.Group{Capturing: true, Body: body}
}

// Quant creates a quantifier node with greedy mode.
func Quant(target core.Node, min, max int) core.Node {
    var maxVal interface{} = max
    return core.Quant{Child: target, Min: min, Max: maxVal, Mode: "Greedy"}
}
