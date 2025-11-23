package strling

import (
	"encoding/json"
	"fmt"

	"github.com/thecyberlocal/strling/bindings/go/core"
)

// SpecNode is the interface for all AST nodes from the JSON spec.
type SpecNode interface {
	ToCore() (core.Node, error)
}

// NodeWrapper handles polymorphic JSON unmarshalling.
type NodeWrapper struct {
	Node SpecNode
}

func (w *NodeWrapper) UnmarshalJSON(data []byte) error {
	var base struct {
		Type string `json:"type"`
	}
	if err := json.Unmarshal(data, &base); err != nil {
		return err
	}

	switch base.Type {
	case "Literal":
		var n Literal
		if err := json.Unmarshal(data, &n); err != nil {
			return err
		}
		w.Node = &n
	case "Sequence":
		var n Sequence
		if err := json.Unmarshal(data, &n); err != nil {
			return err
		}
		w.Node = &n
	case "Alternation":
		var n Alternation
		if err := json.Unmarshal(data, &n); err != nil {
			return err
		}
		w.Node = &n
	case "Group":
		var n Group
		if err := json.Unmarshal(data, &n); err != nil {
			return err
		}
		w.Node = &n
	case "Quantifier":
		var n Quantifier
		if err := json.Unmarshal(data, &n); err != nil {
			return err
		}
		w.Node = &n
	case "CharacterClass":
		var n CharacterClass
		if err := json.Unmarshal(data, &n); err != nil {
			return err
		}
		w.Node = &n
	case "Anchor":
		var n Anchor
		if err := json.Unmarshal(data, &n); err != nil {
			return err
		}
		w.Node = &n
	case "Dot":
		var n Dot
		if err := json.Unmarshal(data, &n); err != nil {
			return err
		}
		w.Node = &n
	case "Range":
		var n Range
		if err := json.Unmarshal(data, &n); err != nil {
			return err
		}
		w.Node = &n
	case "Backreference":
		var n Backreference
		if err := json.Unmarshal(data, &n); err != nil {
			return err
		}
		w.Node = &n
	case "Lookahead":
		var n Lookaround
		n.Dir = "Ahead"
		n.Neg = false
		if err := json.Unmarshal(data, &n); err != nil {
			return err
		}
		w.Node = &n
	case "Lookbehind":
		var n Lookaround
		n.Dir = "Behind"
		n.Neg = false
		if err := json.Unmarshal(data, &n); err != nil {
			return err
		}
		w.Node = &n
	case "NegativeLookahead":
		var n Lookaround
		n.Dir = "Ahead"
		n.Neg = true
		if err := json.Unmarshal(data, &n); err != nil {
			return err
		}
		w.Node = &n
	case "NegativeLookbehind":
		var n Lookaround
		n.Dir = "Behind"
		n.Neg = true
		if err := json.Unmarshal(data, &n); err != nil {
			return err
		}
		w.Node = &n
	case "Escape":
		var n Escape
		if err := json.Unmarshal(data, &n); err != nil {
			return err
		}
		w.Node = &n
	case "UnicodeProperty":
		var n UnicodeProperty
		if err := json.Unmarshal(data, &n); err != nil {
			return err
		}
		w.Node = &n
	default:
		return fmt.Errorf("unknown node type: %s", base.Type)
	}
	return nil
}

// Literal
type Literal struct {
	Value string `json:"value"`
}

func (n *Literal) ToCore() (core.Node, error) {
	return core.Lit{Value: n.Value}, nil
}

func (n *Literal) ToClassItem() (core.ClassItem, error) {
	if len(n.Value) != 1 {
		return nil, fmt.Errorf("literal in character class must be single char, got '%s'", n.Value)
	}
	return core.ClassLiteral{Ch: n.Value}, nil
}

// Sequence
type Sequence struct {
	Parts []NodeWrapper `json:"parts"`
}

func (n *Sequence) ToCore() (core.Node, error) {
	parts := make([]core.Node, len(n.Parts))
	for i, el := range n.Parts {
		c, err := el.Node.ToCore()
		if err != nil {
			return nil, err
		}
		parts[i] = c
	}
	return core.Seq{Parts: parts}, nil
}

// Alternation
type Alternation struct {
	Alternatives []NodeWrapper `json:"alternatives"`
}

func (n *Alternation) ToCore() (core.Node, error) {
	branches := make([]core.Node, len(n.Alternatives))
	for i, opt := range n.Alternatives {
		c, err := opt.Node.ToCore()
		if err != nil {
			return nil, err
		}
		branches[i] = c
	}
	return core.Alt{Branches: branches}, nil
}

// Group
type Group struct {
	Capturing bool        `json:"capturing"`
	Body      NodeWrapper `json:"body"`
	Name      *string     `json:"name"`
	Atomic    *bool       `json:"atomic"`
}

func (n *Group) ToCore() (core.Node, error) {
	body, err := n.Body.Node.ToCore()
	if err != nil {
		return nil, err
	}
	
	var atomic *bool
	if n.Atomic != nil && *n.Atomic {
		atomic = n.Atomic
	}

	return core.Group{
		Capturing: n.Capturing,
		Body:      body,
		Name:      n.Name,
		Atomic:    atomic,
	}, nil
}

// Quantifier
type Quantifier struct {
	Target     NodeWrapper `json:"target"`
	Min        int         `json:"min"`
	Max        interface{} `json:"max"` // int or string "Inf"
	Greedy     bool        `json:"greedy"`
	Lazy       bool        `json:"lazy"`
	Possessive bool        `json:"possessive"`
}

func (n *Quantifier) ToCore() (core.Node, error) {
	child, err := n.Target.Node.ToCore()
	if err != nil {
		return nil, err
	}

	mode := "Greedy"
	if n.Lazy {
		mode = "Lazy"
	} else if n.Possessive {
		mode = "Possessive"
	}

	var max interface{}
	if n.Max == nil {
		max = "Inf"
	} else {
		max = n.Max
	}

	return core.Quant{
		Child: child,
		Min:   n.Min,
		Max:   max,
		Mode:  mode,
	}, nil
}

// CharacterClass
type CharacterClass struct {
	Negated bool          `json:"negated"`
	Members []NodeWrapper `json:"members"`
}

func (n *CharacterClass) ToCore() (core.Node, error) {
	items := make([]core.ClassItem, len(n.Members))
	for i, m := range n.Members {
		if lit, ok := m.Node.(*Literal); ok {
			item, err := lit.ToClassItem()
			if err != nil {
				return nil, err
			}
			items[i] = item
		} else if rng, ok := m.Node.(*Range); ok {
			item, err := rng.ToClassItem()
			if err != nil {
				return nil, err
			}
			items[i] = item
		} else if esc, ok := m.Node.(*Escape); ok {
			item, err := esc.ToClassItem()
			if err != nil {
				return nil, err
			}
			items[i] = item
		} else if prop, ok := m.Node.(*UnicodeProperty); ok {
			item, err := prop.ToClassItem()
			if err != nil {
				return nil, err
			}
			items[i] = item
		} else {
			return nil, fmt.Errorf("unsupported node type in character class: %T", m.Node)
		}
	}
	return core.CharClass{
		Negated: n.Negated,
		Items:   items,
	}, nil
}

// Range
type Range struct {
	From string `json:"from"`
	To   string `json:"to"`
}

func (n *Range) ToCore() (core.Node, error) {
	return nil, fmt.Errorf("Range cannot be used as a standalone core.Node")
}

func (n *Range) ToClassItem() (core.ClassItem, error) {
	return core.ClassRange{
		FromCh: n.From,
		ToCh:   n.To,
	}, nil
}

// Anchor
type Anchor struct {
	At string `json:"at"`
}

func (n *Anchor) ToCore() (core.Node, error) {
	at := n.At
	if at == "NonWordBoundary" {
		at = "NotWordBoundary"
	}
	return core.Anchor{At: at}, nil
}

// Dot
type Dot struct{}

func (n *Dot) ToCore() (core.Node, error) {
	return core.Dot{}, nil
}

// Backreference
type Backreference struct {
	Index *int    `json:"index"`
	Name  *string `json:"name"`
}

func (n *Backreference) ToCore() (core.Node, error) {
	return core.Backref{
		ByIndex: n.Index,
		ByName:  n.Name,
	}, nil
}

// Lookaround
type Lookaround struct {
	Dir  string      // "Ahead" or "Behind"
	Neg  bool        // true or false
	Body NodeWrapper `json:"body"`
}

func (n *Lookaround) ToCore() (core.Node, error) {
	body, err := n.Body.Node.ToCore()
	if err != nil {
		return nil, err
	}
	return core.Look{
		Dir:  n.Dir,
		Neg:  n.Neg,
		Body: body,
	}, nil
}

// Escape (for CharacterClass)
type Escape struct {
	Kind string `json:"kind"` // digit, word, space, etc.
}

func (n *Escape) ToCore() (core.Node, error) {
	return nil, fmt.Errorf("Escape cannot be used as a standalone core.Node")
}

func (n *Escape) ToClassItem() (core.ClassItem, error) {
	var t string
	switch n.Kind {
	case "digit":
		t = "d"
	case "not-digit":
		t = "D"
	case "word":
		t = "w"
	case "not-word":
		t = "W"
	case "space":
		t = "s"
	case "not-space":
		t = "S"
	default:
		return nil, fmt.Errorf("unknown escape kind: %s", n.Kind)
	}
	return core.ClassEscape{
		Type: t,
	}, nil
}

// UnicodeProperty
type UnicodeProperty struct {
	Value   string `json:"value"`
	Negated bool   `json:"negated"`
}

func (n *UnicodeProperty) ToCore() (core.Node, error) {
	return nil, fmt.Errorf("UnicodeProperty cannot be used as a standalone core.Node")
}

func (n *UnicodeProperty) ToClassItem() (core.ClassItem, error) {
	t := "p"
	if n.Negated {
		t = "P"
	}
	prop := n.Value
	return core.ClassEscape{
		Type:     t,
		Property: &prop,
	}, nil
}
